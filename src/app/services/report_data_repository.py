"""Repositorio de datos para la preparación de reportes (Fase 5)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Dict, Iterable, List, Optional

from abc import ABC, abstractmethod

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
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
    """Repositorio basado en SQLAlchemy con consultas a vistas especializadas."""

    def __init__(self, settings: Settings) -> None:
        if not settings.database_url:
            raise ReportDataRepositoryError("DATABASE_URL no configurada en .env para Fase 5")
        self._engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)
        self._session_factory = sessionmaker(bind=self._engine)

    @contextmanager
    def _session(self) -> Iterable[Session]:
        session = self._session_factory()
        try:
            yield session
        except SQLAlchemyError as exc:  # noqa: BLE001
            session.rollback()
            raise ReportDataRepositoryError(str(exc)) from exc
        finally:
            session.close()

    def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        query = text(
            """
            SELECT
                Rama AS branch_id,
                Distrito AS district,
                CAST(Primera_Generacion AS DATE) AS first_generation_date,
                CAST(Primera_CCM_llegada AS DATE) AS first_ccm_arrival,
                CAST(Ultima_CCM_salida AS DATE) AS last_ccm_departure,
                Total_Misioneros AS total_missionaries
            FROM vwFechasCCMPorDistrito
            WHERE (:branch_id IS NULL OR Rama = :branch_id)
            ORDER BY district
            """
        )

        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id}).mappings().all()

        summaries: List[Dict[str, object]] = []

        for row in rows:
            summaries.append(
                {
                    "branch_id": row.get("branch_id"),
                    "district": row.get("district"),
                    "first_generation_date": row.get("first_generation_date"),
                    "first_ccm_arrival": row.get("first_ccm_arrival"),
                    "last_ccm_departure": row.get("last_ccm_departure"),
                    "total_missionaries": row.get("total_missionaries", 0),
                    "total_companionships": None,
                    "elders_count": None,
                    "sisters_count": None,
                }
            )

        return summaries

    def fetch_district_kpis(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        query = text(
            """
            SELECT
                Rama AS branch_id,
                Distrito AS district,
                COUNT(*) AS total_missionaries,
                SUM(CASE WHEN Status = 'CCM' THEN 1 ELSE 0 END) AS ccm_count,
                SUM(CASE WHEN Status = 'Virtual' THEN 1 ELSE 0 END) AS virtual_count,
                SUM(CASE WHEN Status = 'Futuro' THEN 1 ELSE 0 END) AS future_count,
                SUM(CASE WHEN tres_semanas = 1 THEN 1 ELSE 0 END) AS three_week_count
            FROM vwMisioneros
            WHERE (:branch_id IS NULL OR Rama = :branch_id)
            GROUP BY Rama, Distrito
            ORDER BY district
            """
        )

        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id}).mappings().all()

        today = date.today()
        kpis: List[Dict[str, object]] = []

        for row in rows:
            metrics = {
                "total_missionaries": row.get("total_missionaries", 0),
                "en_ccm": row.get("ccm_count", 0),
                "virtuales": row.get("virtual_count", 0),
                "futuros": row.get("future_count", 0),
                "tres_semanas": row.get("three_week_count", 0),
            }

            for metric, value in metrics.items():
                kpis.append(
                    {
                        "branch_id": row.get("branch_id"),
                        "district": row.get("district"),
                        "metric": metric,
                        "value": float(value or 0),
                        "unit": "misioneros",
                        "generated_for_week": today,
                        "extra": {},
                    }
                )

        return kpis

    def fetch_upcoming_arrivals(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        days_ahead = int(params.get("days_ahead", 60) or 60)

        query = text(
            """
            SELECT
                Distrito AS district,
                RDistrito AS rdistrict,
                Rama AS branch_id,
                DATE(CCM_llegada) AS arrival_date,
                DATE(CCM_salida) AS departure_date,
                COUNT(*) AS missionaries_count,
                CASE WHEN MAX(tres_semanas) = 1 THEN 3 ELSE 6 END AS duration_weeks
            FROM vwMisioneros
            WHERE (:branch_id IS NULL OR Rama = :branch_id)
              AND CCM_llegada IS NOT NULL
              AND DATE(CCM_llegada) BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL :days_ahead DAY)
            GROUP BY Distrito, RDistrito, Rama, DATE(CCM_llegada), DATE(CCM_salida)
            ORDER BY arrival_date ASC, district ASC
            """
        )

        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id, "days_ahead": days_ahead}).mappings().all()

        arrivals: List[Dict[str, object]] = []
        for row in rows:
            arrivals.append(
                {
                    "district": row.get("district"),
                    "rdistrict": row.get("rdistrict"),
                    "branch_id": row.get("branch_id"),
                    "arrival_date": row.get("arrival_date"),
                    "departure_date": row.get("departure_date"),
                    "missionaries_count": row.get("missionaries_count", 0),
                    "duration_weeks": row.get("duration_weeks"),
                    "status": None,
                }
            )

        return arrivals

    def fetch_upcoming_birthdays(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        days_ahead = int(params.get("days_ahead", 90) or 90)

        query = text(
            """
            SELECT
                ID AS missionary_id,
                Rama AS branch_id,
                Distrito AS district,
                Tratamiento AS treatment,
                Nombre_del_misionero AS missionary_name,
                DATE(Fecha_Cumpleanos) AS birthday,
                Nueva_Edad AS age_turning,
                Status AS status,
                Correo_Misional AS email_missionary,
                Correo_Personal AS email_personal,
                tres_semanas AS three_weeks_program
            FROM vwCumpleanosProximos
            WHERE (:branch_id IS NULL OR Rama = :branch_id)
              AND DATE(Fecha_Cumpleanos) BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL :days_ahead DAY)
            ORDER BY birthday ASC, missionary_name ASC
            """
        )

        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id, "days_ahead": days_ahead}).mappings().all()

        birthdays: List[Dict[str, object]] = []
        for row in rows:
            three_weeks_value = row.get("three_weeks_program")
            birthdays.append(
                {
                    "missionary_id": row.get("missionary_id"),
                    "branch_id": row.get("branch_id"),
                    "district": row.get("district"),
                    "treatment": row.get("treatment"),
                    "missionary_name": row.get("missionary_name"),
                    "birthday": row.get("birthday"),
                    "age_turning": row.get("age_turning"),
                    "status": row.get("status"),
                    "email_missionary": row.get("email_missionary"),
                    "email_personal": row.get("email_personal"),
                    "three_weeks_program": bool(three_weeks_value) if three_weeks_value is not None else None,
                }
            )

        return birthdays
