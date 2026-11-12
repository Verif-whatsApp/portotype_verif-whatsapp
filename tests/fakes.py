"""Doublures de test."""

from app.services.whatsapp import WhatsAppError


class FakeGateway:
    """Remplace `WhatsAppClient` : enregistre ce qui serait envoyé à WhatsApp."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.read: list[str] = []
        self.downloaded: list[str] = []
        self.media = b"image-bytes"
        self.send_error: Exception | None = None
        self.read_error: Exception | None = None
        self.media_error: Exception | None = None

    async def send_text(self, to: str, body: str) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent.append((to, body))

    async def mark_as_read(self, message_id: str) -> None:
        if self.read_error is not None:
            raise self.read_error
        self.read.append(message_id)

    async def download_media(self, media_id: str) -> bytes:
        if self.media_error is not None:
            raise self.media_error
        self.downloaded.append(media_id)
        return self.media


def whatsapp_error(text: str = "boom") -> WhatsAppError:
    return WhatsAppError(text)
