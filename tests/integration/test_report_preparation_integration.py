"""Pruebas de integración para pipelines de Fase 5 usando SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import os
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

if "PYTHONPATH" not in os.environ:
    os.environ["PYTHONPATH"] = str(SRC_DIR)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.services.cache_strategies import InMemoryCacheStrategy
from app.services.report_data_repository import ReportDataRepository
from app.services.report_preparation_service import ReportPreparationService


class SQLAlchemyStubRepository(ReportDataRepository):
    """Repositorio que consulta tablas SQLite con SQLAlchemy."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, future=True)

    @contextmanager
    def _session(self) -> Iterable[Session]:
        with self._session_factory() as session:
            yield session

    def fetch_branch_summary(self, branch_id: Optional[int], params: Dict[str, object]) -> Iterable[Dict[str, object]]:
        query = text(
            """
            SELECT
                Rama AS branch_id,
                Distrito AS district,
                Primera_Generacion AS first_generation_date,
                Primera_CCM_llegada AS first_ccm_arrival,
                Ultima_CCM_salida AS last_ccm_departure,
                Total_Misioneros AS total_missionaries
            FROM vwFechasCCMPorDistrito
            WHERE (:branch_id IS NULL OR Rama = :branch_id)
            ORDER BY district
            """
        )
        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id}).mappings().all()
        return [dict(row) for row in rows]

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
        kpis: List[Dict[str, Any]] = []
        for row in rows:
            metrics = {
                "total_missionaries": row["total_missionaries"] or 0,
                "en_ccm": row["ccm_count"] or 0,
                "virtuales": row["virtual_count"] or 0,
                "futuros": row["future_count"] or 0,
                "tres_semanas": row["three_week_count"] or 0,
            }
            for metric, value in metrics.items():
                kpis.append(
                    {
                        "branch_id": row["branch_id"],
                        "district": row["district"],
                        "metric": metric,
                        "value": float(value),
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
              AND DATE(CCM_llegada) BETWEEN DATE('now') AND DATE('now', :interval)
            GROUP BY Distrito, RDistrito, Rama, DATE(CCM_llegada), DATE(CCM_salida)
            ORDER BY arrival_date ASC
            """
        )
        interval = f"+{days_ahead} day"
        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id, "interval": interval}).mappings().all()
        return [dict(row) for row in rows]

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
              AND DATE(Fecha_Cumpleanos) BETWEEN DATE('now') AND DATE('now', :interval)
            ORDER BY birthday ASC
            """
        )
        interval = f"+{days_ahead} day"
        with self._session() as session:
            rows = session.execute(query, {"branch_id": branch_id, "interval": interval}).mappings().all()
        return [dict(row) for row in rows]


@pytest.fixture(scope="module")
def sqlite_engine(tmp_path_factory: pytest.TempPathFactory) -> Engine:
    """Prepara una base SQLite temporal con datos de prueba."""

    db_path = tmp_path_factory.mktemp("report_integration") / "report.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    today = date.today()
    arrival_next_week = today + timedelta(days=7)
    departure_in_six_weeks = today + timedelta(days=42)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE vwFechasCCMPorDistrito (
                    Rama INTEGER,
                    Distrito TEXT,
                    Primera_Generacion TEXT,
                    Primera_CCM_llegada TEXT,
                    Ultima_CCM_salida TEXT,
                    Total_Misioneros INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO vwFechasCCMPorDistrito
                (Rama, Distrito, Primera_Generacion, Primera_CCM_llegada, Ultima_CCM_salida, Total_Misioneros)
                VALUES
                (14, 'Distrito Centro', '2022-01-01', '2024-09-10', '2024-12-01', 18),
                (14, 'Distrito Norte', '2023-03-15', '2024-08-05', '2024-11-20', 12)
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE vwMisioneros (
                    Rama INTEGER,
                    Distrito TEXT,
                    RDistrito TEXT,
                    Status TEXT,
                    tres_semanas INTEGER,
                    CCM_llegada TEXT,
                    CCM_salida TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO vwMisioneros
                (Rama, Distrito, RDistrito, Status, tres_semanas, CCM_llegada, CCM_salida)
                VALUES
                (14, 'Distrito Centro', 'RC-1', 'CCM', 0, :arrival_next_week, :departure_six_weeks),
                (14, 'Distrito Centro', 'RC-1', 'Virtual', 1, :arrival_next_week, :departure_six_weeks),
                (14, 'Distrito Norte', 'RN-1', 'Futuro', 0, :arrival_next_week, :departure_six_weeks)
                """
            ),
            {
                "arrival_next_week": arrival_next_week.isoformat(),
                "departure_six_weeks": departure_in_six_weeks.isoformat(),
            },
        )

        conn.execute(
            text(
                """
                CREATE TABLE vwCumpleanosProximos (
                    ID INTEGER,
                    Rama INTEGER,
                    Distrito TEXT,
                    Tratamiento TEXT,
                    Nombre_del_misionero TEXT,
                    Fecha_Cumpleanos TEXT,
                    Nueva_Edad INTEGER,
                    Status TEXT,
                    Correo_Misional TEXT,
                    Correo_Personal TEXT,
                    tres_semanas INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO vwCumpleanosProximos
                (ID, Rama, Distrito, Tratamiento, Nombre_del_misionero, Fecha_Cumpleanos, Nueva_Edad, Status, Correo_Misional, Correo_Personal, tres_semanas)
                VALUES
                (1, 14, 'Distrito Centro', 'Élder', 'Élder Pérez', DATE('now', '+10 day'), 20, 'CCM', 'elder.perez@ccm.org', 'perez@example.org', 0)
                """
            )
        )

    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def integration_service(sqlite_engine: Engine) -> ReportPreparationService:
    """Instancia la fachada con el repositorio SQLAlchemy stub."""

    repository = SQLAlchemyStubRepository(sqlite_engine)
    cache = InMemoryCacheStrategy()
    return ReportPreparationService(default_branch_id=14, repository=repository, cache_strategy=cache)


def test_integration_branch_summary_pipeline(integration_service: ReportPreparationService):
    """✅ Requisito `docs/plan_fase5.md`: Branch Summary con datos reales por rama."""

    result = integration_service.prepare_branch_summary()
    assert result.metadata.record_count == 2
    districts = {row["district"] for row in result.data}
    assert districts == {"Distrito Centro", "Distrito Norte"}


def test_integration_district_kpis_pipeline(integration_service: ReportPreparationService):
    """✅ Calcula KPIs a partir de tablas SQLite simulando vistas MySQL."""

    result = integration_service.prepare_district_kpis()
    metrics = {(row["district"], row["metric"]): row["value"] for row in result.data}
    assert metrics[("Distrito Centro", "total_missionaries")] == 2.0
    assert metrics[("Distrito Centro", "en_ccm")] == 1.0
    assert metrics[("Distrito Centro", "virtuales")] == 1.0


def test_integration_upcoming_arrivals_pipeline(integration_service: ReportPreparationService):
    """✅ Verifica integración de llegadas próximas con `days_ahead` personalizado."""

    result = integration_service.prepare_upcoming_arrivals(days_ahead=30)
    assert result.metadata.record_count == 2
    counts = [row["missionaries_count"] for row in result.data]
    assert counts == [2, 1]


def test_integration_upcoming_birthdays_pipeline(integration_service: ReportPreparationService):
    """✅ Comprueba que el pipeline de cumpleaños lee información desde SQLAlchemy."""

    result = integration_service.prepare_upcoming_birthdays(days_ahead=30)
    assert result.metadata.record_count == 1
    assert result.data[0]["missionary_name"] == "Élder Pérez"
