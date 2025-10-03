"""Pruebas para `DatabaseSyncService` y utilidades asociadas (Fase 4)."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import sys
from importlib import metadata

import pytest
import structlog


try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - dependiente del entorno
    pytest.skip(
        "Pandas no está disponible en el entorno de pruebas (requisito para fase 4)",
        allow_module_level=True,
    )


_MIN_SQLALCHEMY_VERSION = (2, 0, 40)


def _version_tuple(raw_version: str) -> tuple[int, ...]:
    """Convierte `raw_version` en tupla entera tolerante a sufijos (compatibilidad Py3.13)."""

    chunks: list[int] = []
    for piece in raw_version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            break
        chunks.append(int(digits))
    return tuple(chunks)


try:
    sqlalchemy_version = metadata.version("sqlalchemy")
except metadata.PackageNotFoundError:  # pragma: no cover - dependerá del entorno de ejecución
    pytest.skip(
        "SQLAlchemy no está instalado en el entorno de pruebas",
        allow_module_level=True,
    )
else:
    if sys.version_info >= (3, 13) and _version_tuple(sqlalchemy_version) < _MIN_SQLALCHEMY_VERSION:
        pytest.skip(
            "SQLAlchemy < 2.0.40 presenta incompatibilidades con Python 3.13 (issue upstream)",
            allow_module_level=True,
        )


try:
    import sqlalchemy
except AssertionError as exc:  # pragma: no cover - depende de versión instalada
    pytest.skip(
        "SQLAlchemy no es compatible con Python 3.13 en la versión instalada (AssertionError al importar)",
        allow_module_level=True,
    )


from sqlalchemy import create_engine

from app.config import Settings
from app.services.database_sync_service import (
    DatabaseSyncService,
    DatabaseSyncStateRepository,
    MissionaryRecord,
    ccm_generaciones_table,
)


@pytest.fixture
def base_settings(tmp_path):
    """Config básica para instanciar servicios en pruebas (validación requisito F4)."""

    return Settings(
        gmail_user="user@test.com",
        gmail_app_password="pass",
        processed_label="processed",
        google_drive_attachments_folder_id="root-folder",
        db_host="localhost",
        db_port=3306,
        db_user="tester",
        db_password="secret",
        db_name="ccm",
    )


def test_missionary_record_from_row_maps_and_normalizes_fields(base_settings):
    """Valida que `MissionaryRecord.from_row` normalice datos conforme al inventario (Tabla 1)."""

    row_values = {
        0: "101",
        1: "14A",
        2: "Tres Semanas",
        3: "14",
        4: "Distrito Norte",
        5: "mexico",
        6: "7",
        7: "3",
        8: "Juan Pérez",
        9: "Carlos",
        10: "México Norte",
        11: "Zapotlán",
        12: "Edificio 3",
        13: "foto.jpg",
        14: "2025-01-10",
        15: "2025-02-21",
        16: "2025-01-03",
        17: "Sin observaciones",
        18: "verdadero",
        19: "2000-05-01",
        20: "1",
        21: "0",
        22: "F12345",
        23: "FM15",
        24: "si",
        25: "Casillero 8",
        26: "Vuelo 2",
        27: "Lunes",
        28: "true",
        29: "false",
        30: "true",
        31: "correo@misional.org",
        32: "personal@example.com",
        33: "3/7/2025",
    }
    row = [row_values.get(i) for i in range(34)]

    record = MissionaryRecord.from_row(
        row,
        logger=structlog.get_logger(),
        excel_file_id="file123",
        row_index=2,
    )

    assert record is not None
    assert record.id == 101
    assert record.pais == "Mexico"
    assert record.investido is True
    assert record.fecha_presencial == "2025-07-03"
    assert record.correo_misional == "correo@misional.org"


@pytest.fixture
def sqlite_engine():
    """Crea un engine SQLite en memoria para validar inserciones (requisito Bulk Insert)."""

    engine = create_engine("sqlite:///:memory:")
    ccm_generaciones_table.metadata.create_all(engine)
    return engine


def test_persist_records_inserts_new_and_skips_existing(sqlite_engine, base_settings):
    """Verifica inserciones en lote y detección de duplicados (Tabla 1 → `ccm_generaciones`)."""

    drive_mock = MagicMock()
    service = DatabaseSyncService(
        base_settings,
        drive_mock,
        engine=sqlite_engine,
        state_repository=DatabaseSyncStateRepository(Path("ignored.json")),
    )

    records = [
        MissionaryRecord(
            id=1,
            nombre_misionero="Test Uno",
        ),
        MissionaryRecord(
            id=2,
            nombre_misionero="Test Dos",
        ),
    ]

    inserted, skipped = service._persist_records(records)
    assert inserted == 2
    assert skipped == 0

    inserted_again, skipped_again = service._persist_records(records)
    assert inserted_again == 0
    assert skipped_again == 2


def test_sync_generation_processes_drive_files(monkeypatch, tmp_path, sqlite_engine, base_settings):
    """Comprueba flujo completo: listado Drive → descarga → inserción y limpieza de estado."""

    drive_mock = MagicMock()
    drive_mock.list_folder_files.return_value = [
        {"id": "file-001", "name": "generacion.xlsx"}
    ]
    drive_mock.download_file.return_value = b"ignored"

    state_repo = DatabaseSyncStateRepository(tmp_path / "state.json")
    service = DatabaseSyncService(
        base_settings,
        drive_mock,
        engine=sqlite_engine,
        state_repository=state_repo,
    )

    sample_records = [
        MissionaryRecord(id=10, nombre_misionero="Sample"),
        MissionaryRecord(id=11, nombre_misionero="Sample 2"),
    ]

    def fake_parse(self, excel_bytes: bytes, excel_file_id: str):
        return sample_records, []

    monkeypatch.setattr(DatabaseSyncService, "_parse_excel_rows", fake_parse)

    report = service.sync_generation("20251001", "folder-14A")

    assert report.inserted_count == 2
    assert report.skipped_count == 0
    assert report.continuation_token is None
    assert drive_mock.list_folder_files.called
    assert drive_mock.download_file.called
    assert state_repo.load("folder-14A").last_processed_file_id is None
