# API Documentation - CCM Email Service

## Overview

The CCM Email Service exposes a REST API built with FastAPI to orchestrate the processing of missionary arrival emails. All endpoints return JSON responses and leverage asynchronous handlers.

- **Base URL (local)**: `http://localhost:8000`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Authentication

- The current phase does **not** require authentication.
- Future phases will integrate API keys or JWT once the service is exposed externally.

## Response Format

All responses follow the structure below:

```json
{
  "success": true,
  "result": { /* optional payload */ },
  "detail": "optional message"
}
```

Errors are returned using FastAPI's default error schema:

```json
{
  "detail": "Error message"
}
```

## Endpoints

### 1. Health Check

- **Method**: `GET`
- **Path**: `/health`
- **Purpose**: Validate that the API is running.
- **Response**:

```json
{
  "status": "healthy",
  "service": "email-service",
  "version": "1.0.0"
}
```

### 2. Process Emails

- **Method**: `POST`
- **Path**: `/process-emails`
- **Purpose**: Trigger the email processing workflow.
- **Behavior**:
  - Uses OAuth or IMAP based on configuration.
  - Fetches unprocessed emails that match the configured subject pattern.
  - Extracts body metadata, attachments and marks emails as processed.
  - Derives `fecha_generacion` combinando texto plano, HTML y títulos de tablas (cabeceras tipo "Generación del ...") antes de validar adjuntos.
  - Reutiliza un único consentimiento OAuth (installed app) para Gmail y Google Drive; el token se guarda en `GOOGLE_TOKEN_PATH` y debe incluir los scopes de lectura Gmail y escritura Drive.
- **Success Response** (`HTTP 200`):

```json
{
  "success": true,
  "result": {
    "success": true,
    "processed": 2,
    "errors": 0,
    "details": [
      {
        "success": true,
        "message_id": "ABCDEF123",
        "subject": "Misioneros que llegan el 10 de enero",
        "fecha_generacion": "20250110",
        "attachments_count": 3,
        "validation_errors": [],
        "parsed_table": {
          "headers": ["Distrito", "Zona"],
          "rows": [
            {
              "Distrito": "14A",
              "Zona": "Benemerito"
            }
          ],
          "extra_texts": [
            "Generación del 10 de enero de 2025"
          ]
        },
        "table_errors": [],
        "drive_folder_id": "1ned3xG0oC-SgCUeLXSBADD8PQWV5drVs",
        "drive_uploaded_files": [
          {
            "id": "1abcXYZ",
            "name": "20250110_14A_info.pdf",
            "webViewLink": "https://drive.google.com/file/d/1abcXYZ/view",
            "webContentLink": "https://drive.google.com/file/d/1abcXYZ/download"
          }
        ],
        "drive_upload_errors": []
      }
    ],
    "start_time": "2025-01-10T06:00:04.123Z",
    "end_time": "2025-01-10T06:00:06.450Z",
    "duration_seconds": 2.327
  }
}
```

- **Error Response** (`HTTP 500`):

```json
{
  "detail": "Error procesando emails: Processing error"
}
```

- **Validation Failure Response** (`HTTP 200`)

Cuando uno o más correos no cumplen la estructura esperada, el resultado incluye `validation_errors` para cada mensaje y el campo `success` se marca en `false` a nivel de detalle:

```json
{
  "success": true,
  "result": {
    "success": true,
    "processed": 0,
    "errors": 1,
    "details": [
      {
        "success": false,
        "message_id": "GHI789",
        "subject": "Correo irrelevante",
        "fecha_generacion": null,
        "attachments_count": 0,
        "validation_errors": [
          "subject_pattern_mismatch",
          "attachments_missing",
          "fecha_generacion_missing"
        ],
        "parsed_table": null,
        "table_errors": ["html_missing"],
        "drive_folder_id": null,
        "drive_uploaded_files": [],
        "drive_upload_errors": [
          {
            "stage": "preflight",
            "error": "missing_fecha_generacion"
          }
        ]
      }
    ]
  }
}
```

#### Campos de `parsed_table`

- **`headers`**: Lista en el orden detectado, normalizada a partir de celdas `<th>` o de la primera fila con múltiples valores.
- **`rows`**: Filas de datos mapeadas a los encabezados; las celdas faltantes se completan con cadenas vacías para garantizar consistencia.
- **`extra_texts`**: Texto contextual localizado antes de los encabezados (por ejemplo, títulos como "Generación del ..."), reutilizado para extraer `fecha_generacion` cuando el cuerpo no la incluye.

### 3. Extracción y sincronización de generación (Fase 4)

- **Method**: `POST`
- **Path**: `/extraccion_generacion`
- **Purpose**: Ejecutar la sincronización de una generación específica tomando los archivos XLSX almacenados en Google Drive y persistiendo los registros nuevos en MySQL.
- **Request Body**:

```json
{
  "fecha_generacion": "20250110",
  "drive_folder_id": "1ned3xG0oC-SgCUeLXSBADD8PQWV5drVs",
  "force": false
}
```

  - `fecha_generacion` (**string, requerido**): Identificador de la generación (formato `YYYYMMDD`).
  - `drive_folder_id` (**string, requerido**): Carpeta raíz en Google Drive donde se encuentran los XLSX de la generación.
  - `force` (**boolean, opcional**): Forzar reproceso ignorando el estado previo (tokens de continuación). Por defecto `false`.

- **Behavior**:
  - Lista los archivos XLSX en `drive_folder_id` usando `DriveService.list_folder_files()`.
  - Descarga cada archivo con `DriveService.download_file()`.
  - Convierte el contenido a `MissionaryRecord` aplicando normalizadores equivalentes a `normalizarFecha*` y `normalizarBooleano`.
  - Inserta solamente registros nuevos (detección por `id`) usando `sqlalchemy` + `pymysql` y lotes de 50.
  - Actualiza tokens de continuación en `data/state/database_sync_state.json` para reanudar en caso de fallo.
  - Emite logs estructurados en español con claves mínimas: `message_id`, `etapa`, `drive_folder_id`, `excel_file_id`, `batch_size`, `records_processed`, `records_skipped`, `table_errors`, `error_code`.

- **Success Response** (`HTTP 200`):

```json
{
  "success": true,
  "report": {
    "fecha_generacion": "20250110",
    "drive_folder_id": "1ned3xG0oC-SgCUeLXSBADD8PQWV5drVs",
    "processed_files": [
      {
        "file_id": "1abcXYZ",
        "filename": "20250110_distrito14A.xlsx",
        "inserted": 45,
        "skipped": 0,
        "rows_total": 45
      }
    ],
    "inserted_count": 45,
    "skipped_count": 0,
    "errors": [],
    "duration_seconds": 12.4,
    "continuation_token": null
  }
}
```

- **Error Response** (`HTTP 500`):

```json
{
  "detail": "Error procesando extracción: db_insert_failed (1049: Unknown database)"
}
```

- **Errores comunes**:
  - `drive_listing_failed`: Problema al listar la carpeta (permisos o ID incorrecto).
  - `drive_download_failed`: Descarga interrumpida; la respuesta incluirá `continuation_token` con el `file_id` para reintentar.
  - `db_insert_failed`: Error de conexión o bloqueo MySQL; la sincronización se detiene y guarda estado para reanudar.
  - `excel_read_failed`: Formato de XLSX inválido o dañado.

- **Notas de operación**:
  - Requiere que Fase 3 haya colocado los archivos XLSX en la carpeta indicada.
  - Para ejecución automática, se invoca inmediatamente después de marcar el correo como leído y subir adjuntos en Drive.
  - Mantener `force=false` en escenarios normales para evitar reprocesos innecesarios.

### 4. Search Emails (Debug/Test)

- **Method**: `GET`
- **Path**: `/emails/search`
- **Query Parameters**:
  - `query` *(optional)*: Custom Gmail search string.
- **Purpose**: Inspect recent emails for debugging.
- **Success Response** (`HTTP 200`):

```json
{
  "success": true,
  "emails": [
    {
      "id": "ABC123",
      "subject": "Misioneros que llegan el 10 de enero",
      "sender": "natalia.leyva@ccm.org",
      "date": "Fri, 10 Jan 2025 06:12:31 +0000",
      "has_attachments": true
    }
  ]
}
```

- **Error Response** (`HTTP 500`):

```json
{
  "detail": "Error buscando emails: Connection reset"
}
```

## Testing the API

### Via Swagger UI

1. Start the application.
2. Navigate to `http://localhost:8000/docs`.
3. Use the **Try it out** button for each endpoint.

### Via HTTP client (curl example)

```bash
# Health check
curl http://localhost:8000/health

# Process emails
curl -X POST http://localhost:8000/process-emails

# Search emails
curl "http://localhost:8000/emails/search?query=subject:%5C"Misioneros%20que%20llegan%5C""
```

## Error Handling

| Error Scenario | HTTP Code | Suggested Action |
|----------------|-----------|------------------|
| Missing OAuth credentials | 500 | Verify `GOOGLE_APPLICATION_CREDENTIALS` and `GOOGLE_TOKEN_PATH` |
| IMAP login failure | 500 | Check `GMAIL_APP_PASSWORD` or OAuth fallback |
| Gmail API quota exceeded | 429/500 | Wait and retry, consider exponential backoff |
| HTML table without required columns (`column_missing:<col>`) | 200 | Revisar el cuerpo del correo y solicitar el formato correcto |
| HTML table with empty values (`value_missing:<col>:<row>`) | 200 | Corregir datos faltantes antes de reprocesar |
| Google Drive upload failed (`drive_upload_failed`) | 200 | Revisar `drive_upload_errors`, validar credenciales y permisos en Drive |
| Google Drive insufficient permissions | 200 | Eliminar `GOOGLE_TOKEN_PATH` y reautorizar para incluir el scope `https://www.googleapis.com/auth/drive` |

## Logging & Tracing

Each request writes structured logs using `structlog`. Contextual fields include:

- `authentication` (OAuth/IMAP)
- `message_id`
- `attachments` count
- `validation_errors`
- `table_errors`
- `drive_folder_id`
- `drive_uploaded_files`
- `drive_upload_errors`
- `duration_seconds`
- `error`

Log file location is defined by `LOG_FILE_PATH` (defaults to `logs/email_service.log`).

## Future Extensions

- Authentication (JWT/API keys).
- Pagination on `/emails/search`.
- Webhook-like async processing.
- Integration with Google Drive and further services in upcoming project phases.
