"""Servicio para interacción con Google Drive."""

import io
import os
from typing import Dict, Optional

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.config import Settings


class DriveService:
    """Encapsula operaciones comunes contra Google Drive."""

    SCOPES = [
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger()
        self._service = None

    def _ensure_service(self):
        """Inicializar el cliente de Drive una sola vez."""
        if self._service is not None:
            return

        credentials_path = self.settings.google_drive_credentials_path
        if not credentials_path:
            raise ValueError("No se definió GOOGLE_DRIVE_CREDENTIALS_PATH en la configuración")

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"No se encontró el archivo de credenciales de Drive: {credentials_path}")

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=self.SCOPES,
        )

        self._service = build("drive", "v3", credentials=credentials)
        self.logger.info("✅ Cliente de Google Drive inicializado correctamente")

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

    @staticmethod
    def format_filename(
        fecha_generacion: Optional[str],
        distrito: Optional[str],
        original_name: str,
    ) -> str:
        """Generar nombre consistente YYYYMMDD_Distrito_original.ext."""
        sanitized = original_name.replace(" ", "_")
        parts = [
            part for part in [fecha_generacion, (distrito or "").replace(" ", ""), sanitized]
            if part
        ]
        return "_".join(parts) if parts else sanitized

    def close(self):
        """Liberar el cliente de Drive."""
        self._service = None
        self.logger.info("🔌 Cliente de Google Drive liberado")
