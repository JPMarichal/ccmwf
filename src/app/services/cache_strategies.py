"""Estrategias de caché para la preparación de reportes."""

from __future__ import annotations

import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger("report_cache")

try:  # pragma: no cover - import opcional
    import redis  # type: ignore
except ImportError:  # pragma: no cover - redis es opcional
    redis = None  # type: ignore


@dataclass
class CacheMetrics:
    """Métricas básicas de uso de caché."""

    hits: int = 0
    misses: int = 0
    writes: int = 0
    invalidations: int = 0
    expirations: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


class CacheStrategy(ABC):
    """Interfaz para estrategias de caché."""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def invalidate(self, key: str) -> None:
        raise NotImplementedError

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidar todos los elementos cuyo key inicie con el prefijo dado."""
        raise NotImplementedError

    @abstractmethod
    def get_metrics(self) -> Dict[str, int]:
        raise NotImplementedError


class InMemoryCacheStrategy(CacheStrategy):
    """Estrategia de caché en memoria con TTL simple."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._expirations: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._metrics = CacheMetrics()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            expires_at = self._expirations.get(key)
            expired = expires_at is not None and expires_at < time.time()
            if expired:
                self._store.pop(key, None)
                self._expirations.pop(key, None)
                self._metrics.expirations += 1
                logger.debug(
                    "cache_expirada_memoria",
                    etapa="fase_5_preparacion",
                    clave=key,
                )

            value = self._store.get(key)
            if value is not None:
                self._metrics.hits += 1
                logger.debug("cache_hit_memoria", etapa="fase_5_preparacion", clave=key)
                return value

            self._metrics.misses += 1
            logger.debug("cache_fallo_memoria", etapa="fase_5_preparacion", clave=key)
            return None

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            logger.debug("cache_descartada_memoria", etapa="fase_5_preparacion", clave=key, ttl=ttl_seconds)
            return

        with self._lock:
            self._store[key] = value
            if ttl_seconds:
                self._expirations[key] = time.time() + ttl_seconds
            else:
                self._expirations.pop(key, None)
            self._metrics.writes += 1
            logger.debug("cache_guardada_memoria", etapa="fase_5_preparacion", clave=key, ttl=ttl_seconds)

    def invalidate(self, key: str) -> None:
        with self._lock:
            removed = self._store.pop(key, None)
            self._expirations.pop(key, None)
            if removed is not None:
                self._metrics.invalidations += 1
            logger.debug("cache_invalidada_memoria", etapa="fase_5_preparacion", clave=key)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            if not keys:
                return

            for key in keys:
                self._store.pop(key, None)
                self._expirations.pop(key, None)

            self._metrics.invalidations += len(keys)
            logger.debug(
                "cache_invalidada_prefijo_memoria",
                etapa="fase_5_preparacion",
                prefijo=prefix,
                total=len(keys),
            )

    def get_metrics(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._metrics.to_dict())


class RedisCacheStrategy(CacheStrategy):
    """Estrategia de caché basada en Redis."""

    def __init__(self, redis_url: str) -> None:
        if not redis:  # pragma: no cover - dependiente de import opcional
            raise RuntimeError("redis no está instalado. Instálalo para usar RedisCacheStrategy")
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._metrics = CacheMetrics()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        payload = self._client.get(key)
        if payload is None:
            with self._lock:
                self._metrics.misses += 1
            logger.debug("cache_fallo_redis", etapa="fase_5_preparacion", clave=key)
            return None
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - datos corruptos
            self.invalidate(key)
            logger.warning(
                "cache_payload_invalido_redis",
                etapa="fase_5_preparacion",
                clave=key,
            )
            return None

        with self._lock:
            self._metrics.hits += 1
        logger.debug("cache_hit_redis", etapa="fase_5_preparacion", clave=key)
        return value

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            logger.debug("cache_descartada_redis", etapa="fase_5_preparacion", clave=key, ttl=ttl_seconds)
            return

        payload = json.dumps(value, default=str)
        if ttl_seconds:
            self._client.setex(key, ttl_seconds, payload)
        else:
            self._client.set(key, payload)
        with self._lock:
            self._metrics.writes += 1
        logger.debug("cache_guardada_redis", etapa="fase_5_preparacion", clave=key, ttl=ttl_seconds)

    def invalidate(self, key: str) -> None:
        self._client.delete(key)
        with self._lock:
            self._metrics.invalidations += 1
        logger.debug("cache_invalidada_redis", etapa="fase_5_preparacion", clave=key)

    def invalidate_prefix(self, prefix: str) -> None:
        pattern = f"{prefix}*"
        keys = list(self._client.scan_iter(match=pattern))
        if not keys:
            return

        self._client.delete(*keys)
        with self._lock:
            self._metrics.invalidations += len(keys)
        logger.debug(
            "cache_invalidada_prefijo_redis",
            etapa="fase_5_preparacion",
            prefijo=prefix,
            total=len(keys),
        )

    def get_metrics(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._metrics.to_dict())


def create_cache_strategy(settings: Any) -> CacheStrategy:
    """Crear estrategia de caché basada en configuración."""

    provider = getattr(settings, "cache_provider", "memory") or "memory"
    provider = provider.lower()

    if provider == "redis":
        redis_url = getattr(settings, "redis_url", None)
        if not redis_url:
            raise ValueError("redis_url es requerido cuando cache_provider=redis")
        return RedisCacheStrategy(redis_url)

    if provider != "memory":
        logger.warning(
            "cache_provider_desconocido",
            etapa="fase_5_preparacion",
            provider=provider,
            accion="se usa memoria",
        )
    return InMemoryCacheStrategy()
