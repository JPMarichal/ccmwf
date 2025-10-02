# Guía de Logging - Aplicación CCM

## Objetivo
Documentar las pautas generales de logging para todos los servicios de la aplicación CCM, garantizando trazabilidad, seguridad y mantenimiento conforme a los lineamientos definidos en `logging-rules.md` y los planes por fase (`docs/plan*.md`).

## Principios fundamentales
- **Responsabilidad única**
  Cada archivo de log corresponde a un servicio o componente (p.ej. `email_service`, `database_sync`, `report_service`). Evita mezclar eventos heterogéneos.
- **Formato estructurado**
  Usa JSON plano en español con claves claras y consistentes. Campos estándar mínimos:
  - `timestamp_utc`
  - `nivel`
  - `message_id`
  - `etapa` o subproceso
  - Identificadores relevantes (`drive_folder_id`, `excel_file_id`, `request_id`, etc.)
  - Métricas (`records_processed`, `records_skipped`, `duration_ms`, etc.)
- **Integración con `.env`**
  Las configuraciones sensibles provienen de `.env` (ver `docs/environment_variables.md`). Nunca registrar credenciales ni valores sensibles.

## Niveles de severidad
- `DEBUG`: Diagnóstico detallado (parsing, normalizaciones). Activar solo durante soporte puntual.
- `INFO`: Hitos normales, métricas agregadas, confirmaciones de procesos.
- `WARNING`: Situaciones recuperables (reintentos, datos omitidos, encabezados inesperados tolerados).
- `ERROR`: Fallos que interrumpen la unidad de trabajo actual (rollback, descargas fallidas tras reintentos).
- `CRITICAL`: Interrupciones globales que requieren intervención manual inmediata.

## Cuándo registrar
- Inicio y fin de procesos clave descritos en `docs/workflow.md`.
- Validaciones de estructura o datos (tabla HTML, encabezados XLSX, duplicados en MySQL).
- Interacciones con servicios externos (Gmail, Google Drive, MySQL, Telegram, SMTP) incluyendo métricas de duración.
- Reintentos con backoff (causa y próximo intento).
- Excepciones, códigos de error (`db_connection_failed`, `drive_listing_failed`, etc.) y decisiones tomadas (reintentar, abortar).

## Contenido mínimo por fase
- **Fases 1-2**: `message_id`, `attachments_count`, `validation_errors`, `parsed_table_status`.
- **Fase 3**: `drive_folder_id`, `file_original_name`, `file_new_name`, `upload_status`.
- **Fase 4**: `excel_file_id`, `batch_size`, `records_processed`, `records_skipped`, `table_errors`, `duration_ms`, tokens de reanudación.
- **Fases 5-8**: Destinatarios, URLs generadas (`sheet_url`, `telegram_chat_id`), métricas de notificaciones y estados (`success`, `partial`, `failed`).

## Retención y rotación
- Implementar rotación diaria o por tamaño máximo 10 MB.
- Retener logs 30 días en almacenamiento activo; después, purgar o archivar comprimidos según políticas.
- Revisar el volumen semanalmente para prevenir crecimiento descontrolado (ver `docs/performance_metrics.md`).

## Seguridad y privacidad
- Enmascarar datos personales (correos, identificadores sensibles).
- No registrar tokens, contraseñas, rutas privilegiadas ni valores de `.env`.
- Asegurar que los archivos de log respeten permisos adecuados.

## Monitoreo y alertas
- Canalizar `WARNING`, `ERROR` y `CRITICAL` hacia los mecanismos de alertas definidos para Fase 9 (`docs/plan.md`).
- Documentar ajustes y hallazgos con símbolos ✅/⚠️/ℹ️ en los planes correspondientes (`docs/plan_fase4.md`, etc.).

## Testing y calidad
- Validar en `tests/` que los logs contengan campos obligatorios y cubran ramas de error según `MEMORY[test-rules.md]`.
- Incluir asserts sobre contenido de logs en pruebas unitarias, modulares e integración cuando aplique.
- Revisar logs generados tras ejecutar `pytest` y en pipelines de CI/CD.

## Estado actual del logging (⚠️ 2025-10-02)
- **Configuración central**: `src/app/config.py` usa `logging.config.dictConfig` con `RotatingFileHandler` único (`logs/email_service.log`) y `structlog`. El `formatter` estándar (`"%(asctime)s %(name)s %(levelname)s %(message)s"`) antepone metadatos al JSON de `structlog`, produciendo salidas mixtas.
- **Separación por servicio**: Todos los servicios (`src/app/services/email_service.py`, `drive_service.py`, `database_sync_service.py`) consumen el logger raíz; no existen archivos dedicados por responsabilidad como exige `logging-rules.md`.
- **Campos emitidos**: `TimeStamper` de `structlog` publica la clave `timestamp` en lugar de `timestamp_utc`, y no se establecen campos obligatorios (`message_id`, `etapa`, etc.) desde la configuración global.
- **Rotación y retención**: El tope es 100 MB con cinco respaldos, sin rotación temporal ni retención explícita de 30 días.
- **Trazabilidad actual**: Los mensajes incluyen emojis y cadenas libres; se requiere normalizar a JSON estructurado en español conforme a los lineamientos actualizados.

## Ajustes diseñados (ℹ️ Etapa 2)
- **Separación de handlers**: `src/app/config.py` creará `application.log`, `email_service.log`, `drive_service.log` y `database_sync.log` con `TimedRotatingFileHandler` diario (`backupCount=30`).
- **Formato JSON puro**: Se usará `structlog.stdlib.ProcessorFormatter` con `JSONRenderer`; `timestamp_utc` será parte de cada entrada.
- **Identificación de servicio**: Los servicios (`EmailService`, `DriveService`, `DatabaseSyncService`, `GmailOAuthService`) se inicializan con `structlog.get_logger("<servicio>")` y `bind(servicio=...)` para cumplir responsabilidad única.
- **Console logging**: El handler raíz permanecerá en consola con el mismo formato JSON para trazabilidad en desarrollo.
- **Próximos pasos**: Validar en la Etapa 3 que los logs incluyan campos obligatorios (ej. `message_id`, `etapa`) y eliminar emojis/iconografía no estructurada.

## Flujo de actualización
1. Ajustar `logging-rules.md` si cambian los lineamientos globales.
2. Actualizar planes de fase y documentación (`docs/plan_fase4.md`, `docs/development_guide.md`) con los cambios específicos.
3. Reflejar configuraciones nuevas de rotación o almacenamiento en `docs/infrastructure.md` cuando corresponda.

## Referencias
- `logging-rules.md`
- `docs/plan.md`
- `docs/workflow.md`
- `docs/plan_fase4.md`
- `docs/development_guide.md`
- `docs/environment_variables.md`
- `docs/performance_metrics.md`
