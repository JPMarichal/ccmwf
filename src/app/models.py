"""
Modelos de datos para el Email Service
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
from enum import Enum


class EmailStatus(str, Enum):
    """Estados posibles de un email"""
    UNREAD = "unread"
    READ = "read"
    PROCESSED = "processed"
    ERROR = "error"


class EmailAttachment(BaseModel):
    """Modelo para archivos adjuntos de email"""
    filename: str
    size: int  # en bytes
    content_type: Optional[str] = None
    data: Optional[bytes] = None  # Base64 encoded para API

    class Config:
        arbitrary_types_allowed = True


class EmailMessage(BaseModel):
    """Modelo para mensajes de email"""
    message_id: str
    subject: str
    sender: EmailStr
    date: datetime
    body: str
    status: EmailStatus = EmailStatus.UNREAD
    attachments: List[EmailAttachment] = []
    thread_id: Optional[str] = None
    labels: List[str] = []

    @validator('body')
    def clean_body(cls, v):
        """Limpiar y validar el cuerpo del mensaje"""
        if len(v) > 50000:  # Limitar tamaño
            return v[:50000] + "... [truncado]"
        return v


class ProcessingResult(BaseModel):
    """Resultado del procesamiento de emails"""
    success: bool
    processed: int
    errors: int
    details: List[Dict[str, Any]] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class EmailSearchQuery(BaseModel):
    """Query para búsqueda de emails"""
    query: Optional[str] = None
    limit: int = 50
    status: Optional[EmailStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class EmailServiceStatus(BaseModel):
    """Estado del servicio de email"""
    status: str  # "healthy", "degraded", "unhealthy"
    imap_connected: bool
    last_check: datetime
    version: str = "1.0.0"
    uptime_seconds: Optional[int] = None
