"""Offline: o teste live repõe chave e modelo a partir do `.env` (arquivos temporários, sem rede)."""

import os

from OSDroupa.ai.providers import gemini
from test_gemini_live import configure_from_env


def _env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_model_from_env_file_is_used(tmp_path, monkeypatch):
    env = _env(tmp_path, "GEMINI_API_KEY=chave-de-teste-nao-real\nGEMINI_MODEL=gemini-3.6-flash\n")
    has_key, model = configure_from_env(monkeypatch, env)
    assert has_key and model == "gemini-3.6-flash"
    assert os.environ["GEMINI_MODEL"] == "gemini-3.6-flash"
    assert gemini.GeminiTextProvider().model_name() == "gemini-3.6-flash"


def test_without_model_keeps_provider_default(tmp_path, monkeypatch):
    env = _env(tmp_path, "GEMINI_API_KEY=chave-de-teste-nao-real\n")
    has_key, model = configure_from_env(monkeypatch, env)
    assert has_key and model == gemini.DEFAULT_MODEL
    assert "GEMINI_MODEL" not in os.environ


def test_blank_model_keeps_provider_default(tmp_path, monkeypatch):
    env = _env(tmp_path, "GEMINI_API_KEY=chave-de-teste-nao-real\nGEMINI_MODEL=   \n")
    assert configure_from_env(monkeypatch, env) == (True, gemini.DEFAULT_MODEL)


def test_missing_key_or_file_reports_no_key(tmp_path, monkeypatch):
    env = _env(tmp_path, "GEMINI_MODEL=gemini-3.6-flash\n")
    assert configure_from_env(monkeypatch, env) == (False, "gemini-3.6-flash")
    assert "GEMINI_API_KEY" not in os.environ
    assert configure_from_env(monkeypatch, tmp_path / "nao-existe.env")[0] is False


def test_result_never_contains_key(tmp_path, monkeypatch):
    env = _env(tmp_path, "GEMINI_API_KEY=chave-de-teste-nao-real\nGEMINI_MODEL=gemini-3.6-flash\n")
    assert "chave-de-teste-nao-real" not in repr(configure_from_env(monkeypatch, env))
