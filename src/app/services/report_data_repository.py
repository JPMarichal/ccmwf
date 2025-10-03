"""Repositorio de datos para la preparación de reportes (Fase 5)."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from abc import ABC, abstractmethod

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


class ReportDataRepositoryError(Exception):
    """Errores relacionados con la obtención de datos para reportes."""


class ReportDataRepository(ABC):
    """Contrato para repositorios que suministran datasets de reportes."""

    @abstractmethod
    def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_district_kpis(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_upcoming_arrivals(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_upcoming_birthdays(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise NotImplementedError


class SQLAlchemyReportDataRepository(ReportDataRepository):
    """Implementación base usando SQLAlchemy (consultas a definir en issues siguientes)."""

    def __init__(self, settings: Settings) -> None:
        if not settings.database_url:
            raise ReportDataRepositoryError("DATABASE_URL no configurada en .env para Fase 5")
        self._engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)
        self._session_factory = sessionmaker(bind=self._engine)

    def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise ReportDataRepositoryError("Consulta branch_summary no implementada. Ver issue #16")

    def fetch_district_kpis(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise ReportDataRepositoryError("Consulta district_kpi no implementada. Ver issue #16")

    def fetch_upcoming_arrivals(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise ReportDataRepositoryError("Consulta upcoming_arrivals no implementada. Ver issue #16")

    def fetch_upcoming_birthdays(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        raise ReportDataRepositoryError("Consulta upcoming_birthdays no implementada. Ver issue #16")

    def _session(self) -> Session:
        return self._session_factory()
