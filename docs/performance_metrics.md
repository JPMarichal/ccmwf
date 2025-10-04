# Métricas de Performance

Registro de mediciones observadas durante las fases actuales del proyecto. Todas las mediciones se ejecutan en el entorno local (`Python 3.13.5`, Windows) utilizando la virtualenv del repositorio.

## Fase 1 – Recepción
- **Cobertura post pruebas**: `85%` (`pytest src/tests/test_gmail_oauth_service.py src/tests/test_email_service.py src/tests/test_drive_service.py --cov=src --cov-report=term`).
- **Observación de startup**: `EmailService.test_connection()` concluye en <1s en entorno local (sin errores de IMAP/OAuth). Se mantiene monitoreo a medida que se disponga de cuentas productivas.

## Fase 2 – Procesamiento inicial
- **Parser HTML + extracción de fecha**: `68.57 ms` promedio (20 iteraciones) ejecutando `tmp_phase2_metrics.py` con la muestra `originalBody.html`.
- **Cobertura módulos de parsing/validación**: `>=94%` (`email_html_parser.py`, `email_content_utils.py`, `validators.py`) según último reporte de cobertura (`pytest ... --cov=src`).
- **Logging estructurado**: se registran `table_errors`, `validation_errors` y `extra_texts` en cada resultado; tiempos de parsing disponibles para instrumentación futura (pendiente de habilitar en logs de producción).

## Fase 5 – Preparación de reportes
- **Tiempo de preparación (pytest unitario)**: `5.93 s` al ejecutar `pytest tests/test_report_preparation_service.py` con `PYTHONPATH` apuntando a `src/` y caché in-memory (`CACHE_PROVIDER=memory`).
- **Tiempo de integración (SQLite stub)**: `1.58 s` al ejecutar `pytest tests/integration/test_report_preparation_integration.py` bajo el mismo entorno.
- **Validación de caché**: Métricas (`hits`, `misses`, `writes`, `invalidations`) consultadas vía `ReportPreparationService._cache.get_metrics()` después de pruebas unitarias (resultado esperado tras dos consultas consecutivas: `{'hits': 1, 'misses': 1, 'writes': 1, 'invalidations': 0}`).
- **Procedimiento de medición**:
  1. Activar virtualenv: `. .\.venv\Scripts\Activate.ps1`.
  2. Exportar `PYTHONPATH="d:/myapps/ccmwf/src"`.
  3. Ejecutar pruebas listadas y registrar duración reportada por pytest.
  4. Para Redis, repetir con `CACHE_PROVIDER=redis` y documentar latencias comparativas.

> Última actualización: 2025-10-04.
