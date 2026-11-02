"""Imagem do look (Change 027): referências, anti-SSRF e chamada.

A geração usa um cliente FALSO (MOCK); nenhuma imagem real é gerada nem cobrada.
"""

import asyncio
import base64
from types import SimpleNamespace as NS

import pytest
from google.genai import errors

from OSDroupa.ai import imaging as im

PNG = base64.b64encode(b"\x89PNG fake").decode()
PIECES = [
    {"papel": "Cima", "nome": "Camisa", "descricao": "", "imagem_url": f"data:image/png;base64,{PNG}"},
    {"papel": "Calçado", "nome": "Tênis", "descricao": "", "imagem_url": ""},
]


def test_data_uri_references():
    assert asyncio.run(im.load_reference(f"data:image/png;base64,{PNG}")) == (b"\x89PNG fake", "image/png")
    assert asyncio.run(im.load_reference("data:text/html;base64,PGI+")) is None
    assert asyncio.run(im.load_reference("data:image/png;base64,@@@")) is None


@pytest.mark.parametrize("url", [
    "http://example.com/a.png", "https://127.0.0.1/a.png", "https://localhost/a.png",
    "https://10.0.0.5/a.png", "https://169.254.169.254/latest", "ftp://x/a.png",
    "file:///c:/a.png", "/../requirements.txt", "/products/inexistente.png",
])
def test_blocked_references(url):
    assert asyncio.run(im.load_reference(url)) is None


def test_svg_assets_are_not_references():
    assert asyncio.run(im.load_reference("/products/blazer.svg")) is None


def test_prompt():
    prompt = im.build_prompt("Look A", [{"papel": "Parte de cima", "nome": "Camisa", "descricao": "aberta"}], "bege", "linho", True)
    assert "Camisa (aberta)" in prompt and "fotos das peças reais" in prompt and "sem rosto" in prompt
    assert "fotos das peças reais" not in im.build_prompt("L", [], "", "", False)


class FakeInteractions:
    """MOCK da Interactions API do Gemini."""

    def __init__(self, result):
        self.result, self.calls = result, []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def fake_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("OSDROUPA_IMAGES_ENABLED", "true")

    def install(result):
        fake = FakeInteractions(result)
        monkeypatch.setattr(im, "_client", NS(aio=NS(interactions=fake)))
        return fake
    return install


def test_disabled_by_default_even_with_key(monkeypatch, tmp_path):
    """A geração de imagens é paga: a chave sozinha não liga o recurso."""
    monkeypatch.delenv("OSDROUPA_IMAGES_ENABLED", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    called = []
    monkeypatch.setattr(im, "_client", NS(aio=NS(interactions=NS(create=lambda **kw: called.append(kw)))))
    assert not im.images_enabled() and not im.is_configured()
    with pytest.raises(im.ImageUnavailable, match="desativada"):
        asyncio.run(im.generate_look_image("L", PIECES, "", "", tmp_path))
    assert called == []


@pytest.mark.parametrize("value,enabled", [("true", True), ("1", True), ("sim", True), ("false", False), ("", False), ("talvez", False)])
def test_enabled_flag_values(monkeypatch, value, enabled):
    monkeypatch.setenv("OSDROUPA_IMAGES_ENABLED", value)
    assert im.images_enabled() is enabled


def test_enabled_without_key(monkeypatch, tmp_path):
    monkeypatch.setenv("OSDROUPA_IMAGES_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(im.ImageUnavailable, match="não está configurada"):
        asyncio.run(im.generate_look_image("L", [], "", "", tmp_path))


def test_generate_writes_file(fake_gemini, tmp_path):
    fake = fake_gemini(NS(output_image=NS(data=base64.b64encode(b"IMG").decode(), mime_type="image/png")))
    name = asyncio.run(im.generate_look_image("Look A", PIECES, "bege", "linho", tmp_path))
    assert (tmp_path / name).read_bytes() == b"IMG" and name.endswith(".png")
    kwargs = fake.calls[0]
    assert kwargs["response_format"]["type"] == "image"
    assert [c["type"] for c in kwargs["input"]] == ["image", "text"] and kwargs["input"][0]["data"] == PNG


@pytest.mark.parametrize("result,message", [
    (NS(output_image=None), "não devolveu"),
    (errors.ClientError(429, {"error": {"message": "quota"}}), "muito requisitado"),
    (errors.ClientError(400, {"error": {"message": "bad"}}), "recusou"),
    (errors.ServerError(503, {"error": {"message": "x"}}), "indisponível"),
])
def test_generate_errors(fake_gemini, tmp_path, result, message):
    fake_gemini(result)
    with pytest.raises(im.ImageUnavailable, match=message):
        asyncio.run(im.generate_look_image("L", PIECES, "", "", tmp_path))
    assert list(tmp_path.iterdir()) == []
