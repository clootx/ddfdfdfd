"""Estilista: contexto, validação, trocas e chamada ao provedor (Changes 025/026).

A chamada ao modelo usa um cliente FALSO (MOCK) que devolve respostas fixas.
Esses testes não comprovam que a API do provedor funciona.
"""

import asyncio
import json

import pytest

from OSDroupa.ai import stylist as s
from OSDroupa.ai.providers import ProviderError

WARDROBE = [
    {"local_id": "w1", "name": "Camiseta linho", "category": "Partes de cima", "status": "No armário", "color": "branca", "season": "Verão", "image_url": "http://x/1.png"},
    {"local_id": "w2", "name": "Bermuda sarja", "category": "Partes de baixo", "status": "Em uso", "color": "bege", "season": "", "image_url": ""},
    {"local_id": "w3", "name": "Calça suja", "category": "Partes de baixo", "status": "Suja", "color": "", "season": "", "image_url": ""},
    {"local_id": "c1", "name": "Camisa social", "category": "Partes de cima", "status": "No armário", "image_url": "http://x/c.png"},
    {"local_id": "p1", "name": "Calça alfaiataria", "category": "Partes de baixo", "status": "No armário"},
]
CATALOG = [
    {"id": "7", "name": "Tênis lona", "category": "Calçados", "availability": "Disponível agora", "image_url": "http://x/t.png"},
    {"id": "8", "name": "Bota", "category": "Calçados", "availability": "Sem estoque"},
    {"id": "9", "name": "Mocassim", "category": "Calçados", "availability": "Sob encomenda"},
]
EVALUATION = {
    "nota_clima": 4, "nota_harmonia": 3, "nota_ocasiao": 1, "nota_conforto": 5, "nota_estilo": 9,
    "pontos_fortes": "Fresco", "problemas": ["Informal para trabalho"],
    "trocas": [
        {"papel": "cima", "sai_ref": "w1", "entra_origem": "armario", "entra_ref": "c1", "entra_descricao": "", "motivo": "mais formal"},
        {"papel": "baixo", "sai_ref": "w2", "entra_origem": "armario", "entra_ref": "w3", "entra_descricao": "Calça escura", "motivo": "x"},
        {"papel": "calcado", "sai_ref": "nao-esta", "entra_origem": "catalogo", "entra_ref": "9", "entra_descricao": "", "motivo": "completa"},
        {"papel": "baixo", "sai_ref": "w2", "entra_origem": "armario", "entra_ref": "p1", "entra_descricao": "", "motivo": "quarta é ignorada"},
    ],
}
RAW_LOOK = {
    "nome": "Look A", "conforto": "alto", "paleta": ["branco", "bege"], "tecidos": ["linho"],
    "justificativa_clima": "33 °C", "justificativa_estilo": "ok", "avaliacao": EVALUATION,
    "pecas": [
        {"papel": "cima", "origem": "armario", "ref": "w1", "descricao": "solta"},
        {"papel": "baixo", "origem": "armario", "ref": "w2", "descricao": ""},
        {"papel": "calcado", "origem": "catalogo", "ref": "7", "descricao": ""},
        {"papel": "acessorio", "origem": "armario", "ref": "inventada", "descricao": "Óculos de sol. Proteção UV"},
        {"papel": "baixo", "origem": "armario", "ref": "w3", "descricao": "calça"},
        {"papel": "calcado", "origem": "catalogo", "ref": "8", "descricao": "bota"},
    ],
}


def test_prompt_context_excludes_dirty_items_and_personal_data():
    ctx = s.build_prompt_context({"cidade": "Recife", "uf": "PE", "sensacao": "33", "manual": ""}, "Trabalho", "minimalista", "x" * 400, WARDROBE, CATALOG)
    assert [i["chave"] for i in ctx["armario"]] == ["w1", "w2", "c1", "p1"]
    assert [p["id"] for p in ctx["catalogo"]] == ["7", "9"]
    assert len(ctx["observacao_usuario"]) == 280 and "manual" not in ctx["clima"]
    assert "image_url" not in json.dumps(ctx) and "http://" not in json.dumps(ctx)


def test_validate_looks_downgrades_invalid_references():
    (look,), downgraded = s.validate_looks([RAW_LOOK], WARDROBE, CATALOG)
    assert downgraded == 4  # 3 peças do look + 1 troca da avaliação (peça suja)
    assert [p.origem for p in look.pecas] == ["armario", "armario", "catalogo", "sugerida", "sugerida", "sugerida"]
    assert look.pecas[3].nome == "Óculos de sol" and look.pecas[2].imagem_url == "http://x/t.png"
    assert not look.precisa_pecas and look.conforto == "Conforto alto"


def test_coverage_flag():
    raw = {**RAW_LOOK, "pecas": [{"papel": "cima", "origem": "armario", "ref": "w1", "descricao": ""}], "avaliacao": None}
    (look,), _ = s.validate_looks([raw], WARDROBE, CATALOG)
    assert look.precisa_pecas and not look.avaliacao.disponivel


def test_review_scores_and_swaps():
    pieces = s.closet_pieces(["w1", "w2", "zz"], WARDROBE)
    assert [(p.papel, p.ref) for p in pieces] == [("cima", "w1"), ("baixo", "w2")]
    review = s.validate_evaluation(EVALUATION, pieces, WARDROBE, CATALOG)
    assert review.disponivel and review.nota_estilo == 3 and review.nota_geral == "3,2"
    first, invalid, addition = review.trocas
    assert first.aplicavel and first.sai_nome == "Camiseta linho" and first.entra.nome == "Camisa social"
    assert not invalid.aplicavel and invalid.entra.origem == "sugerida" and invalid.entra.nome == "Calça escura"
    assert addition.aplicavel and addition.sai_ref == "" and addition.entra.origem == "catalogo"


def test_apply_swap():
    (look,), _ = s.validate_looks([{**RAW_LOOK, "pecas": RAW_LOOK["pecas"][:2]}], WARDROBE, CATALOG)
    swaps = look.avaliacao.trocas
    assert not s.apply_swap(look, swaps[1].id)
    assert s.apply_swap(look, swaps[0].id) and [p.ref for p in look.pecas] == ["c1", "w2"]
    assert s.apply_swap(look, swaps[2].id) and [p.ref for p in look.pecas] == ["c1", "w2", "9"]
    assert len(look.avaliacao.trocas) == 1 and not s.apply_swap(look, "inexistente")


def test_heuristic_proposal_roles():
    proposal = s.heuristic_proposal(WARDROBE[:2], "Trabalho", "Quente")
    assert [p.papel for p in proposal.pecas] == ["cima", "baixo"] and proposal.fonte == "heuristica"




# ── Chamada ao provedor (MOCK) ──────────────────────────────────────────────
class FakeProvider:
    """MOCK de TextProvider: devolve respostas fixas em ordem. Não comprova a API real."""

    name = "fake"

    def __init__(self, replies, configured=True):
        self.replies, self.calls, self.configured = list(replies), [], configured

    def is_configured(self):
        return self.configured

    def model_name(self):
        return "modelo-falso"

    async def generate_json(self, kind, system, user_text, schema):
        self.calls.append({"kind": kind, "system": system, "user_text": user_text, "schema": schema})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def fake_provider(monkeypatch):
    def install(replies, configured=True):
        fake = FakeProvider(replies, configured)
        monkeypatch.setattr(s, "get_text_provider", lambda: fake)
        return fake
    return install


def test_request_without_key_is_unavailable(fake_provider):
    fake = fake_provider([], configured=False)
    with pytest.raises(s.StylistUnavailable, match="não está configurada") as info:
        asyncio.run(s.request_looks({}))
    assert info.value.reason == "not_configured" and fake.calls == []


def test_request_retries_once_on_invalid_json(fake_provider):
    fake = fake_provider(["{quebrado", json.dumps({"looks": [RAW_LOOK] * 3})])
    looks = asyncio.run(s.request_looks({"ocasiao": "Trabalho"}))
    assert len(looks) == 3 and len(fake.calls) == 2
    assert fake.calls[0]["schema"] is s.LOOKS_SCHEMA and fake.calls[0]["system"] == s.SYSTEM_PROMPT


def test_request_double_invalid(fake_provider):
    fake_provider(["{x", "{y"])
    with pytest.raises(s.StylistUnavailable, match="inválida") as info:
        asyncio.run(s.request_looks({}))
    assert info.value.reason == "invalid_output"


@pytest.mark.parametrize("reason", ["quota", "auth", "blocked", "timeout", "unavailable"])
def test_provider_errors_are_not_retried(fake_provider, reason):
    fake = fake_provider([ProviderError("mensagem segura", reason=reason), json.dumps({"looks": [RAW_LOOK] * 3})])
    with pytest.raises(s.StylistUnavailable, match="mensagem segura") as info:
        asyncio.run(s.request_looks({}))
    assert info.value.reason == reason and len(fake.calls) == 1  # não gasta cota repetindo


def test_empty_output_is_retried_once(fake_provider):
    fake = fake_provider([ProviderError("vazia", reason="invalid_output"), json.dumps({"looks": [RAW_LOOK] * 3})])
    assert len(asyncio.run(s.request_looks({}))) == 3 and len(fake.calls) == 2


def test_request_evaluation_payload(fake_provider):
    fake = fake_provider([json.dumps(EVALUATION)])
    pieces = s.closet_pieces(["w1", "w2"], WARDROBE)
    result = asyncio.run(s.request_evaluation({"ocasiao": "Trabalho"}, "Meu look", pieces))
    assert result["nota_ocasiao"] == 1 and fake.calls[0]["schema"] is s.EVALUATION_SCHEMA
    body = fake.calls[0]["user_text"]
    assert '"ref": "w1"' in body and "Meu look" in body


def test_schemas_have_no_provider_specific_keywords():
    dumped = json.dumps([s.LOOKS_SCHEMA, s.EVALUATION_SCHEMA])
    assert '"enum": [1' not in dumped  # notas usam minimum/maximum


# ── Etapa 6: looks mais ricos, 3 a 5 looks, sem repetição ───────────────────
def _look(name: str, keys: list[str], **extra) -> dict:
    return {**RAW_LOOK, "nome": name, "descricao": f"Proposta {name}", "acessorios_sugeridos": [], **extra,
            "pecas": [{"papel": "cima" if i == 0 else "baixo", "origem": "armario", "ref": k, "descricao": ""} for i, k in enumerate(keys)]}


def test_schema_requires_description_accessories_and_three_to_five_looks():
    looks = s.LOOKS_SCHEMA["properties"]["looks"]
    assert looks["minItems"] == 3 and looks["maxItems"] == 5
    assert {"descricao", "acessorios_sugeridos"} <= set(looks["items"]["required"])
    assert "looks_recentes" in s.SYSTEM_PROMPT and "acessorios_sugeridos" in s.SYSTEM_PROMPT


def test_fewer_than_three_looks_is_retried_then_fails(fake_provider):
    fake = fake_provider([json.dumps({"looks": [RAW_LOOK] * 2}), json.dumps({"looks": [RAW_LOOK]})])
    with pytest.raises(s.StylistUnavailable) as info:
        asyncio.run(s.request_looks({}))
    assert info.value.reason == "invalid_output" and len(fake.calls) == 2


def test_more_than_five_looks_is_truncated(fake_provider):
    fake_provider([json.dumps({"looks": [RAW_LOOK] * 7})])
    assert len(asyncio.run(s.request_looks({}))) == 5


def test_description_and_accessories_are_kept_and_trimmed():
    raw = _look("A", ["w1", "w2"], acessorios_sugeridos=["cinto caramelo", "  ", "x" * 200, "brinco", "relógio", "quinto"])
    (look,), _ = s.validate_looks([raw], WARDROBE, CATALOG)
    assert look.descricao == "Proposta A"
    assert look.acessorios_sugeridos[0] == "cinto caramelo" and len(look.acessorios_sugeridos) == 3
    assert len(look.acessorios_sugeridos[1]) == 80


def test_repeated_looks_are_discarded():
    recent = s.recent_looks([{"nome": "Salvo", "roupa_chaves": ["w2", "w1"]}], [], WARDROBE)
    raws = [_look("Igual ao salvo", ["w1", "w2"]), _look("Novo", ["c1", "p1"]), _look("Igual ao novo", ["p1", "c1"]), _look("Outro", ["c1", "w2"])]
    looks, _ = s.validate_looks(raws, WARDROBE, CATALOG, recent)
    assert [look.nome for look in looks] == ["Novo", "Outro"]


def test_recent_looks_context_uses_only_closet_keys():
    previous = s.validate_looks([_look("Anterior", ["c1", "p1"])], WARDROBE, CATALOG)[0]
    saved = [{"nome": "A", "roupa_chaves": ["w1", "apagada"]}, {"nome": "B", "roupa_chaves": ["w1", "w2"]},
             {"nome": "B de novo", "roupa_chaves": ["w2", "w1"]}, {"nome": "Quebrado", "roupa_chaves": "w1"}]
    recent = s.recent_looks(saved, previous, WARDROBE)
    assert recent == [{"nome": "B", "chaves": ["w1", "w2"]}, {"nome": "Anterior", "chaves": ["c1", "p1"]}]
    ctx = s.build_prompt_context({}, "Trabalho", "", "", WARDROBE, CATALOG, recent)
    assert ctx["looks_recentes"] == recent


def test_heuristic_has_description():
    assert s.heuristic_proposal(WARDROBE[:2], "Trabalho", "Quente").descricao
