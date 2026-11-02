"""Carregamento do arquivo .env da raiz do projeto.

Regras:
- Variáveis já definidas no terminal têm prioridade (override=False); o .env só
  preenche o que falta. O `env_file` do rx.Config faria o contrário
  (override=True), por isso não é usado.
- Os testes definem OSDROUPA_DISABLE_DOTENV=1 para nunca ler chaves reais.
- Só registra quais nomes foram carregados, nunca os valores.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger("osdroupa.env")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

_loaded = False


def load_project_env(env_file: Path | None = None) -> list[str]:
    """Carrega o .env uma vez por processo; devolve os nomes das variáveis aplicadas."""
    global _loaded
    if _loaded or os.environ.get("OSDROUPA_DISABLE_DOTENV") == "1":
        return []
    _loaded = True
    path = env_file or DEFAULT_ENV_FILE
    if not path.is_file():
        return []
    try:
        from dotenv import dotenv_values
    except ImportError:
        logger.error("Arquivo .env encontrado, mas o pacote python-dotenv não está instalado (pip install -r requirements.txt).")
        return []
    applied = []
    for key, value in dotenv_values(path).items():
        if value is None or key in os.environ:
            continue
        os.environ[key] = value
        applied.append(key)
    if applied:
        logger.info("Variáveis carregadas do .env: %s", ", ".join(sorted(applied)))
    return applied
