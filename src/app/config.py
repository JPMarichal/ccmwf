"""
Configuración de la aplicación Email Service
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings
import structlog

APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR.parent
PROJECT_ROOT = SRC_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Gmail Configuration - OAuth 2.0 (primario)
    gmail_user: str
    google_application_credentials: Optional[str] = None
    google_token_path: Optional[str] = None
    google_project_id: Optional[str] = None

    # Fallback IMAP Configuration (si no hay OAuth)
    gmail_app_password: Optional[str] = None
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993

    # Search Configuration
    email_subject_pattern: str = "Misioneros que llegan"
    processed_label: str = "misioneros-procesados"
    email_table_required_columns: List[str] = Field(default_factory=lambda: ["Distrito", "Zona"])

    # Application Configuration
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Google Drive Configuration (para futuras fases)
    google_drive_credentials_path: Optional[str] = None
    google_drive_token_path: Optional[str] = None
    google_drive_attachments_folder_id: Optional[str] = None

    # Database Configuration (para futuras fases)
    database_url: Optional[str] = None

    # Security
    secret_key: str = "change-this-secret-key-in-production"

    # Logging
    log_file_path: str = str(PROJECT_ROOT / "logs" / "email_service.log")
    log_max_file_size: int = 100  # MB
    log_backup_count: int = 5

    # Development
    debug: bool = True
    enable_swagger: bool = True

    class Config:
        env_file = str(ENV_PATH)
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignorar campos extra del .env

    @field_validator('log_level')
    def validate_log_level(cls, v: str) -> str:
        """Validar nivel de logging"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()

    @field_validator('app_env')
    def validate_app_env(cls, v: str) -> str:
        """Validar entorno de aplicación"""
        valid_envs = ['development', 'staging', 'production']
        if v.lower() not in valid_envs:
            raise ValueError(f'App env must be one of: {valid_envs}')
        return v.lower()


def get_settings() -> Settings:
    """Obtener configuración de la aplicación"""
    return Settings()


def configure_logging(settings: Settings):
    """Configurar logging estructurado"""
    import logging.config

    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": settings.log_file_path,
                "maxBytes": settings.log_max_file_size * 1024 * 1024,
                "backupCount": settings.log_backup_count,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": settings.log_level,
        },
    }

    logging.config.dictConfig(log_config)

    # Configurar structlog
    structlog.contextvars.clear_contextvars()
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
