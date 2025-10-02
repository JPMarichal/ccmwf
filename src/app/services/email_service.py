"""
Servicio de Email - Implementación principal (Compatible con OAuth e IMAP)
"""

import imapclient
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import List, Dict, Optional, Tuple
import structlog
from datetime import datetime
import asyncio

from app.config import Settings
from app.models import EmailMessage, EmailAttachment, ProcessingResult, EmailStatus
from app.services.gmail_oauth_service import GmailOAuthService
from app.services.validators import validate_email_structure, validate_table_structure
from app.services.email_html_parser import extract_primary_table
from app.services.email_content_utils import (
    extract_fecha_generacion,
    collect_table_texts,
)
from app.services.drive_service import DriveService
from app.logging_utils import ensure_log_context, bind_log_context


class EmailService:
    """Servicio principal para manejo de emails - Soporta OAuth e IMAP"""

    def __init__(self, settings: Settings, drive_service: Optional[DriveService] = None):
        self.settings = settings
        self.logger = structlog.get_logger("email_service").bind(
            servicio="email_service",
        )
        self.drive_service = drive_service

        # Detectar si usar OAuth o IMAP basado en configuración
        self.use_oauth = self._should_use_oauth()
        self.logger.info(
            "Servicio de email inicializado",
            authentication="OAuth" if self.use_oauth else "IMAP",
            etapa="inicio_servicio",
        )

        if self.use_oauth:
            self.gmail_oauth_service = GmailOAuthService(settings, drive_service=drive_service)
        else:
            self.imap_client = None
            self._connected = False

    def _should_use_oauth(self) -> bool:
        """Determinar si usar OAuth basado en configuración"""
        # Si tenemos credenciales OAuth configuradas, usar OAuth
        if (hasattr(self.settings, 'google_application_credentials') and
            self.settings.google_application_credentials and
            hasattr(self.settings, 'google_token_path') and
            self.settings.google_token_path):
            return True
        return False

    async def test_connection(self) -> bool:
        """Test de conexión (OAuth o IMAP)"""
        if self.use_oauth:
            return await self.gmail_oauth_service.test_connection()
        else:
            return await self._test_imap_connection()

    async def _test_imap_connection(self) -> bool:
        """Test de conexión IMAP (fallback)"""
        try:
            await self._ensure_imap_connection()
            if self._connected:
                self.logger.info("✅ Conexión IMAP exitosa")
                return True
            else:
                self.logger.error("❌ Falló conexión IMAP")
                return False
        except Exception as e:
            self.logger.error("Error en test de conexión IMAP", error=str(e))
            return False
        finally:
            if self.imap_client:
                self.imap_client.logout()

    async def _ensure_imap_connection(self) -> None:
        """Asegurar que hay conexión IMAP activa (fallback)"""
        if self._connected and self.imap_client:
            return

        context = ensure_log_context(etapa="conexion_imap")
        logger = bind_log_context(self.logger, context)

        try:
            logger.info(
                "Conectando a IMAP",
                server=self.settings.imap_server,
                port=self.settings.imap_port,
            )

            self.imap_client = imapclient.IMAPClient(
                self.settings.imap_server,
                port=self.settings.imap_port
            )

            # Login con app password
            self.imap_client.login(
                self.settings.gmail_user,
                self.settings.gmail_app_password
            )

            # Configurar para usar UTF-8
            self.imap_client.enable('UTF-8')

            self._connected = True
            logger.info("Conexión IMAP establecida")

        except Exception as e:
            self._connected = False
            logger.error("Error conectando a IMAP", error=str(e))
            raise

    async def process_incoming_emails(self) -> ProcessingResult:
        """Procesar correos de misioneros entrantes"""
        if self.use_oauth:
            return await self.gmail_oauth_service.process_incoming_emails()
        else:
            return await self._process_imap_emails()

    async def _process_imap_emails(self) -> ProcessingResult:
        """Procesar emails usando IMAP (fallback)"""
        start_time = datetime.now()

        process_context = ensure_log_context(etapa="recepcion_correo")
        process_logger = bind_log_context(self.logger, process_context)

        try:
            await self._ensure_imap_connection()

            # Buscar correos no leídos que coincidan con el patrón
            search_criteria = f'SUBJECT "{self.settings.email_subject_pattern}" UNSEEN'
            self.imap_client.select_folder('INBOX')

            message_ids = self.imap_client.search(search_criteria)

            if not message_ids:
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
                ensure_log_context(etapa="recepcion_correo"),
                total=len(message_ids),
            )
            process_logger.info("Procesando correos")

            results = []
            processed_count = 0
            error_count = 0

            for msg_id in message_ids:
                try:
                    # Obtener el mensaje
                    raw_messages = self.imap_client.fetch([msg_id], ['RFC822', 'FLAGS'])
                    raw_email = raw_messages[msg_id]['RFC822']

                    # Parsear el email
                    email_message = email.message_from_bytes(raw_email)

                    # Procesar el mensaje
                    result = await self._process_single_imap_email(email_message, msg_id)
                    results.append(result)

                    if result['success']:
                        processed_count += 1
                    else:
                        error_count += 1

                    # Pausa para evitar límites de API
                    await asyncio.sleep(1)

                except Exception as e:
                    error_count += 1
                    error_logger = bind_log_context(
                        self.logger,
                        ensure_log_context(etapa="recepcion_correo", message_id=str(msg_id)),
                    )
                    error_logger.error("Error procesando mensaje individual", error=str(e))
                    results.append({
                        'success': False,
                        'error': str(e),
                        'message_id': msg_id
                    })

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
                details=results,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration
            )

        except Exception as e:
            end_time = datetime.now()
            process_logger.error("Error en procesamiento general", error=str(e))

            return ProcessingResult(
                success=False,
                processed=0,
                errors=1,
                details=[{'error': str(e)}],
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds()
            )

    async def _process_single_imap_email(self, email_message: email.message.Message, msg_id: int) -> Dict:
        """Procesar un mensaje individual usando IMAP (fallback)"""
        log_context = ensure_log_context(etapa="recepcion_correo", message_id=str(msg_id))
        logger = bind_log_context(self.logger, log_context)

        try:
            # Extraer información básica
            subject = self._decode_header(email_message['Subject']) if email_message['Subject'] else ""
            sender = email_message['From'] or ""
            date_str = email_message['Date'] or ""

            # Parsear fecha
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except:
                date = datetime.now()

            # Obtener cuerpo del mensaje
            body = self._get_email_body(email_message)
            html_body = self._get_email_html(email_message)

            parsed_table, parse_errors = extract_primary_table(html_body or "")
            table_texts = collect_table_texts(parsed_table)

            fecha_generacion = extract_fecha_generacion(
                self.logger,
                body,
                html_body,
                subject,
                table_texts,
            )

            # Obtener attachments
            attachments = []
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue

                filename = part.get_filename()
                if not filename:
                    continue

                attachment_data = part.get_payload(decode=True)
                attachments.append(EmailAttachment(
                    filename=filename,
                    size=len(attachment_data) if attachment_data else 0,
                    content_type=part.get_content_type(),
                    data=attachment_data
                ))

            is_valid, validation_errors = validate_email_structure(
                subject=subject,
                fecha_generacion=fecha_generacion,
                attachments=attachments,
                expected_subject_pattern=self.settings.email_subject_pattern,
            )

            # Marcar como leído y etiquetado
            self.imap_client.add_flags([msg_id], ['\\Seen'])
            if self.settings.processed_label:
                try:
                    self.imap_client.add_labels([msg_id], [self.settings.processed_label])
                except:
                    pass  # Ignorar errores de etiquetado

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
                            log_context,
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
                        bind_log_context(logger, ensure_log_context(etapa="drive_upload")).error(
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
                        ensure_log_context(log_context, etapa="drive_upload", drive_folder_id=drive_folder_id),
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
                    ensure_log_context(log_context, etapa="drive_upload", drive_folder_id=drive_folder_id),
                ).warning("Errores al subir archivos a Drive", errors=drive_upload_errors)

            return result

        except Exception as e:
            logger.error("Error procesando mensaje individual", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'message_id': msg_id,
                'parsed_table': None,
                'table_errors': ['processing_exception'],
                'drive_folder_id': None,
                'drive_uploaded_files': [],
                'drive_upload_errors': [{'code': 'drive_upload_failed', 'message': str(e)}]
            }

    def _decode_header(self, header_value: str) -> str:
        """Decodificar headers de email"""
        if not header_value:
            return ""

        decoded_parts = decode_header(header_value)
        decoded_string = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    part = part.decode(encoding)
                else:
                    part = part.decode('utf-8', errors='ignore')
            decoded_string += part

        return decoded_string

    def _get_email_body(self, email_message: email.message.Message) -> str:
        """Extraer cuerpo del email"""
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='ignore')
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                charset = email_message.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')

        return body.strip()

    def _get_email_html(self, email_message: email.message.Message) -> str:
        """Extraer cuerpo HTML completo del email"""
        html_content = []

        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_content.append(payload.decode(charset, errors='ignore'))
        else:
            if email_message.get_content_type() == 'text/html':
                payload = email_message.get_payload(decode=True)
                if payload:
                    charset = email_message.get_content_charset() or 'utf-8'
                    html_content.append(payload.decode(charset, errors='ignore'))

        return "\n".join(html_content).strip()

    async def search_emails(self, query: Optional[str] = None) -> List[Dict]:
        """Buscar emails (para testing y debugging)"""
        if self.use_oauth:
            return await self.gmail_oauth_service.search_emails(query)
        else:
            return await self._search_imap_emails(query)

    async def _search_imap_emails(self, query: Optional[str] = None) -> List[Dict]:
        """Buscar emails usando IMAP (fallback)"""
        try:
            await self._ensure_imap_connection()

            self.imap_client.select_folder('INBOX')

            if query:
                search_criteria = query
            else:
                search_criteria = 'ALL'

            message_ids = self.imap_client.search(search_criteria)

            emails = []
            for msg_id in message_ids[:10]:  # Limitar a 10 para evitar sobrecarga
                try:
                    raw_messages = self.imap_client.fetch([msg_id], ['RFC822'])
                    raw_email = raw_messages[msg_id]['RFC822']
                    email_message = email.message_from_bytes(raw_email)

                    subject = self._decode_header(email_message['Subject']) if email_message['Subject'] else ""

                    emails.append({
                        'id': msg_id,
                        'subject': subject,
                        'sender': email_message['From'] or "",
                        'date': email_message['Date'] or "",
                        'has_attachments': len(email_message.get_payload()) > 1 if email_message.is_multipart() else False
                    })

                except Exception as e:
                    self.logger.error("Error procesando email en búsqueda",
                                    message_id=msg_id, error=str(e))

            return emails

        except Exception as e:
            self.logger.error("Error en búsqueda de emails", error=str(e))
            return []

    async def close(self):
        """Cerrar conexión (OAuth o IMAP)"""
        if self.use_oauth:
            await self.gmail_oauth_service.close()
        else:
            if self.imap_client:
                try:
                    self.imap_client.logout()
                    self._connected = False
                    self.logger.info("🔌 Conexión IMAP cerrada")
                except Exception as e:
                    self.logger.error("Error cerrando conexión IMAP", error=str(e))
