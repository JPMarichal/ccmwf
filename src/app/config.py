"""
Configuración de la aplicación Email Service
"""

import os
from pathlib import Path
from typing import Optional, List, Any
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

    # Google Drive Configuration (para nuevas fases)
    google_drive_credentials_path: Optional[str] = None
    google_drive_token_path: Optional[str] = None
    google_drive_attachments_folder_id: Optional[str] = None
    generations_backup_folder_id: Optional[str] = None

    # Database Configuration (para futuras fases)
    database_url: Optional[str] = None
    db_host: Optional[str] = None
    db_port: int = 3306
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = None

    # Security
    secret_key: str = "change-this-secret-key-in-production"

    # Logging
    log_file_path: str = str(PROJECT_ROOT / "logs" / "email_service.log")
    log_max_file_size: int = 10  # MB (usado para validaciones puntuales)
    log_backup_count: int = 30  # Equivalente a 30 días de retención cuando se rota diariamente

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

    def model_post_init(self, __context: Any) -> None:  # noqa: D401
        """Normaliza rutas relativas para credenciales después de cargar el .env."""
        credential_fields = [
            'google_application_credentials',
            'google_token_path',
            'google_drive_credentials_path',
            'google_drive_token_path',
            'google_sheets_credentials_path',
            'log_file_path',
        ]

        for field_name in credential_fields:
            value = getattr(self, field_name, None)
            if not value:
                continue

            path = Path(value)
            if not path.is_absolute():
                path = PROJECT_ROOT / path

            object.__setattr__(self, field_name, str(path))


def get_settings() -> Settings:
    """Obtener configuración de la aplicación"""
    return Settings()


def configure_logging(settings: Settings):
    """Configurar logging estructurado con separación por servicio."""
    import logging.config

    log_path = Path(settings.log_file_path)
    log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    service_log_paths = {
        "app": log_dir / "application.log",
        "email_service": log_path,
        "drive_service": log_dir / "drive_service.log",
        "database_sync": log_dir / "database_sync.log",
    }

    for path in service_log_paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    structlog.contextvars.clear_contextvars()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", key="timestamp_utc"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter(
                structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter_name = "structlog_json"
    foreign_pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", key="timestamp_utc"),
    ]

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            formatter_name: {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": foreign_pre_chain,
            },
        },
        "filters": {
            "app_filter": {"()": "logging.Filter", "name": "app"},
            "email_service_filter": {"()": "logging.Filter", "name": "email_service"},
            "drive_service_filter": {"()": "logging.Filter", "name": "drive_service"},
            "database_sync_filter": {"()": "logging.Filter", "name": "database_sync"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
                "stream": "ext://sys.stdout",
            },
            "app_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": formatter_name,
                "filename": str(service_log_paths["app"]),
                "when": "midnight",
                "backupCount": settings.log_backup_count,
                "encoding": "utf-8",
                "utc": True,
                "filters": ["app_filter"],
            },
            "email_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": formatter_name,
                "filename": str(service_log_paths["email_service"]),
                "when": "midnight",
                "backupCount": settings.log_backup_count,
                "encoding": "utf-8",
                "utc": True,
                "filters": ["email_service_filter"],
            },
            "drive_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": formatter_name,
                "filename": str(service_log_paths["drive_service"]),
                "when": "midnight",
                "backupCount": settings.log_backup_count,
                "encoding": "utf-8",
                "utc": True,
                "filters": ["drive_service_filter"],
            },
            "database_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": formatter_name,
                "filename": str(service_log_paths["database_sync"]),
                "when": "midnight",
                "backupCount": settings.log_backup_count,
                "encoding": "utf-8",
                "utc": True,
                "filters": ["database_sync_filter"],
            },
        },
        "loggers": {
            "app": {
                "handlers": ["app_file"],
                "level": settings.log_level,
                "propagate": True,
            },
            "email_service": {
                "handlers": ["email_file"],
                "level": settings.log_level,
                "propagate": True,
            },
            "drive_service": {
                "handlers": ["drive_file"],
                "level": settings.log_level,
                "propagate": True,
            },
            "database_sync": {
                "handlers": ["database_file"],
                "level": settings.log_level,
                "propagate": True,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": settings.log_level,
        },
    }

    logging.config.dictConfig(log_config)
