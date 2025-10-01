# Métricas de Performance

Registro de mediciones observadas durante las fases actuales del proyecto. Todas las mediciones se ejecutan en el entorno local (`Python 3.13.5`, Windows) utilizando la virtualenv del repositorio.

## Fase 1 – Recepción
- **Cobertura post pruebas**: `85%` (`pytest src/tests/test_gmail_oauth_service.py src/tests/test_email_service.py src/tests/test_drive_service.py --cov=src --cov-report=term`).
- **Observación de startup**: `EmailService.test_connection()` concluye en <1s en entorno local (sin errores de IMAP/OAuth). Se mantiene monitoreo a medida que se disponga de cuentas productivas.

## Fase 2 – Procesamiento inicial
- **Parser HTML + extracción de fecha**: `68.57 ms` promedio (20 iteraciones) ejecutando `tmp_phase2_metrics.py` con la muestra `originalBody.html`.
- **Cobertura módulos de parsing/validación**: `>=94%` (`email_html_parser.py`, `email_content_utils.py`, `validators.py`) según último reporte de cobertura (`pytest ... --cov=src`).
- **Logging estructurado**: se registran `table_errors`, `validation_errors` y `extra_texts` en cada resultado; tiempos de parsing disponibles para instrumentación futura (pendiente de habilitar en logs de producción).

> Última actualización: 2025-10-01.
