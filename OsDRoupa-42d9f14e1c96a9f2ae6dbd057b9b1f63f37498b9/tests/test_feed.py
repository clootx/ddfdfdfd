"""Inspirações e feed (Change 028): backend SQLite temporário + conversão no estado."""

import uuid

import pytest

from OSDroupa.OSDroupa import Inspiration, InspirationState


def inspiration_payload(**overrides):
    payload = {
        "chave_local": uuid.uuid4().hex, "nome": "Linho no calor", "ocasiao": "Trabalho", "clima": "Quente",
        "regiao": "Nordeste", "estacao": "Primavera", "paleta": "bege", "tecidos": "linho",
        "justificativa": "33 °C", "nota": "4,2", "imagem": f"looks/{'a' * 32}.png",
        "pecas": [
            {"papel": "Cima", "nome": "Camisa", "origem": "armario", "imagem_url": "data:image/png;base64,SEGREDO"},
            {"papel": "Calçado", "nome": "Tênis", "origem": "catalogo", "imagem_url": "/products/canvas-sneakers.svg"},
            {"papel": "Bolsa", "nome": "X", "origem": "catalogo", "imagem_url": "javascript:alert(1)"},
        ],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def owner(api):
    return api.account()


def test_create_sanitizes_pieces_and_is_idempotent(api, owner):
    payload = inspiration_payload()
    status, body = api.call("POST", "minhasInspiracoes", owner, payload)
    assert status == 201 and body["inspiracao"]["status"] == "Privado"
    pieces = body["inspiracao"]["pecas"]
    assert pieces[0]["imagem_url"] == "" and pieces[1]["imagem_url"] == "/products/canvas-sneakers.svg" and pieces[2]["imagem_url"] == ""
    assert "SEGREDO" not in str(body)
    assert api.call("POST", "minhasInspiracoes", owner, payload)[0] == 200
    assert api.call("POST", "minhasInspiracoes", api.account(), payload)[0] == 403


@pytest.mark.parametrize("override", [
    {"imagem": "https://evil/x.png"}, {"pecas": []}, {"chave_local": "curta"}, {"ocasiao": "Balada"}, {"nome": ""},
])
def test_create_rejects_invalid(api, owner, override):
    assert api.call("POST", "minhasInspiracoes", owner, inspiration_payload(**override))[0] == 400


def test_publication_flow_and_moderation(api, owner):
    iid = api.call("POST", "minhasInspiracoes", owner, inspiration_payload())[1]["inspiracao"]["id"]
    other, admin = api.account(), api.account("admin@teste.osdroupa")
    assert api.call("GET", "feedInspiracoes")[1]["inspiracoes"] == []
    assert api.call("POST", f"publicarInspiracao/{iid}", owner, {})[0] == 400
    assert api.call("POST", f"publicarInspiracao/{iid}", other, {"autorizo_publicacao": True})[0] == 404
    assert api.call("POST", f"publicarInspiracao/{iid}", owner, {"autorizo_publicacao": True})[1]["status"] == "Pendente"
    assert api.call("GET", "feedInspiracoes")[1]["inspiracoes"] == []
    assert api.call("POST", f"inspiracoesSalvas/{iid}", other)[0] == 404
    assert api.call("GET", "adminInspiracoes", owner)[0] == 403
    assert api.call("GET", "adminInspiracoes", admin)[1]["inspiracoes"][0]["status"] == "Pendente"
    assert api.call("PATCH", f"adminInspiracoes/{iid}", admin, {"status": "Apagado"})[0] == 400
    assert api.call("PATCH", f"adminInspiracoes/{iid}", admin, {"status": "Publicado"})[0] == 200
    item = api.call("GET", "feedInspiracoes")[1]["inspiracoes"][0]
    assert item["autor"] == "Pessoa da comunidade"
    assert not {"status", "chave_local", "user_id"} & set(item)


def test_filters_and_saves(api, owner):
    iid = api.call("POST", "minhasInspiracoes", owner, inspiration_payload())[1]["inspiracao"]["id"]
    admin, other = api.account("admin@teste.osdroupa"), api.account()
    api.call("POST", f"publicarInspiracao/{iid}", owner, {"autorizo_publicacao": True})
    api.call("PATCH", f"adminInspiracoes/{iid}", admin, {"status": "Publicado"})
    assert api.call("GET", "feedInspiracoes", params={"regiao": "Sul"})[1]["inspiracoes"] == []
    assert len(api.call("GET", "feedInspiracoes", params={"ocasiao": "Trabalho", "clima": "Quente", "regiao": "Nordeste"})[1]["inspiracoes"]) == 1
    assert api.call("GET", "feedInspiracoes", params={"regiao": "Marte"})[0] == 400
    assert api.call("POST", f"inspiracoesSalvas/{iid}", other)[0] == 200
    assert api.call("POST", f"inspiracoesSalvas/{iid}", other)[0] == 200
    mine = api.call("GET", "minhasInspiracoes", other)[1]
    assert mine["criadas"] == [] and mine["salvas"][0]["salvo"] is True
    assert api.call("DELETE", f"inspiracoesSalvas/{iid}", other)[0] == 200
    assert api.call("GET", "minhasInspiracoes", other)[1]["salvas"] == []


def test_delete_only_by_owner_and_auth_required(api, owner):
    iid = api.call("POST", "minhasInspiracoes", owner, inspiration_payload())[1]["inspiracao"]["id"]
    assert api.call("DELETE", f"minhasInspiracoes/{iid}", api.account())[0] == 404
    assert api.call("DELETE", f"minhasInspiracoes/{iid}", owner)[0] == 200
    assert api.call("GET", "minhasInspiracoes")[0] == 401


def test_feed_pagination(api, owner):
    admin = api.account("admin@teste.osdroupa")
    for _ in range(26):
        iid = api.call("POST", "minhasInspiracoes", owner, inspiration_payload())[1]["inspiracao"]["id"]
        api.call("POST", f"publicarInspiracao/{iid}", owner, {"autorizo_publicacao": True})
        api.call("PATCH", f"adminInspiracoes/{iid}", admin, {"status": "Publicado"})
    first = api.call("GET", "feedInspiracoes")[1]
    second = api.call("GET", "feedInspiracoes", params={"pagina": 2})[1]
    assert len(first["inspiracoes"]) == 24 and first["tem_mais"]
    assert len(second["inspiracoes"]) == 2 and not second["tem_mais"]


def test_state_conversion(api, owner):
    created = api.call("POST", "minhasInspiracoes", owner, inspiration_payload())[1]["inspiracao"]
    item = InspirationState._to_inspiration(created)
    assert isinstance(item, Inspiration) and item.status == "Privado" and item.imagem.startswith("looks/")
    assert item.capa_catalogo == "/products/canvas-sneakers.svg" and item.pecas[0].imagem_url == "" and item.nota == "4,2"
