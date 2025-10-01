# Checklist Operativo – Subida a Google Drive (Fase 3)

Esta guía resume los pasos para ejecutar y verificar la carga de adjuntos a Google Drive desde el servicio de correos del CCM. Basado en las implementaciones y pruebas a la fecha.

## 1. Preparación
- Verificar variables en `.env`:
  - `GOOGLE_DRIVE_ATTACHMENTS_FOLDER_ID`
  - `GOOGLE_APPLICATION_CREDENTIALS` o `GOOGLE_DRIVE_CREDENTIALS_PATH`
  - `GOOGLE_TOKEN_PATH` (token OAuth compartido con Gmail).
- Confirmar que el token incluye el scope `https://www.googleapis.com/auth/drive` (ver logs al autenticar).
- Eliminar archivos temporales de ejecuciones previas (si se crearon fuera del flujo automático).

## 2. Ejecución
1. Iniciar el servicio (`uvicorn app.main:app --reload`).
2. Ejecutar `/process-emails` (via Swagger o script). El flujo `DriveService.upload_attachments()` realizará:
   - Creación/obtención de carpeta `YYYYMMDD` (`ensure_generation_folder`).
   - Sanitización y verificación de nombres (`format_filename`, `_generate_unique_filename`).
   - Subida binaria (`upload_file`).
3. Revisar los logs estructurados (`drive_upload_errors`, `drive_uploaded_files`, `table_errors`). Todos los mensajes están en español, por requerimiento de trazabilidad.

## 3. Validaciones post-ejecución
- Cada detalle en `ProcessingResult.details` debe incluir:
  - `drive_folder_id`
  - `drive_uploaded_files` con `id`, `name`, `webViewLink`, `webContentLink`
  - `drive_upload_errors` vacío o con objetos `{code,message}`.
- Confirmar que no queden archivos temporales en disco local.
- Verificar manualmente en Drive la carpeta `YYYYMMDD` correspondiente (comprobar sufijos únicos para duplicados).

## 4. Escenarios de error cubiertos por pruebas
- `drive_attachment_without_data`
- `drive_folder_missing`
- `drive_upload_failed` (incluye `quotaExceeded` via mocks)
- Duplicados masivos con sufijos de timestamp (ver `src/tests/test_drive_service.py`).

## 5. Pruebas automatizadas
```bash
./venv/Scripts/python.exe -m pytest src/tests/test_drive_service.py
```
Resultados esperados:
- Sanitización y renombrado ✅
- Sufijos únicos para duplicados consecutivos ✅
- Manejo de cuota (`HttpError 403 quotaExceeded`) ✅
- Actualización de credenciales OAuth compartidas ✅

## 6. Preparación para Fase 4 (Persistencia)
- Los siguientes campos del `ProcessingResult` serán insumos directos:
  - `fecha_generacion`
  - `drive_folder_id`
  - `drive_uploaded_files`
  - `parsed_table` (headers/rows) y `extra_texts`
- Documentar cualquier error en `drive_upload_errors` antes de persistir.
- Mantener `docs/performance_metrics.md` actualizado con tiempos de subida una vez se ejecute contra Drive real.
