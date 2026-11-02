"""Roteamento do XanoAsyncClient nos modos SQLite e Xano.

No modo Xano, a rede é substituída por um httpx.MockTransport (MOCK): isso
verifica o roteamento e o tratamento do 429, não o workspace Xano real.
"""

import asyncio

import httpx

import OSDroupa.OSDroupa as app
from conftest import XANO_BASE


def test_sqlite_mode_routes_to_local_backend(monkeypatch, backend):
    monkeypatch.setenv("OSDROUPA_BACKEND", "sqlite")
    monkeypatch.setattr("professormateria.local_backend.local_backend", backend)

    def network_must_not_be_used(request):
        raise AssertionError(f"rede usada no modo SQLite: {request.url}")

    async def run():
        async with app.XanoAsyncClient(transport=httpx.MockTransport(network_must_not_be_used)) as client:
            return await client.get(f"{app.XANO_PDB}/feedInspiracoes")

    response = asyncio.run(run())
    assert response.status_code == 200 and response.json()["inspiracoes"] == []


def test_xano_mode_uses_network_mock(monkeypatch, backend):
    monkeypatch.setenv("OSDROUPA_BACKEND", "xano")
    monkeypatch.setattr("professormateria.local_backend.local_backend", backend)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"inspiracoes": [{"id": 1}]})

    async def run():
        async with app.XanoAsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await client.get(f"{app.XANO_PDB}/feedInspiracoes")

    response = asyncio.run(run())
    assert seen and seen[0].startswith(XANO_BASE) and response.json()["inspiracoes"][0]["id"] == 1


def test_xano_mode_429_pauses_shared_limiter(monkeypatch, backend):
    monkeypatch.setenv("OSDROUPA_BACKEND", "xano")
    monkeypatch.setattr("professormateria.local_backend.local_backend", backend)
    paused = []
    monkeypatch.setattr(backend, "pause_rate_limit", lambda bucket, seconds: paused.append((bucket, seconds)))

    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "7"}, json={"message": "limite"})

    async def run():
        async with app.XanoAsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await client.get(f"{app.XANO_PDB}/meuArmario")

    response = asyncio.run(run())
    assert response.status_code == 429 and paused == [("xano", 7)]
    assert "7" in app._xano_rate_limit_message(response)


def test_non_xano_urls_are_not_rerouted(monkeypatch, backend):
    monkeypatch.setenv("OSDROUPA_BACKEND", "sqlite")
    monkeypatch.setattr("professormateria.local_backend.local_backend", backend)

    def handler(request):
        return httpx.Response(200, json={"cep": "ok"})

    async def run():
        async with app.XanoAsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await client.get("https://viacep.com.br/ws/01001000/json/")

    assert asyncio.run(run()).json() == {"cep": "ok"}
