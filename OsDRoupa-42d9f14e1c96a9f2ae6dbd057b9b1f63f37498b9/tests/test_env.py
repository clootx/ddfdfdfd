"""Carregamento do .env (Etapa 2). Usa arquivos .env temporários, nunca o real."""

import logging

import pytest

from OSDroupa import env


@pytest.fixture
def fresh_loader(monkeypatch):
    monkeypatch.setattr(env, "_loaded", False)
    monkeypatch.delenv("OSDROUPA_DISABLE_DOTENV", raising=False)
    for key in ("OSD_TEST_A", "OSD_TEST_B", "OSD_TEST_SECRET"):
        monkeypatch.delenv(key, raising=False)
    return env.load_project_env


def write_env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_missing_variables(fresh_loader, tmp_path, monkeypatch):
    path = write_env(tmp_path, "OSD_TEST_A=valor-a\n# comentário\nOSD_TEST_B=\"com espaço\"\n")
    applied = fresh_loader(path)
    assert sorted(applied) == ["OSD_TEST_A", "OSD_TEST_B"]
    import os
    assert os.environ["OSD_TEST_A"] == "valor-a" and os.environ["OSD_TEST_B"] == "com espaço"


def test_terminal_has_priority(fresh_loader, tmp_path, monkeypatch):
    monkeypatch.setenv("OSD_TEST_A", "do-terminal")
    path = write_env(tmp_path, "OSD_TEST_A=do-arquivo\n")
    assert fresh_loader(path) == []
    import os
    assert os.environ["OSD_TEST_A"] == "do-terminal"


def test_disabled_flag_skips_file(fresh_loader, tmp_path, monkeypatch):
    monkeypatch.setenv("OSDROUPA_DISABLE_DOTENV", "1")
    path = write_env(tmp_path, "OSD_TEST_A=x\n")
    assert fresh_loader(path) == []


def test_missing_file_and_load_once(fresh_loader, tmp_path):
    assert fresh_loader(tmp_path / "nao-existe.env") == []
    path = write_env(tmp_path, "OSD_TEST_A=x\n")
    assert fresh_loader(path) == []  # já carregado neste processo


def test_never_logs_values(fresh_loader, tmp_path, caplog):
    path = write_env(tmp_path, "OSD_TEST_SECRET=chave-super-secreta\n")
    with caplog.at_level(logging.INFO, logger="osdroupa.env"):
        fresh_loader(path)
    assert "OSD_TEST_SECRET" in caplog.text and "chave-super-secreta" not in caplog.text


def test_tests_never_read_real_env():
    import os
    assert os.environ.get("OSDROUPA_DISABLE_DOTENV") == "1"
    assert not os.environ.get("GEMINI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY")
