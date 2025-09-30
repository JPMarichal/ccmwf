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
from app.models import EmailMessage, EmailAttachment, ProcessingResult
from app.services.validators import validate_email_structure, validate_table_structure
from app.services.email_html_parser import extract_primary_table


class GmailOAuthService:
    """Servicio para Gmail usando OAuth 2.0"""

    # Scopes requeridos para Gmail API
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels'
    ]

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger()
        self.credentials = None
        self.gmail_service = None
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Autenticar con Gmail usando OAuth 2.0"""
        try:
            creds = None

            # Verificar si ya tenemos credenciales guardadas
            if os.path.exists(self.settings.google_token_path):
                with open(self.settings.google_token_path, 'rb') as token:
                    creds = pickle.load(token)

            # Si no hay credenciales válidas, hacer flow OAuth
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    self.logger.info("🔄 Refrescando token de acceso...")
                    creds.refresh(Request())
                else:
                    self.logger.info("🔐 Iniciando flow OAuth...")
                    creds = await self._oauth_flow()

                # Guardar credenciales para futuras ejecuciones
                with open(self.settings.google_token_path, 'wb') as token:
                    pickle.dump(creds, token)

            self.credentials = creds
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            self._authenticated = True

            self.logger.info("✅ Autenticación OAuth exitosa")
            return True

        except Exception as e:
            self._authenticated = False
            self.logger.error("❌ Error en autenticación OAuth", error=str(e))
            return False

    async def _oauth_flow(self) -> Credentials:
        """Ejecutar flow OAuth 2.0"""
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
            self.logger.error("Error en flow OAuth", error=str(e))
            raise

    async def test_connection(self) -> bool:
        """Test de conexión a Gmail API"""
        try:
            await self.authenticate()

            if not self._authenticated:
                return False

            # Test simple: obtener perfil del usuario
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'unknown')

            self.logger.info("✅ Conexión Gmail API exitosa",
                           email_address=email_address)
            return True

        except Exception as e:
            self.logger.error("❌ Error en test de conexión Gmail API", error=str(e))
            return False

    async def process_incoming_emails(self) -> ProcessingResult:
        """Procesar correos de misioneros usando Gmail API"""
        start_time = datetime.now()

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

            # Buscar mensajes no leídos con el patrón
            query = f'subject:"{self.settings.email_subject_pattern}" is:unread'

            try:
                # Buscar mensajes
                results = self.gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=50
                ).execute()

                messages = results.get('messages', [])

                if not messages:
                    self.logger.info("ℹ️ No se encontraron correos nuevos")
                    return ProcessingResult(
                        success=True,
                        processed=0,
                        errors=0,
                        details=[],
                        start_time=start_time,
                        end_time=datetime.now(),
                        duration_seconds=(datetime.now() - start_time).total_seconds()
                    )

            except HttpError as e:
                self.logger.error("Error buscando mensajes",
                                error_code=e.resp.status,
                                error_details=str(e))
                return ProcessingResult(
                    success=False,
                    processed=0,
                    errors=1,
                    details=[{"error": f"Gmail API error: {e}"}],
                    start_time=start_time,
                    end_time=datetime.now(),
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )

            self.logger.info("📧 Procesando correos",
                           count=len(messages))

            results = []
            processed_count = 0
            error_count = 0

            for msg_data in messages:
                try:
                    msg_id = msg_data['id']

                    # Obtener el mensaje completo
                    message = self.gmail_service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ).execute()

                    # Procesar el mensaje
                    result = await self._process_single_message(message, msg_id)
                    results.append(result)

                    if result['success']:
                        processed_count += 1
                    else:
                        error_count += 1

                    # Pausa para evitar límites de API
                    import asyncio
                    await asyncio.sleep(0.5)

                except Exception as e:
                    error_count += 1
                    self.logger.error("Error procesando mensaje individual",
                                    message_id=msg_id, error=str(e))
                    results.append({
                        'success': False,
                        'error': str(e),
                        'message_id': msg_id,
                        'parsed_table': None,
                        'table_errors': ['processing_exception']
                    })

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.logger.info("✅ Procesamiento completado",
                           processed=processed_count,
                           errors=error_count,
                           duration_seconds=duration)

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
            self.logger.error("❌ Error en procesamiento general", error=str(e))

            return ProcessingResult(
                success=False,
                processed=0,
                errors=1,
                details=[{'error': str(e)}],
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds()
            )

    async def _process_single_message(self, message: Dict[str, Any], msg_id: str) -> Dict:
        """Procesar un mensaje individual usando Gmail API"""
        try:
            # Extraer headers
            headers = message['payload']['headers']
            subject = self._get_header_value(headers, 'Subject')
            sender = self._get_header_value(headers, 'From')
            date_str = self._get_header_value(headers, 'Date')

            # Parsear fecha
            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00').replace('+0000', '+00:00'))
            except:
                date = datetime.now()

            # Obtener cuerpo del mensaje
            body = self._get_message_body(message['payload'])
            html_body = self._get_html_body(message['payload'])

            # Buscar fecha de generación en el cuerpo
            fecha_generacion = self._extract_fecha_generacion(body)

            # Obtener attachments
            attachments = []
            if 'parts' in message['payload']:
                for part in self._get_all_parts(message['payload']):
                    if part.get('filename') and part['filename']:
                        attachment_data = self._get_attachment_data(msg_id, part['partId'])
                        if attachment_data:
                            attachments.append(EmailAttachment(
                                filename=part['filename'],
                                size=len(attachment_data),
                                content_type=part.get('mimeType', ''),
                                data=attachment_data
                            ))

            # Marcar como leído y etiquetado
            await self._mark_message_processed(msg_id)

            is_valid, validation_errors = validate_email_structure(
                subject=subject,
                fecha_generacion=fecha_generacion,
                attachments=attachments,
                expected_subject_pattern=self.settings.email_subject_pattern,
            )

            parsed_table, table_errors = extract_primary_table(html_body or "")
            table_errors.extend(
                validate_table_structure(
                    parsed_table,
                    self.settings.email_table_required_columns,
                )
            )

            success = is_valid and not table_errors

            table_headers_count = len(parsed_table["headers"]) if parsed_table else 0
            table_rows_count = len(parsed_table["rows"]) if parsed_table else 0

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
                'body_preview': body[:200] + "..." if len(body) > 200 else body
            }

            if success:
                self.logger.info("✅ Mensaje procesado correctamente",
                               message_id=msg_id,
                               subject=subject,
                               attachments=len(attachments),
                               table_headers=table_headers_count,
                               table_rows=table_rows_count)
            else:
                self.logger.warning("⚠️ Validación de estructura fallida",
                                    message_id=msg_id,
                                    errors=validation_errors,
                                    table_errors=table_errors,
                                    subject=subject)

            if table_errors:
                self.logger.warning("⚠️ Problemas al parsear tabla HTML",
                                    message_id=msg_id,
                                    errors=table_errors)
            elif parsed_table:
                self.logger.info("📊 Tabla HTML extraída",
                                 message_id=msg_id,
                                 headers=table_headers_count,
                                 rows=table_rows_count)

            return result

        except Exception as e:
            self.logger.error("Error procesando mensaje individual",
                            message_id=msg_id, error=str(e))
            return {
                'success': False,
                'error': str(e),
                'message_id': msg_id
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

    def _extract_fecha_generacion(self, body: str) -> Optional[str]:
        """Extraer fecha de generación del cuerpo del email"""
        import re

        # Patrón para "Generación del DD de MES de YYYY"
        pattern = r'Generación del (\d{1,2}) de (\w+) de (\d{4})'

        match = re.search(pattern, body, re.IGNORECASE)

        if match:
            dia = match.group(1).zfill(2)
            mes_texto = match.group(2).lower()
            año = match.group(3)

            # Mapeo de meses
            meses = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }

            mes = meses.get(mes_texto)
            if mes:
                fecha_formateada = f"{año}{mes}{dia}"
                self.logger.info("📅 Fecha de generación extraída",
                               fecha_original=match.group(0),
                               fecha_formateada=fecha_formateada)
                return fecha_formateada

        self.logger.warning("⚠️ No se pudo extraer fecha de generación", body_preview=body[:100])
        return None

    async def _mark_message_processed(self, message_id: str):
        """Marcar mensaje como procesado"""
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

            self.logger.info("✅ Mensaje marcado como procesado", message_id=message_id)

        except Exception as e:
            self.logger.error("Error marcando mensaje como procesado",
                            message_id=message_id, error=str(e))

    async def search_emails(self, query: Optional[str] = None) -> List[Dict]:
        """Buscar emails usando Gmail API (para testing)"""
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
                        self.logger.error("Error procesando email en búsqueda",
                                        message_id=msg_id, error=str(e))

                return emails

            except HttpError as e:
                self.logger.error("Error en búsqueda Gmail API", error=str(e))
                return []

        except Exception as e:
            self.logger.error("Error en búsqueda de emails", error=str(e))
            return []

    async def close(self):
        """Cerrar conexión y limpiar recursos"""
        try:
            self.gmail_service = None
            self.credentials = None
            self._authenticated = False
            self.logger.info("🔌 Conexión Gmail API cerrada")
        except Exception as e:
            self.logger.error("Error cerrando conexión Gmail API", error=str(e))
