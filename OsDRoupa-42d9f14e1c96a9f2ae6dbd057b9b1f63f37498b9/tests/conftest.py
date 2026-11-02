"""Configuração compartilhada dos testes.

Isolamento obrigatório: antes de importar qualquer módulo do projeto, o banco
SQLite é apontado para uma pasta temporária e as chaves de API são removidas.
Os dados reais em data/ nunca são abertos pelos testes.
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TEST_DIR = Path(tempfile.mkdtemp(prefix="osdroupa-tests-"))

os.environ["OSDROUPA_DISABLE_DOTENV"] = "1"  # nunca ler o .env real (chaves) nos testes
os.environ["OSDROUPA_DB_PATH"] = str(_TEST_DIR / "global.sqlite3")
os.environ["OSDROUPA_BACKEND"] = "sqlite"
os.environ["OSDROUPA_ADMIN_EMAIL"] = "admin@teste.osdroupa"
for _secret in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL", "OSDROUPA_IMAGES_ENABLED", "MERCADOPAGO_ACCESS_TOKEN", "MERCADOPAGO_WEBHOOK_SECRET"):
    os.environ.pop(_secret, None)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402

from professormateria import local_backend as local_backend_module  # noqa: E402
from professormateria.local_backend import LocalBackend  # noqa: E402

REAL_DATA_DIR = (PROJECT_ROOT / "data").resolve()
assert REAL_DATA_DIR not in local_backend_module.local_backend.db_path.resolve().parents, (
    "Os testes não podem usar o banco real em data/."
)

XANO_BASE = "https://x8ki-letl-twmt.n7.xano.io"
AUTH_API = "/api:nqm5-KuC/auth/"
PDB_API = "/api:6LtoY7Zt/"
PASSWORD = "Senha@123"


@pytest.fixture
def backend(tmp_path) -> LocalBackend:
    """Backend SQLite novo em banco temporário, um por teste."""
    return LocalBackend(tmp_path / "test.sqlite3")


class Api:
    """Atalho para chamar o backend local como o XanoAsyncClient faz."""

    def __init__(self, backend: LocalBackend):
        self.backend = backend

    def call(self, method: str, endpoint: str, token: str | None = None, payload: dict | None = None,
             params: dict | None = None, api: str = PDB_API) -> tuple[int, dict]:
        response = self.backend.dispatch(
            method, XANO_BASE + api + endpoint,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            payload=payload, params=params,
        )
        return response.status_code, response.json()

    def register(self, email: str, password: str = PASSWORD) -> tuple[int, dict]:
        return self.call("POST", "cadastraCliente", payload={
            "nome": "Pessoa Teste", "email": email, "celular": "11999999999",
            "senha": password, "aceitou_termos": True,
        })

    def login(self, email: str, password: str = PASSWORD) -> tuple[int, dict]:
        return self.call("POST", "login", payload={"email": email, "password": password}, api=AUTH_API)

    def account(self, email: str | None = None) -> str:
        email = email or f"{uuid.uuid4().hex[:10]}@teste.osdroupa"
        status, body = self.register(email)
        assert status in (200, 201), body
        status, body = self.login(email)
        assert status == 200, body
        return body["authToken"]


@pytest.fixture
def api(backend) -> Api:
    return Api(backend)
