import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock

from app.config import Settings
from app.services.gmail_oauth_service import GmailOAuthService


def _encode_body(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")


async def main():
    settings = Settings(
        _env_file=None,
        gmail_user="test@example.com",
        google_application_credentials="creds.json",
        google_token_path="token.pickle",
        email_subject_pattern="Misioneros que llegan",
        processed_label="misioneros-procesados",
    )
    service = GmailOAuthService(settings)
    service.authenticate = AsyncMock(return_value=True)
    service._authenticated = True

    gmail_service = MagicMock(name="gmail_service")
    messages = gmail_service.users.return_value.messages.return_value
    labels = gmail_service.users.return_value.labels.return_value

    html_body = (
        "<html><body><p>Generación del 10 de enero de 2025</p>"
        "<table><tr><th>Distrito</th><th>Zona</th></tr>"
        "<tr><td>14A</td><td>Benemerito</td></tr></table>"
        "</body></html>"
    )

    payload = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Misioneros que llegan el 10 de enero"},
                {"name": "From", "value": "natalia@example.com"},
                {"name": "Date", "value": "2025-01-10T00:00:00+00:00"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _encode_body("Generación del 10 de enero de 2025")}},
                {"mimeType": "text/html", "body": {"data": _encode_body(html_body)}},
                {
                    "mimeType": "application/pdf",
                    "filename": "info.pdf",
                    "body": {"attachmentId": "att1"},
                    "partId": "part_1",
                },
            ],
        }
    }

    messages.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}
    messages.get.return_value.execute.return_value = payload
    attachments_api = messages.attachments.return_value
    attachments_api.get.return_value.execute.return_value = {"data": _encode_body("PDFDATA")}
    labels.create.return_value.execute.return_value = {"id": "lbl123"}
    messages.modify.return_value.execute.return_value = {}

    service.gmail_service = gmail_service

    result = await service.process_incoming_emails()
    print("processed:", result.processed)
    print("details:", result.details)


if __name__ == "__main__":
    asyncio.run(main())
