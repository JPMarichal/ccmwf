"""
Email Service - Fase 1 del Proyecto CCM
Servicio para recepción y procesamiento de correos de misioneros
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from app.config import configure_logging, get_settings
from app.logging_utils import ensure_log_context, bind_log_context
from app.services.email_service import EmailService
from app.services.drive_service import DriveService
from app.services.database_sync_service import DatabaseSyncService

# Configurar logger
logger = structlog.get_logger("app").bind(servicio="app")

# Estado global de la aplicación
email_service = None
drive_service = None
database_sync_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configuración del ciclo de vida de la aplicación"""
    global email_service, drive_service, database_sync_service

    settings = get_settings()
    configure_logging(settings)

    startup_context = ensure_log_context(etapa="startup")
    startup_logger = bind_log_context(logger, startup_context)

    startup_logger.info("Iniciando Email Service")
    drive_service = DriveService(settings)
    email_service = EmailService(settings, drive_service=drive_service)
    database_sync_service = DatabaseSyncService(settings, drive_service)

    # Test de conexión durante startup
    try:
        await email_service.test_connection()
        startup_logger.info("Conexión IMAP establecida correctamente")
    except Exception as e:
        startup_logger.error("Error en conexión IMAP durante startup", error=str(e))
        # No fallar el startup, solo loguear el error

    yield

    # Shutdown
    shutdown_logger = bind_log_context(logger, ensure_log_context(etapa="shutdown"))
    shutdown_logger.info("Cerrando Email Service")
    if email_service:
        await email_service.close()
    if drive_service:
        drive_service.close()

# Crear aplicación FastAPI
app = FastAPI(
    title="CCM Email Service",
    description="Servicio para recepción y procesamiento de correos de misioneros",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar apropiadamente para producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DatabaseSyncRequest(BaseModel):
    fecha_generacion: str = Field(..., description="Fecha de generación en formato YYYYMMDD")
    drive_folder_id: str = Field(..., description="ID de la carpeta en Google Drive donde están los XLSX")
    force: bool = Field(False, description="Forzar reproceso incluso si hay estado previo")


class DatabaseSyncResponse(BaseModel):
    success: bool
    report: dict

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "CCM Email Service - Fase 1",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "email-service",
        "version": "1.0.0"
    }

@app.post("/process-emails")
async def process_emails():
    """Procesar correos de misioneros"""
    try:
        if not email_service:
            raise HTTPException(status_code=500, detail="Email service no inicializado")

        result = await email_service.process_incoming_emails()

        return {
            "success": True,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        bind_log_context(
            logger,
            ensure_log_context(etapa="process_emails"),
        ).error("Error procesando emails", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error procesando emails: {str(e)}")

@app.get("/emails/search")
async def search_emails(query: str = None):
    """Buscar correos (para testing)"""
    try:
        if not email_service:
            raise HTTPException(status_code=500, detail="Email service no inicializado")

        emails = await email_service.search_emails(query)

        return {
            "success": True,
            "emails": emails
        }

    except HTTPException:
        raise
    except Exception as e:
        bind_log_context(
            logger,
            ensure_log_context(etapa="search_emails"),
        ).error("Error buscando emails", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error buscando emails: {str(e)}")


@app.post("/extraccion_generacion", response_model=DatabaseSyncResponse)
def extraccion_generacion(payload: DatabaseSyncRequest):
    """Sincronizar una generación desde Google Drive hacia MySQL."""

    if not database_sync_service:
        raise HTTPException(status_code=500, detail="Database sync service no inicializado")

    context = ensure_log_context(
        etapa="extraccion_generacion",
        fecha_generacion=payload.fecha_generacion,
        drive_folder_id=payload.drive_folder_id,
    )
    endpoint_logger = bind_log_context(logger, context)

    try:
        report = database_sync_service.sync_generation(
            fecha_generacion=payload.fecha_generacion,
            drive_folder_id=payload.drive_folder_id,
            force=payload.force,
        )
    except Exception as exc:  # noqa: BLE001
        endpoint_logger.error(
            "Error en extracción de generación",
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"Error procesando extracción: {exc}")

    endpoint_logger.info(
        "Extracción de generación completada",
        force=payload.force,
    )
    return DatabaseSyncResponse(success=True, report=report.to_dict())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
