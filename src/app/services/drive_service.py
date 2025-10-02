"""Servicio para interacción con Google Drive utilizando OAuth de usuario."""

import io
import os
import re
import pickle
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple, TYPE_CHECKING

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

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

    def list_folder_files(
        self,
        folder_id: str,
        *,
        mime_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Listar archivos dentro de una carpeta específica de Drive."""

        if not folder_id:
            raise ValueError("Se requiere el ID de la carpeta para listar archivos")

        self._ensure_service()

        query_parts = [f"'{folder_id}' in parents", "trashed = false"]
        if mime_types:
            mime_filters = " or ".join([f"mimeType = '{mime}'" for mime in mime_types])
            query_parts.append(f"({mime_filters})")

        query = " and ".join(query_parts)
        files_service = self._service.files()
        page_token = None
        files: List[Dict[str, Any]] = []

        while True:
            try:
                response = files_service.list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    spaces="drive",
                    pageToken=page_token,
                ).execute()
            except HttpError as exc:
                self.logger.error(
                    "❌ Error listando archivos en Drive",
                    folder_id=folder_id,
                    error=str(exc),
                )
                raise

            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        self.logger.info(
            "📄 Archivos listados en carpeta",
            folder_id=folder_id,
            total=len(files),
        )
        return files

    def download_file(self, file_id: str) -> bytes:
        """Descargar archivo binario desde Google Drive y devolver sus bytes."""

        if not file_id:
            raise ValueError("Se requiere el ID del archivo para descargarlo")

        self._ensure_service()
        request = self._service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        try:
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    self.logger.info(
                        "⬇️ Descargando archivo de Drive",
                        file_id=file_id,
                        progress=f"{int(status.progress() * 100)}%",
                    )
        except HttpError as exc:
            self.logger.error(
                "❌ Error descargando archivo de Drive",
                file_id=file_id,
                error=str(exc),
            )
            raise

        self.logger.info(
            "✅ Archivo descargado correctamente",
            file_id=file_id,
            bytes=buffer.getbuffer().nbytes,
        )
        return buffer.getvalue()

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
        logger = structlog.get_logger()
        sanitized_original = DriveService._sanitize_filename(original_name)
        sanitized_original = DriveService._strip_leading_gender_prefix(sanitized_original)
        original_base, original_ext = os.path.splitext(sanitized_original)
        sanitized_district = DriveService._sanitize_component(distrito)

        components = [fecha_generacion]
        if sanitized_district:
            components.append(DriveService._strip_single_letter_component_prefix(sanitized_district))
        if original_base:
            components.append(DriveService._strip_single_letter_component_prefix(original_base))

        components = [component for component in components if component]

        if not components:
            components.append("archivo")

        combined = "_".join(components)
        if original_ext:
            combined = f"{combined}{original_ext}"

        combined = DriveService._remove_duplicate_tokens(combined)
        combined = DriveService._strip_leading_gender_prefix(combined)

        logger.info(
            "📁 Nombre de archivo normalizado para Drive",
            fecha_generacion=fecha_generacion,
            distrito_original=distrito,
            distrito_normalizado=sanitized_district,
            nombre_original=original_name,
            nombre_sanitizado=sanitized_original,
            nombre_final=combined,
        )
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
    def _strip_leading_gender_prefix(cls, filename: str) -> str:
        """Eliminar prefijos tipo `F_` o `M_` cuando forman parte del nombre original."""

        if not filename:
            return filename

        base, ext = os.path.splitext(filename)
        tokens = base.split("_")
        if len(tokens) <= 1:
            return filename

        index = 0
        while index < len(tokens) and len(tokens[index]) == 1 and tokens[index].isalpha():
            index += 1

        if index == 0 or index >= len(tokens):
            return filename

        remainder_tokens = tokens[index:]
        remainder = "_".join(remainder_tokens).strip("_")
        if not remainder:
            return filename

        cleaned = cls._enforce_max_length(f"{remainder}{ext}")
        return cleaned

    @classmethod
    def _strip_single_letter_component_prefix(cls, value: str) -> str:
        if not value:
            return value

        tokens = value.split("_")
        while tokens and len(tokens[0]) == 1 and tokens[0].isalpha():
            tokens = tokens[1:]
        if not tokens:
            return ""
        remainder = "_".join(tokens).strip("_")
        return remainder or value

    @classmethod
    def _sanitize_component(cls, value: Optional[str]) -> str:
        if not value:
            return ""
        sanitized = re.sub(r'[<>:"/\\|?*.]', "_", value)
        sanitized = re.sub(r"\s+", "_", sanitized)
        sanitized = sanitized.strip("_")
        sanitized = re.sub(r"__+", "_", sanitized)
        sanitized = sanitized.strip("_")
        sanitized = cls._strip_single_letter_component_prefix(sanitized)
        if not sanitized:
            return ""
        return cls._enforce_max_length(sanitized)

    @staticmethod
    def _remove_duplicate_tokens(filename: str) -> str:
        base, ext = os.path.splitext(filename)
        tokens = base.split("_")
        seen = set()
        ordered_tokens: List[str] = []

        for token in tokens:
            normalized = re.sub(r"[^a-z0-9]", "", token.lower())
            if not normalized:
                ordered_tokens.append(token)
                continue
            if len(normalized) == 1 and normalized.isalpha():
                # Omit prefijos como "F" que no aportan información a nombres finales.
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            ordered_tokens.append(token)

        cleaned_base = "_".join(filter(None, ordered_tokens)) or base
        return f"{cleaned_base}{ext}"

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
                        candidate = value.strip()
                        cleaned_candidate = DriveService._clean_district_candidate(candidate)
                        logger = structlog.get_logger()
                        logger.info(
                            "📋 Evaluando distrito detectado en tabla",
                            raw_candidate=candidate,
                            cleaned_candidate=cleaned_candidate,
                        )
                        if cleaned_candidate and re.search(r"\d", cleaned_candidate):
                            return cleaned_candidate
        return None

    @staticmethod
    def _clean_district_candidate(value: str) -> str:
        """Depurar valores detectados en tablas (p. ej. `F District 10C`)."""

        if not value:
            return ""

        cleaned = value.strip()

        # Eliminar prefijos de una sola letra seguidos de separadores (F District, H-District, etc.).
        while True:
            match = re.match(r"^[A-Za-z](?:[\s_\-:]+)(.+)$", cleaned)
            if not match:
                break
            cleaned = match.group(1).strip()

        if cleaned != value:
            logger = structlog.get_logger()
            logger.info(
                "🔍 Normalizando valor de distrito",
                raw_value=value,
                cleaned_value=cleaned,
            )

        return cleaned

    def close(self):
        """Liberar el cliente de Drive."""
        self._service = None
        self.logger.info("🔌 Cliente de Google Drive liberado")
