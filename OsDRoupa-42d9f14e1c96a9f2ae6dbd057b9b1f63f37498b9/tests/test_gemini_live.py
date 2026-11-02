"""Chamada REAL ao Gemini (Etapa 8). Só roda com `pytest -m live tests/test_gemini_live.py`.

Faz exatamente uma requisição de texto, direto no provedor (sem a nova tentativa do
estilista), com armário e catálogo fictícios: nenhum dado de pessoa real é enviado.
A chave é lida do `.env` da raiz (o conftest remove as chaves do ambiente) e nunca é impressa.
Antes de rodar: confirmar no AI Studio que o projeto está no Free Tier, sem faturamento.
"""

import asyncio
import json
import time
from pathlib import Path

import pytest
from dotenv import dotenv_values

from OSDroupa.ai import stylist
from OSDroupa.ai.providers.gemini import GeminiTextProvider

WARDROBE = [
    {"id": "1", "local_id": "t-camisa-linho", "name": "Camisa de linho branca", "category": "Partes de cima", "status": "No armário", "color": "branca", "season": "Verão"},
    {"id": "2", "local_id": "t-blusa-malha", "name": "Blusa de malha azul", "category": "Partes de cima", "status": "No armário", "color": "azul", "season": ""},
    {"id": "3", "local_id": "t-calca-alfaiataria", "name": "Calça de alfaiataria bege", "category": "Partes de baixo", "status": "No armário", "color": "bege", "season": ""},
    {"id": "4", "local_id": "t-bermuda-sarja", "name": "Bermuda de sarja verde", "category": "Partes de baixo", "status": "No armário", "color": "verde", "season": "Verão"},
    {"id": "5", "local_id": "t-vestido-midi", "name": "Vestido midi estampado", "category": "Vestidos", "status": "No armário", "color": "estampado", "season": "Verão"},
    {"id": "6", "local_id": "t-tenis-branco", "name": "Tênis branco", "category": "Calçados", "status": "No armário", "color": "branco", "season": ""},
    {"id": "7", "local_id": "t-sandalia", "name": "Sandália de couro caramelo", "category": "Calçados", "status": "No armário", "color": "caramelo", "season": "Verão"},
]
CATALOG = [{"id": "901", "name": "Mocassim marrom", "category": "Calçados", "product_type": "Mocassim", "colors": "marrom", "material": "couro", "availability": "Disponível agora"}]
WEATHER = {"cidade": "Recife", "uf": "PE", "regiao": "Nordeste", "sensacao": 33, "temperatura": 30, "chuva_prob": 40, "umidade": 78, "periodo": "manhã", "categoria": "Quente"}


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def configure_from_env(monkeypatch, env_file: Path = ENV_FILE) -> tuple[bool, str]:
    """Repõe a chave e o modelo do `.env` (o conftest remove ambos do ambiente).

    Sem GEMINI_MODEL no arquivo, o provedor usa o próprio padrão, como no app.
    Devolve se há chave e o modelo que o provedor vai usar; a chave nunca é devolvida.
    """
    values = dotenv_values(env_file) if env_file.exists() else {}
    key = (values.get("GEMINI_API_KEY") or "").strip()
    model = (values.get("GEMINI_MODEL") or "").strip()
    if key:
        monkeypatch.setenv("GEMINI_API_KEY", key)
    if model:
        monkeypatch.setenv("GEMINI_MODEL", model)
    return bool(key), GeminiTextProvider().model_name()


@pytest.mark.live
def test_single_real_gemini_call(monkeypatch):
    has_key, model = configure_from_env(monkeypatch)
    if not has_key:
        pytest.skip("GEMINI_API_KEY ausente no .env")
    print(f"\nmodelo selecionado para a chamada real: {model}")
    provider = GeminiTextProvider()
    context = stylist.build_prompt_context(WEATHER, "Trabalho", "Minimalista", "", WARDROBE, CATALOG, [], None)

    started = time.monotonic()
    text = asyncio.run(provider.generate_json("looks", stylist.SYSTEM_PROMPT,
                                              f"Contexto da pessoa (JSON):\n{json.dumps(context, ensure_ascii=False)}",
                                              stylist.LOOKS_SCHEMA))
    elapsed = time.monotonic() - started

    raw_looks = stylist._parse_looks(text)  # 3 a 5 looks, JSON válido
    proposals, downgraded = stylist.validate_looks(raw_looks, WARDROBE, CATALOG)
    print(f"\nmodelo={provider.model_name()} segundos={elapsed:.1f} looks={len(raw_looks)} validos={len(proposals)} refs_rebaixadas={downgraded}")
    for p in proposals:
        print(f"- {p.nome} | {p.descricao[:90]} | pecas={[piece.ref or piece.nome for piece in p.pecas]} | acessorios={p.acessorios_sugeridos} | nota={p.avaliacao.nota_geral}")
    assert 3 <= len(raw_looks) <= 5 and proposals
    assert all(p.descricao for p in proposals)
