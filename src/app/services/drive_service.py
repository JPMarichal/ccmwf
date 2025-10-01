"""Servicio para interacción con Google Drive utilizando OAuth de usuario."""

import io
import os
import re
import pickle
from datetime import datetime
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.config import Settings

if TYPE_CHECKING:
    from app.models import EmailAttachment


class DriveService:
    """Encapsula operaciones comunes contra Google Drive usando credenciales OAuth de usuario."""

    SCOPES = [
        "https://www.googleapis.com/auth/drive",
    ]

    MAX_FILENAME_LENGTH = 100

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger()
        self._service = None
        self._oauth_credentials: Optional[Credentials] = None

    def _ensure_service(self):
        """Inicializar el cliente de Drive una sola vez."""
        if self._service is not None:
            return

        credentials = self._obtain_credentials()

        if not credentials:
            raise ValueError(
                "No se pudieron obtener credenciales OAuth para Google Drive. "
                "Ejecuta el flujo OAuth o comparte las credenciales desde GmailOAuthService."
            )

        self._service = build("drive", "v3", credentials=credentials)
        self._oauth_credentials = credentials
        self.logger.info("✅ Cliente de Google Drive inicializado correctamente")

    def set_oauth_credentials(self, creds: Credentials) -> None:
        """Recibir credenciales OAuth (por ejemplo, compartidas desde GmailOAuthService)."""

        if not creds:
            return

        self._oauth_credentials = creds
        self._service = None  # Forzar re-creación con las nuevas credenciales
        self.logger.info("🔐 Credenciales OAuth de Drive actualizadas desde Gmail")

    def _obtain_credentials(self) -> Optional[Credentials]:
        """Obtener credenciales OAuth usando el mismo flujo que Gmail (installed app)."""

        creds = self._oauth_credentials

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("⚠️ Error refrescando token de Drive", error=str(exc))
                creds = None

        if creds and creds.valid:
            return creds

        credentials_path = (
            self.settings.google_application_credentials
            or self.settings.google_drive_credentials_path
        )
        token_path = (
            self.settings.google_token_path
            or self.settings.google_drive_token_path
        )

        if token_path and os.path.exists(token_path):
            try:
                with open(token_path, "rb") as token_file:
                    creds = pickle.load(token_file)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("⚠️ No se pudo cargar token OAuth existente", error=str(exc))
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("⚠️ Error refrescando token OAuth", error=str(exc))
                creds = None

        if creds and creds.valid:
            return creds

        if not credentials_path or not os.path.exists(credentials_path):
            self.logger.error(
                "❌ No se encontró archivo de credenciales para iniciar flujo OAuth de Drive",
                credentials_path=credentials_path,
            )
            return None

        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            self.SCOPES,
        )

        creds = flow.run_local_server(port=0, prompt="consent", authorization_prompt_message="")

        if token_path:
            try:
                with open(token_path, "wb") as token_file:
                    pickle.dump(creds, token_file)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("⚠️ No se pudo guardar token OAuth", error=str(exc))

        return creds

    def ensure_generation_folder(self, fecha_generacion: str) -> str:
        """Crear (si es necesario) y devolver la carpeta para una generación específica."""
        if not fecha_generacion:
            raise ValueError("La fecha de generación es obligatoria para crear la carpeta")

        parent_folder_id = self.settings.google_drive_attachments_folder_id
        if not parent_folder_id:
            raise ValueError("No se configuró GOOGLE_DRIVE_ATTACHMENTS_FOLDER_ID")

        self._ensure_service()

        safe_name = fecha_generacion.replace("'", "\'")
        query = (
            f"name = '{safe_name}' "
            "and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_folder_id}' in parents and trashed = false"
        )

        files_service = self._service.files()

        try:
            response = files_service.list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
            ).execute()
        except HttpError as exc:
            self.logger.error("❌ Error consultando carpeta de generación", error=str(exc), fecha=fecha_generacion)
            raise

        folders = response.get("files", []) if response else []
        if folders:
            folder_id = folders[0]["id"]
            self.logger.info(
                "📁 Carpeta de generación existente reutilizada",
                fecha_generacion=fecha_generacion,
                folder_id=folder_id,
            )
            return folder_id

        metadata = {
            "name": fecha_generacion,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }

        try:
            folder = files_service.create(body=metadata, fields="id, name").execute()
        except HttpError as exc:
            self.logger.error("❌ Error creando carpeta de generación", error=str(exc), fecha=fecha_generacion)
            raise

        folder_id = folder["id"]
        self.logger.info(
            "📁 Carpeta de generación creada",
            fecha_generacion=fecha_generacion,
            folder_id=folder_id,
        )
        return folder_id

    def upload_file(
        self,
        filename: str,
        mime_type: str,
        data: bytes,
        parent_folder_id: str,
    ) -> Dict[str, str]:
        """Subir un archivo binario a Google Drive."""
        if not filename:
            raise ValueError("El nombre del archivo es obligatorio")
        if not parent_folder_id:
            raise ValueError("Se requiere el ID de la carpeta destino")

        self._ensure_service()

        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=True)
        metadata = {
            "name": filename,
            "parents": [parent_folder_id],
        }

        files_service = self._service.files()

        try:
            drive_file = files_service.create(
                body=metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink",
            ).execute()
        except HttpError as exc:
            self.logger.error(
                "❌ Error subiendo archivo a Drive",
                error=str(exc),
                filename=filename,
                parent_folder_id=parent_folder_id,
            )
            raise

        self.logger.info(
            "✅ Archivo cargado en Drive",
            filename=filename,
            file_id=drive_file.get("id"),
            parent_folder_id=parent_folder_id,
        )
        return drive_file

    def upload_attachments(
        self,
        fecha_generacion: str,
        attachments: List["EmailAttachment"],
        distrito: Optional[str] = None,
    ) -> Tuple[Optional[str], List[Dict[str, str]], List[Dict[str, str]]]:
        """Subir múltiples attachments y devolver resultados."""

        uploaded: List[Dict[str, str]] = []
        errors: List[Dict[str, str]] = []

        if not attachments:
            return None, uploaded, errors

        try:
            folder_id = self.ensure_generation_folder(fecha_generacion)
        except Exception as exc:
            errors.append({
                "code": "drive_folder_missing",
                "message": str(exc),
            })
            return None, uploaded, errors

        for attachment in attachments:
            if not getattr(attachment, "data", None):
                errors.append({
                    "code": "drive_attachment_without_data",
                    "filename": getattr(attachment, "filename", ""),
                    "message": "Attachment sin datos binarios",
                })
                continue

            drive_filename = self.format_filename(
                fecha_generacion,
                distrito,
                getattr(attachment, "filename", "archivo_sin_nombre"),
            )

            safe_filename = self._generate_unique_filename(folder_id, drive_filename)
            if safe_filename != drive_filename:
                self.logger.info(
                    "ℹ️ Nombre de archivo ajustado por duplicado",
                    original=drive_filename,
                    ajustado=safe_filename,
                    fecha_generacion=fecha_generacion,
                )

            mime_type = getattr(attachment, "content_type", None) or "application/octet-stream"

            try:
                drive_file = self.upload_file(
                    filename=safe_filename,
                    mime_type=mime_type,
                    data=attachment.data,
                    parent_folder_id=folder_id,
                )
                uploaded.append({
                    "id": drive_file.get("id"),
                    "name": drive_file.get("name"),
                    "webViewLink": drive_file.get("webViewLink"),
                    "webContentLink": drive_file.get("webContentLink"),
                })
            except Exception as exc:  # noqa: BLE001
                errors.append({
                    "code": "drive_upload_failed",
                    "filename": getattr(attachment, "filename", ""),
                    "message": str(exc),
                })

        return folder_id, uploaded, errors

    @staticmethod
    def format_filename(
        fecha_generacion: Optional[str],
        distrito: Optional[str],
        original_name: str,
    ) -> str:
        """Generar nombre consistente YYYYMMDD_Distrito_original.ext."""
        sanitized_original = DriveService._sanitize_filename(original_name)
        sanitized_district = DriveService._sanitize_component(distrito)

        parts = [
            part for part in [fecha_generacion, sanitized_district, sanitized_original]
            if part
        ]
        combined = "_".join(parts) if parts else sanitized_original
        return DriveService._enforce_max_length(combined)

    @classmethod
    def _sanitize_filename(cls, original_name: str) -> str:
        value = original_name or "archivo"
        value = re.sub(r'[<>:"/\\|?*]', "_", value)
        value = re.sub(r"\s+", "_", value)
        value = value.strip("_") or "archivo"
        value = re.sub(r"__+", "_", value)
        return cls._enforce_max_length(value)

    @classmethod
    def _sanitize_component(cls, value: Optional[str]) -> str:
        if not value:
            return ""
        sanitized = re.sub(r'[<>:"/\\|?*.]', "_", value)
        sanitized = re.sub(r"\s+", "_", sanitized)
        sanitized = sanitized.strip("_")
        sanitized = re.sub(r"__+", "_", sanitized)
        return cls._enforce_max_length(sanitized)

    @classmethod
    def _enforce_max_length(cls, filename: str) -> str:
        if len(filename) <= cls.MAX_FILENAME_LENGTH:
            return filename

        base, ext = os.path.splitext(filename)
        if not ext:
            return filename[:cls.MAX_FILENAME_LENGTH]

        allowed_base = max(1, cls.MAX_FILENAME_LENGTH - len(ext))
        return f"{base[:allowed_base]}{ext}"

    def _generate_unique_filename(self, folder_id: str, desired_name: str) -> str:
        """Evitar colisiones reutilizando convención del wrapper original."""

        self._ensure_service()
        files_service = self._service.files()

        try:
            response = files_service.list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields="files(name)",
                pageSize=1000,
            ).execute()
        except HttpError as exc:
            self.logger.error(
                "❌ Error obteniendo nombres existentes en carpeta",
                error=str(exc),
                folder_id=folder_id,
            )
            raise

        existing_names = {
            file.get("name")
            for file in (response or {}).get("files", [])
            if file.get("name")
        }

        if desired_name not in existing_names:
            return desired_name

        base, ext = os.path.splitext(desired_name)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        counter = 0

        while True:
            suffix = f"_{timestamp}" if counter == 0 else f"_{timestamp}_{counter}"
            max_base_len = max(1, self.MAX_FILENAME_LENGTH - len(ext) - len(suffix))
            trimmed_base = base[:max_base_len]
            candidate = f"{trimmed_base}{suffix}{ext}"
            candidate = self._enforce_max_length(candidate)

            if candidate not in existing_names:
                return candidate

            counter += 1

    @staticmethod
    def guess_primary_district(parsed_table: Optional[Dict[str, object]]) -> Optional[str]:
        """Inferir el distrito primario desde la tabla parseada."""

        if not parsed_table:
            return None

        rows = parsed_table.get("rows") if isinstance(parsed_table, dict) else None
        if not rows:
            return None

        for row in rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if "distrito" in key.lower():
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        return None

    def close(self):
        """Liberar el cliente de Drive."""
        self._service = None
        self.logger.info("🔌 Cliente de Google Drive liberado")
