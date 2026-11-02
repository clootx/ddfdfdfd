"""Provedor Gemini (Change 029) com a Interactions API substituída por um FALSO (MOCK).

Verifica parâmetros enviados e tratamento de erros. NÃO comprova que a API real
responde nem que o modelo está disponível na sua conta (isso só a chamada real
autorizada na Etapa 8 confirma).
"""

import asyncio
import logging
from types import SimpleNamespace as NS

import pytest
from google.genai import errors

from OSDroupa.ai.providers import ProviderError, gemini
from OSDroupa.ai import providers


class FakeInteractions:
    def __init__(self, result):
        self.result, self.calls = result, []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste-nao-real")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    p = gemini.GeminiTextProvider()

    def install(result):
        fake = FakeInteractions(result)
        p._client = NS(aio=NS(interactions=fake))
        return fake
    p.install = install
    return p


def ok(text='{"looks": []}', status="completed"):
    return NS(status=status, output_text=text, usage=None, errors=None)


def test_default_model_and_override(provider, monkeypatch):
    assert provider.model_name() == "gemini-3.8-flash"
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    assert provider.model_name() == "gemini-3.6-flash"


def test_request_parameters(provider):
    fake = provider.install(ok())
    schema = {"type": "object", "properties": {}, "required": []}
    text = asyncio.run(provider.generate_json("looks", "instrução", "contexto", schema))
    assert text == '{"looks": []}'
    kwargs = fake.calls[0]
    assert kwargs["model"] == "gemini-3.8-flash" and kwargs["system_instruction"] == "instrução"
    assert kwargs["input"] == "contexto"
    assert kwargs["response_format"] == {"type": "text", "mime_type": "application/json", "schema": schema}


def test_not_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = gemini.GeminiTextProvider()
    assert not p.is_configured()
    with pytest.raises(ProviderError) as info:
        asyncio.run(p.generate_json("looks", "", "", {}))
    assert info.value.reason == "not_configured"


@pytest.mark.parametrize("error,reason", [
    (errors.ClientError(429, {"error": {"message": "quota"}}), "quota"),
    (errors.ClientError(401, {"error": {"message": "key"}}), "auth"),
    (errors.ClientError(403, {"error": {"message": "perm"}}), "auth"),
    (errors.ClientError(404, {"error": {"message": "model"}}), "not_configured"),
    (errors.ClientError(400, {"error": {"message": "bad"}}), "blocked"),
    (errors.ServerError(503, {"error": {"message": "down"}}), "unavailable"),
])
def test_error_mapping(provider, error, reason):
    provider.install(error)
    with pytest.raises(ProviderError) as info:
        asyncio.run(provider.generate_json("looks", "", "", {}))
    assert info.value.reason == reason


def test_failed_status_and_empty_output(provider):
    provider.install(ok(status="failed"))
    with pytest.raises(ProviderError) as info:
        asyncio.run(provider.generate_json("looks", "", "", {}))
    assert info.value.reason == "blocked"
    provider.install(ok(text="   "))
    with pytest.raises(ProviderError) as info:
        asyncio.run(provider.generate_json("looks", "", "", {}))
    assert info.value.reason == "invalid_output"


def test_key_never_logged(provider, caplog):
    provider.install(errors.ClientError(401, {"error": {"message": "key"}}))
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ProviderError):
            asyncio.run(provider.generate_json("looks", "", "", {}))
    assert "chave-de-teste-nao-real" not in caplog.text


def test_provider_factory(monkeypatch):
    monkeypatch.setattr(providers, "_provider", None)
    monkeypatch.setenv("OSDROUPA_AI_PROVIDER", "gemini")
    assert providers.get_text_provider().name == "gemini"
    monkeypatch.setattr(providers, "_provider", None)
    monkeypatch.setenv("OSDROUPA_AI_PROVIDER", "outro")
    with pytest.raises(ProviderError):
        providers.get_text_provider()
    monkeypatch.setattr(providers, "_provider", None)


# ── Ajustes pós-timeout: 1 requisição por chamada, erros reais da Interactions API ──
def test_generation_limits_and_single_request_options(provider):
    fake = provider.install(ok())
    asyncio.run(provider.generate_json("looks", "", "", {}))
    kwargs = fake.calls[0]
    assert kwargs["generation_config"] == {"thinking_level": "low", "max_output_tokens": gemini.MAX_OUTPUT_TOKENS}
    # Sem timeout por chamada: o SDK reduziria o httpx.Timeout ao maior valor; ele fica no cliente.
    assert kwargs["automatic_continuation"] is False and "timeout" not in kwargs


def test_incomplete_status_is_not_retried_as_invalid(provider):
    provider.install(ok(status="incomplete"))
    with pytest.raises(ProviderError) as info:
        asyncio.run(provider.generate_json("looks", "", "", {}))
    assert info.value.reason == "unavailable"  # o estilista não repete: outra tentativa cortaria igual


@pytest.fixture
def sdk_transport(monkeypatch):
    """Cliente REAL do google-genai sobre um transporte httpx FALSO (MOCK): conta requisições, sem rede."""
    import httpx
    from google.genai import types

    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste-nao-real")
    state = {"calls": [], "respond": None}

    def handler(request):
        state["calls"].append(request)
        return state["respond"](request)

    real_client = gemini.genai.Client

    def client_with_mock_transport(api_key, http_options):
        # Mantém os argumentos do provedor (ex.: timeout) e só troca o transporte de rede.
        args = {**(http_options.async_client_args or {}), "transport": httpx.MockTransport(handler)}
        return real_client(api_key=api_key, http_options=types.HttpOptions(async_client_args=args))

    monkeypatch.setattr(gemini.genai, "Client", client_with_mock_transport)
    return state


def _status(code):
    import httpx
    return lambda request: httpx.Response(code, headers={"Retry-After": "0"}, json={"error": {"code": code, "message": "x"}})


def _raise(exc_type):
    def respond(request):
        raise exc_type("falha simulada", request=request)
    return respond


@pytest.mark.parametrize("respond,reason", [
    (_status(429), "quota"),
    (_status(503), "unavailable"),
    (_status(500), "unavailable"),
    (_status(400), "blocked"),
    (_status(401), "auth"),
    (_status(403), "auth"),
    (_status(404), "not_configured"),
    (_status(408), "blocked"),
])
def test_real_sdk_makes_exactly_one_request_per_status(sdk_transport, respond, reason):
    sdk_transport["respond"] = respond
    with pytest.raises(ProviderError) as info:
        asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "", {}))
    assert info.value.reason == reason
    assert len(sdk_transport["calls"]) == 1  # sem repetição automática do SDK


@pytest.mark.parametrize("exc_name,reason", [("ConnectError", "unavailable"), ("ReadTimeout", "timeout")])
def test_real_sdk_connection_errors_are_not_retried(sdk_transport, exc_name, reason):
    import httpx
    sdk_transport["respond"] = _raise(getattr(httpx, exc_name))
    with pytest.raises(ProviderError) as info:
        asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "", {}))
    assert info.value.reason == reason and len(sdk_transport["calls"]) == 1


def test_real_sdk_key_only_in_header_and_never_logged(sdk_transport, caplog):
    sdk_transport["respond"] = _status(429)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ProviderError):
            asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "", {}))
    request = sdk_transport["calls"][0]
    assert request.headers["x-goog-api-key"] == "chave-de-teste-nao-real"
    assert "chave-de-teste-nao-real" not in str(request.url)
    assert "chave-de-teste-nao-real" not in caplog.text
    assert b'"thinking_level"' in request.content and b'"max_output_tokens"' in request.content


# ── Diagnóstico de erros no log: error.status, error.message (≤200) e Retry-After ──
def test_error_log_has_google_diagnostics_without_secrets(sdk_transport, caplog):
    import httpx
    long_message = "This model is currently experiencing high demand.\nTry later. " + "x" * 400
    sdk_transport["respond"] = lambda request: httpx.Response(
        503, headers={"Retry-After": "7"},
        json={"error": {"code": 503, "status": "UNAVAILABLE", "message": long_message + " chave-de-teste-nao-real"}})
    with caplog.at_level(logging.WARNING, logger="osdroupa.ai.gemini"):
        with pytest.raises(ProviderError) as info:
            asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "contexto-pessoal-secreto", {}))
    assert info.value.reason == "unavailable" and len(sdk_transport["calls"]) == 1  # tratamento e 1 requisição mantidos
    record = next(r.getMessage() for r in caplog.records if "erro HTTP 503" in r.getMessage())
    assert "status=UNAVAILABLE" in record and "retry_after=7" in record
    assert "experiencing high demand. Try later." in record  # quebra de linha removida
    logged = record.split("mensagem=", 1)[1].strip("'\"")
    assert len(logged) == gemini.MAX_LOGGED_MESSAGE
    assert "chave-de-teste-nao-real" not in caplog.text and "contexto-pessoal-secreto" not in caplog.text


def test_error_log_without_body_or_retry_after(sdk_transport, caplog):
    import httpx
    sdk_transport["respond"] = lambda request: httpx.Response(429, text="sem json")
    with caplog.at_level(logging.WARNING, logger="osdroupa.ai.gemini"):
        with pytest.raises(ProviderError) as info:
            asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "", {}))
    assert info.value.reason == "quota"
    record = next(r.getMessage() for r in caplog.records if "erro HTTP 429" in r.getMessage())
    assert "status=-" in record and "retry_after=-" in record


def test_error_details_from_legacy_sdk_errors(provider, caplog):
    provider.install(errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded"}}))
    with caplog.at_level(logging.WARNING, logger="osdroupa.ai.gemini"):
        with pytest.raises(ProviderError) as info:
            asyncio.run(provider.generate_json("looks", "", "", {}))
    assert info.value.reason == "quota"
    assert "status=RESOURCE_EXHAUSTED" in caplog.text and "Quota exceeded" in caplog.text


# ── Timeout: conexão 10 s, leitura/total 90 s, e fase do tempo esgotado no log ──
def test_http_timeout_values():
    assert gemini.REQUEST_TIMEOUT == 90.0 and gemini.CONNECT_TIMEOUT == 10.0
    assert gemini.HTTP_TIMEOUT.as_dict() == {"connect": 10.0, "read": 90.0, "write": 90.0, "pool": 90.0}


def test_real_sdk_applies_connect_and_read_timeouts(sdk_transport):
    sdk_transport["respond"] = _status(503)
    with pytest.raises(ProviderError):
        asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "", {}))
    applied = sdk_transport["calls"][0].extensions["timeout"]
    assert applied == {"connect": 10.0, "read": 90.0, "write": 90.0, "pool": 90.0}


@pytest.mark.parametrize("exc_name", ["ReadTimeout", "ConnectTimeout", "WriteTimeout", "PoolTimeout"])
def test_timeout_phase_is_logged_from_inner_exception(sdk_transport, caplog, exc_name):
    import httpx
    sdk_transport["respond"] = _raise(getattr(httpx, exc_name))
    with caplog.at_level(logging.WARNING, logger="osdroupa.ai.gemini"):
        with pytest.raises(ProviderError) as info:
            asyncio.run(gemini.GeminiTextProvider().generate_json("looks", "", "contexto-pessoal-secreto", {}))
    assert info.value.reason == "timeout" and len(sdk_transport["calls"]) == 1
    record = next(r.getMessage() for r in caplog.records if "sem resposta" in r.getMessage())
    assert f"fase={exc_name}" in record and "APITimeoutError" in record
    assert "chave-de-teste-nao-real" not in caplog.text and "contexto-pessoal-secreto" not in caplog.text


def test_timeout_phase_classification():
    import httpx
    from google.genai._interactions import APITimeoutError

    def wrapped(inner):
        try:
            try:
                raise inner
            except Exception as cause:
                raise APITimeoutError(request=httpx.Request("POST", "https://exemplo.invalid")) from cause
        except APITimeoutError as exc:
            return exc

    request = httpx.Request("POST", "https://exemplo.invalid")
    assert gemini._timeout_phase(wrapped(httpx.ReadTimeout("x", request=request))) == "ReadTimeout"
    assert gemini._timeout_phase(wrapped(httpx.ConnectTimeout("x", request=request))) == "ConnectTimeout"
    assert gemini._timeout_phase(wrapped(ValueError("outra"))) == "ValueError"
    assert gemini._timeout_phase(asyncio.TimeoutError()) == "guarda_externa"
    assert gemini._timeout_phase(APITimeoutError(request=request)) == "desconhecida"
