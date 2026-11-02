"""Limites persistentes de uso da IA (Change 029, Etapa 4).

Usa as tabelas `outbound_rate_limits` do SQLite local (as mesmas do controle de
chamadas ao Xano), então os limites valem entre reinícios e entre processos.
Funciona nos dois modos (SQLite e Xano), pois o banco local sempre existe.

Cada pedido reserva, de forma atômica, uma vaga em três baldes:
- por conta e por hora (abuso individual);
- global por minuto (respeitar o RPM do plano gratuito);
- global por dia (respeitar a cota diária do plano gratuito).
Texto e imagem têm baldes separados.
"""

import asyncio
import logging
import math
import os
from dataclasses import dataclass

logger = logging.getLogger("osdroupa.ai.limits")

KINDS = ("texto", "imagem")

# (variável de ambiente, padrão) — padrões conservadores para o plano gratuito.
_DEFAULTS = {
    "texto": {"conta_hora": ("OSDROUPA_AI_LOOKS_PER_HOUR", 10), "minuto": ("OSDROUPA_AI_RPM", 5), "dia": ("OSDROUPA_AI_DAILY_LIMIT", 200)},
    "imagem": {"conta_hora": ("OSDROUPA_IMAGES_PER_HOUR", 5), "minuto": ("OSDROUPA_IMAGES_RPM", 2), "dia": ("OSDROUPA_IMAGES_DAILY_LIMIT", 20)},
}
QUOTA_PAUSE_ENV = ("OSDROUPA_AI_QUOTA_PAUSE_SECONDS", 60)


@dataclass
class LimitResult:
    allowed: bool
    wait_seconds: int = 0
    scope: str = ""  # "conta" | "global" | "pausa"

    def message(self, kind: str) -> str:
        minutes = max(1, math.ceil(self.wait_seconds / 60))
        label = "pedidos de imagem" if kind == "imagem" else "pedidos à IA de estilo"
        if self.scope == "conta":
            return f"Você atingiu o limite de {label} por hora. Tente novamente em {minutes} min."
        if self.scope == "pausa":
            return f"A cota gratuita da IA foi atingida há pouco. Tente novamente em {minutes} min."
        return f"A plataforma atingiu o limite de {label} no momento. Tente novamente em {minutes} min."


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


def _backend():
    from professormateria import local_backend as module

    return module.local_backend


def bucket_names(kind: str, account_id: str) -> dict[str, str]:
    return {
        "conta_hora": f"ai:{kind}:conta:{account_id}",
        "minuto": f"ai:{kind}:global:minuto",
        "dia": f"ai:{kind}:global:dia",
        "pausa": f"ai:{kind}:global:pausa",
    }


def reserve(kind: str, account_id: str) -> LimitResult:
    """Reserva uma vaga (síncrono, acessa o SQLite)."""
    if kind not in KINDS:
        raise ValueError(f"Tipo de limite desconhecido: {kind}")
    if not account_id:
        return LimitResult(False, 60, "conta")
    config = _DEFAULTS[kind]
    names = bucket_names(kind, account_id)
    limits = [
        (names["pausa"], 1_000_000, 60.0),  # só bloqueia quando pausado após um 429
        (names["minuto"], _int_env(*config["minuto"]), 60.0),
        (names["conta_hora"], _int_env(*config["conta_hora"]), 3600.0),
        (names["dia"], _int_env(*config["dia"]), 86400.0),
    ]
    wait, bucket = _backend().reserve_rate_limit_slots(limits)
    if wait <= 0:
        return LimitResult(True)
    scope = {names["conta_hora"]: "conta", names["pausa"]: "pausa"}.get(bucket, "global")
    logger.info("limite atingido kind=%s escopo=%s espera=%.0fs", kind, scope, wait)
    return LimitResult(False, math.ceil(wait), scope)


async def reserve_async(kind: str, account_id: str) -> LimitResult:
    return await asyncio.to_thread(reserve, kind, account_id)


def pause_after_quota(kind: str, seconds: int | None = None) -> None:
    """Bloqueia novos pedidos de todas as contas após um 429 do provedor."""
    seconds = seconds or _int_env(*QUOTA_PAUSE_ENV)
    _backend().pause_rate_limit(bucket_names(kind, "_")["pausa"], float(seconds))
    logger.warning("cota do provedor atingida; pedidos de %s pausados por %ss", kind, seconds)


async def pause_after_quota_async(kind: str, seconds: int | None = None) -> None:
    await asyncio.to_thread(pause_after_quota, kind, seconds)
