"""Pruebas específicas de validaciones para pipelines de Fase 5.

Cada prueba documenta el requisito asociado para mantener trazabilidad
frente a `docs/plan_fase5.md` y las reglas de testing del proyecto.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Iterable, List, Optional

import pytest

from app.services.report_data_repository import ReportDataRepository
from app.services.report_preparation_service import (
    BaseDatasetPipeline,
    BranchSummaryPipeline,
    DatasetValidationError,
    UpcomingArrivalPipeline,
    UpcomingBirthdayPipeline,
)


class _ListRepository(ReportDataRepository):
    """Repositorio mínimo que devuelve listas precargadas."""

    def __init__(
        self,
        *,
        branch_summary_rows: Iterable[Dict[str, Any]] | None = None,
        district_kpis_rows: Iterable[Dict[str, Any]] | None = None,
        upcoming_arrivals_rows: Iterable[Dict[str, Any]] | None = None,
        upcoming_birthdays_rows: Iterable[Dict[str, Any]] | None = None,
    ) -> None:
        self.branch_summary_rows = list(branch_summary_rows or [])
        self.district_kpis_rows = list(district_kpis_rows or [])
        self.upcoming_arrivals_rows = list(upcoming_arrivals_rows or [])
        self.upcoming_birthdays_rows = list(upcoming_birthdays_rows or [])

    def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.branch_summary_rows

    def fetch_district_kpis(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.district_kpis_rows

    def fetch_upcoming_arrivals(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.upcoming_arrivals_rows

    def fetch_upcoming_birthdays(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        return self.upcoming_birthdays_rows


class _SimplePipeline(BaseDatasetPipeline):
    """Pipeline de prueba que expone validaciones básicas."""

    dataset_id = "simple_dataset"
    required_fields = ("id", "value")

    def __init__(self, *, rows: Iterable[Dict[str, Any]]) -> None:
        super().__init__(repository=_ListRepository())
        self._rows = list(rows)

    def _load(self) -> Iterable[Dict[str, Any]]:
        return self._rows


def test_branch_summary_pipeline_detects_duplicates():
    """✅ `BranchSummaryPipeline` rechaza duplicados (`docs/plan_fase5.md`)."""

    repo = _ListRepository(
        branch_summary_rows=[
            {
                "branch_id": 14,
                "district": "Distrito Alfa",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 10,
            },
            {
                "branch_id": 14,
                "district": "Distrito Alfa",
                "first_generation_date": None,
                "first_ccm_arrival": None,
                "last_ccm_departure": None,
                "total_missionaries": 11,
            },
        ]
    )

    pipeline = BranchSummaryPipeline(repository=repo, branch_id=14)

    with pytest.raises(DatasetValidationError) as exc_info:
        pipeline.prepare()

    assert exc_info.value.error_code == "duplicate_records"


def test_upcoming_arrival_pipeline_allows_empty():
    """ℹ️ `UpcomingArrivalPipeline` respeta `allow_empty=True` (notificaciones)."""

    repo = _ListRepository(upcoming_arrivals_rows=[])
    pipeline = UpcomingArrivalPipeline(repository=repo, branch_id=14)

    result = pipeline.prepare()

    assert result.metadata.record_count == 0
    assert result.metadata.dataset_id == "upcoming_arrivals"


def test_upcoming_birthday_pipeline_detects_duplicates():
    """✅ `UpcomingBirthdayPipeline` detecta duplicados relevantes (`docs/plan_fase5.md`)."""

    repo = _ListRepository(
        upcoming_birthdays_rows=[
            {
                "missionary_id": None,
                "missionary_name": "Élder Ramírez",
                "birthday": date.today(),
            },
            {
                "missionary_id": None,
                "missionary_name": "Élder Ramírez",
                "birthday": date.today(),
            },
        ]
    )

    pipeline = UpcomingBirthdayPipeline(repository=repo, branch_id=14)

    with pytest.raises(DatasetValidationError) as exc_info:
        pipeline.prepare()

    assert exc_info.value.error_code == "duplicate_records"


def test_missing_required_fields_raise_custom_error():
    """⚠️ `_SimplePipeline` marca `missing_required_fields` cuando faltan campos."""

    pipeline = _SimplePipeline(
        rows=[
            {"id": 1, "value": "ok"},
            {"id": 2, "value": " "},
            {"id": 3, "value": None},
        ]
    )

    with pytest.raises(DatasetValidationError) as exc_info:
        pipeline.prepare()

    assert exc_info.value.error_code == "missing_required_fields"


def test_empty_dataset_without_allow_empty_triggers_error():
    """⚠️ Las colecciones vacías sin `allow_empty` devuelven `dataset_missing_rows`."""

    pipeline = _SimplePipeline(rows=[])

    with pytest.raises(DatasetValidationError) as exc_info:
        pipeline.prepare()

    assert exc_info.value.error_code == "dataset_missing_rows"
