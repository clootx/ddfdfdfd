"""Change 030: feedback 👍/👎, opção de desligar a personalização e perfil de estilo para a IA."""

import json

from OSDroupa.ai import stylist as s


def _account_with_wardrobe(api, email="perfil@teste.osdroupa"):
    token = api.account(email)
    for key, status in (("k1", "No armário"), ("k2", "No armário"), ("k3", "Suja")):
        code, _ = api.call("POST", "meuArmario", token, payload={"chave_local": key, "nome": key, "status": status})
        assert code in (200, 201)
    return token


# ── Backend SQLite ──────────────────────────────────────────────────────────
def test_feedback_roundtrip_filters_foreign_keys(api):
    token = _account_with_wardrobe(api)
    code, _ = api.call("POST", "feedbackLooks", token, payload={
        "nome": "Look A", "roupa_chaves": ["k1", "k2", "de-outra-conta"], "avaliacao": "positivo", "motivo": "ignorado"})
    assert code == 201
    code, _ = api.call("POST", "feedbackLooks", token, payload={
        "nome": "Look B", "roupa_chaves": ["k1"], "avaliacao": "negativo", "motivo": "Não serve para o clima", "clima": "Quente"})
    assert code == 201
    code, body = api.call("GET", "feedbackLooks", token)
    assert code == 200
    latest, first = body["feedbacks"]
    assert latest["avaliacao"] == "negativo" and latest["motivo"] == "Não serve para o clima" and latest["clima"] == "Quente"
    assert first["roupa_chaves"] == ["k1", "k2"] and first["motivo"] == ""


def test_feedback_validation(api):
    token = _account_with_wardrobe(api)
    assert api.call("POST", "feedbackLooks", token, payload={"avaliacao": "talvez"})[0] == 400
    assert api.call("POST", "feedbackLooks", token, payload={"avaliacao": "negativo", "motivo": "texto livre"})[0] == 400
    assert api.call("POST", "feedbackLooks", token, payload={"avaliacao": "positivo", "roupa_chaves": "k1"})[0] == 400
    assert api.call("GET", "feedbackLooks")[0] == 401


def test_feedback_is_per_account_and_can_be_erased(api):
    token_a = _account_with_wardrobe(api, "a@teste.osdroupa")
    token_b = _account_with_wardrobe(api, "b@teste.osdroupa")
    api.call("POST", "feedbackLooks", token_a, payload={"avaliacao": "positivo", "roupa_chaves": ["k1"]})
    assert api.call("GET", "feedbackLooks", token_b)[1]["feedbacks"] == []
    code, body = api.call("DELETE", "feedbackLooks", token_a)
    assert code == 200 and body["apagados"] == 1
    assert api.call("GET", "feedbackLooks", token_a)[1]["feedbacks"] == []


def test_personalization_opt_out_in_profile(api):
    token = api.account("optout@teste.osdroupa")
    code, profile = api.call("GET", "buscaCliente", token)
    assert code == 200 and profile["personalizacao_ia"] is True  # padrão: ativa
    base = {"nome": profile["nome"], "celular": profile["celular"] or "11999990000"}
    code, saved = api.call("PATCH", "perfil", token, payload={**base, "personalizacao_ia": False})
    assert code == 200 and saved["personalizacao_ia"] is False
    assert api.call("GET", "buscaCliente", token)[1]["personalizacao_ia"] is False
    # Salvar o perfil sem o campo mantém a escolha
    assert api.call("PATCH", "perfil", token, payload=base)[1]["personalizacao_ia"] is False
    assert api.call("PATCH", "perfil", token, payload={**base, "personalizacao_ia": "sim"})[0] == 400


# ── Perfil de estilo enviado à IA ───────────────────────────────────────────
WARDROBE = [
    {"id": "1", "local_id": "a", "name": "Camisa", "category": "Partes de cima", "status": "No armário"},
    {"id": "2", "local_id": "b", "name": "Calça", "category": "Partes de baixo", "status": "No armário"},
    {"id": "3", "local_id": "c", "name": "Saia", "category": "Partes de baixo", "status": "No armário"},
    {"id": "4", "local_id": "d", "name": "Blusa suja", "category": "Partes de cima", "status": "Suja"},
]


def test_style_profile_summarizes_usage_and_feedback():
    usage = [{"id": 1, "usos": 2}, {"id": 2, "usos": 7}, {"id": 3, "usos": 0}, {"id": 4, "usos": 9}, {"id": 99, "usos": 5}]
    feedback = [
        {"avaliacao": "positivo", "roupa_chaves": ["b", "a"]},
        {"avaliacao": "negativo", "roupa_chaves": ["c", "x"], "motivo": "Pouco confortável"},
        {"avaliacao": "negativo", "roupa_chaves": ["d"], "motivo": "Outro motivo"},  # só peça suja: ignorado
    ]
    profile = s.build_style_profile(" azul, verde ", usage, feedback, WARDROBE)
    assert profile == {
        "cores_favoritas": "azul, verde",
        "pecas_mais_usadas": ["b", "a"],   # suja e desconhecida ficam de fora
        "pecas_pouco_usadas": ["c"],
        "looks_aprovados": [{"chaves": ["a", "b"]}],
        "looks_rejeitados": [{"chaves": ["c"], "motivo": "Pouco confortável"}],
    }


def test_style_profile_has_no_personal_data_and_empty_parts_are_omitted():
    profile = s.build_style_profile("", [], [], WARDROBE)
    assert profile == {"pecas_pouco_usadas": ["a", "b", "c"]}
    ctx = s.build_prompt_context({}, "Trabalho", "Clássico", "", WARDROBE, [], None, profile)
    text = json.dumps(ctx, ensure_ascii=False)
    assert ctx["perfil_estilo"] == profile
    for forbidden in ("tamanho", "email", "nome_completo", "celular"):
        assert forbidden not in text


def test_without_profile_context_has_no_personalization():
    ctx = s.build_prompt_context({}, "Trabalho", "", "", WARDROBE, [], None, None)
    assert "perfil_estilo" not in ctx and ctx["estilo_preferido"] == "não informado"
    assert "perfil_estilo" in s.SYSTEM_PROMPT and "looks_rejeitados" in s.SYSTEM_PROMPT
