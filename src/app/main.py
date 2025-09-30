"""
Email Service - Fase 1 del Proyecto CCM
Servicio para recepción y procesamiento de correos de misioneros
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import structlog
from contextlib import asynccontextmanager

from app.config import get_settings
from app.services.email_service import EmailService
from app.services.drive_service import DriveService

# Configurar logger
logger = structlog.get_logger()

# Estado global de la aplicación
email_service = None
drive_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configuración del ciclo de vida de la aplicación"""
    global email_service, drive_service

    # Startup
    logger.info("🚀 Iniciando Email Service...")

    settings = get_settings()
    drive_service = DriveService(settings)
    email_service = EmailService(settings, drive_service=drive_service)

    # Test de conexión durante startup
    try:
        await email_service.test_connection()
        logger.info("✅ Conexión IMAP establecida correctamente")
    except Exception as e:
        logger.error("❌ Error en conexión IMAP durante startup", error=str(e))
        # No fallar el startup, solo loguear el error

    yield

    # Shutdown
    logger.info("🛑 Cerrando Email Service...")
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
        logger.error("Error procesando emails", error=str(e))
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
        logger.error("Error buscando emails", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error buscando emails: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
