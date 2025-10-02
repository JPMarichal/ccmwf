# Plan de Trabajo Fase 4 - Procesamiento e Inserción en MySQL

## Objetivo General
Persistir en MySQL la información de misioneros extraída de los archivos XLSX organizados en Google Drive, reproduciendo el comportamiento de `gscripts/extraer_datos.js` dentro del stack Python con técnicas modernas de mapeo (DTOs + dominio), garantizando integridad de datos, trazabilidad y manejo robusto de errores.

## Alcance
- Leer archivos XLSX ubicados en la carpeta raíz configurada en Google Drive y procesarlos por generación (YYYYMMDD).
- Normalizar encabezados y valores según el mapeo del script original (`extraer_datos.js`) mediante un catálogo central de columnas y transformaciones reutilizables.
- Sincronizar registros contra la tabla `ccm_generaciones` utilizando inserciones en lote y detección de duplicados por `id`.
- Gestionar tokens de continuación/reanudación para evitar reprocesos (equivalente a `scriptProperties`).
- Emitir logs estructurados en español con claves (`message_id`, `table_errors`, `table_rows`, `table_headers`, etc.) y métricas por lote.
- Respetar transacciones y reintentos ante errores de conexión o bloqueos.
- Diseñar un flujo coordinado con Fase 3 para ejecutar la sincronización inmediatamente después de marcar el correo como leído, manteniendo un endpoint independiente para pruebas controladas.

## Inventario de columnas XLSX → MySQL (Semana 9 - Día 1)
- **Fuente XLSX**: primer worksheet de cada archivo generado por el CCM.
- **Destino MySQL**: tabla `ccm_generaciones`.

| Índice XLSX | Columna origen (Sheet)         | Campo destino (`ccm_generaciones`) | Transformación/Notas |
|-------------|--------------------------------|------------------------------------|----------------------|
| 0           | `ID`                           | `id`                               | Entero, clave primaria. |
| 1           | `iddistric`                    | `id_distrito`                      | Texto opcional. |
| 2           | `Tipo`                         | `tipo`                             | Texto en mayúsculas opcional. |
| 3           | `Rama`                         | `rama`                             | Entero opcional. |
| 4           | `Distrito`                     | `distrito`                         | Texto. |
| 5           | `Pais`                         | `pais`                             | Texto normalizado título. |
| 6           | `Numero_de_lista`              | `numero_lista`                     | Entero opcional. |
| 7           | `Numero_de_companerismo`       | `numero_companerismo`              | Entero opcional. |
| 8           | *(vacío en Apps Script)*       | `tratamiento`                      | Dejar `NULL`. |
| 9           | `Nombre_del_misionero`         | `nombre_misionero`                 | Texto obligatorio. |
| 10          | `Companero`                    | `companero`                        | Texto opcional. |
| 11          | `Mision_asignada`              | `mision_asignada`                  | Texto opcional. |
| 12          | `Estaca`                       | `estaca`                           | Texto opcional. |
| 13          | `Hospedaje`                    | `hospedaje`                        | Texto opcional. |
| 14          | `foto`                         | `foto`                             | URL/identificador (texto). |
| 15          | `llego`                        | `fecha_llegada`                    | Fecha → `YYYY-MM-DD`. |
| 16          | `salida`                       | `fecha_salida`                     | Fecha → `YYYY-MM-DD`. |
| 17          | `Generacion`                   | `fecha_generacion`                 | Fecha → `YYYY-MM-DD`. |
| 18          | `Comentarios`                  | `comentarios`                      | Texto opcional largo. |
| 19          | `Investido`                    | `investido`                        | Booleano (`normalizarBooleano`). |
| 20          | `Cumpleanos`                   | `fecha_nacimiento`                 | Fecha → `YYYY-MM-DD`. |
| 21          | `FotoN`                        | `foto_tomada`                      | Booleano. |
| 22          | `Pasaporte`                    | `pasaporte`                        | Booleano. |
| 23          | `Folio_P`                      | `folio_pasaporte`                  | Texto opcional. |
| 24          | `FM`                           | `fm`                               | Texto opcional. |
| 25          | `iPad`                         | `ipad`                             | Booleano. |
| 26          | `Closet`                       | `closet`                           | Texto opcional. |
| 27          | `llego2`                       | `llegada_secundaria`               | Texto opcional. |
| 28          | `Pday`                         | `pday`                             | Texto opcional. |
| 29          | `Host`                         | `host`                             | Booleano. |
| 30          | `tres_semanas`                 | `tres_semanas`                     | Booleano. |
| 31          | `Device`                       | `device`                           | Booleano. |
| 32          | `Correo_Misional`              | `correo_misional`                  | Email opcional. |
| 33          | `Correo_Personal`              | `correo_personal`                  | Email opcional. |
| 34          | `Fecha_Presencial`             | `fecha_presencial`                 | Fecha `D/M/YYYY` → `YYYY-MM-DD`. |
| 35          | *(constante)*                  | `activo`                           | `True` para registros nuevos. |
| 36          | *(timestamp generación)*       | `created_at`                       | Timestamp UTC al momento de inserción. |
| 37          | *(timestamp generación)*       | `updated_at`                       | Timestamp UTC al momento de inserción. |

- **Campos no presentes en XLSX**: `tratamiento`, `activo`, `created_at`, `updated_at` se establecerán desde el servicio.
- **Transformaciones clave**: reutilizar funciones `normalizarFecha`, `normalizarFechaPresencial`, `normalizarBooleano` adaptadas a Python.


## Dependencias
- Fases 1-3 completadas: `ProcessingResult` debe incluir `parsed_table`, `drive_details` y metadatos de generación.
- Variables de entorno definidas en `.env`:
  - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DATABASE_URL`.
  - `GENERACIONES_BACKUP_FOLDER_ID` (carpeta secundaria opcional para respaldos).
  - `GOOGLE_DRIVE_ATTACHMENTS_FOLDER_ID` (carpeta raíz de generaciones).
- Servicio `DriveService` reutilizable para listar/descargar archivos.
- Librerías requeridas: `pandas`, `sqlalchemy`, `pymysql`, `openpyxl` o `xlrd` según formato.

## Entregables
- Servicio Python (`DatabaseSyncService`) responsable de:
  - Enumerar carpetas por generación.
  - Descargar y procesar archivos XLSX.
  - Mapear columnas a los campos de la tabla `ccm_generaciones` usando modelos de dominio (`MissionaryRecord`) y patrones Repository/Unit of Work.
  - Ejecutar inserciones en lote con manejo de transacciones y detección de duplicados.
- Repositorio local de estado (archivo JSON o tabla auxiliar) para tokens de continuación.
- Tests unitarios y de integración con mocks de Drive y MySQL (`pytest`, `pytest-mock`).
- Logs estructurados y documentación actualizada (`docs/api_documentation.md`, `docs/development_guide.md`).

### Estado de logging (ℹ️ 2025-10-02)
- **✅ Configuración separada por servicio**: `src/app/config.py` define handlers diarios para `application.log`, `email_service.log`, `drive_service.log` y `database_sync.log`, cumpliendo responsabilidad única.
- **✅ Formato JSON**: Todos los logs utilizan `structlog` con `timestamp_utc` y campos comunes; se retiraron emojis de mensajes operativos.
- **⚠️ Pruebas pendientes**: Falta instrumentar asserts en `tests/` para validar presencia de campos obligatorios (`message_id`, `etapa`, etc.) y rotación.
- **ℹ️ Documentación**: `docs/logging.md` actualizado; `docs/development_guide.md` requiere reflejar la nueva estructura durante la siguiente fase de documentación.
- Checklist de despliegue para base de datos y credenciales.
- Endpoint permanente (`POST /extraccion_generacion`) para invocar la extracción y sincronización por generación, reutilizable para pruebas controladas y para la ejecución encadenada tras la fase 3.

## Plan Semanal

### Semana 9 – Análisis y Diseño
- **Día 1**
  - Inventariar estructuras de columnas del XLSX original y equivalencias en MySQL.
  - Definir interfaz del nuevo servicio (`DatabaseSyncService`) y DTOs auxiliares.
  - Resultado:
    - Interfaz propuesta `DatabaseSyncService.sync_generation(fecha_generacion: str, drive_folder_id: str, *, force: bool = False) -> DatabaseSyncReport`.
    - DTO principal `MissionaryRecord` (Pydantic) con mapeo 1:1 al inventario anterior y validaciones de tipo.
    - `DatabaseSyncReport` incluirá métricas (`inserted_count`, `skipped_count`, `duration_seconds`, `drive_file_ids`, `continuation_token`).
- **Día 2**
  - Diseñar estrategia de control de reprocesos (continuation tokens) y reanudación segura.
  - Especificar modelo de logs y códigos de error (`db_connection_failed`, `db_insert_failed`, `drive_listing_failed`).
  - Resultado:
    - Repositorio de estado `DatabaseSyncStateRepository` respaldado por archivo JSON `data/state/database_sync_state.json` (con clave `last_processed_file_id` y `continuation_token`).
    - Estrategia de reanudación: procesar carpetas ordenadas por fecha, almacenar token al detectar límite de tiempo o error, limpiar al finalizar exitosamente.
    - Esquema de logging estructurado (en español) con campos obligatorios: `message_id`, `etapa`, `drive_folder_id`, `excel_file_id`, `batch_size`, `records_processed`, `records_skipped`, `table_errors`, `error_code`.
- **Día 3**
  - Elaborar plan de pruebas (unitarias para normalización y mapeo, integración para inserción y reanudación).
  - Documentar diagramas de secuencia actualizados en `docs/workflow.md`.
  - Resultado:
    - **Pruebas unitarias**: normalización de fechas/booleanos, mapeo `MissionaryRecord`, detección de duplicados, manejo de tokens.
    - **Pruebas modulares**: mock de `DriveService` y `SQLAlchemy` para verificar lotes, rollback y logging por códigos de error.
    - **Pruebas de integración**: escenario feliz con fixture de XLSX y base MySQL dockerizada, escenario con interrupción/reanudación.
    - Se actualizará `docs/workflow.md` con una subsección "Fase 3 → Fase 4" y diagrama de secuencia reflejando la llamada a `/extraccion_generacion`.

### Semana 10 – Implementación Inicial
- **Día 4-5**
  - Implementar capa de acceso a Drive (listado/descarga) reutilizando `DriveService`.
  - Crear parsers de XLSX utilizando `pandas.read_excel` y normalizadores de fechas/booleanos (equivalentes a `normalizarFecha*`, `normalizarBooleano`) encapsulados en `MissionaryRecord`.
- **Día 6**
  - Implementar inserciones en lote con `sqlalchemy`/`pymysql`, manejo de transacciones y commits parciales, más repositorio dedicado.
  - Añadir métricas (registros insertados, ignorados, duración por lote) al logging estructurado.
- **Día 7**
  - Gestionar tokens/estado de ejecución y pruebas unitarias de normalización y deduplicación.
  - Diseñar endpoint permanente `/extraccion_generacion`; la orquestación automática con la Fase 3 se documenta como actividad diferida para la fase siguiente (ℹ️ pendiente de implementación).

### Semana 11 – Pruebas y Optimización
- **Día 8**
  - Ejecutar pruebas de integración contra MySQL (docker o base de datos mockeada) cubriendo casos de éxito y fallas.
  - Medir tiempos y ajustar tamaño de lote.
- **Día 9**
  - Implementar reintentos con exponencial backoff para errores transitorios.
  - Revisar y ajustar logs para cumplimiento de trazabilidad.
- **Día 10**
  - Actualizar documentación (`docs/api_documentation.md`, `docs/development_guide.md`) con la nueva API/servicio y el enlace fase 3 → fase 4.
  - Preparar checklist de despliegue y handoff (marcado ✅/⚠️/ℹ️).

## Riesgos y Mitigaciones
- **Bloqueos en MySQL**: configurar `innodb_lock_wait_timeout` y reintentos controlados.
- **Cambios en estructura del XLSX**: diseñar validaciones de encabezados con tolerancia y registro de errores específicos.
- **Tiempos de ejecución largos**: usar lotes configurables y tokens de reanudación.
- **Inconsistencias entre Drive y BD**: generar reporte de sincronización (`ProcessingResult.details`) y respaldos opcionales en carpeta `GENERACIONES_BACKUP_FOLDER_ID`.

## Métricas de Éxito
- 100% de nuevas filas insertadas o registradas como duplicadas.
- Logs con trazabilidad completa (IDs de archivo, generación, número de registros, duración) y sin pérdidas por reproceso.
- Cobertura de pruebas ≥80% en módulos de sincronización y normalización.
- Documentación y checklist actualizados (✅) tras la implementación.
