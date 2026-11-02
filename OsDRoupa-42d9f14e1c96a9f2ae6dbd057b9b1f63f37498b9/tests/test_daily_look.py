"""Plano B do Look do Dia (Etapa 5): mesma escolha do endpoint lookDoDia do SQLite."""

import httpx
import pytest

from OSDroupa import daily_look

WARDROBE = [
    ("c1", "Camisa de linho", "Partes de cima", "No armário", "Verão"),
    ("c2", "Suéter de lã", "Partes de cima", "No armário", "Inverno"),
    ("b1", "Calça de alfaiataria", "Partes de baixo", "No armário", ""),
    ("b2", "Bermuda", "Partes de baixo", "Suja", "Verão"),
    ("v1", "Vestido midi", "Vestidos", "No armário", "Meia-estação"),
    ("v2", "Vestido de festa", "Vestidos", "Lavando", ""),
    ("s1", "Tênis branco", "Calçados", "No armário", ""),
    ("s2", "Bota de couro", "Calçados", "No armário", "Inverno, frio"),
    ("a1", "Lenço", "Acessórios", "No armário", "Inverno"),
]


def _normalized(item: dict) -> dict:
    # Mesmas chaves que WardrobeLifeState._normalize_wardrobe_item produz
    return {"id": str(item["id"]), "category": item["categoria"], "status": item["status"],
            "season": item["estacao"], "name": item["nome"]}


@pytest.fixture
def wardrobe(api):
    token = api.account("plano.b@teste.osdroupa")
    for key, name, category, status, season in WARDROBE:
        code, body = api.call("POST", "meuArmario", token, payload={
            "chave_local": key, "nome": name, "categoria": category, "status": status, "estacao": season})
        assert code in (200, 201), body
    code, body = api.call("GET", "meuArmario", token)
    assert code == 200
    return token, [_normalized(item) for item in body["itens"]]


@pytest.mark.parametrize("weather", ["Quente", "Ameno", "Frio", "Chuvoso"])
@pytest.mark.parametrize("occasion", ["Dia a dia", "Trabalho", "Evento", "Lazer"])
def test_fallback_matches_sqlite_endpoint(api, wardrobe, weather, occasion):
    token, items = wardrobe
    code, body = api.call("GET", "lookDoDia", token, params={"clima": weather, "ocasiao": occasion})
    assert code == 200
    expected = [str(piece["id"]) for piece in body["pecas"]]
    assert [piece["id"] for piece in daily_look.pick_daily_look(items, weather, occasion)] == expected


def test_fallback_rules():
    items = [
        {"id": "1", "category": "Partes de cima", "status": "Suja", "season": "Inverno"},
        {"id": "2", "category": "Partes de cima", "status": "No armário", "season": ""},
        {"id": "3", "category": "Partes de cima", "status": "No armário", "season": "Inverno"},
        {"id": "4", "category": "Calçados", "status": "Lavando", "season": ""},
    ]
    chosen = daily_look.pick_daily_look(items, "Frio", "Dia a dia")
    assert [piece["id"] for piece in chosen] == ["3"]  # suja e lavando ficam de fora; inverno vence
    assert daily_look.pick_daily_look([], "Frio", "Dia a dia") == []


def test_fallback_limits_to_four_pieces_one_per_category():
    items = [{"id": str(i), "category": f"Cat {i % 6}", "status": "No armário", "season": ""} for i in range(12)]
    chosen = daily_look.pick_daily_look(items, "Ameno", "Dia a dia")
    assert len(chosen) == 4 and len({piece["category"] for piece in chosen}) == 4


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://exemplo.invalid/lookDoDia")
    return httpx.HTTPStatusError("erro", request=request, response=httpx.Response(status, request=request))


@pytest.mark.parametrize("exc, fragment", [
    (_http_error(404), "não está publicado"),
    (_http_error(429), "limite"),
    (_http_error(401), "sessão"),
    (_http_error(503), "erro 503"),
    (ValueError("json"), "resposta inválida"),
    (httpx.ConnectError("sem rede"), "não respondeu"),
])
def test_failure_reason_is_short_and_safe(exc, fragment):
    reason = daily_look.failure_reason(exc)
    assert fragment in reason and "exemplo.invalid" not in reason
