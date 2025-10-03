"""Pruebas del parser de tablas HTML de correos del CCM.

Cada caso documenta la heurística añadida para identificar tablas válidas
(issue: validación de estructura en email_service).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from app.services.email_html_parser import extract_primary_table
from app.services.validators import validate_table_structure
from app.config import Settings


@pytest.fixture(scope="module")
def sample_settings() -> Settings:
    """Crea configuración mínima para validar columnas requeridas en pruebas."""
    return Settings(gmail_user="tests@example.com")


def test_extract_primary_table_real_email_selects_ccm_table(sample_settings: Settings):
    """Valida la heurística con el correo real (req: issue parser HTML en fase 4)."""
    html = (PROJECT_ROOT / "originalBody.html").read_text(encoding="utf-8")

    parsed_table, errors = extract_primary_table(html)

    assert not errors, f"Se esperaban 0 errores, se obtuvieron: {errors}"
    assert parsed_table is not None, "El parser debe encontrar una tabla válida"

    headers_normalized = {header.strip().lower() for header in parsed_table["headers"]}
    assert {"distrito", "zona"}.issubset(headers_normalized)

    validation_errors = validate_table_structure(
        parsed_table,
        sample_settings.email_table_required_columns,
    )
    assert not validation_errors, f"La validación no debe reportar errores: {validation_errors}"


def test_extract_primary_table_without_tables_returns_error():
    """Confirma que se devuelve error claro cuando el HTML no contiene tablas."""
    parsed_table, errors = extract_primary_table("<html><body><p>Hola</p></body></html>")

    assert parsed_table is None
    assert "table_missing" in errors


def test_extract_primary_table_prefers_table_with_expected_headers():
    """Garantiza que la heurística prefiera tablas con columnas esperadas."""
    html = """
    <html>
      <body>
        <table>
          <tr><th>Foo</th><th>Bar</th></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>
        <table>
          <tr><th>Distrito</th><th>Zona</th><th>Total</th></tr>
          <tr><td>A</td><td>10</td><td>15</td></tr>
        </table>
      </body>
    </html>
    """

    parsed_table, errors = extract_primary_table(html)

    assert parsed_table is not None
    assert "Distrito" in parsed_table["headers"], "Debe elegir la tabla con encabezados esperados"
    assert "Zona" in parsed_table["headers"]
    assert not errors, f"No se esperaban errores: {errors}"
