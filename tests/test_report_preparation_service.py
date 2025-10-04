"""Pruebas unitarias para `ReportPreparationService` y pipelines de Fase 5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import pytest

from app.services.cache_strategies import InMemoryCacheStrategy
from app.services.report_data_repository import ReportDataRepository, ReportDataRepositoryError
from app.services.report_preparation_service import (
    DatasetValidationError,
    ReportPreparationError,
    ReportPreparationService,
)


@dataclass
class StubRepository(ReportDataRepository):
    """Repositorio en memoria para simular respuestas de vistas MySQL."""

    branch_summary_rows: List[Dict[str, Any]]
    district_kpis_rows: List[Dict[str, Any]]
    upcoming_arrivals_rows: List[Dict[str, Any]]
    upcoming_birthdays_rows: List[Dict[str, Any]]

    def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.branch_summary_rows

    def fetch_district_kpis(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.district_kpis_rows

    def fetch_upcoming_arrivals(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.upcoming_arrivals_rows

    def fetch_upcoming_birthdays(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.upcoming_birthdays_rows


def build_service(repository: ReportDataRepository) -> ReportPreparationService:
    """Crea la fachada con caché en memoria para pruebas."""

    cache = InMemoryCacheStrategy()
    return ReportPreparationService(default_branch_id=14, cache_strategy=cache, repository=repository)


def test_prepare_branch_summary_success():
    """Valida ruta feliz de Branch Summary (requisito: dataset completo)."""
    # Requisito: Fase 5 debe entregar `BranchSummary` consistente para consumo de reportes (`docs/plan_fase5.md`).

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito 1",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 12,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            }
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)
    result = service.prepare_branch_summary()
    assert result.metadata.record_count == 1
    assert result.metadata.cache_hit is False
    assert result.data[0]["district"] == "Distrito 1"
    assert result.data[0]["total_missionaries"] == 12


def test_prepare_branch_summary_negative_total_raises():
    """Detecta métricas inválidas y devuelve `invalid_total_missionaries`."""
    # Requisito: Validar métricas derivadas antes de distribuir datos (`docs/plan_fase5.md`, Validadores).

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito 1",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": -5,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            }
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)
    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_branch_summary()

    assert exc_info.value.error_code == "invalid_total_missionaries"


def test_upcoming_arrivals_allows_empty():
    """Los pipelines configurados con `allow_empty` no deben fallar (Telegram)."""
    # Requisito: Notificaciones Telegram/Messenger deben tolerar ausencia de datos (`docs/reportes_inventario.md`).

    repository = StubRepository(
        branch_summary_rows=[],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)
    result = service.prepare_upcoming_arrivals()

    assert result.metadata.record_count == 0
    assert result.metadata.cache_hit is False


def test_cache_hit_on_second_call():
    """La estrategia de caché debe responder con `cache_hit=True` en la segunda consulta."""
    # Requisito: Reutilizar datasets mediante caché configurable (`docs/plan_fase5.md`, capa de caché).

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito 2",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 5,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            }
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)
    first = service.prepare_branch_summary()
    second = service.prepare_branch_summary()

    assert first.metadata.cache_hit is False
    assert second.metadata.cache_hit is True
    assert second.metadata.record_count == 1


def test_cache_metrics_track_usage():
    """✅ Registra métricas de caché para auditoría (`docs/plan_fase5.md`)."""

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito 5",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 9,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            }
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    first = service.prepare_branch_summary()
    metrics_after_first = service._cache.get_metrics()

    assert first.metadata.cache_hit is False
    assert metrics_after_first["misses"] == 1
    assert metrics_after_first["writes"] == 1

    second = service.prepare_branch_summary()
    metrics_after_second = service._cache.get_metrics()

    assert second.metadata.cache_hit is True
    assert metrics_after_second["hits"] == 1
    assert metrics_after_second["misses"] == 1
    assert metrics_after_second["writes"] == 1
    assert metrics_after_second["expirations"] == 0


def test_branch_summary_duplicate_rows_raise_error():
    """Detecta duplicados en campos clave y emite `duplicate_records`."""
    # Requisito: Controlar duplicados en pipelines (`docs/plan_fase5.md`, validaciones adicionales).

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito 6",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 8,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            },
            {
                "branch_id": 14,
                "district": "Distrito 6",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 9,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            },
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_branch_summary()

    assert exc_info.value.error_code == "duplicate_records"


def test_district_kpis_out_of_range_value_raises():
    """Controla KPIs fuera de rango y devuelve `invalid_kpi_value`."""
    # Requisito: Validar valores anómalos antes de distribuir KPIs (`docs/plan_fase5.md`).

    repository = StubRepository(
        branch_summary_rows=[],
        district_kpis_rows=[
            {
                "branch_id": 14,
                "district": "Distrito Centro",
                "metric": "total_missionaries",
                "value": 999.0,
                "unit": "misioneros",
                "generated_for_week": date.today(),
                "extra": {},
            }
        ],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_district_kpis()

    assert exc_info.value.error_code == "invalid_kpi_value"


def test_prepare_branch_summary_invalid_branch_rejected():
    """Impide preparar datasets con ramas no autorizadas (`invalid_branch`)."""
    # Requisito: Limitar el procesamiento a ramas autorizadas (`.env`, `docs/plan_fase5.md`).

    repository = StubRepository(
        branch_summary_rows=[],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_branch_summary(branch_id=99)

    assert exc_info.value.error_code == "invalid_branch"


def test_branch_summary_missing_required_fields_error_code():
    """Valida presencia de campos obligatorios y retorna `missing_required_fields`."""
    # Requisito: Detectar registros incompletos previo a serialización (`docs/plan_fase5.md`).

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": " ",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 7,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            }
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_branch_summary()

    assert exc_info.value.error_code == "missing_required_fields"


def test_cache_stale_invalidates_and_refreshes():
    """Renueva entradas caducas y actualiza métricas de invalidación (`stale_cache`)."""
    # Requisito: Detectar caché obsoleta y regenerar dataset (`docs/plan_fase5.md`, códigos de error).

    repository = StubRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito Original",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 10,
                "total_companionships": None,
                "elders_count": None,
                "sisters_count": None,
            }
        ],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    first_result = service.prepare_branch_summary()
    assert first_result.metadata.cache_hit is False

    cache_key = service._build_cache_key("branch_summary", 14, {})
    cached_payload = service._cache._store[cache_key]
    cached_payload["metadata"]["generated_at"] = (datetime.utcnow() - timedelta(hours=2)).isoformat()

    repository.branch_summary_rows = [
        {
            "branch_id": 14,
            "district": "Distrito Renovado",
            "first_generation_date": None,
            "first_ccm_arrival": None,
            "last_ccm_departure": None,
            "total_missionaries": 11,
            "total_companionships": None,
            "elders_count": None,
            "sisters_count": None,
        }
    ]

    refreshed_result = service.prepare_branch_summary()
    metrics_after_refresh = service._cache.get_metrics()

    assert refreshed_result.metadata.cache_hit is False
    assert refreshed_result.data[0]["district"] == "Distrito Renovado"
    assert metrics_after_refresh["invalidations"] >= 1


def test_upcoming_arrivals_negative_count():
    """Controla escenarios inválidos para reportes de Telegram/Messenger."""
    # Requisito: Logs de errores con códigos específicos al detectar datos incorrectos (`docs/plan_fase5.md`).

    repository = StubRepository(
        branch_summary_rows=[],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[
            {
                "district": "Distrito 3",
                "rdistrict": "R-3",
                "branch_id": 14,
                "arrival_date": date.today(),
                "departure_date": date.today() + timedelta(weeks=6),
                "missionaries_count": -1,
                "duration_weeks": 6,
                "status": None,
            }
        ],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_upcoming_arrivals()

    assert exc_info.value.error_code == "invalid_missionaries_count"

def test_branch_summary_missing_rows_triggers_error():
    """Detecta ausencia de registros cuando no se permite `allow_empty`."""
    # Requisito: Evitar datasets vacíos para reportes críticos (`docs/plan_fase5.md`, riesgos de datos incompletos).

    repository = StubRepository(
        branch_summary_rows=[],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(DatasetValidationError) as exc_info:
        service.prepare_branch_summary()

    assert exc_info.value.error_code == "dataset_missing_rows"


def test_repository_error_is_wrapped():
    """Errores de repositorio se envuelven como `ReportPreparationError`."""
    # Requisito: Manejo uniforme de fallos en consultas SQL (`docs/plan_fase5.md`, capa de integridad).

    class FailingRepository(StubRepository):
        def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]):  # type: ignore[override]
            raise ReportDataRepositoryError("Repo error")

    repository = FailingRepository(
        branch_summary_rows=[],
        district_kpis_rows=[],
        upcoming_arrivals_rows=[],
        upcoming_birthdays_rows=[],
    )

    service = build_service(repository)

    with pytest.raises(ReportPreparationError):
        service.prepare_branch_summary()
