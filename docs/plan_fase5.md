# Plan de Trabajo Fase 5 - Preparación de Datos para Reportes

## Objetivo General
Preparar datasets consolidados y consistentes desde la base de datos MySQL para abastecer los canales de reporte (Google Sheets, PDFs, Telegram, email y futuros dashboards), reproduciendo en Python la lógica hoy contenida en los scripts de Google Apps Script.

## Alcance
- Generar vistas y agregaciones por rama, zona y distrito que alimenten todos los reportes automatizados.
- Calcular métricas derivadas (conteos, totales por cohorte, duración de estancias, próximos hitos).
- Implementar una capa de caché parametrizable para reutilizar resultados entre múltiples consumidores.
- Validar integridad de datos (completitud, duplicados, estatus inconsistentes) previo a la distribución.
- Estandarizar estructuras de salida (DTOs/serializadores) reutilizables por servicios de reporte y notificación.

## Scripts de Google a Emular
- **`scripts_google/ConsolidarReporte.gs.js`**: Consolidación de hojas "Reporte misional concentrado" sin duplicados ni filas vacías.
- **`scripts_google/Llenar Branch in a Glance.js`**: Resumen por distrito con primeras llegadas/salidas y totales.
- **`scripts_google/Extraer datos misionales.js`**: Normalización de campos y control de reanudación (referencia para consistencia de columnas).
- **`scripts_google/EnviarReportesPDF.js`** y **`scripts_google/AutomatizacionReportes.js`**: Necesitan datasets preformateados para PDFs y programación de envíos.
- **`scripts_google/TelegramNotifier.js`** y **`scripts_google/Correos de Cumpleanos.js`**: Consumen datos agregados (próximos ingresos, cumpleaños, estadísticas).

## Arquitectura Objetivo en Python (Fase 5)
- **Servicios**: Diseñar `ReportPreparationService` con submódulos especializados (`AggregationsService`, `CachingService`, `ValidationService`).
- **DTOs**: Crear modelos Pydantic para `BranchSummary`, `DistrictKPI`, `UpcomingArrival`, `UpcomingBirthday`, `ReportDatasetMetadata`.
- **Capa de caché**: Soportar backend configurable (memoria/Redis). TTL y keys derivados de `branch_id` y fecha de generación.
- **Validadores**: Reutilizar reglas de `src/app/services/validators.py` y añadir verificaciones contra estructuras esperadas de reportes.
- **Logging**: Mensajes en español con campos obligatorios (`message_id`, `etapa="fase_5_preparacion"`, `dataset_id`, `records_processed`, `cache_hit`, `error_code`).

## Patrones de Diseño Prioritarios
- **Facade**: `ReportPreparationService` actuará como fachada única para los consumidores (Telegram, email, Sheets), encapsulando la orquestación interna de agregaciones y validaciones.
- **Strategy**: Implementar estrategias intercambiables para la capa de caché (`InMemoryCacheStrategy`, `RedisCacheStrategy`) y para fuentes de agregación (p. ej. vistas MySQL vs. consultas directas).
- **Template Method**: Definir plantillas de preparación (`BaseDatasetPipeline.prepare()`) que aseguren pasos consistentes: carga→validación→transformación→serialización, reutilizable por cada reporte.
- **Builder**: Utilizar constructores especializados para componer DTOs complejos (ej. `BranchSummaryBuilder`) evitando constructores con demasiados parámetros y permitiendo validaciones intermedias.
- **Observer/Event Publisher**: Publicar eventos `dataset.invalidated` para que Fase 6-8 actualicen cachés tras nuevas sincronizaciones (suscribirse desde servicios de entrega).
- **Adapter** (opcional): Envolver estructuras heredadas de MySQL o pandas en interfaces amigables para los DTOs actuales si las vistas cambian.

## Dependencias
- Datos persistidos por la fase 4 en MySQL (`ccm_generaciones`, vistas `vwMisioneros`, `vwFechasCCMPorDistrito`, `vwCumpleanerosDeHoy`, `vwCumpleanosProximos`).
- Variables en `.env`: `DB_*`, `REPORT_BRANCH_ID`, `CACHE_PROVIDER`, `REDIS_URL` (si aplica), `REPORT_CACHE_TTL_MINUTES`.
- Librerías existentes (`sqlalchemy`, `pandas`). Evaluar agregar `redis` sólo si se confirma su uso.
- Coordinación con `docs/workflow.md` y `docs/plan.md` para mantener congruencia.

## Entregables
- ⚠️ **Servicio de preparación de datasets** (`src/app/services/report_preparation_service.py`) listo para consumo interno.
- ⚠️ **Esquemas DTO + serializadores** en `src/app/models.py` o módulo dedicado.
- ⚠️ **Capa de caché** con estrategia de invalidación y métricas.
- ⚠️ **Validadores y reglas de consistencia** documentadas.
- ⚠️ **Tests unitarios/modulares** (`tests/test_report_preparation_service.py`, `tests/test_report_validations.py`) cubriendo casos exitosos y fallos.
- ⚠️ **Documentación** actualizada (`docs/development_guide.md`, `docs/api_documentation.md`, `docs/performance_metrics.md`, `docs/plan.md`).

## Plan Semanal

### Semana 7 – Descubrimiento y Diseño
- **Día 1**: Analizar vistas MySQL y confirmar mapeos requeridos por cada reporte (Branch in a Glance, consolidado, Telegram, cumpleaños). Resultado: especificaciones de campos y contratos de salida.
- **Día 2**: Diseñar la fachada (`ReportPreparationService`) y definir estrategias de caché/aggregaciones (patrón Strategy). Documentar decisiones en `docs/development_guide.md`.
- **Día 3**: Elaborar plantilla base de pipelines (Template Method) y catálogo de códigos de error (`dataset_missing_rows`, `invalid_branch`, `stale_cache`).

### Semana 8 – Implementación de Agregaciones y Caché
- **Día 4-5**: Implementar pipelines concretos heredando de la plantilla y usar Builders para DTOs (`BranchSummaryBuilder`, `UpcomingArrivalBuilder`).
- **Día 6**: Integrar capa de caché con estrategias configurables y métricas (`cache_hit`, `cache_miss`, `duration_ms`). Preparar hooks Observer para invalidación tras sincronización de Fase 4.
- **Día 7**: Instrumentar validaciones y logging estructurado. Configurar manejo de excepciones y códigos.

### Semana 9 – Validaciones, Pruebas y Documentación
- **Día 8**: Construir pruebas unitarias contemplando variantes de Strategy, Template Method y Builders (normalización de fechas, agregaciones sin duplicados, detección de datos faltantes). Mock de DB y caché.
- **Día 9**: Pruebas de integración con base de datos (fixtures controlados). Medir desempeño y ajustar índices/consultas.
- **Día 10**: Actualizar documentación y checklist, explicitando cómo las capas Facade/Observer se enlazan con Fase 6. Preparar handoff para servicios de entrega de reportes.

## Riesgos y Mitigaciones
- **Desalineación con vistas MySQL**: Revisar definiciones actuales y coordinar cambios antes de codificar producción.
- **Costos de consultas pesadas**: Usar agregaciones optimizadas y paginar por rama/distrito; monitorear tiempos en `docs/performance_metrics.md`.
- **Datos incompletos**: Validaciones estrictas con códigos específicos y reportes al equipo (registrar en `logs/report_service.log`).
- **Inconsistencia de caché**: Implementar invalidación en eventos (nueva generación importada) y TTL configurable.

## Métricas de Éxito
- Preparación de datasets < **5 segundos** por generación (sin caché) y < **500 ms** con caché.
- Cobertura de pruebas ≥ **85%** en nuevos módulos.
- 0 discrepancias entre datos mostrados y registros en MySQL (validaciones preventivas).
- Documentación y checklist marcados con ✅ tras completar entregables.

## Checklist de Coordinación
- ⚠️ Actualizar `docs/plan.md` cuando avance el estado de actividades de la fase.
- ⚠️ Mantener `docs/workflow.md` alineado con nuevos pasos de preparación/caché.
- ⚠️ Confirmar presencia de variables en `.env` antes de usar nuevas configuraciones.
- ⚠️ Registrar en `docs/performance_metrics.md` resultados de benchmarks.

## Próximos Pasos Inmediatos
1. Levantar especificaciones de datasets basado en scripts históricos (Branch in a Glance y consolidado).
2. Definir contratos DTO y rutas de obtención para cada reporte.
3. Evaluar necesidades de caché y seleccionar backend (memoria o Redis).
