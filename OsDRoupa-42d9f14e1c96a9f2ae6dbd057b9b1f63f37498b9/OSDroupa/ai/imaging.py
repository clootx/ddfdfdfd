"""Imagem editorial do look com a API Gemini do Google (Change 027).

Executado somente no servidor Reflex. A chave vem de GEMINI_API_KEY. As fotos
reais das peças vão como referência para a imagem ficar próxima do acervo.
Toda imagem gerada pelo Gemini contém a marca d'água SynthID.
"""

import asyncio
import base64
import ipaddress
import logging
import os
import socket
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from google import genai
from google.genai import errors as genai_errors
# A Interactions API do google-genai 2.x lança estas classes, que não herdam de google.genai.errors.
from google.genai._interactions import APIConnectionError, APIStatusError, APITimeoutError

logger = logging.getLogger("osdroupa.imaging")

DEFAULT_MODEL = "gemini-nano-banana-2.1"
REQUEST_TIMEOUT = 120.0  # segundos
MAX_REFERENCES = 10
MAX_REFERENCE_BYTES = 4 * 1024 * 1024
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}


class ImageUnavailable(Exception):
    """Geração de imagem indisponível; a mensagem é segura para exibir ao usuário."""

    def __init__(self, message: str, reason: str = "unavailable"):
        super().__init__(message)
        self.reason = reason


def images_enabled() -> bool:
    """Geração de imagens é paga (sem plano gratuito); precisa de ativação explícita."""
    return os.environ.get("OSDROUPA_IMAGES_ENABLED", "false").strip().lower() in {"1", "true", "sim", "yes"}


def is_configured() -> bool:
    return images_enabled() and bool(os.environ.get("GEMINI_API_KEY", "").strip())


def model_name() -> str:
    return os.environ.get("OSDROUPA_IMAGE_MODEL", "").strip() or DEFAULT_MODEL



# ── Referências (fotos reais das peças) ─────────────────────────────────────
def _decode_data_uri(uri: str) -> tuple[bytes, str] | None:
    header, _, payload = uri.partition(",")
    mime = header[5:].split(";")[0].lower()
    if mime not in ALLOWED_MIME or ";base64" not in header:
        return None
    try:
        data = base64.b64decode(payload, validate=True)
    except ValueError:
        return None
    return (data, mime) if len(data) <= MAX_REFERENCE_BYTES else None


def _read_asset(path: str) -> tuple[bytes, str] | None:
    target = (ASSETS_DIR / path.lstrip("/")).resolve()
    if ASSETS_DIR not in target.parents or not target.is_file():
        return None
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(target.suffix.lower())
    if not mime or target.stat().st_size > MAX_REFERENCE_BYTES:
        return None
    return target.read_bytes(), mime


def _is_public_host(host: str) -> bool:
    """Evita SSRF: só busca imagens em hosts que resolvem para IPs públicos."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    return bool(infos) and all(ipaddress.ip_address(info[4][0]).is_global for info in infos)


async def _fetch_https(url: str) -> tuple[bytes, str] | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if not await asyncio.to_thread(_is_public_host, parsed.hostname):
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            async with client.stream("GET", url) as response:
                mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if response.status_code != 200 or mime not in ALLOWED_MIME:
                    return None
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_REFERENCE_BYTES:
                        return None
                    chunks.append(chunk)
        return b"".join(chunks), mime
    except httpx.HTTPError:
        return None


async def load_reference(image_url: str) -> tuple[bytes, str] | None:
    url = (image_url or "").strip()
    if url.startswith("data:"):
        return _decode_data_uri(url)
    if url.startswith("/"):
        return _read_asset(url)
    if url.startswith("https://"):
        return await _fetch_https(url)
    return None


# ── Prompt e chamada ────────────────────────────────────────────────────────
def build_prompt(look_name: str, pieces: list[dict], palette: str, fabrics: str, with_references: bool) -> str:
    lines = [f"- {p['papel']}: {p['nome']}" + (f" ({p['descricao']})" if p.get("descricao") else "") for p in pieces]
    reference_note = (
        "As imagens enviadas são fotos das peças reais da pessoa; reproduza cada peça com a mesma cor, modelagem e detalhes. "
        if with_references else ""
    )
    return (
        "Fotografia editorial de moda brasileira, de corpo inteiro, de um look completo vestido em um manequim invisível, "
        "fundo neutro claro, luz natural suave, todas as peças inteiras e visíveis, sem pessoas, sem rosto, sem texto e sem logotipos. "
        f"{reference_note}"
        f"Look \"{look_name}\" composto por:\n" + "\n".join(lines) +
        (f"\nPaleta: {palette}." if palette else "") +
        (f"\nTecidos: {fabrics}." if fabrics else "")
    )


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    return _client


async def generate_look_image(look_name: str, pieces: list[dict], palette: str, fabrics: str, output_dir: Path) -> str:
    """Gera a imagem do look e salva em `output_dir`; devolve o nome do arquivo."""
    if not images_enabled():
        raise ImageUnavailable("A geração de imagens está desativada (OSDROUPA_IMAGES_ENABLED=false).")
    if not is_configured():
        raise ImageUnavailable("A geração de imagens não está configurada.")
    references = []
    for piece in pieces:
        if len(references) >= MAX_REFERENCES:
            break
        loaded = await load_reference(piece.get("imagem_url", ""))
        if loaded:
            references.append(loaded)
    prompt = build_prompt(look_name, pieces, palette, fabrics, bool(references))
    content = [
        *[{"type": "image", "data": base64.b64encode(data).decode("ascii"), "mime_type": mime} for data, mime in references],
        {"type": "text", "text": prompt},
    ]
    try:
        interaction = await asyncio.wait_for(
            _get_client().aio.interactions.create(
                model=model_name(),
                input=content,
                response_format={"type": "image", "aspect_ratio": "3:4", "image_size": "1K"},
            ),
            timeout=REQUEST_TIMEOUT,
        )
    except (asyncio.TimeoutError, APITimeoutError) as exc:
        raise ImageUnavailable("A geração da imagem demorou demais.") from exc
    except (genai_errors.ClientError, APIStatusError) as exc:
        # A Interactions API lança APIStatusError (status_code); o formato antigo, ClientError (code).
        code = getattr(exc, "status_code", None) or getattr(exc, "code", 0)
        logger.warning("Gemini imagem erro HTTP %s", code)
        if code == 429:
            raise ImageUnavailable("O serviço de imagens está muito requisitado agora.", reason="quota") from exc
        if isinstance(code, int) and code >= 500:
            raise ImageUnavailable("O serviço de imagens está indisponível no momento.") from exc
        raise ImageUnavailable("O serviço de imagens recusou este pedido.") from exc
    except (genai_errors.APIError, APIConnectionError, httpx.HTTPError) as exc:
        logger.warning("Gemini indisponível: %s", type(exc).__name__)
        raise ImageUnavailable("O serviço de imagens está indisponível no momento.") from exc
    except Exception as exc:  # ex.: HTTP 200 com corpo inválido ou erro novo do SDK
        logger.warning("Gemini imagem erro inesperado: %s", type(exc).__name__)
        raise ImageUnavailable("O serviço de imagens está indisponível no momento.") from exc

    image = getattr(interaction, "output_image", None)
    data = getattr(image, "data", None)
    if not data:
        raise ImageUnavailable("O serviço de imagens não devolveu uma imagem para este look.")
    try:
        raw = base64.b64decode(data) if isinstance(data, str) else bytes(data)
    except (ValueError, TypeError) as exc:
        raise ImageUnavailable("O serviço de imagens devolveu uma imagem inválida.") from exc
    mime = str(getattr(image, "mime_type", "") or "image/png")
    extension = {"image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime, ".png")
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    (output_dir / filename).write_bytes(raw)
    logger.info("imagem model=%s refs=%d bytes=%d", model_name(), len(references), len(raw))
    return filename
