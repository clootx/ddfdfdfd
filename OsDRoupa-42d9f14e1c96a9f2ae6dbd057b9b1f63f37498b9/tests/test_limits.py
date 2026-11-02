"""Limites persistentes da IA (Etapa 4) sobre SQLite temporário."""

import asyncio

import pytest

from OSDroupa.ai import limits
from professormateria.local_backend import LocalBackend


@pytest.fixture
def limiter(monkeypatch, backend):
    """Aponta o limitador para o backend temporário do teste."""
    monkeypatch.setattr("professormateria.local_backend.local_backend", backend)
    for name in ("OSDROUPA_AI_LOOKS_PER_HOUR", "OSDROUPA_AI_RPM", "OSDROUPA_AI_DAILY_LIMIT",
                 "OSDROUPA_IMAGES_PER_HOUR", "OSDROUPA_IMAGES_RPM", "OSDROUPA_IMAGES_DAILY_LIMIT"):
        monkeypatch.delenv(name, raising=False)
    return backend


def test_atomic_multi_bucket_does_not_consume_on_denial(backend):
    assert backend.reserve_rate_limit_slots([("a", 1, 60), ("b", 5, 60)]) == (0.0, "")
    wait, bucket = backend.reserve_rate_limit_slots([("b", 5, 60), ("a", 1, 60)])
    assert wait > 0 and bucket == "a"
    # "b" não pode ter consumido vaga na tentativa recusada: sobram 4 de 5
    for _ in range(4):
        assert backend.reserve_rate_limit_slots([("b", 5, 60)])[0] == 0
    assert backend.reserve_rate_limit_slots([("b", 5, 60)])[1] == "b"


def test_invalid_configuration(backend):
    with pytest.raises(ValueError):
        backend.reserve_rate_limit_slots([])
    with pytest.raises(ValueError):
        backend.reserve_rate_limit_slots([("x", 0, 60)])


def test_per_account_hourly_limit(limiter, monkeypatch):
    monkeypatch.setenv("OSDROUPA_AI_LOOKS_PER_HOUR", "2")
    assert limits.reserve("texto", "1").allowed and limits.reserve("texto", "1").allowed
    denied = limits.reserve("texto", "1")
    assert not denied.allowed and denied.scope == "conta" and 3000 < denied.wait_seconds <= 3600
    assert "por hora" in denied.message("texto")
    assert limits.reserve("texto", "2").allowed  # outra conta não é afetada


def test_global_per_minute_limit(limiter, monkeypatch):
    monkeypatch.setenv("OSDROUPA_AI_RPM", "2")
    assert limits.reserve("texto", "1").allowed and limits.reserve("texto", "2").allowed
    denied = limits.reserve("texto", "3")
    assert not denied.allowed and denied.scope == "global" and denied.wait_seconds <= 60
    assert "plataforma" in denied.message("texto")


def test_global_daily_limit(limiter, monkeypatch):
    monkeypatch.setenv("OSDROUPA_AI_DAILY_LIMIT", "1")
    assert limits.reserve("texto", "1").allowed
    denied = limits.reserve("texto", "2")
    assert not denied.allowed and denied.scope == "global" and denied.wait_seconds > 3600


def test_text_and_image_are_separate(limiter, monkeypatch):
    monkeypatch.setenv("OSDROUPA_AI_LOOKS_PER_HOUR", "1")
    monkeypatch.setenv("OSDROUPA_IMAGES_PER_HOUR", "1")
    assert limits.reserve("texto", "1").allowed
    assert limits.reserve("imagem", "1").allowed
    assert not limits.reserve("texto", "1").allowed and not limits.reserve("imagem", "1").allowed


def test_limits_survive_restart(tmp_path, monkeypatch):
    db = tmp_path / "persist.sqlite3"
    monkeypatch.setenv("OSDROUPA_AI_LOOKS_PER_HOUR", "1")
    monkeypatch.setattr("professormateria.local_backend.local_backend", LocalBackend(db))
    assert limits.reserve("texto", "1").allowed
    # "Reinício": nova instância do backend, mesmo arquivo
    monkeypatch.setattr("professormateria.local_backend.local_backend", LocalBackend(db))
    assert not limits.reserve("texto", "1").allowed


def test_pause_after_quota_blocks_everyone(limiter, monkeypatch):
    monkeypatch.setenv("OSDROUPA_AI_QUOTA_PAUSE_SECONDS", "120")
    limits.pause_after_quota("texto")
    for account in ("1", "2"):
        denied = limits.reserve("texto", account)
        assert not denied.allowed and denied.scope == "pausa" and 100 < denied.wait_seconds <= 120
        assert "cota gratuita" in denied.message("texto")
    assert limits.reserve("imagem", "1").allowed  # pausa do texto não afeta imagem


def test_paused_request_consumes_nothing(limiter, monkeypatch):
    monkeypatch.setenv("OSDROUPA_AI_LOOKS_PER_HOUR", "1")
    limits.pause_after_quota("texto", 1)
    assert not limits.reserve("texto", "1").allowed
    # Sem a pausa (expirou), a conta ainda tem sua única vaga
    limiter.pause_rate_limit("noop", 0)
    import time
    time.sleep(1.1)
    assert limits.reserve("texto", "1").allowed


def test_missing_account_and_unknown_kind(limiter):
    assert not limits.reserve("texto", "").allowed
    with pytest.raises(ValueError):
        limits.reserve("video", "1")


def test_async_wrapper(limiter):
    assert asyncio.run(limits.reserve_async("texto", "1")).allowed
