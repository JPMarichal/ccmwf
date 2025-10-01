# Guía de Desarrollo - CCM Email Service

## Requisitos Previos

- Python 3.11+ (recomendado Python 3.13 según entorno actual).
- Acceso a una cuenta de Google con permisos para habilitar Gmail API.
- Docker y Docker Compose (para ejecución en contenedores).
- Git.

## Estructura del Proyecto

```
ccmwf/
├── docs/                      # Documentación de apoyo
├── src/
│   ├── app/
│   │   ├── main.py            # Entradas FastAPI
│   │   ├── config.py          # Configuración vía Pydantic Settings
│   │   ├── models.py          # Modelos Pydantic
│   │   └── services/
│   │       ├── email_service.py
│   │       ├── gmail_oauth_service.py
│   │       └── database_sync_service.py
│   ├── tests/                 # Tests unitarios e integración
│   ├── docker/                # Dockerfile y docker-compose.yml
│   └── requirements.txt
├── .env (no versionado)
└── README.md
```

## Configuración Inicial

1. Crear entorno virtual y activar (ver instrucciones en `README.md`).
2. Instalar dependencias: `pip install -r src/requirements.txt`.
3. Copiar `.env.example` a `.env` en la raíz y completar variables (ver `docs/environment_variables.md`).
4. Colocar `credentials.json` de Google en `src/credentials.json`.
5. Iniciar la app y completar el flow OAuth ejecutando `/process-emails` desde Swagger.

## Ejecución en Desarrollo

```bash
# Desde la carpeta src/
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger disponible en http://localhost:8000/docs
```

## Ejecutar con Docker

```bash
# Desde src/
docker-compose up --build
```

## Testing

```bash
# Tests unitarios
python -m pytest tests/test_email_service.py -q
python -m pytest tests/test_database_sync_service.py -q

# Tests de integración
python -m pytest tests/test_integration_flow.py -q

# Todos los tests con coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

**ℹ️ Nota**: Para los tests de Fase 4 se requiere ejecutar `pytest` con el directorio `src/` en el `PYTHONPATH`. Puedes exportarlo antes de correr pruebas:

```powershell
$env:PYTHONPATH="D:/myapps/ccmwf/src"
python -m pytest src/tests/test_database_sync_service.py -vv
```

## Flujo de Trabajo Recomendado

1. Crear rama para la feature.
2. Agregar/actualizar tests (unitarios e integración).
3. Ejecutar `pytest` antes de hacer commit.
4. Actualizar documentación relevante (`README.md`, `docs/`).
5. Abrir Pull Request con descripción de cambios y resultados de pruebas.

## Convenciones de Código

- Base PEP8, formateo con `black` (opcional) y `isort` para imports.
- Logging con `structlog`, sin imprimir directamente a stdout/stderr.
- Configuración centralizada en `Settings` (`app/config.py`).
- Preferir async/await para llamadas que interactúan con IO.

## Checklists Antes de Entregar

- Logs sin credenciales ni datos sensibles.
- Tests unitarios + integración pasando.
- Documentación actualizada (`docs/plan_fase1.md`, `docs/api_documentation.md`, `docs/environment_variables.md`).
- `.env` y credenciales fuera de control de versiones.

## Fase 4 - Sincronización MySQL (Resumen operativo)

- **Servicios clave**:
  - `DatabaseSyncService` (`app/services/database_sync_service.py`) controla la sincronización y mantiene tokens de continuación en `data/state/database_sync_state.json`.
  - `DriveService.list_folder_files()` y `DriveService.download_file()` facilitan la lectura de XLSX desde Google Drive.
- **Endpoint permanente**: `POST /extraccion_generacion` (ver `app/main.py`, documentado en `docs/api_documentation.md`).
- **Logs estructurados**: Todos los mensajes emiten claves `message_id`, `etapa`, `drive_folder_id`, `excel_file_id`, `records_processed`, `records_skipped`, `table_errors`, `error_code`.
- **Pruebas**: `tests/test_database_sync_service.py` cubre normalización y persistencia; utiliza mocks de Drive y SQLAlchemy.

**ℹ️ Flujo integrado**: Tras Fase 3, cuando el correo se marca como leído y los archivos se suben a Drive, se debe invocar `/extraccion_generacion` para persistir los datos en MySQL.

## Handoff: Pasos recomendados

1. **Verificar cobertura**: `python -m pytest tests/ --cov=app --cov-report=term-missing`. Tomar nota del porcentaje actual (objetivo ≥80 %).
2. **Revisar logs generados**: Abrir `logs/email_service.log` y confirmar entradas por cada correo procesado (`message_id`, `attachments_count`, `validation_errors`).
3. **Ejecución de pruebas clave**:
   - `python -m pytest tests/test_email_service.py -q`
   - `python -m pytest tests/test_integration_flow.py -q`
4. **Validar estructura de correos**: Asegurar que los campos `validation_errors` sean vacíos en correos válidos y contengan códigos (`subject_pattern_mismatch`, `attachments_missing`, etc.) cuando la estructura falle.
5. **Actualizar documentación**: Confirmar que `docs/api_documentation.md`, `docs/development_guide.md` y `docs/environment_variables.md` reflejen cualquier cambio de contratos o variables (Fase 4 ✅ documentada).
6. **Respaldo de configuraciones**: Guardar `.env`, `credentials.json` y `token.pickle` en ubicación segura (no versionada) antes de transferir.
7. **Checklist final**: Documentar en `docs/plan_fase1.md` el estado final (cobertura alcanzada, tareas pendientes y recomendaciones para la siguiente fase).

## Recursos Adicionales

- `docs/oauth_setup_guide.md`: Pasos para habilitar Gmail API y crear `credentials.json`.
- `docs/credentials_setup.md`: Guía rápida para credenciales locales.
- `docs/workflow.md`: Contexto de negocio y flujo detallado del CCM.

## Próximas Fases

- Integración con Google Drive (subida de archivos y creación de carpetas).
- Persistencia en base de datos MySQL.
- Notificaciones (Telegram, correo) y reportes automatizados.
