"""Pruebas para las estrategias de caché empleadas en reportes (Fase 5)."""

from __future__ import annotations

import types

import pytest

from app.services import cache_strategies


@pytest.fixture(autouse=True)
def _restore_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restaura la referencia al módulo redis tras cada prueba."""

    original_redis = cache_strategies.redis
    try:
        yield
    finally:
        monkeypatch.setattr(cache_strategies, "redis", original_redis, raising=False)


def test_create_cache_strategy_fallbacks_to_memory_when_redis_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Issue #26: Debe caer a memoria si la dependencia redis no está instalada."""

    monkeypatch.setattr(cache_strategies, "redis", None, raising=False)
    settings = types.SimpleNamespace(cache_provider="redis", redis_url="redis://localhost:6379/0")

    strategy = cache_strategies.create_cache_strategy(settings)

    assert isinstance(strategy, cache_strategies.InMemoryCacheStrategy)
