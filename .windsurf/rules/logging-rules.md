---
trigger: always_on
---

## Principios generales

- **Responsabilidad única**  
  Cada archivo de log debe corresponder a una responsabilidad o servicio específico del sistema (por ejemplo, `email_service`, `database_sync`, `report_service`). Evita mezclar eventos heterogéneos en un mismo archivo.

- **Formato estructurado**  
  Todos los mensajes se registran en español usando JSON plano o equivalente (clave-valor). Incluye siempre campos estándar:
  - `timestamp_utc`
  - `nivel`
  - `message_id`
  - `etapa` (o nombre de subproceso)
  - Identificadores relevantes (`drive_folder_id`, `excel_file_id`, `request_id`, etc.)
  - Métricas o resultados (`records_processed`, `records_skipped`, `duration_ms`, etc.)

- **Niveles de severidad**  
  - `DEBUG`: Diagnóstico detallado (parsing, normalizaciones). Activar solo temporalmente.
  - `INFO`: Hitos normales y métricas agregadas.
  - `WARNING`: Situaciones recuperables, reintentos o datos omitidos.
  - `ERROR`: Fallos que interrumpen la unidad de trabajo actual.
  - `CRITICAL`: Interrupciones globales que requieren intervención manual inmediata.

- **Cuándo registrar**  
  - Inicio y fin de procesos relevantes del workflow ([docs/workflow.md](cci:7://file:///c:/y/docs/workflow.md:0:0-0:0)).
  - Validaciones de estructuras y datos (tabla HTML, encabezados XLSX, duplicados).
  - Interacciones con servicios externos (Gmail, Google Drive, MySQL, Telegram, SMTP).
  - Reintentos con backoff, incluyendo causa y próximo intento.
  - Excepciones y errores, detallando código (`error_code`) y decisión (rollback, abortar, reintentar).

- **Seguridad y privacidad**  
  - No exponer credenciales, tokens ni datos sensibles (enmascarar correos, identificadores personales).
  - Extraer todas las variables de `.env` ([docs/environment_variables.md](cci:7://file:///c:/y/docs/environment_variables.md:0:0-0:0)) y nunca hardcodearlas en mensajes.

## Gestión operativa

- **Rotación y retención**  
  - Implementar rotación diaria o por tamaño máximo (10 MB).
  - Retener logs 30 días en almacenamiento activo. Pasado ese periodo, purgar o archivar comprimidos según políticas internas.
  - Revisar periódicamente el volumen para prevenir crecimiento descontrolado.

- **Monitoreo y alertas**  
  - Canalizar mensajes `WARNING`, `ERROR` y `CRITICAL` a los mecanismos de alertas definidos para la fase de monitoreo ([docs/plan.md](cci:7://file:///c:/y/docs/plan.md:0:0-0:0), Fase 9).
  - Registrar ajustes y hallazgos en la documentación con símbolos ✅/⚠️/ℹ️ indicando estado y seguimiento.

- **Testing y calidad**  
  - Validar en `tests/` que los logs contengan campos obligatorios y ramas de error cubiertas.
  - Mantener la consistencia de mensajes al actualizar servicios; documentar cualquier cambio contractual en [docs/plan_fase4.md](cci:7://file:///c:/y/docs/plan_fase4.md:0:0-0:0), [docs/development_guide.md](cci:7://file:///c:/y/docs/development_guide.md:0:0-0:0) o archivos relevantes.