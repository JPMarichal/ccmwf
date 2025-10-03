# Inventario de Reportes - Fase 5

## Referencias Base
- **`scripts_google/ConsolidarReporte.gs.js`**: Consolidación de reportes misionales en Google Sheets.
- **`scripts_google/Llenar Branch in a Glance.js`**: Resumen por distrito (primeras llegadas/salidas, totales).
- **`scripts_google/EnviarReportesPDF.js`** + **`scripts_google/AutomatizacionReportes.js`**: Generación y programación de PDFs para liderazgo.
- **`scripts_google/TelegramNotifier.js`**, **`scripts_google/Notificacion Ingresos CCM.js`**: Notificaciones de próximos ingresos y métricas en Telegram.
- **`scripts_google/Correos de Cumpleanos.js`**: Correos personalizados de cumpleaños.

## Reportes y Consumidores

### Reportes en Google Sheets
- **Branch in a Glance**
  - **Objetivo**: Mostrar, por distrito, la primera generación, llegada y salida al CCM, y total de misioneros.
  - **Fuente original**: `Llenar Branch in a Glance.js` (consulta vista `vwFechasCCMPorDistrito`).
  - **Datos clave**: `Distrito`, `Generacion`, `CCM_llegada`, `CCM_salida`, `Total_Misioneros`.
  - **Consumidor Python esperado**: Servicio Fase 5 → Google Sheets (Fase 8) y PDF Branch in a Glance.

- **Reporte Misional Concentrado**
  - **Objetivo**: Consolidar todas las hojas de reporte misional en una tabla única.
  - **Fuente original**: `ConsolidarReporte.gs.js`.
  - **Datos clave**: Filas filtradas sin encabezados duplicados, métricas por distrito/rama.
  - **Consumidor Python esperado**: Servicio Fase 5 → Consolidado para PDF, email y dashboards.

### Reportes PDF y Email
- **PDF Branch in a Glance**
  - **Objetivo**: Enviar resumen de rama en PDF al liderazgo.
  - **Fuente original**: `EnviarReportesPDF.js` (usa dataset Branch in a Glance).
  - **Consumidor**: `AutomatizacionReportes.js` para programación.

- **PDF Reporte Misional Concentrado**
  - **Objetivo**: Entregar datos completos de misioneros en PDF.
  - **Fuente original**: `EnviarReportesPDF.js` (usa Consolidado).
  - **Consumidor**: Liderazgo vía email, triggers automáticos.

### Notificaciones Telegram
- **Próximos Ingresos CCM**
  - **Objetivo**: Avisar por canal Telegram sobre distritos que ingresan próximamente.
  - **Fuente original**: `TelegramNotifier.js`, `Notificacion Ingresos CCM.js`.
  - **Datos clave**: `Distrito`, `RDistrito`, `fecha_llegada`, `fecha_salida`, `cantidad`, `duracion_semanas`.
  - **Consumidor Python esperado**: Servicio Fase 5 → Fase 6 (Report Service Telegram).

- **Estadísticas / Métricas Semanales**
  - **Origen**: funciones adicionales en `TelegramNotifier.js` (cuentas, métricas por rama).
  - **Datos clave**: Totales por semana, comparativas.

### Notificaciones Messenger
- **Notificaciones CCM Maestro**
  - **Objetivo**: Coordinar envíos a Telegram y Messenger desde un único script maestro.
  - **Fuente original**: `Notificaciones CCM Maestro.js`.
  - **Datos clave**: Resultados agregados por plataforma (`Telegram`, `Messenger`), métricas de éxito/fallo.
  - **Consumidor Python esperado**: Orquestador que combine pipelines de Telegram/Messenger usando el patrón Facade.

- **Messenger Notifier / Notificaciones CCM Messenger**
  - **Objetivo**: Distribuir reportes de próximos ingresos y cumpleaños a líderes vía Facebook Messenger.
  - **Fuente original**: `MessengerNotifier.js`, `Notificaciones CCM Messenger.js`.
  - **Datos clave**: Formatos texto plano para `UpcomingArrival`, `UpcomingBirthday` con agrupaciones por fecha/mes, destinatarios específicos.
  - **Consumidor Python esperado**: Fase 6-7 reutilizando los DTOs generados en Fase 5 y adaptadores para Messenger API.

### Correos Personalizados
- **Correos de Cumpleaños**
  - **Objetivo**: Enviar email personalizado a misioneros que cumplen años.
  - **Fuente original**: `Correos de Cumpleanos.js`.
  - **Datos clave**: `Nombre`, `Tratamiento`, `Nueva_Edad`, `tres_semanas`, `correo_misional`, `correo_personal`, `Status`, `Rama`.
  - **Consumidor Python esperado**: Servicio Fase 5 → Fase 7 (Email report service).

### Otros Canales / Futuro
- **Telegram Messenger Notifier** (`Notificaciones CCM Messenger.js`, `MessengerNotifier.js`)
  - Requiere datos similares a Telegram (ingresos, estadísticas). Preparar DTOs reutilizables.
- **Backups / Consolidaciones adicionales** (`Backup generaciones.js`)
  - Relacionado con estados históricos, considerar en planificación de caché.

## Requerimientos de Datos por Reporte
- **Common**: Filtrado por rama (`RAMA_ACTUAL`), periodo (generación actual, próximas semanas), estatus (`Virtual`, `CCM`, `Campo`).
- **Atributos derivados**: duración en semanas (`tres_semanas` → 3 vs 6), conteo por distrito, totales por rama.
- **Otros cálculos**: detección de duplicados por distrito, fechas mínimas/máximas, métricas comparativas.

## Entradas y Vistas en MySQL
- `ccm_generaciones`: datos brutos cargados en Fase 4.
- `vwFechasCCMPorDistrito`: base para Branch in a Glance.
- `vwMisioneros`: para próximas llegadas (Telegram, Messenger).
- `vwCumpleanerosDeHoy`, `vwCumpleanosProximos`: soporte para correos/notificaciones de cumpleaños.
- `vwEstadisticasCumpleanos`, `vwEstadisticasIngresos`: respaldan métricas avanzadas usadas en Messenger.

## Consideraciones para la Implementación
- Normalizar datos a DTOs reutilizables (`BranchSummary`, `DistrictKPI`, `UpcomingArrival`, `UpcomingBirthday`).
- Exponer puntos de invalidación de cache tras sincronización Fase 4.
- Registrar en logs (`report_service.log`) la fuente del dataset y métricas (`cache_hit`, `records_processed`).
- Documentar contratos de salida en `docs/api_documentation.md` y `docs/development_guide.md`.
