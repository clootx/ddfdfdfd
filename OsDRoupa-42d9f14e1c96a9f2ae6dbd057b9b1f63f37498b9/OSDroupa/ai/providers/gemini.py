"""Provedor de texto Google Gemini via Interactions API (SDK oficial google-genai).

Executado somente no servidor Reflex. A chave vem de GEMINI_API_KEY e nunca é
registrada em log. O modelo vem de GEMINI_MODEL (padrão gemini-3.8-flash).

Uma chamada a `generate_json` faz no máximo UMA requisição HTTP:
- repetições automáticas do SDK desligadas (quem decide repetir é o estilista);
- continuação automática desligada (ela enviaria novas requisições).

Privacidade: no plano gratuito, o Google informa que o conteúdo enviado pode ser
usado para melhorar seus produtos. Por isso o estilista envia apenas dados
mínimos (sem nome, e-mail, endereço completo ou fotos).
"""

import asyncio
import logging
import os
import time

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
# A Interactions API do google-genai 2.x lança estas classes, que não herdam de google.genai.errors.
from google.genai._interactions import APIConnectionError, APIStatusError, APITimeoutError

from OSDroupa.ai.providers import ProviderError

logger = logging.getLogger("osdroupa.ai.gemini")

DEFAULT_MODEL = "gemini-3.8-flash"
REQUEST_TIMEOUT = 90.0  # segundos, limite do SDK para a requisição (leitura da resposta incluída)
CONNECT_TIMEOUT = 10.0  # segundos para abrir a conexão; separa "não conectou" de "não respondeu"
HTTP_TIMEOUT = httpx.Timeout(REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT)
GUARD_MARGIN = 5.0  # segundos a mais na proteção externa (asyncio), caso o SDK não encerre
THINKING_LEVEL = "low"  # raciocínio curto: a tarefa é montar JSON a partir de listas dadas
MAX_OUTPUT_TOKENS = 8192  # cabe 5 looks completos com avaliação; corta respostas descontroladas


MAX_LOGGED_MESSAGE = 200


def _clean(value, limit: int) -> str:
    """Texto de uma linha, sem a chave da API, cortado no limite."""
    text = " ".join(str(value or "").split())
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        text = text.replace(key, "[chave omitida]")
    return text[:limit]


def _error_details(exc: BaseException) -> dict:
    """Só o diagnóstico do Google: `error.status`, `error.message` e o cabeçalho Retry-After.

    O corpo de erro da API não contém o pedido enviado; ainda assim nada além desses três
    campos é lido, e a mensagem é cortada e limpa da chave.
    """
    body = getattr(exc, "body", None)
    if body is None:
        body = getattr(exc, "details", None)  # google.genai.errors.APIError
    error = body.get("error", body) if isinstance(body, dict) else {}
    error = error if isinstance(error, dict) else {}
    status = error.get("status") or getattr(exc, "status", None)
    message = error.get("message") or getattr(exc, "message", None)
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    retry_after = headers.get("retry-after") if headers is not None and hasattr(headers, "get") else None
    return {"status": _clean(status, 40), "message": _clean(message, MAX_LOGGED_MESSAGE), "retry_after": _clean(retry_after, 20)}


TIMEOUT_PHASES = {
    httpx.ConnectTimeout: "ConnectTimeout",  # não abriu a conexão em CONNECT_TIMEOUT
    httpx.WriteTimeout: "WriteTimeout",  # não terminou de enviar o pedido
    httpx.ReadTimeout: "ReadTimeout",  # conectou e enviou, mas o Google não respondeu a tempo
    httpx.PoolTimeout: "PoolTimeout",  # nenhuma conexão livre no cliente
}


def _timeout_phase(exc: BaseException) -> str:
    """Fase do tempo esgotado, pelo tipo da exceção interna; só o nome da classe vai para o log."""
    if isinstance(exc, asyncio.TimeoutError):
        return "guarda_externa"
    cause = exc.__cause__ or exc.__context__
    for timeout_type, name in TIMEOUT_PHASES.items():
        if isinstance(cause, timeout_type):
            return name
    return type(cause).__name__ if cause is not None else "desconhecida"


class GeminiTextProvider:
    name = "gemini"

    def __init__(self):
        self._client: genai.Client | None = None

    def is_configured(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())

    def model_name(self) -> str:
        return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL

    def _get_client(self) -> genai.Client:
        if self._client is None:
            # O tempo limite fica no cliente httpx do SDK: passado por chamada, o SDK reduz o
            # httpx.Timeout ao maior valor e perderia o limite de conexão separado.
            self._client = genai.Client(
                api_key=os.environ["GEMINI_API_KEY"].strip(),
                http_options=genai_types.HttpOptions(async_client_args={"timeout": HTTP_TIMEOUT}),
            )
            # No google-genai 2.34.0, HttpRetryOptions(attempts=0|1) ainda vira uma repetição na
            # Interactions API (o 0 é normalizado para 1 e tratado como max_retries). Sem
            # retry_config, o SDK não repete nem por status HTTP nem por erro de conexão.
            self._client.aio.interactions.sdk_configuration.retry_config = None
        return self._client

    async def generate_json(self, kind: str, system: str, user_text: str, schema: dict) -> str:
        if not self.is_configured():
            raise ProviderError("A IA de estilo não está configurada.", reason="not_configured")
        started = time.monotonic()
        try:
            interaction = await asyncio.wait_for(
                self._get_client().aio.interactions.create(
                    model=self.model_name(),
                    system_instruction=system,
                    input=user_text,
                    response_format={"type": "text", "mime_type": "application/json", "schema": schema},
                    generation_config={"thinking_level": THINKING_LEVEL, "max_output_tokens": MAX_OUTPUT_TOKENS},
                    automatic_continuation=False,
                ),
                timeout=REQUEST_TIMEOUT + GUARD_MARGIN,
            )
        except (asyncio.TimeoutError, APITimeoutError) as exc:
            logger.warning(
                "Gemini %s sem resposta em %.1f s (%s, fase=%s)",
                kind, time.monotonic() - started, type(exc).__name__, _timeout_phase(exc),
            )
            raise ProviderError("A IA de estilo demorou demais para responder.", reason="timeout") from exc
        except APIStatusError as exc:
            raise self._status_error(kind, getattr(exc, "status_code", 0) or 0, started, _error_details(exc)) from exc
        except genai_errors.ClientError as exc:
            raise self._status_error(kind, getattr(exc, "code", 0) or 0, started, _error_details(exc)) from exc
        except (APIConnectionError, genai_errors.APIError, httpx.HTTPError) as exc:
            logger.warning("Gemini %s indisponível após %.1f s: %s", kind, time.monotonic() - started, type(exc).__name__)
            raise ProviderError("A IA de estilo está indisponível no momento.", reason="unavailable") from exc
        except Exception as exc:  # ex.: HTTP 200 com corpo inválido (APIResponseValidationError) ou erro novo do SDK
            logger.warning("Gemini %s erro inesperado após %.1f s: %s", kind, time.monotonic() - started, type(exc).__name__)
            raise ProviderError("A IA de estilo está indisponível no momento.", reason="unavailable") from exc

        status = str(getattr(interaction, "status", "") or "")
        usage = getattr(interaction, "usage", None)
        logger.info(
            "%s model=%s status=%s secs=%.1f usage=%s",
            kind, self.model_name(), status, time.monotonic() - started,
            {k: v for k, v in (usage.model_dump() if hasattr(usage, "model_dump") else {}).items() if "token" in k},
        )
        if status == "incomplete":
            logger.warning("Gemini %s cortado pelo limite de %d tokens de saída", kind, MAX_OUTPUT_TOKENS)
            raise ProviderError("A IA de estilo não conseguiu concluir este pedido.", reason="unavailable")
        if status and status != "completed":
            errors = getattr(interaction, "errors", None) or []
            logger.warning("Gemini %s terminou com status=%s erros=%s", kind, status, [getattr(e, "code", "") for e in errors])
            raise ProviderError("A IA de estilo não conseguiu concluir este pedido.", reason="blocked")
        text = str(getattr(interaction, "output_text", "") or "")
        if not text.strip():
            raise ProviderError("A IA de estilo devolveu uma resposta vazia.", reason="invalid_output")
        return text

    def _status_error(self, kind: str, code: int, started: float, details: dict | None = None) -> ProviderError:
        """Converte o código HTTP em erro seguro para exibir; o log leva o diagnóstico do Google, nunca a chave."""
        details = details or {}
        logger.warning(
            "Gemini %s erro HTTP %s após %.1f s status=%s retry_after=%s mensagem=%r",
            kind, code, time.monotonic() - started,
            details.get("status") or "-", details.get("retry_after") or "-", details.get("message") or "",
        )
        if code == 429:
            return ProviderError("A cota gratuita da IA de estilo foi atingida. Tente novamente mais tarde.", reason="quota")
        if code in (401, 403):
            logger.error("Gemini recusou a autenticação; verifique GEMINI_API_KEY e o acesso ao modelo %s.", self.model_name())
            return ProviderError("A IA de estilo não está configurada corretamente.", reason="auth")
        if code == 404:
            logger.error("Modelo %s não encontrado ou indisponível para esta chave.", self.model_name())
            return ProviderError("O modelo de IA configurado não está disponível.", reason="not_configured")
        if code >= 500:
            return ProviderError("A IA de estilo está indisponível no momento.", reason="unavailable")
        return ProviderError("A IA de estilo recusou este pedido.", reason="blocked")
