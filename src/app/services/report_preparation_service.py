"""Servicios de preparación de datasets para reportes (Fase 5)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type

import structlog

from app.config import get_settings
from app.models import (
    BranchSummary,
    DistrictKPI,
    ReportDatasetMetadata,
    ReportDatasetResult,
    UpcomingArrival,
    UpcomingBirthday,
)
from app.services.cache_strategies import CacheStrategy, create_cache_strategy
from app.services.report_data_repository import (
    ReportDataRepository,
    ReportDataRepositoryError,
    SQLAlchemyReportDataRepository,
)

logger = structlog.get_logger("report_preparation")


class ReportPreparationError(Exception):
    """Error genérico de preparación de reportes."""


class DatasetValidationError(ReportPreparationError):
    """Errores de validación específicos de datasets."""

    def __init__(self, message: str, *, error_code: str = "validation_error") -> None:
        super().__init__(message)
        self.error_code = error_code


class BaseDatasetPipeline:
    """Plantilla base para preparar datasets reutilizables."""

    dataset_id: str = "base_dataset"

    required_fields: Iterable[str] = ()
    allow_empty: bool = False
    unique_fields: Iterable[str] = ()

    def __init__(
        self,
        *,
        repository: ReportDataRepository,
        branch_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.repository = repository
        self.branch_id = branch_id
        self.params = params or {}
        self._context: Dict[str, Any] = {}

    def prepare(self) -> ReportDatasetResult:
        start = datetime.utcnow()
        raw_rows = list(self._load())
        self._ensure_not_empty(raw_rows, stage="load")
        cleaned = list(self._validate(raw_rows))
        self._ensure_not_empty(cleaned, stage="validate")
        transformed = list(self._transform(cleaned))
        result = self._serialize(transformed)
        metadata = ReportDatasetMetadata(
            dataset_id=self.dataset_id,
            generated_at=start,
            record_count=len(result),
            branch_id=self.branch_id,
            duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
            cache_hit=False,
            parameters=self.params,
        )
        return ReportDatasetResult(metadata=metadata, data=result)

    # Métodos plantilla

    def _validate(self, rows: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        validated: List[Dict[str, Any]] = []
        required = tuple(self.required_fields)
        unique_fields = tuple(self.unique_fields)
        seen_unique: Set[Tuple[Any, ...]] = set()
        rows_list = rows if isinstance(rows, list) else list(rows)
        for index, row in enumerate(rows_list):
            if required:
                missing = [
                    field
                    for field in required
                    if row.get(field) is None
                    or (isinstance(row.get(field), str) and not str(row.get(field)).strip())
                ]
                if missing:
                    raise DatasetValidationError(
                        f"Campos faltantes {missing} en registro {index} del dataset {self.dataset_id}",
                        error_code="missing_required_fields",
                    )
            if unique_fields:
                key_components: List[Any] = []
                has_meaningful_value = False
                for field in unique_fields:
                    value = row.get(field)
                    if isinstance(value, str):
                        value = value.strip() or None
                    if value is not None:
                        has_meaningful_value = True
                    key_components.append(value)
                if not has_meaningful_value:
                    validated.append(row)
                    continue
                key = tuple(key_components)
                if key in seen_unique:
                    raise DatasetValidationError(
                        f"Registros duplicados en {self.dataset_id} para campos {unique_fields}",
                        error_code="duplicate_records",
                    )
                seen_unique.add(key)
            validated.append(row)
        return validated

    def _transform(self, rows: Iterable[Dict[str, Any]]) -> Iterable[Any]:
        return rows

    def _serialize(self, rows: Iterable[Any]) -> List[Any]:
        serialized: List[Any] = []
        for row in rows:
            if hasattr(row, "model_dump"):
                serialized.append(row.model_dump(mode="json"))
            else:
                serialized.append(row)
        return serialized

    def _ensure_not_empty(self, rows: List[Dict[str, Any]], *, stage: str) -> None:
        if rows or self.allow_empty:
            return
        raise DatasetValidationError(
            f"El dataset '{self.dataset_id}' no produjo resultados durante la etapa {stage}",
            error_code="dataset_missing_rows",
        )


class BranchSummaryPipeline(BaseDatasetPipeline):
    dataset_id = "branch_summary"
    required_fields = (
        "branch_id",
        "district",
        "total_missionaries",
    )
    allow_empty = False
    unique_fields = ("branch_id", "district")

    def _load(self) -> Iterable[Dict[str, Any]]:
        return self.repository.fetch_branch_summary(self.branch_id, self.params)

    def _transform(self, rows: Iterable[Dict[str, Any]]) -> Iterable[BranchSummary]:
        for row in rows:
            yield BranchSummary(**row)

    def _validate(self, rows: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        validated = list(super()._validate(rows))
        for index, row in enumerate(validated):
            total = row.get("total_missionaries")
            if total is not None and total < 0:
                raise DatasetValidationError(
                    f"Total de misioneros negativo en registro {index} del dataset {self.dataset_id}",
                    error_code="invalid_total_missionaries",
                )
            if total is not None and total > 500:
                raise DatasetValidationError(
                    f"Total de misioneros fuera de rango en registro {index} del dataset {self.dataset_id}",
                    error_code="invalid_total_missionaries",
                )
        return validated


class DistrictKPIPipeline(BaseDatasetPipeline):
    dataset_id = "district_kpi"
    required_fields = (
        "branch_id",
        "district",
        "metric",
        "value",
    )
    allow_empty = False
    unique_fields = ("branch_id", "district", "metric")

    def _load(self) -> Iterable[Dict[str, Any]]:
        return self.repository.fetch_district_kpis(self.branch_id, self.params)

    def _transform(self, rows: Iterable[Dict[str, Any]]) -> Iterable[DistrictKPI]:
        for row in rows:
            yield DistrictKPI(**row)

    def _validate(self, rows: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        validated = list(super()._validate(rows))
        for index, row in enumerate(validated):
            value = row.get("value")
            if value is not None and value < 0:
                raise DatasetValidationError(
                    f"Valor negativo en KPI '{row.get('metric')}' en registro {index}",
                    error_code="invalid_kpi_value",
                )
            if value is not None and value > 500:
                raise DatasetValidationError(
                    f"Valor fuera de rango en KPI '{row.get('metric')}' en registro {index}",
                    error_code="invalid_kpi_value",
                )
        return validated


class UpcomingArrivalPipeline(BaseDatasetPipeline):
    dataset_id = "upcoming_arrivals"
    required_fields = (
        "district",
        "arrival_date",
        "missionaries_count",
    )
    allow_empty = True
    unique_fields = ("district", "arrival_date")

    def _load(self) -> Iterable[Dict[str, Any]]:
        return self.repository.fetch_upcoming_arrivals(self.branch_id, self.params)

    def _transform(self, rows: Iterable[Dict[str, Any]]) -> Iterable[UpcomingArrival]:
        for row in rows:
            yield UpcomingArrival(**row)

    def _validate(self, rows: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        validated = list(super()._validate(rows))
        for index, row in enumerate(validated):
            count = row.get("missionaries_count")
            if count is not None and count < 0:
                raise DatasetValidationError(
                    f"Conteo negativo de misioneros en registro {index}",
                    error_code="invalid_missionaries_count",
                )
            if count is not None and count > 200:
                raise DatasetValidationError(
                    f"Conteo de misioneros fuera de rango en registro {index}",
                    error_code="invalid_missionaries_count",
                )
        return validated


class UpcomingBirthdayPipeline(BaseDatasetPipeline):
    dataset_id = "upcoming_birthdays"
    required_fields = (
        "missionary_name",
        "birthday",
    )
    allow_empty = True
    unique_fields = ("missionary_id", "missionary_name", "birthday")

    def _load(self) -> Iterable[Dict[str, Any]]:
        return self.repository.fetch_upcoming_birthdays(self.branch_id, self.params)

    def _transform(self, rows: Iterable[Dict[str, Any]]) -> Iterable[UpcomingBirthday]:
        for row in rows:
            yield UpcomingBirthday(**row)


PIPELINES: Dict[str, Type[BaseDatasetPipeline]] = {
    BranchSummaryPipeline.dataset_id: BranchSummaryPipeline,
    DistrictKPIPipeline.dataset_id: DistrictKPIPipeline,
    UpcomingArrivalPipeline.dataset_id: UpcomingArrivalPipeline,
    UpcomingBirthdayPipeline.dataset_id: UpcomingBirthdayPipeline,
}


class ReportPreparationService:
    """Fachada para preparar datasets reciclables por múltiples canales."""

    def __init__(
        self,
        *,
        default_branch_id: Optional[int] = None,
        cache_strategy: Optional[CacheStrategy] = None,
        repository: Optional[ReportDataRepository] = None,
    ) -> None:
        self._settings = get_settings()
        self._allowed_branches = set(self._settings.ramas_autorizadas)
        self.default_branch_id = default_branch_id or self._settings.rama_actual
        self._cache: CacheStrategy = cache_strategy or create_cache_strategy(self._settings)
        self._ttl_seconds = max(self._settings.report_cache_ttl_minutes, 0) * 60
        self._cache_enabled = self._ttl_seconds > 0
        self._repository: ReportDataRepository = repository or SQLAlchemyReportDataRepository(self._settings)

    def prepare_branch_summary(self, *, branch_id: Optional[int] = None, **params: Any) -> ReportDatasetResult:
        return self._run_pipeline(BranchSummaryPipeline, branch_id, params)

    def prepare_district_kpis(self, *, branch_id: Optional[int] = None, **params: Any) -> ReportDatasetResult:
        return self._run_pipeline(DistrictKPIPipeline, branch_id, params)

    def prepare_upcoming_arrivals(self, *, branch_id: Optional[int] = None, **params: Any) -> ReportDatasetResult:
        return self._run_pipeline(UpcomingArrivalPipeline, branch_id, params)

    def prepare_upcoming_birthdays(self, *, branch_id: Optional[int] = None, **params: Any) -> ReportDatasetResult:
        return self._run_pipeline(UpcomingBirthdayPipeline, branch_id, params)

    def _run_pipeline(
        self,
        pipeline_cls: Type[BaseDatasetPipeline],
        branch_id: Optional[int],
        params: Dict[str, Any],
    ) -> ReportDatasetResult:
        request_message_id = uuid4().hex
        resolved_branch = self._resolve_branch(branch_id, pipeline_cls.dataset_id, request_message_id)
        pipeline = pipeline_cls(repository=self._repository, branch_id=resolved_branch, params=params)
        cache_key = self._build_cache_key(pipeline.dataset_id, resolved_branch, params)
        cached = self._cache.get(cache_key) if self._cache_enabled else None
        if cached:
            metadata = ReportDatasetMetadata(**cached["metadata"])  # type: ignore[arg-type]
            if self._is_cache_stale(metadata):
                logger.warning(
                    "pipeline_cache_stale",
                    etapa="fase_5_preparacion",
                    dataset_id=pipeline.dataset_id,
                    branch_id=resolved_branch,
                    cache_key=cache_key,
                    cache_hit=False,
                    error_code="stale_cache",
                    cache_metrics=self._cache.get_metrics(),
                    message_id=metadata.message_id,
                    request_message_id=request_message_id,
                )
                self._cache.invalidate(cache_key)
            else:
                metadata.cache_hit = True
                result = ReportDatasetResult(metadata=metadata, data=cached["data"])
                cache_metrics = self._cache.get_metrics()
                logger.info(
                    "pipeline_cache_hit",
                    etapa="fase_5_preparacion",
                    dataset_id=pipeline.dataset_id,
                    branch_id=resolved_branch,
                    cache_key=cache_key,
                    cache_hit=True,
                    records_processed=metadata.record_count,
                    duration_ms=metadata.duration_ms,
                    cache_metrics=cache_metrics,
                    message_id=metadata.message_id,
                )
                return result

        logger.info(
            "pipeline_cache_miss",
            etapa="fase_5_preparacion",
            dataset_id=pipeline.dataset_id,
            branch_id=resolved_branch,
            params=params,
            cache_key=cache_key,
            cache_hit=False,
            message_id=request_message_id,
        )
        try:
            result = pipeline.prepare()
        except ReportDataRepositoryError as exc:
            logger.error(
                "pipeline_repository_error",
                etapa="fase_5_preparacion",
                dataset_id=pipeline.dataset_id,
                branch_id=resolved_branch,
                error=str(exc),
                cache_metrics=self._cache.get_metrics(),
                message_id=request_message_id,
            )
            raise ReportPreparationError(str(exc)) from exc
        except DatasetValidationError as exc:
            logger.error(
                "pipeline_validation_error",
                etapa="fase_5_preparacion",
                dataset_id=pipeline.dataset_id,
                branch_id=resolved_branch,
                error_code=exc.error_code,
                error=str(exc),
                cache_metrics=self._cache.get_metrics(),
                message_id=request_message_id,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "pipeline_error",
                etapa="fase_5_preparacion",
                dataset_id=pipeline.dataset_id,
                branch_id=resolved_branch,
                error=str(exc),
                cache_metrics=self._cache.get_metrics(),
                message_id=request_message_id,
            )
            raise ReportPreparationError(str(exc)) from exc

        result.metadata.message_id = request_message_id
        logger.info(
            "pipeline_completed",
            etapa="fase_5_preparacion",
            dataset_id=pipeline.dataset_id,
            branch_id=resolved_branch,
            record_count=result.metadata.record_count,
            duration_ms=result.metadata.duration_ms,
            cache_hit=False,
            cache_key=cache_key,
            cache_metrics=self._cache.get_metrics(),
            message_id=request_message_id,
        )
        if self._cache_enabled:
            self._cache.set(
                cache_key,
                {
                    "metadata": result.metadata.model_dump(mode="json"),
                    "data": result.data,
                },
                ttl_seconds=self._ttl_seconds,
            )
        return result

    def _build_cache_key(self, dataset_id: str, branch_id: Optional[int], params: Dict[str, Any]) -> str:
        branch_part = branch_id if branch_id is not None else "global"
        sorted_params = "|".join(f"{k}={params[k]}" for k in sorted(params))
        return f"report:{dataset_id}:branch:{branch_part}:{sorted_params}"

    def _resolve_branch(
        self,
        explicit_branch_id: Optional[int],
        dataset_id: str,
        message_id: str,
    ) -> Optional[int]:
        resolved = explicit_branch_id if explicit_branch_id is not None else self.default_branch_id
        if self._allowed_branches:
            if resolved is None or resolved not in self._allowed_branches:
                logger.error(
                    "pipeline_invalid_branch",
                    etapa="fase_5_preparacion",
                    dataset_id=dataset_id,
                    branch_id=resolved,
                    error_code="invalid_branch",
                    cache_metrics=self._cache.get_metrics(),
                    message_id=message_id,
                )
                raise DatasetValidationError(
                    f"La rama especificada '{resolved}' no está autorizada para el dataset {dataset_id}",
                    error_code="invalid_branch",
                )
        return resolved

    def _is_cache_stale(self, metadata: ReportDatasetMetadata) -> bool:
        if not self._cache_enabled:
            return True
        age = datetime.utcnow() - metadata.generated_at
        return age.total_seconds() > self._ttl_seconds

    def invalidate(self, dataset_id: Optional[str] = None, branch_id: Optional[int] = None) -> None:
        """Invalidar caché de datasets específicos."""

        if dataset_id is None and branch_id is None:
            prefix = "report:"
        else:
            branch_part = branch_id if branch_id is not None else ""
            dataset_part = dataset_id if dataset_id is not None else ""
            prefix = f"report:{dataset_part}:branch:{branch_part}"
        self._cache.invalidate_prefix(prefix)


__all__ = [
    "ReportPreparationService",
    "ReportPreparationError",
    "DatasetValidationError",
    "BaseDatasetPipeline",
    "BranchSummaryPipeline",
    "DistrictKPIPipeline",
    "UpcomingArrivalPipeline",
    "UpcomingBirthdayPipeline",
    "PIPELINES",
]
