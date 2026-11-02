"""Plano B do Look do Dia: mesma regra do endpoint ``lookDoDia`` calculada no servidor Reflex.

Usado apenas quando o endpoint (Xano ou SQLite) falha. Trabalha sobre as peças já
normalizadas pelo estado (chaves ``id``, ``category``, ``season``, ``status``) e não
faz nenhuma chamada externa.
"""

UNAVAILABLE_STATUSES = {"Suja", "Lavando"}
MAX_PIECES = 4


def _sort_id(item: dict) -> int:
    try:
        return int(item.get("id") or 0)
    except (TypeError, ValueError):
        return 0


def _score(item: dict, weather: str, occasion: str) -> int:
    category = str(item.get("category") or "").casefold()
    season = str(item.get("season") or "").casefold()
    weather, occasion = weather.casefold(), occasion.casefold()
    score = 0
    if weather == "frio" and any(word in season for word in ("inverno", "frio")):
        score += 3
    if weather == "quente" and any(word in season for word in ("verão", "quente")):
        score += 3
    if occasion == "evento" and any(word in category for word in ("vestido", "acessório")):
        score += 2
    if occasion == "trabalho" and any(word in category for word in ("partes de cima", "partes de baixo", "vestido")):
        score += 2
    return score


def pick_daily_look(items: list[dict], weather: str, occasion: str) -> list[dict]:
    """Escolhe até quatro peças limpas, uma por categoria, priorizando clima e ocasião."""
    usable = [item for item in items if item.get("status") not in UNAVAILABLE_STATUSES]
    # Mesma ordem do endpoint SQLite: maior pontuação, empate pelo menor id
    usable.sort(key=lambda item: (-_score(item, weather, occasion), _sort_id(item)))
    selected: list[dict] = []
    used_categories: set[str] = set()
    for item in usable:
        if item.get("category") not in used_categories:
            selected.append(item)
            used_categories.add(item.get("category"))
        if len(selected) >= MAX_PIECES:
            break
    return selected


def failure_reason(exc: BaseException) -> str:
    """Motivo curto e sem dados sensíveis para mostrar à pessoa."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status == 404:
        return "o serviço do Look do Dia ainda não está publicado no backend"
    if status == 429:
        return "o backend atingiu o limite de requisições"
    if status in (401, 403):
        return "o backend recusou a sessão"
    if isinstance(status, int) and status >= 500:
        return f"o backend respondeu com erro {status}"
    if isinstance(exc, ValueError):
        return "o backend devolveu uma resposta inválida"
    return "o backend não respondeu"
