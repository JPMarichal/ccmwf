# Plan de Trabajo Fase 6 - Generación de Reportes por Telegram

## Objetivo General
Habilitar un servicio de notificaciones que distribuya por Telegram los reportes del CCM (próximos ingresos, próximos cumpleaños y alertas operativas) reutilizando los datasets preparados en la Fase 5 y garantizando trazabilidad, logging estructurado y pruebas automatizadas.

## Alcance
- **Consumo de datasets**: Integrar `ReportPreparationService` para obtener `UpcomingArrival`, `UpcomingBirthday` y métricas complementarias filtradas por `RAMA_ACTUAL`.
- **Cliente Telegram**: Implementar un adaptador de la API `sendMessage` con manejo de reintentos, timeouts y mascarado de credenciales.
- **Formateadores de mensajes**: Replicar formatos históricos de `scripts_google/TelegramNotifier.js`, `Notificacion Ingresos CCM.js` y `Notificacion Cumpleanos.js` con soporte para mensajes vacíos.
- **Endpoints FastAPI**: Publicar endpoints independientes (`/telegram/proximos-ingresos`, `/telegram/proximos-cumpleanos`, `/telegram/alerta`) con parámetros de control (`force_refresh`, `rama_override`).
- **Instrumentación**: Registrar logs JSON en español con campos mínimos `timestamp_utc`, `nivel`, `message_id`, `etapa="fase_6_telegram"`, `telegram_chat_id`, `records_sent`, `error_code`.
- **Testing y documentación**: Incorporar pruebas unitarias/modulares/integración y actualizar documentación operativa, incluyendo checklist con ✅/⚠️/ℹ️.

## Scripts de Google a Emular
- **`scripts_google/TelegramNotifier.js`**: Mensajes CCM Notifications sobre ingresos y cumpleaños.
- **`scripts_google/Notificacion Ingresos CCM.js`**: Agrupaciones por fecha y conteos por distrito.
- **`scripts_google/Notificacion Cumpleanos.js`**: Agrupaciones por mes/día con encabezados.
- **`scripts_google/Notificaciones CCM Maestro.js`**: Secuencia de disparo posterior a la sincronización de datos.

## Patrones de Diseño Prioritarios
- **Facade**: Servicio Telegram coordinando obtención de datasets, formateo y envío.
- **Template Method**: Flujo estandarizado de notificación (obtener → validar → formatear → enviar → registrar).
- **Strategy**: Selección de backend de caché/invalidador vía `ReportPreparationService`; configuración de cliente HTTP (por ejemplo, sesión vs. request simple).
- **Builder**: Construcción de mensajes complejos (bloques por fecha/mes) antes de serializar a string.
- **Observer**: Suscripción a eventos `dataset.invalidated` para refrescar cache antes de disparar notificaciones.

## Entregables
- **✅ Servicio Telegram** en `src/app/services/telegram_notification_service.py` (o similar) con métodos especializados por reporte y adaptador HTTP desacoplado.
- **✅ Endpoints FastAPI** en `src/app/main.py` o router dedicado que expongan operaciones idempotentes y parametrizables.
- **✅ Configuración `.env`** con variables `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_TIMEOUT_SECONDS` documentadas en `docs/environment_variables.md`.
- **✅ Logging estructurado** con archivo dedicado (`logs/report_service.log`) y métricas de envío (`records_sent`, `records_skipped`, `duration_ms`).
- **✅ Pruebas**: Unit tests para formateadores/adaptador, modulares para el servicio y `TestClient` para endpoints.
- **✅ Documentación actualizada** (`docs/plan.md`, `docs/workflow.md`, `docs/development_guide.md`) con símbolos de estado y referencias cruzadas.

## Avances recientes
- **✅ Issue #22**: Cliente base de Telegram implementado en `src/app/services/telegram_client.py`, exportado en `src/app/services/__init__.py`, con pruebas (`src/tests/test_telegram_client.py`) y documentación (`docs/environment_variables.md`).
- **✅ Issue #23**: `TelegramNotificationService` con Template Method y formateadores específicos (`src/app/services/telegram_notification_service.py`), endpoints FastAPI (`/telegram/proximos-ingresos`, `/telegram/proximos-cumpleanos`, `/telegram/alerta`), pruebas unitarias e integración (`src/tests/test_telegram_notification_service.py`, `tests/integration/test_telegram_endpoints.py`).

## Dependencias y Preparativos
- **Datos**: Pipelines `upcoming_arrivals` y `upcoming_birthdays` provistos por Fase 5; vistas MySQL `vwMisioneros`, `vwCumpleanosProximos`.
- **Variables de entorno**: Verificar presencia en `.env`; agregar antes de codificar si faltan.
- **Infraestructura**: Token y chat ID del bot Telegram vigentes; validar permisos del canal «CCM Notifications».
- **Caché**: Reutilizar estrategias existentes (`InMemoryCacheStrategy`, `RedisCacheStrategy`); garantizar sincronización con eventos de Fase 4.

## Plan de Trabajo
- **Semana 8 – Diseño y configuración**
  - Levantar requisitos de formateo comparando salidas actuales de Apps Script.
  - Definir contrato del servicio Telegram y mapeo de DTOs ↔ mensajes.
  - Documentar variables `.env` y preparar logging dedicado.
- **Semana 9 – Implementación**
  - Codificar cliente/adaptador Telegram con reintentos.
  - Implementar formateadores y servicio aplicando Template Method/Builder.
  - Exponer endpoints FastAPI y validar integración con caché.
- **Semana 10 – Calidad y documentación**
  - Escribir pruebas unitarias, modulares e integración (casos exitosos y fallos).
  - Ejecutar benchmarks básicos y registrar métricas en `docs/performance_metrics.md` (si aplica).
  - Actualizar `docs/plan.md` y `docs/workflow.md` con nuevos pasos de distribución.

## Riesgos y Mitigaciones
- **Rate limit o caídas de Telegram**: Implementar backoff exponencial y alertas `WARNING`/`ERROR` con sugerencias de reintento manual.
- **Datasets vacíos o inconsistentes**: Mensajes amigables («No hay próximos ingresos») y validaciones tempranas (`records_skipped`).
- **Credenciales mal configuradas**: Validar configuración al arranque y abortar con logs `CRITICAL` indicando variable faltante.
- **Desalineación con Apps Script**: Pruebas snapshot y revisión manual con liderazgo para asegurar equivalencia semántica.

## Métricas de Éxito
- **Tiempo de envío** < 1 s por mensaje (sin contar latencia Telegram).
- **Cobertura de pruebas** ≥ 85% en módulos nuevos (`tests/telegram`).
- **Cero discrepancias** entre mensajes Python y los generados históricamente (validado por QA interno).
- **Logs** con 100% de mensajes portando `message_id`, `telegram_chat_id` y `records_sent`.

## Checklist de Coordinación
- ✅ Confirmar variables en `.env` antes de integrar código.
- ⚠️ Actualizar `docs/plan.md` y `docs/workflow.md` al cerrar subtareas.
- ✅ Registrar avances con símbolos ✅/⚠️/ℹ️ en los reportes al usuario.
- ✅ Mantener concordancia con `scripts_google/` hasta completar migración total.
