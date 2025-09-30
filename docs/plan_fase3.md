# Plan de Trabajo Fase 3 - Organización en Google Drive

## Objetivo General
Organizar y almacenar en Google Drive la información procesada en fases anteriores (attachments, tablas HTML, metadatos) garantizando integridad, nomenclatura consistente y trazabilidad.

## Alcance
- Subir archivos PDF y XLSX asociados a cada generación.
- Generar estructuras de carpetas por fecha (YYYYMMDD) y zona/distrito cuando aplique.
- Registrar metadatos y enlaces permanentes en la salida del servicio.
- Limpiar archivos temporales locales tras la carga exitosa.

## Dependencias
- Fase 2 finalizada: `ProcessingResult` con `parsed_table`, `table_errors`, `validation_errors`.
- Credenciales OAuth/Service Account para Google Drive.
- Librerías: `google-api-python-client`, `google-auth`.
- Configuración en `.env` para IDs de carpeta base (`GOOGLE_DRIVE_ATTACHMENTS_FOLDER_ID`).

## Entregables
- Servicio que tras una ejecución de `/process-emails` sube documentos a Drive.
- Estructura de carpetas consistente y renombrado controlado (`{fecha}_{distrito}_{archivo}`).
- Registro en `ProcessingResult.details` de enlaces Drive y estado de la carga.
- Documentación actualizada (`docs/plan_fase3.md`, `docs/api_documentation.md`, `docs/development_guide.md`).
- Pruebas unitarias/integración para operaciones en Drive (mock de APIs).

## Plan Semanal

### Semana 7 – Preparación y Diseño ✅
- **Día 1**
  - ✅ Revisar requisitos de Drive (permisos, límites de cuota, estructura deseada). *(Cubierto durante el análisis previo a `DriveService`)*
- **Día 2**
  - ✅ Definir esquema de carpetas/archivos y convención final de nombres. *(Aplicado en `DriveService.format_filename()` y uso de carpetas por generación)*
- **Día 3**
  - ✅ Diseñar módulos/servicios para subida a Drive (interfaz y dependencias). *(Definido en `app/services/drive_service.py`)*
- **Día 4**
  - ℹ️ Plan de pruebas: casos de éxito, errores de quota, archivos duplicados, limpieza temporal. *(Plan documentado; ejecución programada para Semana 9)*

### Semana 8 – Implementación (iniciada)
- **Día 5-6**
  - ✅ Implementar cliente Drive (wrapper con autenticación y utilidades). *(Ver `app/services/drive_service.py`)*
- **Día 7-8**
  - ⚠️ Integrar carga de PDFs/XLSX al flujo actual (`EmailService`, `ProcessingResult`).
- **Día 9**
  - ⚠️ Gestión de errores y reintentos: códigos específicos (`drive_upload_failed`, `drive_folder_missing`). *(Actualmente se registran errores en logs; falta estandarizar códigos compartidos)*

### Semana 9 – Pruebas y Documentación
- **Día 10**
  - ⚠️ Pruebas unitarias y de integración con mocks de Drive.
- **Día 11**
  - ⚠️ Documentar proceso (guías, API docs) y checklist de subida. *(Progreso: `docs/api_documentation.md` actualizado con campos Drive)*
- **Día 12**
  - ⚠️ Revisión final, retroalimentación y preparación para persistencia (Fase 4).

## Riesgos y Mitigaciones
- **Cuotas de API**: Implementar reintentos con backoff y monitoreo de límites.
- **Nombres de archivos conflictivos**: Aplicar convención única (`timestamp` o hash) y verificación previa.
- **Permisos insuficientes**: Validar credenciales y scopes en entorno de staging antes de producción.
- **Fallas de red**: Registrar reintentos y permitir reanudación manual.

## Métricas de Éxito
- 100% de archivos relevantes subidos a Drive por generación.
- Cero archivos temporales pendientes tras ejecución.
- Reporte claro de enlaces Drive y errores por mensaje.
- Cobertura de pruebas >80% en módulos de Drive.
