"""
Modelos de datos para el Email Service
"""

from datetime import date, datetime
from uuid import uuid4
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
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


class ReportDatasetMetadata(BaseModel):
    """Metadatos que describen un dataset preparado para reportes."""

    dataset_id: str
    generated_at: datetime
    record_count: int
    branch_id: Optional[int] = None
    duration_ms: Optional[int] = None
    cache_hit: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)
    message_id: str = Field(default_factory=lambda: uuid4().hex)

    @validator('record_count')
    def validate_record_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError('record_count must be non-negative')
        return value


class ReportDatasetResult(BaseModel):
    """Resultado genérico de un dataset listo para consumo."""

    metadata: ReportDatasetMetadata
    data: List[Any]


class BranchSummary(BaseModel):
    """Resumen por rama/distrito para reportes ejecutivos."""

    branch_id: int
    district: str
    first_generation_date: Optional[date] = None
    first_ccm_arrival: Optional[date] = None
    last_ccm_departure: Optional[date] = None
    total_missionaries: int
    total_companionships: Optional[int] = None
    elders_count: Optional[int] = None
    sisters_count: Optional[int] = None


class DistrictKPI(BaseModel):
    """Indicadores clave de desempeño por distrito."""

    branch_id: int
    district: str
    metric: str
    value: float
    unit: Optional[str] = None
    generated_for_week: Optional[date] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class UpcomingArrival(BaseModel):
    """Detalle de próximos ingresos de misioneros al CCM."""

    district: str
    rdistrict: Optional[str] = None
    branch_id: Optional[int] = None
    arrival_date: date
    departure_date: Optional[date] = None
    missionaries_count: int
    duration_weeks: Optional[int] = None
    status: Optional[str] = None


class UpcomingBirthday(BaseModel):
    """Registro de cumpleaños próximos para notificaciones y correos."""

    missionary_id: Optional[int] = None
    branch_id: Optional[int] = None
    district: Optional[str] = None
    treatment: Optional[str] = None
    missionary_name: str
    birthday: date
    age_turning: Optional[int] = None
    status: Optional[str] = None
    email_missionary: Optional[str] = None
    email_personal: Optional[str] = None
    three_weeks_program: Optional[bool] = None
