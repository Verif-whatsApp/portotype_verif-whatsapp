"""Traitement d'un message WhatsApp entrant : vérification puis réponse.

Confidentialité : le contenu des messages et les numéros complets ne sont jamais écrits
dans les logs, et rien n'est conservé après la réponse (sauf l'identifiant du message,
gardé en mémoire pour ignorer les doublons).
"""

import contextlib
import logging
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import Protocol

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.schemas.whatsapp import IncomingMessage
from app.services.formatting import (
    format_error,
    format_image_error,
    format_response,
    format_unreadable_image,
    format_unsupported,
)
from app.services.matching import find_best_match
from app.services.ocr import extract_text_from_image
from app.services.whatsapp import WhatsAppError

logger = logging.getLogger(__name__)

# Notifications qui n'appellent aucune réponse (réactions, messages système)
IGNORED_MESSAGE_TYPES = frozenset({"reaction", "system"})

SessionFactory = Callable[[], Session]


class WhatsAppGateway(Protocol):
    """Ce dont le traitement a besoin pour parler à WhatsApp (voir `WhatsAppClient`)."""

    async def send_text(self, to: str, body: str) -> None: ...

    async def mark_as_read(self, message_id: str) -> None: ...

    async def download_media(self, media_id: str) -> bytes: ...


class MessageDeduplicator:
    """Mémorise les derniers identifiants de messages pour ignorer les renvois de Meta.

    Valable pour un seul processus : avec plusieurs workers, utiliser un stockage partagé.
    """

    def __init__(self, capacity: int = 2048) -> None:
        self._capacity = capacity
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    def is_duplicate(self, message_id: str) -> bool:
        """Vrai si l'identifiant a déjà été vu ; sinon l'enregistre et retourne faux."""
        with self._lock:
            if message_id in self._seen:
                self._seen.move_to_end(message_id)
                return True
            self._seen[message_id] = None
            if len(self._seen) > self._capacity:
                self._seen.popitem(last=False)
            return False


def mask_phone_number(number: str) -> str:
    """`22997123456` devient `***3456` pour les logs."""
    return f"***{number[-4:]}" if len(number) > 4 else "***"


async def handle_incoming_message(
    message: IncomingMessage, gateway: WhatsAppGateway, session_factory: SessionFactory
) -> None:
    """Accuse réception, vérifie le message et envoie la réponse. Ne lève jamais d'exception."""
    if message.type in IGNORED_MESSAGE_TYPES:
        return

    sender = mask_phone_number(message.sender)
    try:
        await _mark_as_read(gateway, message.id)
        reply = await _build_reply(message, gateway, session_factory)
        await gateway.send_text(message.sender, reply)
    except WhatsAppError as exc:
        logger.error("Envoi de la réponse impossible (destinataire %s) : %s", sender, exc)
    except Exception:
        logger.exception(
            "Erreur inattendue en traitant le message %s (expéditeur %s)", message.id, sender
        )
        with contextlib.suppress(WhatsAppError):
            await gateway.send_text(message.sender, format_error())


async def _mark_as_read(gateway: WhatsAppGateway, message_id: str) -> None:
    """Accusé de lecture : utile mais facultatif, son échec ne bloque pas la réponse."""
    try:
        await gateway.mark_as_read(message_id)
    except WhatsAppError as exc:
        logger.warning("Accusé de lecture impossible (message %s) : %s", message_id, exc)


async def _build_reply(
    message: IncomingMessage, gateway: WhatsAppGateway, session_factory: SessionFactory
) -> str:
    if message.type == "text" and message.text is not None and message.text.body.strip():
        return await _verify_text(message.text.body, session_factory)
    if message.type == "image" and message.image is not None:
        return await _verify_image(message.image.id, gateway, session_factory)
    return format_unsupported()


async def _verify_image(
    media_id: str, gateway: WhatsAppGateway, session_factory: SessionFactory
) -> str:
    try:
        image_bytes = await gateway.download_media(media_id)
    except WhatsAppError as exc:
        logger.error("Image %s impossible à télécharger : %s", media_id, exc)
        return format_image_error()

    # Tesseract est lent et bloquant : hors de la boucle d'événements
    text = await run_in_threadpool(extract_text_from_image, image_bytes)
    if not text:
        return format_unreadable_image()
    return await _verify_text(text, session_factory)


async def _verify_text(text: str, session_factory: SessionFactory) -> str:
    return await run_in_threadpool(_reply_for_text, session_factory, text)


def _reply_for_text(session_factory: SessionFactory, text: str) -> str:
    with session_factory() as session:
        return format_response(find_best_match(session, text))
