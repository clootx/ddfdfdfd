"""Provedores de texto do estilista (Change 029).

O estilista (`stylist.py`) só conhece a interface `TextProvider`; trocar de
provedor é implementar outra classe aqui e apontar OSDROUPA_AI_PROVIDER para ela.
"""

import os
from typing import Protocol


class ProviderError(Exception):
    """Falha do provedor; `reason` classifica o erro e a mensagem é segura para o usuário."""

    def __init__(self, message: str, reason: str = "unavailable", retry_after: int | None = None):
        super().__init__(message)
        self.reason = reason  # not_configured | quota | auth | blocked | invalid_output | timeout | unavailable
        self.retry_after = retry_after


class TextProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def model_name(self) -> str: ...

    async def generate_json(self, kind: str, system: str, user_text: str, schema: dict) -> str:
        """Devolve o texto JSON gerado conforme `schema` ou levanta ProviderError."""
        ...


_provider: TextProvider | None = None


def get_text_provider() -> TextProvider:
    global _provider
    if _provider is None:
        name = os.environ.get("OSDROUPA_AI_PROVIDER", "gemini").strip().lower() or "gemini"
        if name != "gemini":
            raise ProviderError(f"Provedor de IA desconhecido: {name}.", reason="not_configured")
        from OSDroupa.ai.providers.gemini import GeminiTextProvider

        _provider = GeminiTextProvider()
    return _provider
