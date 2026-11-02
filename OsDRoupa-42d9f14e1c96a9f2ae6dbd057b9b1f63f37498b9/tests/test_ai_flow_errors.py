"""Erros nos três fluxos de IA do app (auditoria): o carregamento sempre termina e a mensagem é amigável.

Executa a função REAL de cada evento de fundo com um estado FALSO (MOCK) e provedores FALSOS;
nenhuma chamada real ao Gemini.
"""

import asyncio
import json

import httpx
import pytest
from google.genai import types

import OSDroupa.OSDroupa as app
from OSDroupa.ai import imaging, limits, providers, stylist
from OSDroupa.ai.providers import gemini
from OSDroupa.ai.stylist import LookPiece, LookProposal

SECRET_DETAIL = "detalhe-interno-secreto"


class FakeState:
    """Estado mínimo: suporta `async with self` e registra o que o fluxo fez."""

    def __init__(self, **attrs):
        self.ai_loading = False
        self.ai_error = self.ai_notice = self.ai_note = ""
        self.ai_proposals = []
        self.review_loading = False
        self.review_error = ""
        self.image_loading_id = ""
        self.current_user = {"id": "1"}
        self.client_profile = {}
        self.wardrobe_items = [
            {"id": "1", "local_id": "w1", "name": "Camisa", "category": "Partes de cima", "status": "No armário", "image_url": ""},
            {"id": "2", "local_id": "w2", "name": "Calça", "category": "Partes de baixo", "status": "No armário", "image_url": ""},
        ]
        self.daily_occasion = "Trabalho"
        self.ai_personalization_on = False
        self.heuristic_reasons = []
        self.loading_seen = []
        self.get_state_error = None
        self.__dict__.update(attrs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def _session_gate(self):
        return "ok"

    async def load_wardrobe(self):
        return None

    async def get_state(self, cls):
        if self.get_state_error:
            raise self.get_state_error
        self.loading_seen.append((self.ai_loading, self.review_loading, self.image_loading_id))
        return FakeOther()

    async def _saved_looks_for_ai(self):
        return []

    async def _optional_rows(self, endpoint, key):
        return []

    def _weather_for_ai(self):
        return {"categoria": "Quente"}

    async def _use_heuristic_look(self, reason):
        self.heuristic_reasons.append(reason)
        self.ai_notice = f"Sugestão básica (IA indisponível). {reason}"


class FakeOther:
    """Faz o papel de StoreState e de WardrobeLifeState em `get_state`."""
    products = [{"id": "9", "name": "Tênis", "availability": "Disponível agora"}]
    has_weather = True

    async def load_catalog(self):
        return None

    async def load_weather_context(self):
        return None

    def _weather_for_ai(self):
        return {"categoria": "Quente"}


@pytest.fixture
def ai_ready(monkeypatch):
    monkeypatch.setattr(stylist, "is_configured", lambda: True)
    monkeypatch.setattr(imaging, "is_configured", lambda: True)

    async def allow(kind, account_id):
        return limits.LimitResult(allowed=True)
    paused = []

    async def pause(kind, seconds=None):
        paused.append(kind)
    monkeypatch.setattr(limits, "reserve_async", allow)
    monkeypatch.setattr(limits, "pause_after_quota_async", pause)
    return paused


def run(handler, state, *args):
    asyncio.run(handler.fn(state, *args))
    return state


def _raise(exc):
    async def fail(*args, **kwargs):
        raise exc
    return fail


def _look(name):
    return {"nome": name, "descricao": "d", "acessorios_sugeridos": [], "paleta": [], "tecidos": [], "justificativa_clima": "",
            "justificativa_estilo": "", "conforto": "alto", "avaliacao": {},
            "pecas": [{"papel": "cima", "origem": "armario", "ref": "w1", "descricao": ""},
                      {"papel": "baixo", "origem": "armario", "ref": "w2", "descricao": ""}]}


# ── generate_ai_looks ───────────────────────────────────────────────────────
def test_looks_success_unchanged(ai_ready, monkeypatch):
    async def ok(context):
        return [_look("A"), {**_look("B"), "pecas": _look("B")["pecas"][:1]}]
    monkeypatch.setattr(stylist, "request_looks", ok)
    state = run(app.WardrobeLifeState.generate_ai_looks, FakeState())
    assert [p.nome for p in state.ai_proposals] == ["A", "B"]
    assert state.ai_notice.startswith("2 looks criados pela IA") and not state.ai_error
    assert state.ai_loading is False and state.loading_seen[0][0] is True  # ligou durante e desligou no fim


def test_looks_http_200_with_invalid_body_reproduces_audit(ai_ready, monkeypatch):
    """Cenário da auditoria: corpo não-JSON com HTTP 200 pelo cliente REAL do SDK (transporte falso)."""
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste-nao-real")
    real_client = gemini.genai.Client
    monkeypatch.setattr(gemini.genai, "Client", lambda api_key, http_options: real_client(
        api_key=api_key, http_options=types.HttpOptions(async_client_args={
            **http_options.async_client_args, "transport": httpx.MockTransport(lambda r: httpx.Response(200, text="<html>proxy</html>"))})))
    monkeypatch.setattr(providers, "_provider", gemini.GeminiTextProvider())
    state = run(app.WardrobeLifeState.generate_ai_looks, FakeState())
    assert state.ai_loading is False
    assert state.heuristic_reasons == ["A IA de estilo está indisponível no momento."]  # sugestão básica, como antes
    assert "html" not in state.ai_notice.lower() and "chave" not in state.ai_notice


def test_looks_unexpected_error_in_ai_call(ai_ready, monkeypatch):
    monkeypatch.setattr(stylist, "request_looks", _raise(RuntimeError(SECRET_DETAIL)))
    state = run(app.WardrobeLifeState.generate_ai_looks, FakeState())
    assert state.ai_loading is False and state.heuristic_reasons == ["A IA de estilo está indisponível no momento."]
    assert SECRET_DETAIL not in state.ai_notice + state.ai_error


def test_looks_unexpected_error_before_ai_call(ai_ready):
    state = run(app.WardrobeLifeState.generate_ai_looks, FakeState(get_state_error=RuntimeError(SECRET_DETAIL)))
    assert state.ai_loading is False and state.ai_error == app.AI_LOOKS_FAILURE
    assert SECRET_DETAIL not in state.ai_error


def test_looks_quota_still_pauses_and_falls_back(ai_ready, monkeypatch):
    monkeypatch.setattr(stylist, "request_looks", _raise(stylist.StylistUnavailable("Cota atingida.", reason="quota")))
    state = run(app.WardrobeLifeState.generate_ai_looks, FakeState())
    assert ai_ready == ["texto"] and state.heuristic_reasons == ["Cota atingida."] and state.ai_loading is False


@pytest.mark.parametrize("reason,message", [("timeout", "A IA de estilo demorou demais para responder."),
                                            ("unavailable", "A IA de estilo está indisponível no momento.")])
def test_looks_known_errors_keep_their_messages(ai_ready, monkeypatch, reason, message):
    monkeypatch.setattr(stylist, "request_looks", _raise(stylist.StylistUnavailable(message, reason=reason)))
    state = run(app.WardrobeLifeState.generate_ai_looks, FakeState())
    assert state.heuristic_reasons == [message] and ai_ready == [] and state.ai_loading is False


# ── evaluate_look ───────────────────────────────────────────────────────────
def _review_state(**attrs):
    look = {"id": "L1", "name": "Meu look", "occasion": "Trabalho", "garment_keys": json.dumps(["w1", "w2"])}
    state = FakeState(looks=[look], **attrs)
    state.review_look_id = ""
    return state


def test_review_success_unchanged(ai_ready, monkeypatch):
    async def ok(context, name, pieces):
        return {"nota_clima": 4, "nota_harmonia": 4, "nota_ocasiao": 4, "nota_conforto": 4, "nota_estilo": 4,
                "pontos_fortes": "Bom", "problemas": [], "trocas": []}
    monkeypatch.setattr(stylist, "request_evaluation", ok)
    state = run(app.LookState.evaluate_look, _review_state(), "L1")
    assert state.look_review.disponivel and state.look_review.nota_geral == "4,0"
    assert state.review_loading is False and not state.review_error and state.loading_seen[0][1] is True


def test_review_unexpected_error_in_ai_call(ai_ready, monkeypatch):
    monkeypatch.setattr(stylist, "request_evaluation", _raise(ValueError(SECRET_DETAIL)))
    state = run(app.LookState.evaluate_look, _review_state(), "L1")
    assert state.review_loading is False and state.review_error == app.AI_REVIEW_FAILURE


def test_review_unexpected_error_before_ai_call(ai_ready):
    state = run(app.LookState.evaluate_look, _review_state(get_state_error=RuntimeError(SECRET_DETAIL)), "L1")
    assert state.review_loading is False and state.review_error == app.AI_REVIEW_FAILURE


def test_review_quota_preserved(ai_ready, monkeypatch):
    monkeypatch.setattr(stylist, "request_evaluation", _raise(stylist.StylistUnavailable("Cota atingida.", reason="quota")))
    state = run(app.LookState.evaluate_look, _review_state(), "L1")
    assert ai_ready == ["texto"] and state.review_error == "Cota atingida." and state.review_loading is False


def test_review_concurrent_call_does_not_clear_other_loading(ai_ready):
    """Uma chamada que sai cedo (look inexistente) não desliga o carregamento ligado por outra."""
    state = _review_state(review_loading=True)
    run(app.LookState.evaluate_look, state, "nao-existe")
    assert state.review_loading is True


# ── generate_look_image ─────────────────────────────────────────────────────
def _image_state(**attrs):
    proposal = LookProposal(id="P1", nome="Look", pecas=[LookPiece(papel_label="Parte de cima", nome="Camisa")])
    return FakeState(ai_proposals=[proposal], **attrs)


def test_image_success_unchanged(ai_ready, monkeypatch):
    seen = []

    async def ok(name, pieces, palette, fabrics, output_dir):
        seen.append(name)
        return "abc.png"
    monkeypatch.setattr(imaging, "generate_look_image", ok)
    state = run(app.WardrobeLifeState.generate_look_image, _image_state(), "P1")
    assert state.ai_proposals[0].imagem_gerada == "looks/abc.png" and state.image_loading_id == "" and not state.ai_error


def test_image_unexpected_error(ai_ready, monkeypatch):
    monkeypatch.setattr(imaging, "generate_look_image", _raise(OSError(SECRET_DETAIL)))
    state = run(app.WardrobeLifeState.generate_look_image, _image_state(), "P1")
    assert state.image_loading_id == "" and state.ai_error == app.AI_IMAGE_FAILURE


def test_image_quota_preserved(ai_ready, monkeypatch):
    monkeypatch.setattr(imaging, "generate_look_image", _raise(imaging.ImageUnavailable("Muito requisitado.", reason="quota")))
    state = run(app.WardrobeLifeState.generate_look_image, _image_state(), "P1")
    assert ai_ready == ["imagem"] and state.ai_error == "Muito requisitado." and state.image_loading_id == ""


def test_image_call_already_running_keeps_other_loading(ai_ready, monkeypatch):
    monkeypatch.setattr(imaging, "generate_look_image", _raise(AssertionError("não deveria chamar")))
    state = run(app.WardrobeLifeState.generate_look_image, _image_state(image_loading_id="OUTRO"), "P1")
    assert state.image_loading_id == "OUTRO"


# ── Provedores: HTTP 200 inválido e erros inesperados viram erros tratados ───
def _sdk_client(monkeypatch, module, respond):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste-nao-real")
    real_client = module.genai.Client

    def factory(api_key, http_options=None):
        args = dict((http_options.async_client_args or {}) if http_options else {})
        args["transport"] = httpx.MockTransport(respond)
        return real_client(api_key=api_key, http_options=types.HttpOptions(async_client_args=args))
    monkeypatch.setattr(module.genai, "Client", factory)


def test_text_provider_invalid_200_body_is_handled(monkeypatch):
    _sdk_client(monkeypatch, gemini, lambda r: httpx.Response(200, text="<html>proxy</html>"))
    with pytest.raises(providers.ProviderError) as info:
        asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "", {}))
    assert info.value.reason == "unavailable"


def test_stylist_converts_non_provider_errors(monkeypatch):
    class Broken:
        def is_configured(self):
            return True

        async def generate_json(self, *args):
            raise KeyError(SECRET_DETAIL)
    monkeypatch.setattr(providers, "_provider", Broken())
    with pytest.raises(stylist.StylistUnavailable) as info:
        asyncio.run(stylist.request_looks({}))
    assert info.value.reason == "unavailable" and SECRET_DETAIL not in str(info.value)


@pytest.mark.parametrize("respond,reason", [
    (lambda r: httpx.Response(200, text="<html>proxy</html>"), "unavailable"),
    (lambda r: httpx.Response(429, json={"error": {"code": 429}}), "quota"),
    (lambda r: httpx.Response(503, json={"error": {"code": 503}}), "unavailable"),
])
def test_image_provider_handles_real_sdk_errors(monkeypatch, tmp_path, respond, reason):
    monkeypatch.setenv("OSDROUPA_IMAGES_ENABLED", "true")
    monkeypatch.setattr(imaging, "_client", None, raising=False)
    _sdk_client(monkeypatch, imaging, respond)
    with pytest.raises(imaging.ImageUnavailable) as info:
        asyncio.run(imaging.generate_look_image("Look", [{"papel": "cima", "nome": "Camisa"}], "", "", tmp_path))
    assert info.value.reason == reason
