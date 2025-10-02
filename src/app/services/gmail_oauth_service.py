"""
Servicio de Gmail con OAuth 2.0 - Reemplaza IMAP para cuentas sin contraseña
"""

import os
import pickle
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import structlog

# Google API Libraries
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import Settings
from app.logging_utils import ensure_log_context, bind_log_context
from app.models import EmailMessage, EmailAttachment, ProcessingResult
from app.services.validators import validate_email_structure, validate_table_structure
from app.services.email_html_parser import extract_primary_table
from app.services.email_content_utils import (
    extract_fecha_generacion,
    collect_table_texts,
)
from app.services.drive_service import DriveService


class GmailOAuthService:
    """Servicio para Gmail usando OAuth 2.0"""

    # Scopes requeridos para Gmail API
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels',
        'https://www.googleapis.com/auth/drive',
    ]

    def __init__(self, settings: Settings, drive_service: Optional[DriveService] = None):
        self.settings = settings
        self.logger = structlog.get_logger("email_service").bind(
            servicio="email_service",
            componente="gmail_oauth",
        )
        self.credentials = None
        self.gmail_service = None
        self._authenticated = False
        self.drive_service = drive_service

    async def authenticate(self) -> bool:
        """Autenticar con Gmail usando OAuth 2.0"""
        context = ensure_log_context(etapa="gmail_oauth")
        logger = bind_log_context(self.logger, context)

        try:
            creds = None

            # Verificar si ya tenemos credenciales guardadas
            if os.path.exists(self.settings.google_token_path):
                with open(self.settings.google_token_path, 'rb') as token:
                    creds = pickle.load(token)

            # Si no hay credenciales válidas, hacer flow OAuth
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refrescando token de acceso")
                    creds.refresh(Request())
                else:
                    logger.info("Iniciando flow OAuth")
                    creds = await self._oauth_flow()

                # Guardar credenciales para futuras ejecuciones
                with open(self.settings.google_token_path, 'wb') as token:
                    pickle.dump(creds, token)

            self.credentials = creds
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            self._authenticated = True

            if self.drive_service:
                self.drive_service.set_oauth_credentials(creds)

            logger.info("Autenticación OAuth exitosa")
            return True

        except Exception as e:
            self._authenticated = False
            logger.error("Error en autenticación OAuth", error=str(e))
            return False

    async def _oauth_flow(self) -> Credentials:
        """Ejecutar flow OAuth 2.0"""
        logger = bind_log_context(self.logger, ensure_log_context(etapa="gmail_oauth"))

        try:
            # Verificar que existe el archivo de credenciales
            if not os.path.exists(self.settings.google_application_credentials):
                raise FileNotFoundError(
                    f"No se encontró archivo de credenciales: {self.settings.google_application_credentials}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                self.settings.google_application_credentials,
                self.SCOPES
            )

            # Para aplicaciones de servidor, usar flow sin navegador
            creds = flow.run_local_server(
                port=0,
                prompt="consent",
                authorization_prompt_message=""
            )

            return creds

        except Exception as e:
            logger.error("Error en flow OAuth", error=str(e))
            raise

    async def test_connection(self) -> bool:
        """Test de conexión a Gmail API"""
        logger = bind_log_context(self.logger, ensure_log_context(etapa="gmail_api"))

        try:
            await self.authenticate()

            if not self._authenticated:
                return False

            # Test simple: obtener perfil del usuario
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'unknown')

            logger.info("Conexión Gmail API exitosa", email_address=email_address)
            return True

        except Exception as e:
            logger.error("Error en test de conexión Gmail API", error=str(e))
            return False

    async def process_incoming_emails(self) -> ProcessingResult:
        """Procesar correos de misioneros usando Gmail API"""
        start_time = datetime.now()
        process_context = ensure_log_context(etapa="recepcion_correo")
        process_logger = bind_log_context(self.logger, process_context)

        try:
            await self.authenticate()

            if not self._authenticated:
                return ProcessingResult(
                    success=False,
                    processed=0,
                    errors=1,
                    details=[{"error": "No se pudo autenticar con Gmail API"}],
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            query = f'subject:"{self.settings.email_subject_pattern}" is:unread'

            try:
                results = self.gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=50,
                ).execute()
                messages = results.get('messages', [])

            except HttpError as exc:
                process_logger.error(
                    "Error buscando mensajes",
                    error_code=exc.resp.status if exc.resp else None,
                    error_details=str(exc),
                )
                return ProcessingResult(
                    success=False,
                    processed=0,
                    errors=1,
                    details=[{"error": f"Gmail API error: {exc}"}],
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            if not messages:
                process_logger.info("No se encontraron correos nuevos")
                return ProcessingResult(
                    success=True,
                    processed=0,
                    errors=0,
                    details=[],
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            process_logger = bind_log_context(
                process_logger,
                ensure_log_context(process_context, total=len(messages)),
            )
            process_logger.info("Procesando correos")

            results_list: List[Dict[str, Any]] = []
            processed_count = 0
            error_count = 0

            import asyncio

            for msg_data in messages:
                msg_id = msg_data.get('id')
                message_context = ensure_log_context(process_context, message_id=msg_id)
                message_logger = bind_log_context(self.logger, message_context)

                try:
                    message = self.gmail_service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full',
                    ).execute()

                    result = await self._process_single_message(
                        message,
                        msg_id,
                        base_context=message_context,
                    )
                    results_list.append(result)

                    if result['success']:
                        processed_count += 1
                    else:
                        error_count += 1

                except Exception as exc:  # noqa: BLE001
                    error_count += 1
                    message_logger.error("Error procesando mensaje individual", error=str(exc))
                    results_list.append({
                        'success': False,
                        'error': str(exc),
                        'message_id': msg_id,
                        'parsed_table': None,
                        'table_errors': ['processing_exception'],
                    })

                await asyncio.sleep(0.5)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            process_logger.info(
                "Procesamiento completado",
                processed=processed_count,
                errors=error_count,
                duration_seconds=duration,
            )

            return ProcessingResult(
                success=True,
                processed=processed_count,
                errors=error_count,
                details=results_list,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
            )

        except Exception as exc:  # noqa: BLE001
            end_time = datetime.now()
            process_logger.error("Error en procesamiento general", error=str(exc))

            return ProcessingResult(
                success=False,
                processed=0,
                errors=1,
                details=[{'error': str(exc)}],
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
            )

    async def _process_single_message(
        self,
        message: Dict[str, Any],
        msg_id: str,
        *,
        base_context: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Procesar un mensaje individual usando Gmail API"""
        message_context = ensure_log_context(base_context, etapa="recepcion_correo", message_id=msg_id)
        logger = bind_log_context(self.logger, message_context)

        try:
            headers = message['payload']['headers']
            subject = self._get_header_value(headers, 'Subject')
            sender = self._get_header_value(headers, 'From')
            date_str = self._get_header_value(headers, 'Date')

            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00').replace('+0000', '+00:00'))
            except Exception:  # noqa: BLE001
                date = datetime.now()

            body = self._get_message_body(message['payload'])
            html_body = self._get_html_body(message['payload'])

            parsed_table, parse_errors = extract_primary_table(html_body or "")
            table_texts = collect_table_texts(parsed_table)

            fecha_generacion = extract_fecha_generacion(
                logger,
                body,
                html_body,
                subject,
                table_texts,
            )

            attachments: List[EmailAttachment] = []
            if 'parts' in message['payload']:
                for part in self._get_all_parts(message['payload']):
                    if part.get('filename'):
                        attachment_id = (
                            part.get('body', {}).get('attachmentId')
                            if isinstance(part.get('body'), dict)
                            else None
                        )
                        if not attachment_id:
                            continue
                        attachment_data = self._get_attachment_data(msg_id, attachment_id)
                        if attachment_data:
                            attachments.append(EmailAttachment(
                                filename=part['filename'],
                                size=len(attachment_data),
                                content_type=part.get('mimeType', ''),
                                data=attachment_data,
                            ))

            await self._mark_message_processed(msg_id, base_context=message_context)

            is_valid, validation_errors = validate_email_structure(
                subject=subject,
                fecha_generacion=fecha_generacion,
                attachments=attachments,
                expected_subject_pattern=self.settings.email_subject_pattern,
            )

            table_errors = list(parse_errors)
            table_errors.extend(
                validate_table_structure(
                    parsed_table,
                    self.settings.email_table_required_columns,
                )
            )

            success = is_valid and not table_errors

            table_headers_count = len(parsed_table["headers"]) if parsed_table else 0
            table_rows_count = len(parsed_table["rows"]) if parsed_table else 0

            drive_folder_id: Optional[str] = None
            drive_uploaded_files: List[Dict[str, str]] = []
            drive_upload_errors: List[Dict[str, str]] = []

            if self.drive_service and attachments:
                if not fecha_generacion:
                    drive_upload_errors.append({
                        "code": "drive_missing_fecha_generacion",
                        "message": "No se pudo subir archivos porque falta la fecha de generación",
                    })
                else:
                    distrito = DriveService.guess_primary_district(parsed_table)
                    try:
                        drive_context = ensure_log_context(
                            message_context,
                            etapa="drive_upload",
                            drive_folder_id=drive_folder_id,
                        )
                        folder_id, uploaded, errors = self.drive_service.upload_attachments(
                            fecha_generacion,
                            attachments,
                            distrito,
                            log_context=drive_context,
                        )
                        drive_folder_id = folder_id
                        if uploaded:
                            drive_uploaded_files = uploaded
                        if errors:
                            drive_upload_errors.extend(errors)
                    except Exception as exc:  # noqa: BLE001
                        bind_log_context(logger, drive_context).error(
                            "Error subiendo attachments a Drive",
                            error=str(exc),
                        )
                        drive_upload_errors.append({
                            "code": "drive_upload_failed",
                            "message": str(exc),
                        })

            result = {
                'success': success,
                'message_id': msg_id,
                'subject': subject,
                'sender': sender,
                'date': date.isoformat(),
                'fecha_generacion': fecha_generacion,
                'attachments_count': len(attachments),
                'validation_errors': validation_errors,
                'parsed_table': parsed_table,
                'table_errors': table_errors,
                'body_preview': body[:200] + "..." if len(body) > 200 else body,
                'drive_folder_id': drive_folder_id,
                'drive_uploaded_files': drive_uploaded_files,
                'drive_upload_errors': drive_upload_errors,
            }

            if success:
                logger.info(
                    "Mensaje procesado correctamente",
                    subject=subject,
                    attachments=len(attachments),
                    table_headers=table_headers_count,
                    table_rows=table_rows_count,
                )
                if drive_uploaded_files:
                    bind_log_context(
                        logger,
                        ensure_log_context(message_context, etapa="drive_upload", drive_folder_id=drive_folder_id),
                    ).info(
                        "Archivos subidos a Drive",
                        files=len(drive_uploaded_files),
                    )
            else:
                logger.warning(
                    "Validación de estructura fallida",
                    errors=validation_errors,
                    table_errors=table_errors,
                    subject=subject,
                )

            if table_errors:
                logger.warning("Problemas al parsear tabla HTML", errors=table_errors)
            elif parsed_table:
                logger.info(
                    "Tabla HTML extraída",
                    headers=table_headers_count,
                    rows=table_rows_count,
                )

            if drive_upload_errors:
                bind_log_context(
                    logger,
                    ensure_log_context(message_context, etapa="drive_upload", drive_folder_id=drive_folder_id),
                ).warning("Errores al subir archivos a Drive", errors=drive_upload_errors)

            return result

        except Exception as exc:  # noqa: BLE001
            logger.error("Error procesando mensaje individual", error=str(exc))
            return {
                'success': False,
                'error': str(exc),
                'message_id': msg_id,
                'parsed_table': None,
                'table_errors': ['processing_exception'],
                'drive_folder_id': None,
                'drive_uploaded_files': [],
                'drive_upload_errors': [{'code': 'drive_upload_failed', 'message': str(exc)}],
            }

    def _get_header_value(self, headers: List[Dict], name: str) -> str:
        """Obtener valor de header específico"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ""

    def _get_message_body(self, payload: Dict) -> str:
        """Extraer cuerpo del mensaje"""
        body = ""

        if 'body' in payload and payload['body'].get('data'):
            # Cuerpo simple
            body_data = payload['body']['data']
            body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')

        elif 'parts' in payload:
            # Cuerpo multipart
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        part_data = part['body']['data']
                        body += base64.urlsafe_b64decode(part_data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    # Si no hay texto plano, usar HTML
                    if not body and 'data' in part['body']:
                        part_data = part['body']['data']
                        body += base64.urlsafe_b64decode(part_data).decode('utf-8', errors='ignore')

        return body.strip()

    def _get_html_body(self, payload: Dict) -> str:
        """Extraer cuerpo HTML del mensaje (concatenado)."""
        fragments: List[str] = []

        mime_type = payload.get('mimeType')
        body = payload.get('body', {})
        data = body.get('data') if isinstance(body, dict) else None

        if mime_type == 'text/html' and data:
            fragments.append(base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore'))

        for part in payload.get('parts', []) or []:
            html_part = self._get_html_body(part)
            if html_part:
                fragments.append(html_part)

        return "\n".join(fragment for fragment in fragments if fragment).strip()

    def _get_all_parts(self, payload: Dict) -> List[Dict]:
        """Obtener todas las partes del mensaje recursivamente"""
        parts = []

        if 'parts' in payload:
            for part in payload['parts']:
                parts.append(part)
                # Llamada recursiva para partes anidadas
                parts.extend(self._get_all_parts(part))

        return parts

    def _get_attachment_data(self, message_id: str, part_id: str) -> Optional[bytes]:
        """Obtener datos de attachment específico"""
        try:
            attachment = self.gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=part_id
            ).execute()

            return base64.urlsafe_b64decode(attachment['data'])

        except Exception as e:
            self.logger.error("Error obteniendo attachment",
                            message_id=message_id,
                            part_id=part_id,
                            error=str(e))
            return None

    async def _mark_message_processed(
        self,
        message_id: str,
        *,
        base_context: Optional[Dict[str, Any]] = None,
    ):
        """Marcar mensaje como procesado"""
        context = ensure_log_context(base_context, etapa="recepcion_correo", message_id=message_id)
        logger = bind_log_context(self.logger, context)

        try:
            # Marcar como leído
            self.gmail_service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            # Agregar etiqueta si existe
            if self.settings.processed_label:
                try:
                    # Crear etiqueta si no existe
                    label_result = self.gmail_service.users().labels().create(
                        userId='me',
                        body={'name': self.settings.processed_label}
                    ).execute()

                    label_id = label_result['id']

                    # Agregar etiqueta al mensaje
                    self.gmail_service.users().messages().modify(
                        userId='me',
                        id=message_id,
                        body={'addLabelIds': [label_id]}
                    ).execute()

                except HttpError as e:
                    # Etiqueta ya existe
                    if e.resp.status == 409:
                        # Obtener ID de etiqueta existente
                        labels = self.gmail_service.users().labels().list(userId='me').execute()
                        for label in labels['labels']:
                            if label['name'] == self.settings.processed_label:
                                label_id = label['id']
                                break

                        # Agregar etiqueta al mensaje
                        self.gmail_service.users().messages().modify(
                            userId='me',
                            id=message_id,
                            body={'addLabelIds': [label_id]}
                        ).execute()
                    else:
                        raise

            logger.info("Mensaje marcado como procesado")

        except Exception as e:
            logger.error("Error marcando mensaje como procesado", error=str(e))

    async def search_emails(self, query: Optional[str] = None) -> List[Dict]:
        """Buscar emails usando Gmail API (para testing)"""
        search_logger = bind_log_context(self.logger, ensure_log_context(etapa="gmail_search"))

        try:
            await self.authenticate()

            if not self._authenticated:
                return []

            search_query = query or f'subject:"{self.settings.email_subject_pattern}"'

            try:
                results = self.gmail_service.users().messages().list(
                    userId='me',
                    q=search_query,
                    maxResults=10
                ).execute()

                messages = results.get('messages', [])

                emails = []
                for msg_data in messages:
                    try:
                        msg_id = msg_data['id']

                        # Obtener headers básicos
                        message = self.gmail_service.users().messages().get(
                            userId='me',
                            id=msg_id,
                            format='minimal'
                        ).execute()

                        headers = message['payload']['headers']
                        subject = self._get_header_value(headers, 'Subject')
                        sender = self._get_header_value(headers, 'From')
                        date_str = self._get_header_value(headers, 'Date')

                        emails.append({
                            'id': msg_id,
                            'subject': subject,
                            'sender': sender,
                            'date': date_str,
                            'has_attachments': len(message.get('payload', {}).get('parts', [])) > 1
                        })

                    except Exception as e:
                        bind_log_context(
                            search_logger,
                            ensure_log_context(etapa="gmail_search", message_id=msg_id),
                        ).error("Error procesando email en búsqueda", error=str(e))

                return emails

            except HttpError as e:
                search_logger.error("Error en búsqueda Gmail API", error=str(e))
                return []

        except Exception as e:
            search_logger.error("Error en búsqueda de emails", error=str(e))
            return []

    async def close(self):
        """Cerrar conexión y limpiar recursos"""
        logger = bind_log_context(self.logger, ensure_log_context(etapa="gmail_oauth"))

        try:
            self.gmail_service = None
            self.credentials = None
            self._authenticated = False
            logger.info("Conexión Gmail API cerrada")
        except Exception as e:
            logger.error("Error cerrando conexión Gmail API", error=str(e))
