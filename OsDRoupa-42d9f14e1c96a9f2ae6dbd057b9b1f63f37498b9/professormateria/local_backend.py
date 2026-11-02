"""Local SQLite backend used by the Reflex app when OSDROUPA_BACKEND=sqlite.

This is a development/single-instance backend. It intentionally keeps the same
JSON contract as the Xano endpoints consumed by the UI, while enforcing user
ownership and admin checks in Python.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from professormateria.demo_catalog import DEMO_BOUTIQUE_PRODUCTS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "osdroupa.sqlite3"
PASSWORD_ITERATIONS = 310_000
SESSION_DAYS = 30
RESET_MINUTES = 30
ORDER_RESERVATION_HOURS = 24
MAX_PRODUCT_PRICE = Decimal("1000000000.00")
MAX_WARDROBE_IMAGE_BYTES = 2 * 1024 * 1024
CHALLENGE_REWARDS = {
    "repeat-three": 30,
    "forgotten-piece": 40,
    "care-routine": 20,
    "plan-week": 25,
    "repair-one": 15,
    "color-repeat": 20,
    "wear-log": 20,
    "closet-review": 25,
}

SEED_PRODUCTS = [
    {
        "name": "Camisa de linho natural",
        "description": "Linho leve com caimento solto, feito para acompanhar dias de sol e camadas frescas.",
        "category": "Roupas", "price_cents": 18900, "stock": 12,
        "image": "/products/linen-shirt.svg",
    },
    {
        "name": "Calça reta de alfaiataria",
        "description": "Cintura confortável e corte reto para composições versáteis do trabalho ao fim de semana.",
        "category": "Roupas", "price_cents": 23900, "stock": 8,
        "image": "/products/tailored-trousers.svg",
    },
    {
        "name": "Vestido midi terracota",
        "description": "Silhueta fluida com bolsos discretos e tecido de toque macio.",
        "category": "Roupas", "price_cents": 27900, "stock": 6,
        "image": "/products/midi-dress.svg",
    },
    {
        "name": "Tricot leve azul-marinho",
        "description": "Malha respirável para sobreposições confortáveis durante todo o ano.",
        "category": "Roupas", "price_cents": 16900, "stock": 10,
        "image": "/products/knitwear.svg",
    },
    {
        "name": "Bolsa transversal de lona",
        "description": "Bolsa compacta em lona resistente, com alça regulável e acabamento em couro vegetal.",
        "category": "Acessórios", "price_cents": 12900, "stock": 9,
        "image": "/products/crossbody-bag.svg",
    },
    {
        "name": "Cinto essencial caramelo",
        "description": "Acessório de couro de origem rastreável que finaliza combinações com simplicidade.",
        "category": "Acessórios", "price_cents": 8900, "stock": 14,
        "image": "/products/caramel-belt.svg",
    },
    {
        "name": "Tênis urbano em lona",
        "description": "Tênis leve de lona de algodão, com solado flexível para a rotina.",
        "category": "Calçados", "price_cents": 21900, "stock": 7,
        "image": "/products/canvas-sneakers.svg",
    },
    {
        "name": "Lenço de algodão estampado",
        "description": "Lenço macio com estampa geométrica de baixo contraste para usar de vários jeitos.",
        "category": "Acessórios", "price_cents": 5900, "stock": 16,
        "image": "/products/cotton-scarf.svg",
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="seconds")


def _as_price(cents: int) -> str:
    return f"{cents / 100:.2f}"


def _price_to_cents(value: Any) -> int:
    """Parse a product price without binary-float rounding or hidden fractions."""
    try:
        price = Decimal(str(value if value is not None else "0").strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Pre\u00e7o inv\u00e1lido.") from exc
    if not price.is_finite() or price < 0 or price > MAX_PRODUCT_PRICE:
        raise ValueError("Informe um pre\u00e7o n\u00e3o negativo com at\u00e9 duas casas decimais.")
    cents = price * 100
    if cents != cents.to_integral_value():
        raise ValueError("Informe um pre\u00e7o n\u00e3o negativo com at\u00e9 duas casas decimais.")
    return int(cents)


def _wardrobe_image_upload(payload: dict[str, Any]) -> tuple[bytes | None, str]:
    """Decode and verify one small raster photo before storing it per account."""
    encoded = str(payload.get("imagem_base64") or "").strip()
    if not encoded:
        return None, ""
    max_encoded_size = ((MAX_WARDROBE_IMAGE_BYTES + 2) // 3) * 4
    if len(encoded) > max_encoded_size:
        raise ValueError("A foto deve ter no máximo 2 MB.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ValueError("O arquivo de imagem enviado é inválido.") from exc
    if not data or len(data) > MAX_WARDROBE_IMAGE_BYTES:
        raise ValueError("A foto deve ter no máximo 2 MB.")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        actual_mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        actual_mime = "image/jpeg"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        actual_mime = "image/webp"
    else:
        raise ValueError("Use uma imagem JPG, PNG ou WebP válida.")
    requested_mime = str(payload.get("imagem_mime") or "").strip().lower()
    if requested_mime and requested_mime != actual_mime:
        raise ValueError("O tipo da imagem não corresponde ao arquivo enviado.")
    return data, actual_mime


def _response(method: str, url: str, status: int, body: Any) -> httpx.Response:
    request = httpx.Request(method, url)
    content = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return httpx.Response(
        status_code=status,
        content=content,
        headers={"content-type": "application/json; charset=utf-8"},
        request=request,
    )


class LocalBackend:
    """Small transactional SQLite repository with an Xano-shaped HTTP adapter."""

    def __init__(self, db_path: str | Path | None = None):
        configured = db_path or os.environ.get("OSDROUPA_DB_PATH") or DEFAULT_DB_PATH
        self.db_path = Path(configured).expanduser()
        if not self.db_path.is_absolute():
            self.db_path = (PROJECT_ROOT / self.db_path).resolve()
        self._schema_lock = threading.Lock()
        self._initialized = False

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=15, isolation_level="DEFERRED")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    @contextmanager
    def _db(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _ensure_rate_limit_tables(db: sqlite3.Connection) -> None:
        db.execute(
            """CREATE TABLE IF NOT EXISTS outbound_rate_limits (
                bucket TEXT PRIMARY KEY,
                blocked_until REAL NOT NULL DEFAULT 0
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS outbound_rate_limit_requests (
                bucket TEXT NOT NULL,
                requested_at REAL NOT NULL
            )"""
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_outbound_rate_limit_window "
            "ON outbound_rate_limit_requests(bucket, requested_at)"
        )

    def reserve_rate_limit_slot(self, bucket: str, max_requests: int, window_seconds: float) -> float:
        """Reserve one shared request slot; return seconds to wait if full."""
        if not bucket or max_requests < 1 or window_seconds <= 0:
            raise ValueError("Configuração de limite de chamadas inválida.")
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._ensure_rate_limit_tables(db)
            db.execute("INSERT OR IGNORE INTO outbound_rate_limits(bucket) VALUES(?)", (bucket,))
            db.execute(
                "DELETE FROM outbound_rate_limit_requests WHERE bucket=? AND requested_at<=?",
                (bucket, now - window_seconds),
            )
            blocked_until = db.execute(
                "SELECT blocked_until FROM outbound_rate_limits WHERE bucket=?", (bucket,)
            ).fetchone()[0]
            if blocked_until > now:
                return blocked_until - now
            row = db.execute(
                "SELECT COUNT(*) AS n, MIN(requested_at) AS oldest "
                "FROM outbound_rate_limit_requests WHERE bucket=?",
                (bucket,),
            ).fetchone()
            if row["n"] >= max_requests:
                return max(0.05, row["oldest"] + window_seconds - now)
            db.execute(
                "INSERT INTO outbound_rate_limit_requests(bucket,requested_at) VALUES(?,?)",
                (bucket, now),
            )
        return 0.0

    def reserve_rate_limit_slots(self, limits: list[tuple[str, int, float]]) -> tuple[float, str]:
        """Reserva uma vaga em todos os baldes de forma atômica (tudo ou nada).

        Devolve (0.0, "") se reservou, ou (segundos de espera, balde que bloqueou).
        Nenhuma vaga é consumida quando algum balde recusa.
        """
        if not limits or any(not b or m < 1 or w <= 0 for b, m, w in limits):
            raise ValueError("Configuração de limite de chamadas inválida.")
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._ensure_rate_limit_tables(db)
            for bucket, max_requests, window_seconds in limits:
                db.execute("INSERT OR IGNORE INTO outbound_rate_limits(bucket) VALUES(?)", (bucket,))
                db.execute(
                    "DELETE FROM outbound_rate_limit_requests WHERE bucket=? AND requested_at<=?",
                    (bucket, now - window_seconds),
                )
                blocked_until = db.execute(
                    "SELECT blocked_until FROM outbound_rate_limits WHERE bucket=?", (bucket,)
                ).fetchone()[0]
                if blocked_until > now:
                    return blocked_until - now, bucket
                row = db.execute(
                    "SELECT COUNT(*) AS n, MIN(requested_at) AS oldest FROM outbound_rate_limit_requests WHERE bucket=?",
                    (bucket,),
                ).fetchone()
                if row["n"] >= max_requests:
                    return max(0.05, row["oldest"] + window_seconds - now), bucket
            db.executemany(
                "INSERT INTO outbound_rate_limit_requests(bucket,requested_at) VALUES(?,?)",
                [(bucket, now) for bucket, _, _ in limits],
            )
        return 0.0, ""

    def pause_rate_limit(self, bucket: str, seconds: float) -> None:
        """Share an upstream cooldown across local app processes."""
        if not bucket or seconds <= 0:
            return
        blocked_until = time.time() + seconds
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._ensure_rate_limit_tables(db)
            db.execute(
                "INSERT INTO outbound_rate_limits(bucket,blocked_until) VALUES(?,?) "
                "ON CONFLICT(bucket) DO UPDATE SET blocked_until=MAX(blocked_until,excluded.blocked_until)",
                (bucket, blocked_until),
            )

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._schema_lock:
            if self._initialized:
                return
            with self._db() as db:
                db.execute("PRAGMA journal_mode = WAL")
                db.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                        phone TEXT NOT NULL DEFAULT '',
                        birth_date TEXT NOT NULL DEFAULT '',
                        pronouns TEXT NOT NULL DEFAULT '',
                        style_preference TEXT NOT NULL DEFAULT '',
                        top_size TEXT NOT NULL DEFAULT '',
                        bottom_size TEXT NOT NULL DEFAULT '',
                        shoe_size TEXT NOT NULL DEFAULT '',
                        favorite_colors TEXT NOT NULL DEFAULT '',
                        bio TEXT NOT NULL DEFAULT '',
                        password_salt TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('member','admin')),
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        expires_at TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                    CREATE TABLE IF NOT EXISTS addresses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        cep TEXT NOT NULL,
                        logradouro TEXT NOT NULL,
                        numero TEXT NOT NULL,
                        complemento TEXT NOT NULL DEFAULT '',
                        bairro TEXT NOT NULL DEFAULT '',
                        referencia TEXT NOT NULL DEFAULT '',
                        cidade TEXT NOT NULL DEFAULT '',
                        uf TEXT NOT NULL DEFAULT '',
                        is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_addresses_user ON addresses(user_id, is_default DESC, id);
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        category TEXT NOT NULL CHECK(category IN ('Roupas','Calçados','Acessórios')),
                        price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                        stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                        image_url TEXT NOT NULL DEFAULT '',
                        brand TEXT NOT NULL DEFAULT '',
                        collection TEXT NOT NULL DEFAULT '',
                        product_type TEXT NOT NULL DEFAULT '',
                        sizes TEXT NOT NULL DEFAULT '',
                        colors TEXT NOT NULL DEFAULT '',
                        material TEXT NOT NULL DEFAULT '',
                        fit TEXT NOT NULL DEFAULT '',
                        made_to_order INTEGER NOT NULL DEFAULT 0 CHECK(made_to_order IN (0,1)),
                        demonstration INTEGER NOT NULL DEFAULT 1 CHECK(demonstration IN (0,1)),
                        active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS wardrobe_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        local_key TEXT NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'No armário',
                        color TEXT NOT NULL DEFAULT '',
                        season TEXT NOT NULL DEFAULT '',
                        size TEXT NOT NULL DEFAULT '',
                        brand TEXT NOT NULL DEFAULT '',
                        image_url TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        UNIQUE(user_id, local_key)
                    );
                    CREATE INDEX IF NOT EXISTS idx_wardrobe_user ON wardrobe_items(user_id, id DESC);
                    CREATE TABLE IF NOT EXISTS looks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        local_key TEXT NOT NULL,
                        name TEXT NOT NULL,
                        occasion TEXT NOT NULL,
                        planned_date TEXT,
                        garment_keys TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(user_id, local_key)
                    );
                    CREATE INDEX IF NOT EXISTS idx_looks_user_date ON looks(user_id, planned_date, id DESC);
                    CREATE TABLE IF NOT EXISTS challenge_completions (
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        challenge_id TEXT NOT NULL,
                        completed_at TEXT NOT NULL,
                        PRIMARY KEY(user_id, challenge_id)
                    );
                    CREATE TABLE IF NOT EXISTS garment_wear_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        garment_id INTEGER NOT NULL REFERENCES wardrobe_items(id) ON DELETE CASCADE,
                        occasion TEXT NOT NULL DEFAULT '',
                        worn_on TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_garment_wear_user_date ON garment_wear_events(user_id,worn_on DESC,id DESC);
                    CREATE TABLE IF NOT EXISTS packing_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        destination TEXT NOT NULL,
                        start_date TEXT NOT NULL DEFAULT '',
                        end_date TEXT NOT NULL DEFAULT '',
                        occasion TEXT NOT NULL DEFAULT '',
                        garment_ids TEXT NOT NULL DEFAULT '[]',
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_packing_user ON packing_plans(user_id,id DESC);
                    CREATE TABLE IF NOT EXISTS tailoring_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        service_type TEXT NOT NULL,
                        garment_name TEXT NOT NULL,
                        notes TEXT NOT NULL DEFAULT '',
                        preferred_date TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'Recebido',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_tailoring_user ON tailoring_requests(user_id,id DESC);
                    CREATE TABLE IF NOT EXISTS testimonials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        display_name TEXT NOT NULL,
                        body TEXT NOT NULL,
                        anonymous INTEGER NOT NULL DEFAULT 0 CHECK(anonymous IN (0,1)),
                        consented INTEGER NOT NULL DEFAULT 0 CHECK(consented IN (0,1)),
                        status TEXT NOT NULL DEFAULT 'Pendente' CHECK(status IN ('Pendente','Publicado','Recusado')),
                        created_at TEXT NOT NULL,
                        moderated_at TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_testimonials_status ON testimonials(status,id DESC);
                    CREATE TABLE IF NOT EXISTS inspirations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        local_key TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        occasion TEXT NOT NULL,
                        weather_category TEXT NOT NULL DEFAULT '',
                        region TEXT NOT NULL DEFAULT '',
                        season TEXT NOT NULL DEFAULT '',
                        palette TEXT NOT NULL DEFAULT '',
                        fabrics TEXT NOT NULL DEFAULT '',
                        rationale TEXT NOT NULL DEFAULT '',
                        score TEXT NOT NULL DEFAULT '',
                        pieces_json TEXT NOT NULL DEFAULT '[]',
                        image_path TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'Privado' CHECK(status IN ('Privado','Pendente','Publicado','Recusado')),
                        created_at TEXT NOT NULL,
                        moderated_at TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_inspirations_feed ON inspirations(status,id DESC);
                    CREATE INDEX IF NOT EXISTS idx_inspirations_user ON inspirations(user_id,id DESC);
                    CREATE TABLE IF NOT EXISTS look_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        look_name TEXT NOT NULL DEFAULT '',
                        garment_keys TEXT NOT NULL DEFAULT '[]',
                        rating INTEGER NOT NULL CHECK(rating IN (-1, 1)),
                        reason TEXT NOT NULL DEFAULT '',
                        occasion TEXT NOT NULL DEFAULT '',
                        weather TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_look_feedback_user ON look_feedback(user_id,id DESC);
                    CREATE TABLE IF NOT EXISTS inspiration_saves (
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        inspiration_id INTEGER NOT NULL REFERENCES inspirations(id) ON DELETE CASCADE,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, inspiration_id)
                    );
                    CREATE TABLE IF NOT EXISTS privacy_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        request_type TEXT NOT NULL,
                        details TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'Recebida',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_privacy_requests_user ON privacy_requests(user_id,id DESC);
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        address_id INTEGER NOT NULL REFERENCES addresses(id),
                        total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
                        status TEXT NOT NULL DEFAULT 'Aguardando confirmação',
                        payment_status TEXT NOT NULL DEFAULT 'Sem pagamento demonstrativo',
                        paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0,1)),
                        idempotency_key TEXT NOT NULL,
                        reservation_expires_at TEXT NOT NULL,
                        stock_reserved INTEGER NOT NULL DEFAULT 1 CHECK(stock_reserved IN (0,1)),
                        gateway TEXT NOT NULL DEFAULT 'demo',
                        gateway_order_id TEXT,
                        checkout_url TEXT,
                        checkout_fingerprint TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(user_id, idempotency_key)
                    );
                    CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, id DESC);
                    CREATE INDEX IF NOT EXISTS idx_orders_expiry ON orders(stock_reserved, reservation_expires_at);
                    CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                        product_id INTEGER NOT NULL REFERENCES products(id),
                        product_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL CHECK(quantity > 0),
                        unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents >= 0),
                        subtotal_cents INTEGER NOT NULL CHECK(subtotal_cents >= 0)
                    );
                    CREATE TABLE IF NOT EXISTS device_pairings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        identifier TEXT NOT NULL,
                        code_hash TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_pairings_user ON device_pairings(user_id, id DESC);
                    CREATE TABLE IF NOT EXISTS devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        pairing_id INTEGER NOT NULL UNIQUE REFERENCES device_pairings(id),
                        name TEXT NOT NULL,
                        identifier TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'online',
                        last_seen TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS device_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                        kind TEXT NOT NULL,
                        value TEXT NOT NULL,
                        unit TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        token_hash TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        expires_at TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_reset_user ON password_reset_tokens(user_id);
                    CREATE TABLE IF NOT EXISTS payment_webhook_events (
                        event_id TEXT PRIMARY KEY,
                        gateway_order_id TEXT NOT NULL,
                        processed_at TEXT NOT NULL
                    );
                    PRAGMA user_version = 1;
                    """
                )
                # Additive, idempotent migrations for existing local databases.
                user_columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
                for column, declaration in (
                    ("birth_date", "TEXT NOT NULL DEFAULT ''"),
                    ("pronouns", "TEXT NOT NULL DEFAULT ''"),
                    ("style_preference", "TEXT NOT NULL DEFAULT ''"),
                    ("top_size", "TEXT NOT NULL DEFAULT ''"),
                    ("bottom_size", "TEXT NOT NULL DEFAULT ''"),
                    ("shoe_size", "TEXT NOT NULL DEFAULT ''"),
                    ("favorite_colors", "TEXT NOT NULL DEFAULT ''"),
                    ("bio", "TEXT NOT NULL DEFAULT ''"),
                    ("ai_personalization", "INTEGER NOT NULL DEFAULT 1"),
                ):
                    if column not in user_columns:
                        db.execute(f"ALTER TABLE users ADD COLUMN {column} {declaration}")
                wardrobe_columns = {row[1] for row in db.execute("PRAGMA table_info(wardrobe_items)")}
                if "purchase_price_cents" not in wardrobe_columns:
                    db.execute("ALTER TABLE wardrobe_items ADD COLUMN purchase_price_cents INTEGER")
                if "image_data" not in wardrobe_columns:
                    db.execute("ALTER TABLE wardrobe_items ADD COLUMN image_data BLOB")
                if "image_mime" not in wardrobe_columns:
                    db.execute("ALTER TABLE wardrobe_items ADD COLUMN image_mime TEXT NOT NULL DEFAULT ''")
                order_columns = {row[1] for row in db.execute("PRAGMA table_info(orders)")}
                for column, declaration in (
                    ("gateway", "TEXT NOT NULL DEFAULT 'demo'"),
                    ("gateway_order_id", "TEXT"),
                    ("checkout_url", "TEXT"),
                    ("checkout_fingerprint", "TEXT NOT NULL DEFAULT ''"),
                ):
                    if column not in order_columns:
                        db.execute(f"ALTER TABLE orders ADD COLUMN {column} {declaration}")
                db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_gateway_order ON orders(gateway,gateway_order_id) WHERE gateway_order_id IS NOT NULL")
                product_columns = {row[1] for row in db.execute("PRAGMA table_info(products)")}
                for column in ("brand", "collection", "product_type", "sizes", "colors", "material", "fit"):
                    if column not in product_columns:
                        db.execute(f"ALTER TABLE products ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
                count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
                if count == 0:
                    now = _stamp()
                    db.executemany(
                        """INSERT INTO products
                        (name,description,category,price_cents,stock,image_url,made_to_order,demonstration,active,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,0,1,1,?,?)""",
                        [
                            (p["name"], p["description"], p["category"], p["price_cents"], p["stock"], p["image"], now, now)
                            for p in SEED_PRODUCTS
                        ],
                    )
                # Add fictional boutiques to existing databases without replacing products.
                for product in DEMO_BOUTIQUE_PRODUCTS:
                    exists = db.execute("SELECT 1 FROM products WHERE name=? LIMIT 1", (product["name"],)).fetchone()
                    if exists:
                        continue
                    now = _stamp()
                    db.execute(
                        """INSERT INTO products
                        (name,description,category,price_cents,stock,image_url,brand,collection,product_type,sizes,colors,material,fit,
                         made_to_order,demonstration,active,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,1,1,?,?)""",
                        (
                            product["name"], product["description"], product["category"], product["price_cents"],
                            product["stock"], product["image"], product["brand"], product["collection"],
                            product["product_type"], product["sizes"], product["colors"], product["material"],
                            product["fit"], now, now,
                        ),
                    )
            self._initialized = True

    @staticmethod
    def _user_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "name": row["name"], "email": row["email"],
            "role": row["role"], "account_id": row["id"], "created_at": row["created_at"],
        }

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
        return salt.hex(), digest.hex()

    @staticmethod
    def _verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
        try:
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except ValueError:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _issue_session(self, db: sqlite3.Connection, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",
            (self._token_hash(token), user_id, _stamp(_now() + timedelta(days=SESSION_DAYS)), _stamp()),
        )
        return token

    def _user_for_token(self, db: sqlite3.Connection, headers: dict[str, str] | None) -> sqlite3.Row | None:
        headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        auth = headers.get("authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            return None
        row = db.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>?""",
            (self._token_hash(token), _stamp()),
        ).fetchone()
        return row

    def _require_user(self, db: sqlite3.Connection, headers: dict[str, str] | None) -> sqlite3.Row:
        user = self._user_for_token(db, headers)
        if user is None:
            raise PermissionError("Sessão inválida ou expirada.")
        return user

    def _require_admin(self, db: sqlite3.Connection, headers: dict[str, str] | None) -> sqlite3.Row:
        user = self._require_user(db, headers)
        if user["role"] != "admin":
            raise PermissionError("Esta área exige uma conta administradora.")
        return user

    @staticmethod
    def _address_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "logradouro": row["logradouro"], "numero": row["numero"],
            "complemento": row["complemento"], "bairro": row["bairro"],
            "referencia": row["referencia"], "padrao": bool(row["is_default"]),
            "_cep": {"cep": row["cep"], "cidade": row["cidade"], "uf": row["uf"]},
        }

    @staticmethod
    def _product_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "Nome": row["name"], "Descricao": row["description"],
            "Categoria": row["category"], "Preco": _as_price(row["price_cents"]),
            "Qtd_Disp": row["stock"], "Url_Imagem": row["image_url"],
            "Marca": row["brand"], "Colecao": row["collection"], "Tipo": row["product_type"],
            "Tamanhos": row["sizes"], "Cores": row["colors"], "Material": row["material"], "Caimento": row["fit"],
            "Precisa_Produzir": bool(row["made_to_order"]),
            "demonstracao": bool(row["demonstration"]), "active": bool(row["active"]),
            "created_at": row["created_at"],
        }

    def _release_expired_reservations(self, db: sqlite3.Connection) -> None:
        expired = db.execute(
            "SELECT id FROM orders WHERE stock_reserved=1 AND status IN ('Aguardando confirma\u00e7\u00e3o','Aguardando pagamento') AND reservation_expires_at<=?",
            (_stamp(),),
        ).fetchall()
        for row in expired:
            order_id = row["id"]
            items = db.execute("SELECT product_id,quantity FROM order_items WHERE order_id=?", (order_id,)).fetchall()
            for item in items:
                db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["quantity"], item["product_id"]))
            db.execute(
                "UPDATE orders SET stock_reserved=0,status='Expirado',updated_at=? WHERE id=?",
                (_stamp(), order_id),
            )

    def _register(self, db: sqlite3.Connection, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        name = str(payload.get("nome") or payload.get("name") or "").strip()
        email = str(payload.get("email") or "").strip().casefold()
        phone = str(payload.get("celular") or payload.get("phone") or "").strip()
        password = str(payload.get("senha") or payload.get("password") or "")
        if payload.get("aceitou_termos") is not True:
            return {"message": "É necessário aceitar os termos para criar a conta."}, 400
        if len(name.split()) < 2 or "@" not in email or len(password) < 8 or not phone:
            return {"message": "Confira nome, e-mail, celular e senha para criar sua conta."}, 400
        if not (any(c.isupper() for c in password) and any(c.isdigit() for c in password) and any(not c.isalnum() for c in password)):
            return {"message": "A senha precisa conter letra maiúscula, número e caractere especial."}, 400
        admin_email = os.environ.get("OSDROUPA_ADMIN_EMAIL", "").strip().casefold()
        role = "admin" if admin_email and hmac.compare_digest(email, admin_email) else "member"
        salt_hex, digest_hex = self._hash_password(password)
        now = _stamp()
        try:
            cursor = db.execute(
                """INSERT INTO users(name,email,phone,password_salt,password_hash,role,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                (name, email, phone, salt_hex, digest_hex, role, now),
            )
        except sqlite3.IntegrityError:
            return {"message": "Não foi possível criar a conta com esses dados."}, 409
        user_id = int(cursor.lastrowid)
        token = self._issue_session(db, user_id)
        user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return {"authToken": token, "user": self._user_dict(user)}, 200

    def _login(self, db: sqlite3.Connection, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        email = str(payload.get("email") or "").strip().casefold()
        password = str(payload.get("password") or "")
        row = db.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        valid = row is not None and self._verify_password(password, row["password_salt"], row["password_hash"])
        if not valid:
            # Run a fixed-cost derivation for unknown accounts to reduce timing-based enumeration.
            self._hash_password(password or "invalid", bytes.fromhex("00112233445566778899aabbccddeeff"))
            return {"message": "E-mail ou senha inválidos."}, 401
        token = self._issue_session(db, row["id"])
        return {"authToken": token, "user": self._user_dict(row)}, 200

    @staticmethod
    def _page_rows(db: sqlite3.Connection, sql: str, params: tuple[Any, ...], query: dict[str, Any]) -> dict[str, Any]:
        try:
            page = max(1, int(query.get("page", 1)))
            per_page = min(100, max(1, int(query.get("per_page", 20))))
        except (TypeError, ValueError):
            page, per_page = 1, 20
        rows = db.execute(sql, (*params, per_page + 1, (page - 1) * per_page)).fetchall()
        has_next = len(rows) > per_page
        return {"items": [dict(row) for row in rows[:per_page]], "nextPage": page + 1 if has_next else None}

    def _order_detail(self, db: sqlite3.Connection, order_id: int) -> dict[str, Any]:
        order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        items = db.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
        if order is None:
            raise LookupError("Pedido não encontrado.")
        return {
            "pedido": {
                "id": order["id"], "Total": _as_price(order["total_cents"]),
                "status": order["status"], "pagamento_status": order["payment_status"],
                "created_at": order["created_at"], "checkout_url": order["checkout_url"],
            },
            "pagamento": {"status_gateway": order["payment_status"], "pago_confirmado": bool(order["paid"])},
            "checkout_url": order["checkout_url"],
            "provedor": "Mercado Pago" if order["gateway"] == "mercadopago" else "Sem cobrança",
            "itens": [
                {"produto_id": item["product_id"], "produto": {"Nome": item["product_name"]},
                 "Qtd": item["quantity"], "Subtotal": _as_price(item["subtotal_cents"])}
                for item in items
            ],
        }

    def _create_demo_order(self, db: sqlite3.Connection, user: sqlite3.Row, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        key = str(payload.get("chave_idempotencia") or "").strip()
        try:
            address_id = int(payload.get("endereco_id"))
        except (TypeError, ValueError):
            return {"message": "Selecione um endereço válido."}, 400
        raw_items = payload.get("itens")
        if not key or len(key) > 160 or not isinstance(raw_items, list) or not raw_items:
            return {"message": "A sacola ou a chave da tentativa é inválida."}, 400
        db.execute("BEGIN IMMEDIATE")
        self._release_expired_reservations(db)
        existing = db.execute(
            "SELECT id FROM orders WHERE user_id=? AND idempotency_key=?",
            (user["id"], key),
        ).fetchone()
        if existing:
            return self._order_detail(db, existing["id"]), 200
        address = db.execute("SELECT id FROM addresses WHERE id=? AND user_id=?", (address_id, user["id"])).fetchone()
        if address is None:
            return {"message": "O endereço não pertence a esta conta."}, 403
        normalized: dict[int, int] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                return {"message": "Item de pedido inválido."}, 400
            try:
                product_id = int(item.get("produto_id"))
                quantity = int(item.get("qtd"))
            except (TypeError, ValueError):
                return {"message": "Produto ou quantidade inválida."}, 400
            if quantity < 1 or quantity > 99:
                return {"message": "A quantidade precisa estar entre 1 e 99."}, 400
            normalized[product_id] = normalized.get(product_id, 0) + quantity
        product_rows = []
        total_cents = 0
        for product_id, quantity in normalized.items():
            product = db.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
            if product is None:
                return {"message": "Um produto não está mais disponível."}, 409
            if not product["demonstration"]:
                return {"message": "O checkout local aceita somente produtos demonstrativos."}, 409
            product_rows.append((product, quantity))
            total_cents += product["price_cents"] * quantity
        now = _stamp()
        expires = _stamp(_now() + timedelta(hours=ORDER_RESERVATION_HOURS))
        cursor = db.execute(
            """INSERT INTO orders(user_id,address_id,total_cents,status,payment_status,paid,idempotency_key,
            reservation_expires_at,stock_reserved,created_at,updated_at)
            VALUES(?,?,?,'Aguardando confirmação','Sem pagamento demonstrativo',0,?, ?,1,?,?)""",
            (user["id"], address_id, total_cents, key, expires, now, now),
        )
        order_id = int(cursor.lastrowid)
        for product, quantity in product_rows:
            db.execute("UPDATE products SET stock=stock-?,updated_at=? WHERE id=?", (quantity, now, product["id"]))
            db.execute(
                """INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents,subtotal_cents)
                VALUES(?,?,?,?,?,?)""",
                (order_id, product["id"], product["name"], quantity, product["price_cents"], product["price_cents"] * quantity),
            )
        return self._order_detail(db, order_id), 201

    def _create_mercadopago_order(self, db: sqlite3.Connection, user: sqlite3.Row, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
        if not access_token:
            return {"message": "Checkout Mercado Pago indisponível. Configure MERCADOPAGO_ACCESS_TOKEN; nenhum pedido foi cobrado."}, 503
        key = str(payload.get("chave_idempotencia") or "").strip()
        try:
            address_id = int(payload.get("endereco_id"))
        except (TypeError, ValueError):
            return {"message": "Selecione um endereço válido."}, 400
        raw_items = payload.get("itens")
        if not key or len(key) > 128 or not isinstance(raw_items, list) or not raw_items:
            return {"message": "A sacola ou a chave de idempotência é inválida."}, 400
        db.execute("BEGIN IMMEDIATE")
        self._release_expired_reservations(db)
        address = db.execute("SELECT id FROM addresses WHERE id=? AND user_id=?", (address_id, user["id"])).fetchone()
        if address is None:
            return {"message": "O endereço não pertence a esta conta."}, 403
        normalized: dict[int, int] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                return {"message": "Item de pedido inválido."}, 400
            try:
                product_id, quantity = int(item.get("produto_id")), int(item.get("qtd"))
            except (TypeError, ValueError):
                return {"message": "Produto ou quantidade inválida."}, 400
            if quantity < 1 or quantity > 99:
                return {"message": "A quantidade precisa estar entre 1 e 99."}, 400
            normalized[product_id] = normalized.get(product_id, 0) + quantity
        product_rows: list[tuple[sqlite3.Row, int]] = []
        total_cents = 0
        for product_id, quantity in sorted(normalized.items()):
            product = db.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
            if product is None:
                return {"message": "Um produto não está mais disponível."}, 409
            if product["demonstration"]:
                return {"message": "Produtos demonstrativos não podem gerar cobrança."}, 409
            if quantity > product["stock"]:
                return {"message": f"Estoque insuficiente para {product['name']}."}, 409
            product_rows.append((product, quantity))
            total_cents += product["price_cents"] * quantity
        fingerprint_data = {"address_id": address_id, "items": [[p["id"], q] for p, q in product_rows]}
        fingerprint = hashlib.sha256(json.dumps(fingerprint_data, sort_keys=True).encode("utf-8")).hexdigest()
        existing = db.execute("SELECT * FROM orders WHERE user_id=? AND idempotency_key=?", (user["id"], key)).fetchone()
        if existing:
            if existing["checkout_fingerprint"] and existing["checkout_fingerprint"] != fingerprint:
                return {"message": "Esta chave de tentativa já foi usada com outro endereço ou itens."}, 409
            if existing["gateway"] != "mercadopago":
                return {"message": "A tentativa existente pertence a outro tipo de pedido."}, 409
            if existing["checkout_url"]:
                result = self._order_detail(db, existing["id"])
                result["cobranca"] = {"id": existing["gateway_order_id"], "checkout_url": existing["checkout_url"], "provedor": "Mercado Pago"}
                return result, 200
            if existing["status"] not in {"Aguardando pagamento"}:
                return {"message": "Esta tentativa expirou. Atualize a sacola para iniciar outra."}, 409
            order_id = int(existing["id"])
        else:
            for product, quantity in product_rows:
                if quantity > product["stock"]:
                    return {"message": f"Estoque insuficiente para {product['name']}."}, 409
            now = _stamp()
            expires = _stamp(_now() + timedelta(hours=ORDER_RESERVATION_HOURS))
            cursor = db.execute(
                """INSERT INTO orders(user_id,address_id,total_cents,status,payment_status,paid,idempotency_key,
                reservation_expires_at,stock_reserved,gateway,checkout_fingerprint,created_at,updated_at)
                VALUES(?,?,?,'Aguardando pagamento','Mercado Pago: aguardando',0,?,?,1,'mercadopago',?,?,?)""",
                (user["id"], address_id, total_cents, key, expires, fingerprint, now, now),
            )
            order_id = int(cursor.lastrowid)
            for product, quantity in product_rows:
                db.execute("UPDATE products SET stock=stock-?,updated_at=? WHERE id=?", (quantity, now, product["id"]))
                db.execute(
                    """INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents,subtotal_cents)
                    VALUES(?,?,?,?,?,?)""",
                    (order_id, product["id"], product["name"], quantity, product["price_cents"], product["price_cents"] * quantity),
                )
        db.commit()

        public_url = os.environ.get("OSDROUPA_PUBLIC_URL", "").strip().rstrip("/")
        body: dict[str, Any] = {
            "type": "online",
            "processing_mode": "manual",
            "total_amount": _as_price(total_cents),
            "external_reference": f"osd-order-{order_id}",
            "description": f"Pedido OSDROUPA #{order_id}",
            "payer": {"email": user["email"]},
            "items": [
                {"title": product["name"], "unit_price": _as_price(product["price_cents"]), "quantity": quantity}
                for product, quantity in product_rows
            ],
        }
        if public_url.startswith("https://") or public_url.startswith("http://localhost") or public_url.startswith("http://127.0.0.1"):
            order_url = f"{public_url}/pedido?id={order_id}"
            body["config"] = {"online": {"success_url": order_url, "pending_url": order_url, "failure_url": order_url}}
        try:
            gateway_idempotency_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"osdroupa:{user['id']}:{key}"))
            with httpx.Client(timeout=18.0) as client:
                response = client.post(
                    "https://api.mercadopago.com/v1/orders",
                    headers={"Authorization": f"Bearer {access_token}", "X-Idempotency-Key": gateway_idempotency_key, "Content-Type": "application/json"},
                    json=body,
                )
            if response.status_code >= 400:
                return {"message": "O Mercado Pago recusou a criação do checkout. Revise as credenciais e a configuração do vendedor; a reserva de estoque continua temporária."}, 502
            gateway_order = response.json()
        except (httpx.HTTPError, ValueError):
            return {"message": "Não foi possível confirmar a criação no Mercado Pago. A chave idempotente foi preservada para repetir sem duplicar a tentativa."}, 502
        gateway_id = str(gateway_order.get("id") or "")
        checkout_url = str(gateway_order.get("checkout_url") or "")
        parsed_checkout = urlsplit(checkout_url)
        checkout_host = (parsed_checkout.hostname or "").lower()
        if not gateway_id or parsed_checkout.scheme != "https" or not (checkout_host == "mercadopago.com.br" or checkout_host.endswith(".mercadopago.com.br")):
            return {"message": "O Mercado Pago não retornou um endereço de checkout válido. Nenhum pagamento foi confirmado."}, 502
        db.execute(
            "UPDATE orders SET gateway_order_id=?,checkout_url=?,payment_status='Mercado Pago: aguardando',updated_at=? WHERE id=? AND user_id=?",
            (gateway_id, checkout_url, _stamp(), order_id, user["id"]),
        )
        result = self._order_detail(db, order_id)
        result["cobranca"] = {"id": gateway_id, "checkout_url": checkout_url, "provedor": "Mercado Pago"}
        return result, 201

    @staticmethod
    def _verify_mercadopago_signature(signature: str, request_id: str, data_id: str, secret: str) -> bool:
        parts = dict(
            part.strip().split("=", 1)
            for part in signature.split(",")
            if "=" in part
        )
        timestamp, received = parts.get("ts", ""), parts.get("v1", "")
        if not timestamp or not received or not data_id:
            return False
        try:
            if abs(int(time.time()) - int(timestamp)) > 300:
                return False
        except ValueError:
            return False
        manifest = f"id:{data_id};request-id:{request_id};ts:{timestamp};"
        expected = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received)

    def process_mercadopago_webhook(self, signature: str, request_id: str, data_id: str, event_id: str) -> tuple[dict[str, Any], int]:
        secret = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
        access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "").strip()
        if not secret or not access_token:
            return {"message": "Webhook Mercado Pago sem segredo ou Access Token configurado."}, 503
        if not self._verify_mercadopago_signature(signature, request_id, data_id, secret):
            return {"message": "Assinatura do webhook inválida ou expirada."}, 401
        try:
            with httpx.Client(timeout=12.0) as client:
                response = client.get(
                    f"https://api.mercadopago.com/v1/orders/{data_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            response.raise_for_status()
            gateway_order = response.json()
        except (httpx.HTTPError, ValueError):
            return {"message": "Não foi possível consultar a Order no Mercado Pago."}, 502
        gateway_id = str(gateway_order.get("id") or "")
        external_reference = str(gateway_order.get("external_reference") or "")
        if gateway_id != data_id or not external_reference.startswith("osd-order-"):
            return {"message": "A notificação não corresponde a um pedido OSDROUPA."}, 200
        try:
            order_id = int(external_reference.removeprefix("osd-order-"))
        except ValueError:
            return {"message": "Referência externa inválida."}, 200
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            duplicate = db.execute("SELECT 1 FROM payment_webhook_events WHERE event_id=?", (event_id or gateway_id,)).fetchone()
            order = db.execute("SELECT * FROM orders WHERE id=? AND gateway='mercadopago' AND gateway_order_id=?", (order_id, gateway_id)).fetchone()
            if duplicate:
                return {"ok": True, "duplicado": True}, 200
            if order is None:
                return {"ok": True, "ignorado": True}, 200
            try:
                paid_cents = _price_to_cents(gateway_order.get("total_paid_amount") or "0")
                total_cents = _price_to_cents(gateway_order.get("total_amount") or "0")
            except ValueError:
                return {"message": "Totais retornados pelo Mercado Pago inválidos."}, 502
            if total_cents != order["total_cents"]:
                return {"message": "O total consultado não corresponde ao total do pedido."}, 409
            status = str(gateway_order.get("status") or "").casefold()
            now = _stamp()
            if status == "processed" and paid_cents == order["total_cents"]:
                db.execute("UPDATE orders SET paid=1,status='Pago',payment_status='Mercado Pago: pago',stock_reserved=0,updated_at=? WHERE id=?", (now, order_id))
            elif status in {"cancelled", "expired", "failed"} and not order["paid"]:
                if order["stock_reserved"]:
                    for item in db.execute("SELECT product_id,quantity FROM order_items WHERE order_id=?", (order_id,)).fetchall():
                        db.execute("UPDATE products SET stock=stock+?,updated_at=? WHERE id=?", (item["quantity"], now, item["product_id"]))
                db.execute("UPDATE orders SET status='Pagamento não concluído',payment_status=?,stock_reserved=0,updated_at=? WHERE id=?", (f"Mercado Pago: {status}", now, order_id))
            else:
                db.execute("UPDATE orders SET payment_status=?,updated_at=? WHERE id=?", (f"Mercado Pago: {status or 'pendente'}", now, order_id))
            db.execute("INSERT INTO payment_webhook_events(event_id,gateway_order_id,processed_at) VALUES(?,?,?)", (event_id or gateway_id, gateway_id, now))
        return {"ok": True}, 200

    def _create_product(self, db: sqlite3.Connection, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        name = str(payload.get("Nome") or payload.get("nome") or payload.get("name") or "").strip()
        description = str(payload.get("Descricao") or payload.get("descricao") or payload.get("description") or "").strip()
        category = str(payload.get("Categoria") or payload.get("categoria") or "").strip()
        image = str(payload.get("Url_Imagem") or payload.get("imagem_url") or "").strip()
        if category not in {"Roupas", "Calçados", "Acessórios"} or not name:
            return {"message": "Informe nome e uma categoria de moda válida."}, 400
        if image and not (image.startswith("https://") or image.startswith("/products/")):
            return {"message": "A imagem precisa usar HTTPS ou um arquivo local de produto."}, 400
        try:
            price = _price_to_cents(payload.get("Preco") or payload.get("preco") or payload.get("price") or "0")
            stock = int(payload.get("Qtd_Disp") or payload.get("estoque") or payload.get("stock") or 0)
        except (ValueError, TypeError, OverflowError):
            return {"message": "Preço ou estoque inválido."}, 400
        if price < 0 or stock < 0 or stock > 1_000_000:
            return {"message": "Preço e estoque precisam ser positivos."}, 400
        demonstration_raw = payload.get("demonstracao", True)
        demonstration = str(demonstration_raw).strip().lower() not in {"false", "0", "nao", "não"}
        metadata = (
            str(payload.get("Marca") or payload.get("brand") or "OSDROUPA").strip()[:100],
            str(payload.get("Colecao") or payload.get("collection") or "Coleção da loja").strip()[:100],
            str(payload.get("Tipo") or payload.get("product_type") or category).strip()[:100],
            str(payload.get("Tamanhos") or payload.get("sizes") or "Consultar disponibilidade").strip()[:160],
            str(payload.get("Cores") or payload.get("colors") or "Consultar disponibilidade").strip()[:160],
            str(payload.get("Material") or payload.get("material") or "Material a confirmar").strip()[:160],
            str(payload.get("Caimento") or payload.get("fit") or "Consultar tabela de medidas").strip()[:160],
        )
        now = _stamp()
        cursor = db.execute(
            """INSERT INTO products
            (name,description,category,price_cents,stock,image_url,brand,collection,product_type,sizes,colors,material,fit,
             made_to_order,demonstration,active,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,1,?,?)""",
            (name, description, category, price, stock, image, *metadata, int(demonstration), now, now),
        )
        return self._product_dict(db.execute("SELECT * FROM products WHERE id=?", (cursor.lastrowid,)).fetchone()), 201

    def _update_product(self, db: sqlite3.Connection, product_id: int, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        row = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if row is None:
            return {"message": "Produto não encontrado."}, 404
        merged = {
            "Nome": payload.get("Nome", row["name"]),
            "Descricao": payload.get("Descricao", row["description"]),
            "Categoria": payload.get("Categoria", row["category"]),
            "Preco": payload.get("Preco", _as_price(row["price_cents"])),
            "Qtd_Disp": payload.get("Qtd_Disp", row["stock"]),
            "Url_Imagem": payload.get("Url_Imagem", row["image_url"]),
            "Marca": payload.get("Marca", row["brand"]),
            "Colecao": payload.get("Colecao", row["collection"]),
            "Tipo": payload.get("Tipo", row["product_type"]),
            "Tamanhos": payload.get("Tamanhos", row["sizes"]),
            "Cores": payload.get("Cores", row["colors"]),
            "Material": payload.get("Material", row["material"]),
            "Caimento": payload.get("Caimento", row["fit"]),
            "demonstracao": payload.get("demonstracao", row["demonstration"]),
        }
        name = str(merged["Nome"] or "").strip()
        description = str(merged["Descricao"] or "").strip()
        category = str(merged["Categoria"] or "").strip()
        image = str(merged["Url_Imagem"] or "").strip()
        if not name or category not in {"Roupas", "Calçados", "Acessórios"}:
            return {"message": "Informe nome e uma categoria de moda válida."}, 400
        if image and not (image.startswith("https://") or image.startswith("/products/")):
            return {"message": "A imagem precisa usar HTTPS ou um arquivo local de produto."}, 400
        try:
            price_cents = _price_to_cents(merged["Preco"])
            stock = int(merged["Qtd_Disp"])
        except (ValueError, TypeError, OverflowError):
            return {"message": "Preço ou estoque inválido."}, 400
        if price_cents < 0 or stock < 0 or stock > 1_000_000:
            return {"message": "Preço e estoque precisam ser positivos."}, 400
        demonstration = str(merged["demonstracao"]).strip().lower() not in {"false", "0", "nao", "não"}
        metadata = (
            str(merged["Marca"] or "").strip()[:100], str(merged["Colecao"] or "").strip()[:100],
            str(merged["Tipo"] or "").strip()[:100], str(merged["Tamanhos"] or "").strip()[:160],
            str(merged["Cores"] or "").strip()[:160], str(merged["Material"] or "").strip()[:160],
            str(merged["Caimento"] or "").strip()[:160],
        )
        db.execute(
            """UPDATE products SET name=?,description=?,category=?,price_cents=?,stock=?,image_url=?,
            brand=?,collection=?,product_type=?,sizes=?,colors=?,material=?,fit=?,demonstration=?,updated_at=? WHERE id=?""",
            (name, description, category, price_cents, stock, image, *metadata, int(demonstration), _stamp(), product_id),
        )
        return self._product_dict(db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()), 200

    def _admin_resource(self, db: sqlite3.Connection, endpoint: str, query: dict[str, Any]) -> tuple[dict[str, Any], int]:
        if endpoint == "adminResumo":
            orders = db.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
            products = db.execute("SELECT COUNT(*) n FROM products WHERE active=1").fetchone()["n"]
            customers = db.execute("SELECT COUNT(*) n FROM users WHERE role='member'").fetchone()["n"]
            month = _now().strftime("%Y-%m")
            paid = db.execute("SELECT COALESCE(SUM(total_cents),0) n FROM orders WHERE paid=1 AND substr(created_at,1,7)=?", (month,)).fetchone()["n"]
            return {"resumo": {
                "pedidos_cadastrados": orders, "vendas_mes": f"R$ {_as_price(paid)}",
                "produtos_cadastrados": products, "clientes_cadastrados": customers,
            }}, 200
        if endpoint == "adminProdutos":
            rows = self._page_rows(db,
                "SELECT id,name AS Nome,description AS Descricao,category AS Categoria,price_cents,stock AS Qtd_Disp,image_url AS Url_Imagem,demonstration,created_at FROM products WHERE active=1 ORDER BY id DESC LIMIT ? OFFSET ?",
                (), query)
            items = rows["items"]
            for row in items:
                row["Preco"] = _as_price(row.pop("price_cents"))
                row["demonstracao"] = bool(row.pop("demonstration"))
            return {"items": items, "nextPage": rows["nextPage"]}, 200
        if endpoint == "adminPedidos":
            rows = self._page_rows(db,
                "SELECT id,total_cents,status,payment_status,created_at FROM orders ORDER BY id DESC LIMIT ? OFFSET ?",
                (), query)
            items = rows["items"]
            for row in items:
                row["Total"] = _as_price(row.pop("total_cents"))
                row["Nome"] = f"Pedido #{row['id']}"
                row["allowed_statuses"] = self._allowed_statuses(row["status"])
            return {"items": items, "nextPage": rows["nextPage"]}, 200
        if endpoint == "adminClientes":
            rows = self._page_rows(db,
                "SELECT id,name AS nome,email,phone AS celular,role,created_at FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
                (), query)
            return rows, 200
        if endpoint == "adminRelatorios":
            rows = self._page_rows(db,
                "SELECT id,total_cents,status,payment_status,paid,created_at FROM orders ORDER BY id DESC LIMIT ? OFFSET ?",
                (), query)
            items = rows["items"]
            for row in items:
                row["Total"] = _as_price(row.pop("total_cents"))
                row["Nome"] = f"Pedido #{row['id']}"
            return {"items": items, "nextPage": rows["nextPage"]}, 200
        return {"message": "Recurso administrativo não encontrado."}, 404

    @staticmethod
    def _allowed_statuses(status: str) -> list[str]:
        return {
            "Aguardando confirmação": ["Confirmado", "Cancelado"],
            "Confirmado": ["Em preparo", "Cancelado"],
            "Em preparo": ["Enviado"],
            "Enviado": ["Entregue"],
            "Entregue": [], "Cancelado": [], "Expirado": [],
        }.get(status, [])

    def _change_order_status(self, db: sqlite3.Connection, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        try:
            order_id = int(payload.get("pedido_id") or payload.get("id"))
        except (TypeError, ValueError):
            return {"message": "Pedido inválido."}, 400
        target = str(payload.get("status") or "").strip()
        db.execute("BEGIN IMMEDIATE")
        self._release_expired_reservations(db)
        order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if order is None:
            return {"message": "Pedido não encontrado."}, 404
        if target not in self._allowed_statuses(order["status"]):
            return {"message": "Transição de pedido não permitida."}, 409
        if target == "Cancelado" and order["stock_reserved"]:
            items = db.execute("SELECT product_id,quantity FROM order_items WHERE order_id=?", (order_id,)).fetchall()
            for item in items:
                db.execute("UPDATE products SET stock=stock+? WHERE id=?", (item["quantity"], item["product_id"]))
        db.execute(
            "UPDATE orders SET status=?,stock_reserved=CASE WHEN ?='Cancelado' THEN 0 ELSE stock_reserved END,updated_at=? WHERE id=?",
            (target, target, _stamp(), order_id),
        )
        return {"pedido": self._order_detail(db, order_id)["pedido"]}, 200

    @staticmethod
    def _address_payload(payload: dict[str, Any]) -> dict[str, Any]:
        cep = "".join(c for c in str(payload.get("cep") or "") if c.isdigit())
        if len(cep) != 8:
            raise ValueError("O CEP precisa ter oito dígitos.")
        logradouro = str(payload.get("logradouro") or "").strip()
        numero = str(payload.get("numero") or "").strip()
        if not logradouro or not numero:
            raise ValueError("Logradouro e número são obrigatórios.")
        return {
            "cep": cep, "logradouro": logradouro, "numero": numero,
            "complemento": str(payload.get("complemento") or "").strip(),
            "bairro": str(payload.get("bairro") or "").strip(),
            "referencia": str(payload.get("referencia") or "").strip(),
            "cidade": str(payload.get("cidade") or "").strip(),
            "uf": str(payload.get("uf") or "").strip().upper()[:2],
            "is_default": bool(payload.get("padrao")),
        }

    def _dispatch(self, method: str, url: str, headers: dict[str, str] | None, payload: dict[str, Any], query: dict[str, Any]) -> tuple[Any, int]:
        parsed = urlsplit(url)
        path = parsed.path
        method = method.upper()
        if not query and parsed.query:
            query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        self.initialize()
        with self._db() as db:
            if path.startswith("/api:nqm5-KuC/auth/"):
                endpoint = path.removeprefix("/api:nqm5-KuC/auth/")
                if endpoint == "login" and method == "POST":
                    return self._login(db, payload)
                if endpoint == "me" and method == "GET":
                    user = self._require_user(db, headers)
                    return self._user_dict(user), 200
                if endpoint == "logout" and method == "POST":
                    auth = {str(k).lower(): str(v) for k, v in (headers or {}).items()}.get("authorization", "")
                    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
                    if token:
                        db.execute("DELETE FROM sessions WHERE token_hash=?", (self._token_hash(token),))
                    return {"ok": True}, 200
                if endpoint == "request-reset" and method == "POST":
                    return self._request_password_reset(db, payload)
                if endpoint == "reset-password" and method == "POST":
                    return self._reset_password(db, payload)
                return {"message": "Rota de autenticação não encontrada."}, 404

            if path.startswith("/api:6LtoY7Zt/"):
                endpoint = path.removeprefix("/api:6LtoY7Zt/")
                user: sqlite3.Row | None = None
                public_endpoints = {"cadastraCliente", "depoimentosPublicos", "feedInspiracoes"}
                if endpoint.split("/", 1)[0] not in public_endpoints:
                    user = self._require_user(db, headers)

                inspiration_result = self._inspiration_routes(db, method, endpoint, payload, query, user, headers)
                if inspiration_result is not None:
                    return inspiration_result
                if endpoint == "feedbackLooks":
                    return self._feedback_routes(db, method, payload, user)

                if endpoint == "cadastraCliente" and method == "POST":
                    return self._register(db, payload)
                if endpoint == "depoimentosPublicos" and method == "GET":
                    rows = db.execute(
                        "SELECT id,display_name,body,anonymous,created_at FROM testimonials WHERE status='Publicado' AND consented=1 ORDER BY id DESC LIMIT 30"
                    ).fetchall()
                    return {"depoimentos": [{"id": row["id"], "nome": "Pessoa da comunidade" if row["anonymous"] else row["display_name"], "texto": row["body"], "data": row["created_at"]} for row in rows]}, 200
                assert user is not None
                if endpoint == "buscaCliente" and method == "GET":
                    return {
                        "id": user["id"], "nome": user["name"], "email": user["email"],
                        "celular": user["phone"], "data_nascimento": user["birth_date"],
                        "pronome": user["pronouns"], "estilo_preferido": user["style_preference"],
                        "tamanho_superior": user["top_size"], "tamanho_inferior": user["bottom_size"],
                        "tamanho_calcado": user["shoe_size"], "cores_favoritas": user["favorite_colors"],
                        "sobre_mim": user["bio"], "personalizacao_ia": bool(user["ai_personalization"]),
                    }, 200
                if endpoint == "perfil" and method in {"PATCH", "PUT"}:
                    name = str(payload.get("nome", user["name"]) or "").strip()
                    phone = str(payload.get("celular", user["phone"]) or "").strip()
                    if len(name.split()) < 2 or not 6 <= len(phone) <= 30:
                        return {"message": "Informe nome completo e um celular válido."}, 400
                    optional_fields = {
                        "data_nascimento": ("birth_date", 10),
                        "pronome": ("pronouns", 40),
                        "estilo_preferido": ("style_preference", 50),
                        "tamanho_superior": ("top_size", 24),
                        "tamanho_inferior": ("bottom_size", 24),
                        "tamanho_calcado": ("shoe_size", 24),
                        "cores_favoritas": ("favorite_colors", 100),
                        "sobre_mim": ("bio", 240),
                    }
                    values: dict[str, str] = {"name": name, "phone": phone}
                    for input_name, (column, max_length) in optional_fields.items():
                        value = str(payload.get(input_name, user[column]) or "").strip()
                        if len(value) > max_length:
                            return {"message": f"O campo {input_name.replace('_', ' ')} excede o limite permitido."}, 400
                        values[column] = value
                    if values["birth_date"]:
                        try:
                            birth_date = datetime.strptime(values["birth_date"], "%Y-%m-%d").date()
                        except ValueError:
                            return {"message": "Informe uma data de nascimento válida."}, 400
                        if birth_date > _now().date():
                            return {"message": "A data de nascimento não pode estar no futuro."}, 400
                    personalization = payload.get("personalizacao_ia", bool(user["ai_personalization"]))
                    if not isinstance(personalization, bool):
                        return {"message": "Informe se a personalização por IA fica ativa."}, 400
                    db.execute("UPDATE users SET ai_personalization=? WHERE id=?", (int(personalization), user["id"]))
                    db.execute(
                        """UPDATE users SET name=?,phone=?,birth_date=?,pronouns=?,style_preference=?,
                        top_size=?,bottom_size=?,shoe_size=?,favorite_colors=?,bio=? WHERE id=?""",
                        (values["name"], values["phone"], values["birth_date"], values["pronouns"],
                         values["style_preference"], values["top_size"], values["bottom_size"],
                         values["shoe_size"], values["favorite_colors"], values["bio"], user["id"]),
                    )
                    return {
                        "id": user["id"], "nome": values["name"], "email": user["email"],
                        "celular": values["phone"], "data_nascimento": values["birth_date"],
                        "pronome": values["pronouns"], "estilo_preferido": values["style_preference"],
                        "tamanho_superior": values["top_size"], "tamanho_inferior": values["bottom_size"],
                        "tamanho_calcado": values["shoe_size"], "cores_favoritas": values["favorite_colors"],
                        "sobre_mim": values["bio"], "personalizacao_ia": personalization,
                    }, 200

                if endpoint == "consultaEnderecoDoCliente" and method == "GET":
                    rows = db.execute("SELECT * FROM addresses WHERE user_id=? ORDER BY is_default DESC,id DESC", (user["id"],)).fetchall()
                    return {"endereco1": [self._address_dict(row) for row in rows]}, 200
                if endpoint in {"salvaEndereco", "atualizaEndereco"} and method in {"POST", "PATCH", "PUT"}:
                    address = self._address_payload(payload)
                    try:
                        address_id = int(payload.get("endereco_id") or 0)
                    except (TypeError, ValueError):
                        address_id = 0
                    if address_id:
                        # Do not clear the current default until ownership is confirmed.
                        # A failed edit must never leave this account without its default.
                        existing = db.execute(
                            "SELECT 1 FROM addresses WHERE id=? AND user_id=?",
                            (address_id, user["id"]),
                        ).fetchone()
                        if existing is None:
                            return {"message": "EndereÃ§o nÃ£o encontrado."}, 404
                    if address["is_default"]:
                        db.execute("UPDATE addresses SET is_default=0 WHERE user_id=?", (user["id"],))
                    if address_id:
                        cursor = db.execute(
                            """UPDATE addresses SET cep=?,logradouro=?,numero=?,complemento=?,bairro=?,referencia=?,cidade=?,uf=?,is_default=?
                            WHERE id=? AND user_id=?""",
                            (*address.values(), address_id, user["id"]),
                        )
                        if not cursor.rowcount:
                            return {"message": "Endereço não encontrado."}, 404
                    else:
                        has_default = db.execute("SELECT 1 FROM addresses WHERE user_id=? LIMIT 1", (user["id"],)).fetchone()
                        address["is_default"] = address["is_default"] or not has_default
                        cursor = db.execute(
                            """INSERT INTO addresses(user_id,cep,logradouro,numero,complemento,bairro,referencia,cidade,uf,is_default,created_at)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (user["id"], *address.values(), _stamp()),
                        )
                        address_id = int(cursor.lastrowid)
                    saved = db.execute("SELECT * FROM addresses WHERE id=? AND user_id=?", (address_id, user["id"])).fetchone()
                    return {"endereco": self._address_dict(saved)}, 200
                if endpoint == "marcarEnderecoPadrao" and method in {"PATCH", "POST"}:
                    try:
                        address_id = int(payload.get("endereco_id"))
                    except (TypeError, ValueError):
                        return {"message": "Endereço inválido."}, 400
                    if not db.execute("SELECT 1 FROM addresses WHERE id=? AND user_id=?", (address_id, user["id"])).fetchone():
                        return {"message": "Endereço não encontrado."}, 404
                    db.execute("UPDATE addresses SET is_default=(id=?) WHERE user_id=?", (address_id, user["id"]))
                    return {"ok": True}, 200

                if endpoint == "meuArmario" and method == "GET":
                    rows = db.execute("SELECT * FROM wardrobe_items WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"itens": [self._wardrobe_dict(row) for row in rows]}, 200
                if endpoint == "meuArmario" and method == "POST":
                    local_key = str(payload.get("chave_local") or "").strip()
                    name = str(payload.get("nome") or "").strip()
                    if not local_key or not name:
                        return {"message": "Nome e chave local da peça são obrigatórios."}, 400
                    image_url = str(payload.get("imagem_url") or "").strip()
                    if image_url:
                        parsed_image_url = urlsplit(image_url)
                        if (
                            len(image_url) > 2048
                            or parsed_image_url.scheme.lower() != "https"
                            or not parsed_image_url.hostname
                            or parsed_image_url.username
                            or parsed_image_url.password
                            or any(ord(char) < 32 or char.isspace() for char in image_url)
                        ):
                            return {"message": "Use o link HTTPS direto da imagem, sem espaços."}, 400
                    try:
                        image_data, image_mime = _wardrobe_image_upload(payload)
                    except ValueError as exc:
                        return {"message": str(exc)}, 400
                    if image_url and image_data is not None:
                        return {"message": "Escolha uma foto enviada ou um link de imagem, não os dois."}, 400
                    try:
                        purchase_price = _price_to_cents(payload.get("preco_compra")) if str(payload.get("preco_compra") or "").strip() else None
                    except ValueError as exc:
                        return {"message": str(exc)}, 400
                    db.execute(
                        """INSERT INTO wardrobe_items(user_id,local_key,name,category,status,color,season,size,brand,image_url,image_data,image_mime,purchase_price_cents,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,local_key) DO UPDATE SET
                        name=excluded.name,category=excluded.category,status=excluded.status,color=excluded.color,
                        season=excluded.season,size=excluded.size,brand=excluded.brand,
                        image_url=CASE WHEN excluded.image_data IS NOT NULL OR excluded.image_url<>'' THEN excluded.image_url ELSE wardrobe_items.image_url END,
                        image_data=CASE WHEN excluded.image_data IS NOT NULL THEN excluded.image_data WHEN excluded.image_url<>'' THEN NULL ELSE wardrobe_items.image_data END,
                        image_mime=CASE WHEN excluded.image_data IS NOT NULL THEN excluded.image_mime WHEN excluded.image_url<>'' THEN '' ELSE wardrobe_items.image_mime END,
                        purchase_price_cents=excluded.purchase_price_cents""",
                        (user["id"], local_key, name, str(payload.get("categoria") or "Partes de cima"),
                         str(payload.get("status") or "No armário"), str(payload.get("cor") or ""),
                         str(payload.get("estacao") or ""), str(payload.get("tamanho") or ""),
                         str(payload.get("marca") or ""), image_url, image_data, image_mime, purchase_price, _stamp()),
                    )
                    saved = db.execute("SELECT * FROM wardrobe_items WHERE user_id=? AND local_key=?", (user["id"], local_key)).fetchone()
                    return {"item": self._wardrobe_dict(saved)}, 200
                if endpoint.startswith("meuArmario/") and method in {"PATCH", "DELETE"}:
                    item_id = self._path_int(endpoint)
                    row = db.execute("SELECT * FROM wardrobe_items WHERE id=? AND user_id=?", (item_id, user["id"])).fetchone()
                    if row is None:
                        return {"message": "Peça não encontrada."}, 404
                    if method == "DELETE":
                        db.execute("DELETE FROM wardrobe_items WHERE id=? AND user_id=?", (item_id, user["id"]))
                        return {"ok": True}, 200
                    status = str(payload.get("status") or "").strip()
                    if not status:
                        return {"message": "Estado da peça inválido."}, 400
                    db.execute("UPDATE wardrobe_items SET status=? WHERE id=? AND user_id=?", (status, item_id, user["id"]))
                    return {"item": self._wardrobe_dict(db.execute("SELECT * FROM wardrobe_items WHERE id=?", (item_id,)).fetchone())}, 200

                if endpoint == "meusLooks" and method == "GET":
                    rows = db.execute("SELECT * FROM looks WHERE user_id=? ORDER BY COALESCE(planned_date,'9999-12-31'),id DESC", (user["id"],)).fetchall()
                    return {"looks": [self._look_dict(row) for row in rows]}, 200
                if endpoint == "meusLooks" and method == "POST":
                    local_key = str(payload.get("chave_local") or "").strip()
                    name = str(payload.get("nome") or "").strip()
                    keys = payload.get("roupa_chaves")
                    if not local_key or not name or not isinstance(keys, list) or not keys:
                        return {"message": "Nome e pelo menos uma peça são obrigatórios."}, 400
                    valid_keys = {row[0] for row in db.execute(
                        f"SELECT local_key FROM wardrobe_items WHERE user_id=? AND local_key IN ({','.join('?' for _ in keys)})",
                        (user["id"], *[str(key) for key in keys]),
                    ).fetchall()} if keys else set()
                    if valid_keys != set(str(key) for key in keys):
                        return {"message": "O look contém peça de outra conta ou removida."}, 403
                    db.execute(
                        """INSERT INTO looks(user_id,local_key,name,occasion,planned_date,garment_keys,created_at)
                        VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,local_key) DO UPDATE SET
                        name=excluded.name,occasion=excluded.occasion,planned_date=excluded.planned_date,garment_keys=excluded.garment_keys""",
                        (user["id"], local_key, name, str(payload.get("ocasiao") or "Dia a dia"),
                         payload.get("data_planejada") or None, json.dumps(sorted(valid_keys)), _stamp()),
                    )
                    saved = db.execute("SELECT * FROM looks WHERE user_id=? AND local_key=?", (user["id"], local_key)).fetchone()
                    return {"look": self._look_dict(saved)}, 200
                if endpoint.startswith("meusLooks/") and method == "DELETE":
                    look_id = self._path_int(endpoint)
                    cursor = db.execute("DELETE FROM looks WHERE id=? AND user_id=?", (look_id, user["id"]))
                    return ({"ok": True}, 200) if cursor.rowcount else ({"message": "Look não encontrado."}, 404)

                if endpoint == "checkoutPedidoDemonstrativo" and method == "POST":
                    return self._create_demo_order(db, user, payload)
                if endpoint == "checkoutPedido" and method == "POST":
                    return self._create_mercadopago_order(db, user, payload)
                if endpoint == "meusPedidos" and method == "GET":
                    db.execute("BEGIN IMMEDIATE")
                    self._release_expired_reservations(db)
                    rows = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"pedidos": [self._order_row(row) for row in rows]}, 200
                if endpoint.startswith("meuPedido/") and method == "GET":
                    order_id = self._path_int(endpoint)
                    db.execute("BEGIN IMMEDIATE")
                    self._release_expired_reservations(db)
                    order = db.execute("SELECT id FROM orders WHERE id=? AND user_id=?", (order_id, user["id"])).fetchone()
                    if order is None:
                        return {"message": "Pedido não encontrado."}, 404
                    return self._order_detail(db, order_id), 200

                if endpoint == "meusDesafios" and method == "GET":
                    rows = db.execute("SELECT challenge_id,completed_at FROM challenge_completions WHERE user_id=? ORDER BY completed_at", (user["id"],)).fetchall()
                    return {"concluidos": [{"desafio_id": row["challenge_id"], "completed_at": row["completed_at"]} for row in rows]}, 200
                if endpoint == "fidelidade" and method == "GET":
                    rows = db.execute("SELECT challenge_id,completed_at FROM challenge_completions WHERE user_id=? ORDER BY completed_at", (user["id"],)).fetchall()
                    points = sum(CHALLENGE_REWARDS.get(row["challenge_id"], 0) for row in rows)
                    tiers = [(0, "Começo"), (25, "Fio"), (60, "Trama"), (100, "Ateliê"), (160, "Ícone")]
                    current_index = max(index for index, (threshold, _) in enumerate(tiers) if points >= threshold)
                    level = tiers[current_index][1]
                    next_tier = tiers[current_index + 1] if current_index + 1 < len(tiers) else None
                    current_floor = tiers[current_index][0]
                    next_target = next_tier[0] if next_tier else current_floor
                    progress = 100 if not next_tier else min(100, int((points - current_floor) * 100 / max(1, next_target - current_floor)))
                    challenge_titles = {
                        "repeat-three": "Três dias, uma peça favorita", "forgotten-piece": "Resgate uma peça esquecida",
                        "care-routine": "Um cuidado que faz diferença", "plan-week": "Planeje três combinações",
                        "repair-one": "Dê um novo ponto a uma peça", "color-repeat": "Repita uma cor com intenção",
                        "wear-log": "Registre três usos", "closet-review": "Revise cinco peças",
                    }
                    history = [{
                        "desafio_id": row["challenge_id"],
                        "titulo": challenge_titles.get(row["challenge_id"], "Desafio concluído"),
                        "pontos": CHALLENGE_REWARDS.get(row["challenge_id"], 0),
                        "concluido_em": row["completed_at"],
                    } for row in reversed(rows)]
                    return {
                        "pontos": points, "nivel": level,
                        "proximo_nivel": next_tier[1] if next_tier else "Nível máximo",
                        "pontos_para_proximo_nivel": max(0, next_target - points) if next_tier else 0,
                        "progresso_nivel": progress, "concluidos": len(rows),
                        "desafios_validos": len(CHALLENGE_REWARDS), "historico": history,
                    }, 200
                if endpoint == "concluirDesafio" and method == "POST":
                    challenge_id = str(payload.get("desafio_id") or "").strip()
                    if challenge_id not in CHALLENGE_REWARDS:
                        return {"message": "Desafio inválido."}, 400
                    cursor = db.execute("INSERT OR IGNORE INTO challenge_completions(user_id,challenge_id,completed_at) VALUES(?,?,?)", (user["id"], challenge_id, _stamp()))
                    return {"desafio_id": challenge_id, "pontos": CHALLENGE_REWARDS[challenge_id], "creditado_agora": cursor.rowcount == 1, "ok": True}, 200

                if endpoint == "lookDoDia" and method == "GET":
                    weather = str(query.get("clima") or "Ameno")[:30]
                    occasion = str(query.get("ocasiao") or "Dia a dia")[:40]
                    rows = db.execute(
                        "SELECT * FROM wardrobe_items WHERE user_id=? AND status NOT IN ('Suja','Lavando') ORDER BY id DESC",
                        (user["id"],),
                    ).fetchall()
                    usable = list(rows)
                    def rank(item: sqlite3.Row) -> tuple[int, int]:
                        category = item["category"].casefold()
                        season = item["season"].casefold()
                        score = 0
                        if weather.casefold() == "frio" and any(word in season for word in ("inverno", "frio")):
                            score += 3
                        if weather.casefold() == "quente" and any(word in season for word in ("verão", "quente")):
                            score += 3
                        if occasion.casefold() == "evento" and any(word in category for word in ("vestido", "acessório")):
                            score += 2
                        if occasion.casefold() == "trabalho" and any(word in category for word in ("partes de cima", "partes de baixo", "vestido")):
                            score += 2
                        return (-score, item["id"])
                    usable.sort(key=rank)
                    selected = []
                    used_categories: set[str] = set()
                    for item in usable:
                        if item["category"] not in used_categories:
                            selected.append(item)
                            used_categories.add(item["category"])
                        if len(selected) >= 4:
                            break
                    return {"clima": weather, "ocasiao": occasion, "pecas": [self._wardrobe_dict(item) for item in selected]}, 200

                if endpoint == "registrarUso" and method == "POST":
                    try:
                        garment_id = int(payload.get("peca_id"))
                    except (TypeError, ValueError):
                        return {"message": "Escolha uma peça válida."}, 400
                    garment = db.execute("SELECT id FROM wardrobe_items WHERE id=? AND user_id=?", (garment_id, user["id"])).fetchone()
                    if garment is None:
                        return {"message": "A peça não pertence a esta conta."}, 404
                    worn_on = str(payload.get("data") or _now().date().isoformat())[:10]
                    try:
                        datetime.strptime(worn_on, "%Y-%m-%d")
                    except ValueError:
                        return {"message": "Informe uma data válida."}, 400
                    cursor = db.execute("INSERT INTO garment_wear_events(user_id,garment_id,occasion,worn_on,created_at) VALUES(?,?,?,?,?)", (user["id"], garment_id, str(payload.get("ocasiao") or "")[:80], worn_on, _stamp()))
                    return {"id": cursor.lastrowid, "ok": True}, 201

                if endpoint == "historicoUso" and method == "GET":
                    rows = db.execute(
                        """SELECT w.id,w.name,w.category,w.purchase_price_cents,COUNT(e.id) AS uses,
                        MAX(e.worn_on) AS last_worn FROM wardrobe_items w LEFT JOIN garment_wear_events e
                        ON e.garment_id=w.id AND e.user_id=w.user_id WHERE w.user_id=? GROUP BY w.id ORDER BY uses DESC,w.name""",
                        (user["id"],),
                    ).fetchall()
                    recent = db.execute(
                        """SELECT e.id,e.worn_on,e.occasion,w.name AS peca FROM garment_wear_events e
                        JOIN wardrobe_items w ON w.id=e.garment_id WHERE e.user_id=? ORDER BY e.worn_on DESC,e.id DESC LIMIT 30""",
                        (user["id"],),
                    ).fetchall()
                    items = []
                    for row in rows:
                        uses = int(row["uses"] or 0)
                        cents = row["purchase_price_cents"]
                        items.append({"id": row["id"], "nome": row["name"], "categoria": row["category"], "usos": uses, "ultimo_uso": row["last_worn"] or "", "preco_compra": _as_price(cents) if cents is not None else "", "custo_por_uso": _as_price(round(cents / uses)) if cents is not None and uses else ""})
                    return {"itens": items, "registros": [dict(row) for row in recent]}, 200

                if endpoint == "malas" and method == "GET":
                    plans = db.execute("SELECT * FROM packing_plans WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"malas": [{**dict(plan), "pecas_ids": json.loads(plan["garment_ids"] or "[]")} for plan in plans]}, 200
                if endpoint == "malas" and method == "POST":
                    name = str(payload.get("nome") or "").strip()[:100]
                    destination = str(payload.get("destino") or "").strip()[:120]
                    ids = payload.get("pecas_ids")
                    if not name or not destination or not isinstance(ids, list):
                        return {"message": "Informe nome, destino e uma lista de peças."}, 400
                    try:
                        ids = sorted({int(item_id) for item_id in ids})
                    except (TypeError, ValueError):
                        return {"message": "A mala contém peças inválidas."}, 400
                    if ids:
                        owned = {row[0] for row in db.execute(f"SELECT id FROM wardrobe_items WHERE user_id=? AND id IN ({','.join('?' for _ in ids)})", (user["id"], *ids)).fetchall()}
                        if owned != set(ids):
                            return {"message": "A mala inclui peça que não pertence a esta conta."}, 403
                    cursor = db.execute("INSERT INTO packing_plans(user_id,name,destination,start_date,end_date,occasion,garment_ids,created_at) VALUES(?,?,?,?,?,?,?,?)", (user["id"], name, destination, str(payload.get("data_inicio") or "")[:10], str(payload.get("data_fim") or "")[:10], str(payload.get("ocasiao") or "")[:80], json.dumps(ids), _stamp()))
                    return {"id": cursor.lastrowid, "ok": True}, 201

                if endpoint == "solicitarAjuste" and method == "POST":
                    service_type = str(payload.get("servico") or "").strip()[:80]
                    garment_name = str(payload.get("peca") or "").strip()[:120]
                    notes = str(payload.get("observacoes") or "").strip()[:2000]
                    if service_type not in {"Ajuste de caimento", "Bainha", "Reparo", "Transformação", "Consultoria de armário"} or len(garment_name) < 2:
                        return {"message": "Escolha um serviço e descreva a peça."}, 400
                    now = _stamp()
                    cursor = db.execute("INSERT INTO tailoring_requests(user_id,service_type,garment_name,notes,preferred_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (user["id"], service_type, garment_name, notes, str(payload.get("data_preferida") or "")[:10], now, now))
                    return {"id": cursor.lastrowid, "status": "Recebido", "ok": True}, 201
                if endpoint == "solicitarAjuste" and method == "GET":
                    rows = db.execute("SELECT id,service_type,garment_name,notes,preferred_date,status,created_at FROM tailoring_requests WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"solicitacoes": [dict(row) for row in rows]}, 200

                if endpoint == "adminSolicitacoesAjuste" and method == "GET":
                    self._require_admin(db, headers)
                    rows = db.execute("SELECT r.id,r.user_id,u.email,r.service_type,r.garment_name,r.notes,r.preferred_date,r.status,r.created_at FROM tailoring_requests r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC LIMIT 100").fetchall()
                    return {"solicitacoes": [dict(row) for row in rows]}, 200
                if endpoint.startswith("adminSolicitacoesAjuste/") and method == "PATCH":
                    self._require_admin(db, headers)
                    request_id = self._path_int(endpoint)
                    status = str(payload.get("status") or "").strip()
                    allowed = {"Recebido", "Em análise", "Orçamento enviado", "Agendado", "Concluído", "Cancelado"}
                    if status not in allowed:
                        return {"message": "Estado de solicitação inválido."}, 400
                    cursor = db.execute("UPDATE tailoring_requests SET status=?,updated_at=? WHERE id=?", (status, _stamp(), request_id))
                    return ({"ok": True, "status": status}, 200) if cursor.rowcount else ({"message": "Solicitação não encontrada."}, 404)

                if endpoint == "depoimentos" and method == "POST":
                    body = str(payload.get("texto") or "").strip()
                    anonymous = bool(payload.get("anonimo"))
                    consented = payload.get("autorizo_publicacao") is True
                    if len(body) < 30 or len(body) > 1500 or not consented:
                        return {"message": "Escreva um relato de 30 a 1.500 caracteres e autorize a publicação."}, 400
                    cursor = db.execute("INSERT INTO testimonials(user_id,display_name,body,anonymous,consented,created_at) VALUES(?,?,?,?,?,?)", (user["id"], "Pessoa da comunidade" if anonymous else user["name"], body, int(anonymous), 1, _stamp()))
                    return {"id": cursor.lastrowid, "status": "Pendente", "ok": True}, 201
                if endpoint == "meusDepoimentos" and method == "GET":
                    rows = db.execute("SELECT id,body,status,anonymous,created_at,moderated_at FROM testimonials WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"depoimentos": [dict(row) for row in rows]}, 200
                if endpoint == "solicitacoesPrivacidade" and method == "POST":
                    request_type = str(payload.get("tipo") or "").strip()[:80]
                    details = str(payload.get("detalhes") or "").strip()[:2000]
                    allowed = {"Acesso aos dados", "Correção", "Exclusão", "Portabilidade", "Informações sobre compartilhamento", "Revisão de recomendação"}
                    if request_type not in allowed:
                        return {"message": "Escolha um tipo de solicitação válido."}, 400
                    now = _stamp()
                    cursor = db.execute("INSERT INTO privacy_requests(user_id,request_type,details,created_at,updated_at) VALUES(?,?,?,?,?)", (user["id"], request_type, details, now, now))
                    return {"id": cursor.lastrowid, "status": "Recebida", "ok": True}, 201
                if endpoint == "solicitacoesPrivacidade" and method == "GET":
                    rows = db.execute("SELECT id,request_type,details,status,created_at,updated_at FROM privacy_requests WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"solicitacoes": [dict(row) for row in rows]}, 200

                if endpoint == "adminDepoimentos" and method == "GET":
                    self._require_admin(db, headers)
                    rows = db.execute("SELECT id,user_id,display_name,body,anonymous,consented,status,created_at FROM testimonials ORDER BY id DESC LIMIT 100").fetchall()
                    return {"depoimentos": [dict(row) for row in rows]}, 200
                if endpoint.startswith("adminDepoimentos/") and method == "PATCH":
                    self._require_admin(db, headers)
                    testimonial_id = self._path_int(endpoint)
                    status = str(payload.get("status") or "").strip()
                    if status not in {"Publicado", "Recusado"}:
                        return {"message": "Escolha publicar ou recusar o relato."}, 400
                    cursor = db.execute("UPDATE testimonials SET status=?,moderated_at=? WHERE id=? AND consented=1", (status, _stamp(), testimonial_id))
                    return ({"ok": True, "status": status}, 200) if cursor.rowcount else ({"message": "Relato não encontrado ou sem consentimento."}, 404)
                if endpoint == "adminSolicitacoesPrivacidade" and method == "GET":
                    self._require_admin(db, headers)
                    rows = db.execute("SELECT r.id,r.user_id,u.email,r.request_type,r.details,r.status,r.created_at FROM privacy_requests r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC LIMIT 100").fetchall()
                    return {"solicitacoes": [dict(row) for row in rows]}, 200
                if endpoint.startswith("adminSolicitacoesPrivacidade/") and method == "PATCH":
                    self._require_admin(db, headers)
                    request_id = self._path_int(endpoint)
                    status = str(payload.get("status") or "").strip()
                    if status not in {"Em análise", "Concluída", "Não aplicável"}:
                        return {"message": "Estado de solicitação inválido."}, 400
                    cursor = db.execute("UPDATE privacy_requests SET status=?,updated_at=? WHERE id=?", (status, _stamp(), request_id))
                    return ({"ok": True, "status": status}, 200) if cursor.rowcount else ({"message": "Solicitação não encontrada."}, 404)

                if endpoint == "meusDispositivos" and method == "GET":
                    rows = db.execute("SELECT * FROM devices WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
                    return {"dispositivos": [self._device_dict(row) for row in rows], "demonstracao": True}, 200
                if endpoint == "solicitarPareamento" and method == "POST":
                    identifier = str(payload.get("identificador") or "").strip()
                    if len(identifier) < 3:
                        return {"message": "Informe um identificador com pelo menos três caracteres."}, 400
                    code = f"{secrets.randbelow(1_000_000):06d}"
                    now = _stamp()
                    expires_at = _stamp(_now() + timedelta(minutes=10))
                    cursor = db.execute(
                        "INSERT INTO device_pairings(user_id,identifier,code_hash,expires_at,status,created_at) VALUES(?,?,?,?,?,?)",
                        (user["id"], identifier, self._token_hash(code), expires_at, "pending", now),
                    )
                    return {"pareamento_id": cursor.lastrowid, "codigo_pareamento": code, "expira_em": expires_at, "demonstracao": True}, 201
                if endpoint == "confirmarPareamentoLocal" and method == "POST":
                    code = str(payload.get("codigo_pareamento") or "").strip()
                    pair = db.execute(
                        "SELECT * FROM device_pairings WHERE user_id=? AND code_hash=? AND status='pending' AND expires_at>? ORDER BY id DESC LIMIT 1",
                        (user["id"], self._token_hash(code), _stamp()),
                    ).fetchone()
                    if pair is None:
                        return {"message": "Código de demonstração inválido ou expirado."}, 400
                    db.execute("UPDATE device_pairings SET status='confirmed' WHERE id=?", (pair["id"],))
                    cursor = db.execute(
                        "INSERT INTO devices(user_id,pairing_id,name,identifier,status,last_seen) VALUES(?,?,?,?,?,?)",
                        (user["id"], pair["id"], f"Armário demonstrativo {pair['identifier']}", pair["identifier"], "online", _stamp()),
                    )
                    return {"dispositivo": self._device_dict(db.execute("SELECT * FROM devices WHERE id=?", (cursor.lastrowid,)).fetchone()), "demonstracao": True}, 201
                if endpoint.startswith("meuDispositivo/") and method == "GET":
                    device_id = self._path_int(endpoint)
                    device = db.execute("SELECT * FROM devices WHERE id=? AND user_id=?", (device_id, user["id"])).fetchone()
                    if device is None:
                        return {"message": "Dispositivo não encontrado."}, 404
                    events = db.execute("SELECT * FROM device_events WHERE device_id=? ORDER BY id DESC", (device_id,)).fetchall()
                    return {"dispositivo": self._device_dict(device), "eventos": [dict(e) for e in events], "demonstracao": True}, 200

                return {"message": "Endpoint local não implementado."}, 404

            if path.startswith("/api:EzKvuCov/"):
                endpoint = path.removeprefix("/api:EzKvuCov/")
                if endpoint == "produto" and method == "GET":
                    self._release_expired_reservations(db)
                    rows = db.execute("SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()
                    return {"produto": [self._product_dict(row) for row in rows]}, 200
                if endpoint.startswith("produto/") and method == "GET":
                    product_id = self._path_int(endpoint)
                    row = db.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
                    return (self._product_dict(row), 200) if row else ({"message": "Produto não encontrado."}, 404)
                self._require_admin(db, headers)
                if endpoint in {"adminResumo", "adminProdutos", "adminPedidos", "adminClientes", "adminRelatorios"} and method == "GET":
                    return self._admin_resource(db, endpoint, query)
                if endpoint == "adminProdutos" and method == "POST":
                    return self._create_product(db, payload)
                if endpoint.startswith("adminProdutos/") and method == "PATCH":
                    return self._update_product(db, self._path_int(endpoint), payload)
                if endpoint == "adminPedidoStatus" and method == "PATCH":
                    return self._change_order_status(db, payload)
                return {"message": "Recurso administrativo local não encontrado."}, 404

        return {"message": "Backend local não reconhece este serviço."}, 404

    # ── Inspirações e feed (Change 028) ──────────────────────────────────────
    INSPIRATION_OCCASIONS = {"Dia a dia", "Trabalho", "Evento", "Viagem", "Outro"}
    INSPIRATION_WEATHER = {"Quente", "Ameno", "Frio", "Chuvoso"}
    INSPIRATION_REGIONS = {"Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"}
    INSPIRATION_PAGE_SIZE = 24

    @staticmethod
    def _clean_image_ref(value: object) -> str:
        """Só aceita imagens do catálogo local (/...) ou HTTPS; nunca data URI (fotos privadas do armário)."""
        text = str(value or "").strip()[:500]
        return text if (text.startswith("/") and ".." not in text) or text.startswith("https://") else ""

    def _clean_inspiration(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("nome") or "").strip()[:80]
        local_key = str(payload.get("chave_local") or "").strip()[:64]
        occasion = str(payload.get("ocasiao") or "").strip()
        if not name or not re.fullmatch(r"[0-9a-f]{32}", local_key) or occasion not in self.INSPIRATION_OCCASIONS:
            raise ValueError("Informe nome, chave e ocasião válidos para a inspiração.")
        weather = str(payload.get("clima") or "").strip()
        region = str(payload.get("regiao") or "").strip()
        image_path = str(payload.get("imagem") or "").strip()
        if image_path and not re.fullmatch(r"looks/[0-9a-f]{32}\.(png|jpg|webp)", image_path):
            raise ValueError("Imagem da inspiração inválida.")
        raw_pieces = payload.get("pecas") or []
        if not isinstance(raw_pieces, list) or not 1 <= len(raw_pieces) <= 12:
            raise ValueError("A inspiração precisa ter de 1 a 12 peças.")
        pieces = []
        for piece in raw_pieces:
            if not isinstance(piece, dict):
                raise ValueError("Peça inválida.")
            origin = str(piece.get("origem") or "")
            pieces.append({
                "papel": str(piece.get("papel") or "")[:40],
                "nome": str(piece.get("nome") or "Peça")[:80],
                "descricao": str(piece.get("descricao") or "")[:240],
                "origem": origin if origin in {"armario", "catalogo", "sugerida"} else "sugerida",
                "imagem_url": self._clean_image_ref(piece.get("imagem_url")) if origin == "catalogo" else "",
            })
        return {
            "local_key": local_key, "name": name, "occasion": occasion,
            "weather_category": weather if weather in self.INSPIRATION_WEATHER else "",
            "region": region if region in self.INSPIRATION_REGIONS else "",
            "season": str(payload.get("estacao") or "").strip()[:20],
            "palette": str(payload.get("paleta") or "").strip()[:200],
            "fabrics": str(payload.get("tecidos") or "").strip()[:200],
            "rationale": str(payload.get("justificativa") or "").strip()[:1200],
            "score": str(payload.get("nota") or "").strip()[:4],
            "pieces_json": json.dumps(pieces, ensure_ascii=False),
            "image_path": image_path,
        }

    @staticmethod
    def _inspiration_dict(row: sqlite3.Row, *, owner_view: bool = False, saved_ids: set[int] | None = None) -> dict[str, Any]:
        data = {
            "id": row["id"], "nome": row["name"], "ocasiao": row["occasion"], "clima": row["weather_category"],
            "regiao": row["region"], "estacao": row["season"], "paleta": row["palette"], "tecidos": row["fabrics"],
            "justificativa": row["rationale"], "nota": row["score"], "pecas": json.loads(row["pieces_json"] or "[]"),
            "imagem": row["image_path"], "autor": "Pessoa da comunidade", "data": row["created_at"],
            "salvo": bool(saved_ids and row["id"] in saved_ids),
        }
        if owner_view:
            data["status"] = row["status"]
            data["chave_local"] = row["local_key"]
        return data

    FEEDBACK_REASONS = ("Não combina comigo", "Não serve para o clima", "Não serve para a ocasião",
                        "Pouco confortável", "Já uso muito essas peças", "Outro motivo")

    def _feedback_routes(self, db: sqlite3.Connection, method: str, payload: dict[str, Any], user: sqlite3.Row) -> tuple[Any, int]:
        """Feedback 👍/👎 dos looks da IA (Change 030); gravado só por ação explícita da pessoa."""
        if method == "GET":
            rows = db.execute(
                "SELECT * FROM look_feedback WHERE user_id=? ORDER BY id DESC LIMIT 30", (user["id"],),
            ).fetchall()
            return {"feedbacks": [{"id": row["id"], "nome": row["look_name"], "roupa_chaves": json.loads(row["garment_keys"]),
                                   "avaliacao": "positivo" if row["rating"] > 0 else "negativo", "motivo": row["reason"],
                                   "ocasiao": row["occasion"], "clima": row["weather"], "created_at": row["created_at"]} for row in rows]}, 200
        if method == "POST":
            rating = {"positivo": 1, "negativo": -1}.get(str(payload.get("avaliacao") or ""))
            if rating is None:
                return {"message": "Avaliação inválida."}, 400
            reason = str(payload.get("motivo") or "").strip()
            if rating < 0 and reason not in self.FEEDBACK_REASONS:
                return {"message": "Escolha um motivo válido."}, 400
            if rating > 0:
                reason = ""
            keys = payload.get("roupa_chaves") or []
            if not isinstance(keys, list) or len(keys) > 12:
                return {"message": "Peças inválidas."}, 400
            owned = {row["local_key"] for row in db.execute("SELECT local_key FROM wardrobe_items WHERE user_id=?", (user["id"],))}
            keys = sorted({str(key) for key in keys if str(key) in owned})
            cursor = db.execute(
                "INSERT INTO look_feedback(user_id,look_name,garment_keys,rating,reason,occasion,weather,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (user["id"], str(payload.get("nome") or "")[:80], json.dumps(keys), rating, reason,
                 str(payload.get("ocasiao") or "")[:40], str(payload.get("clima") or "")[:30], _stamp()),
            )
            return {"id": cursor.lastrowid, "ok": True}, 201
        if method == "DELETE":
            cursor = db.execute("DELETE FROM look_feedback WHERE user_id=?", (user["id"],))
            return {"apagados": cursor.rowcount, "ok": True}, 200
        return {"message": "Método não permitido."}, 405

    def _inspiration_routes(self, db: sqlite3.Connection, method: str, endpoint: str, payload: dict[str, Any],
                            query: dict[str, Any], user: sqlite3.Row | None, headers: dict[str, str] | None) -> tuple[Any, int] | None:
        base = endpoint.split("/", 1)[0]
        if base not in {"feedInspiracoes", "minhasInspiracoes", "publicarInspiracao", "inspiracoesSalvas", "adminInspiracoes"}:
            return None

        if base == "feedInspiracoes" and method == "GET":
            clauses, params = ["status='Publicado'"], []
            for field, column, allowed in (("ocasiao", "occasion", self.INSPIRATION_OCCASIONS), ("clima", "weather_category", self.INSPIRATION_WEATHER), ("regiao", "region", self.INSPIRATION_REGIONS)):
                value = str(query.get(field) or "").strip()
                if value:
                    if value not in allowed:
                        return {"message": f"Filtro de {field} inválido."}, 400
                    clauses.append(f"{column}=?")
                    params.append(value)
            try:
                page = max(1, int(query.get("pagina") or 1))
            except (TypeError, ValueError):
                page = 1
            size = self.INSPIRATION_PAGE_SIZE
            rows = db.execute(
                f"SELECT * FROM inspirations WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT ? OFFSET ?",
                (*params, size + 1, (page - 1) * size),
            ).fetchall()
            return {"inspiracoes": [self._inspiration_dict(r) for r in rows[:size]], "pagina": page, "tem_mais": len(rows) > size}, 200

        if base == "adminInspiracoes":
            self._require_admin(db, headers)
            if method == "GET":
                rows = db.execute("SELECT * FROM inspirations WHERE status IN ('Pendente','Publicado','Recusado') ORDER BY status='Pendente' DESC, id DESC LIMIT 100").fetchall()
                return {"inspiracoes": [self._inspiration_dict(r, owner_view=True) for r in rows]}, 200
            if method == "PATCH":
                status = str(payload.get("status") or "").strip()
                if status not in {"Publicado", "Recusado"}:
                    return {"message": "Escolha publicar ou recusar a inspiração."}, 400
                cursor = db.execute("UPDATE inspirations SET status=?,moderated_at=? WHERE id=? AND status<>'Privado'", (status, _stamp(), self._path_int(endpoint)))
                return ({"ok": True, "status": status}, 200) if cursor.rowcount else ({"message": "Inspiração não encontrada."}, 404)
            return {"message": "Método não suportado."}, 405

        assert user is not None
        if base == "minhasInspiracoes" and method == "GET":
            own = db.execute("SELECT * FROM inspirations WHERE user_id=? ORDER BY id DESC LIMIT 200", (user["id"],)).fetchall()
            saved = db.execute(
                "SELECT i.* FROM inspiration_saves s JOIN inspirations i ON i.id=s.inspiration_id WHERE s.user_id=? AND i.status='Publicado' ORDER BY s.created_at DESC LIMIT 200",
                (user["id"],),
            ).fetchall()
            saved_ids = {r["id"] for r in saved}
            return {
                "criadas": [self._inspiration_dict(r, owner_view=True) for r in own],
                "salvas": [self._inspiration_dict(r, saved_ids=saved_ids) for r in saved],
            }, 200
        if base == "minhasInspiracoes" and method == "POST":
            data = self._clean_inspiration(payload)
            existing = db.execute("SELECT * FROM inspirations WHERE local_key=?", (data["local_key"],)).fetchone()
            if existing:
                if existing["user_id"] != user["id"]:
                    raise PermissionError("A chave já está vinculada a outra conta.")
                return {"inspiracao": self._inspiration_dict(existing, owner_view=True)}, 200
            columns = ", ".join(data)
            cursor = db.execute(
                f"INSERT INTO inspirations(user_id, {columns}, created_at) VALUES(?, {', '.join('?' for _ in data)}, ?)",
                (user["id"], *data.values(), _stamp()),
            )
            row = db.execute("SELECT * FROM inspirations WHERE id=?", (cursor.lastrowid,)).fetchone()
            return {"inspiracao": self._inspiration_dict(row, owner_view=True)}, 201
        if base == "minhasInspiracoes" and method == "DELETE":
            cursor = db.execute("DELETE FROM inspirations WHERE id=? AND user_id=?", (self._path_int(endpoint), user["id"]))
            return ({"deleted": True}, 200) if cursor.rowcount else ({"message": "Inspiração não encontrada."}, 404)
        if base == "publicarInspiracao" and method == "POST":
            if payload.get("autorizo_publicacao") is not True:
                return {"message": "Autorize a publicação anônima para enviar ao feed."}, 400
            cursor = db.execute(
                "UPDATE inspirations SET status='Pendente', moderated_at=NULL WHERE id=? AND user_id=? AND status IN ('Privado','Recusado')",
                (self._path_int(endpoint), user["id"]),
            )
            return ({"ok": True, "status": "Pendente"}, 200) if cursor.rowcount else ({"message": "Inspiração não encontrada ou já enviada."}, 404)
        if base == "inspiracoesSalvas" and method == "POST":
            inspiration_id = self._path_int(endpoint)
            if not db.execute("SELECT 1 FROM inspirations WHERE id=? AND status='Publicado'", (inspiration_id,)).fetchone():
                raise LookupError("Inspiração não encontrada.")
            db.execute("INSERT OR IGNORE INTO inspiration_saves(user_id,inspiration_id,created_at) VALUES(?,?,?)", (user["id"], inspiration_id, _stamp()))
            return {"ok": True, "salvo": True}, 200
        if base == "inspiracoesSalvas" and method == "DELETE":
            db.execute("DELETE FROM inspiration_saves WHERE user_id=? AND inspiration_id=?", (user["id"], self._path_int(endpoint)))
            return {"ok": True, "salvo": False}, 200
        return {"message": "Rota de inspirações não encontrada."}, 404

    @staticmethod
    def _path_int(endpoint: str) -> int:
        try:
            return int(endpoint.rsplit("/", 1)[1])
        except (IndexError, ValueError):
            raise ValueError("Identificador inválido.")

    @staticmethod
    def _wardrobe_dict(row: sqlite3.Row) -> dict[str, Any]:
        image_data = row["image_data"]
        image_mime = row["image_mime"]
        image_url = row["image_url"]
        if image_data and image_mime:
            image_url = f"data:{image_mime};base64,{base64.b64encode(image_data).decode('ascii')}"
        return {"id": row["id"], "chave_local": row["local_key"], "nome": row["name"],
                "categoria": row["category"], "status": row["status"], "cor": row["color"],
                "estacao": row["season"], "tamanho": row["size"], "marca": row["brand"],
                "imagem_url": image_url, "preco_compra": _as_price(row["purchase_price_cents"]) if row["purchase_price_cents"] is not None else "", "created_at": row["created_at"]}

    @staticmethod
    def _look_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "chave_local": row["local_key"], "nome": row["name"],
                "ocasiao": row["occasion"], "data_planejada": row["planned_date"],
                "roupa_chaves": json.loads(row["garment_keys"]), "created_at": row["created_at"]}

    @staticmethod
    def _order_row(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "Total": _as_price(row["total_cents"]), "status": row["status"],
                "pagamento_status": row["payment_status"], "pagamento": {"status_gateway": row["payment_status"], "pago_confirmado": bool(row["paid"])}, "checkout_url": row["checkout_url"], "provedor": "Mercado Pago" if row["gateway"] == "mercadopago" else "Sem cobrança",
                "paid": bool(row["paid"]), "reservation_expires_at": row["reservation_expires_at"], "created_at": row["created_at"]}

    @staticmethod
    def _device_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {"id": row["id"], "nome": row["name"], "tipo": "Demonstração local",
                "status": row["status"], "ultimo_contato": row["last_seen"], "identificador": row["identifier"]}

    def _request_password_reset(self, db: sqlite3.Connection, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        smtp_host = os.environ.get("OSDROUPA_SMTP_HOST", "").strip()
        smtp_from = os.environ.get("OSDROUPA_SMTP_FROM", "").strip()
        email = str(payload.get("email") or "").strip().casefold()
        row = db.execute("SELECT id,email,name FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if not smtp_host or not smtp_from:
            local_enabled = os.environ.get("OSDROUPA_LOCAL_RECOVERY", "1").strip().lower() in {"1", "true", "yes", "on"}
            if not local_enabled:
                return {"message": "Recuperação por e-mail indisponível: configure SMTP no ambiente local."}, 503
            token = secrets.token_urlsafe(32)
            if row is not None:
                expires = _stamp(_now() + timedelta(minutes=RESET_MINUTES))
                db.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (row["id"],))
                db.execute(
                    "INSERT INTO password_reset_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",
                    (self._token_hash(token), row["id"], expires, _stamp()),
                )
            return {
                "message": "Link local de redefinição criado. Nenhum e-mail foi enviado; use o link neste navegador em até 30 minutos.",
                "reset_url": f"/redefinir-senha?token={token}",
            }, 200
        if row is None:
            return {"message": "Se houver uma conta para esse e-mail, as instruções serão enviadas."}, 200
        token = secrets.token_urlsafe(32)
        expires = _stamp(_now() + timedelta(minutes=RESET_MINUTES))
        db.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (row["id"],))
        db.execute("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",
                   (self._token_hash(token), row["id"], expires, _stamp()))
        public_url = os.environ.get("OSDROUPA_PUBLIC_URL", "http://localhost:3001").rstrip("/")
        reset_url = f"{public_url}/redefinir-senha?token={token}"
        message = EmailMessage()
        message["Subject"] = "Redefinição de senha OSDROUPA"
        message["From"] = smtp_from
        message["To"] = row["email"]
        message.set_content(f"Olá, {row['name']}. Use este link em até {RESET_MINUTES} minutos para trocar sua senha:\n\n{reset_url}\n\nSe você não solicitou a troca, ignore esta mensagem.")
        try:
            port = int(os.environ.get("OSDROUPA_SMTP_PORT", "587"))
            username = os.environ.get("OSDROUPA_SMTP_USER", "")
            password = os.environ.get("OSDROUPA_SMTP_PASSWORD", "")
            with smtplib.SMTP(smtp_host, port, timeout=15) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException, ValueError):
            db.execute("DELETE FROM password_reset_tokens WHERE token_hash=?", (self._token_hash(token),))
            return {"message": "O serviço de e-mail não conseguiu enviar as instruções. Tente novamente mais tarde."}, 503
        return {"message": "Se houver uma conta para esse e-mail, as instruções serão enviadas."}, 200

    def _reset_password(self, db: sqlite3.Connection, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        token = str(payload.get("token") or "").strip()
        password = str(payload.get("senha") or payload.get("password") or "")
        if len(password) < 8 or not (any(c.isupper() for c in password) and any(c.isdigit() for c in password) and any(not c.isalnum() for c in password)):
            return {"message": "A senha precisa ter pelo menos 8 caracteres, maiúscula, número e símbolo."}, 400
        row = db.execute("SELECT * FROM password_reset_tokens WHERE token_hash=? AND expires_at>?", (self._token_hash(token), _stamp())).fetchone()
        if row is None:
            return {"message": "O link de redefinição é inválido ou expirou."}, 400
        salt_hex, digest_hex = self._hash_password(password)
        db.execute("UPDATE users SET password_salt=?,password_hash=? WHERE id=?", (salt_hex, digest_hex, row["user_id"]))
        db.execute("DELETE FROM sessions WHERE user_id=?", (row["user_id"],))
        db.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (row["user_id"],))
        return {"ok": True}, 200

    def dispatch(self, method: str, url: str, *, headers: dict[str, str] | None = None,
                 payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> httpx.Response:
        try:
            body, status = self._dispatch(method, url, headers, payload or {}, params or {})
        except PermissionError as exc:
            body, status = {"message": str(exc)}, 401 if "expirada" in str(exc).lower() or "inválida" in str(exc).lower() else 403
        except LookupError as exc:
            body, status = {"message": str(exc)}, 404
        except ValueError as exc:
            body, status = {"message": str(exc)}, 400
        except sqlite3.IntegrityError:
            body, status = {"message": "A alteração não passou pelas regras de integridade."}, 409
        except sqlite3.Error:
            body, status = {"message": "Não foi possível acessar o banco local."}, 500
        return _response(method, url, status, body)


local_backend = LocalBackend()


def set_admin(email: str) -> bool:
    """Promote a local account from an operator-controlled shell command."""
    local_backend.initialize()
    with local_backend._db() as db:
        cursor = db.execute("UPDATE users SET role='admin' WHERE email=? COLLATE NOCASE", (email.strip(),))
        return cursor.rowcount == 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Administração segura do banco local OSDROUPA")
    parser.add_argument("command", choices=["set-admin"])
    parser.add_argument("email")
    args = parser.parse_args()
    if args.command == "set-admin" and set_admin(args.email):
        print("Papel admin atualizado para a conta informada.")
    else:
        raise SystemExit("Conta não encontrada; nenhum papel foi alterado.")
