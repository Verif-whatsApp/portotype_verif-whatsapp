"""Webhook WhatsApp : vérification par Meta (GET) et réception des messages (POST)."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.session import get_session_factory
from app.schemas.whatsapp import WebhookPayload
from app.security import is_valid_signature, tokens_match
from app.services.bot import MessageDeduplicator, handle_incoming_message
from app.services.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["whatsapp"])


def get_whatsapp_client(settings: Annotated[Settings, Depends(get_settings)]) -> WhatsAppClient:
    # Sans identifiants en développement, les réponses sont écrites dans les logs
    dry_run = not settings.whatsapp_access_token and not settings.is_production
    return WhatsAppClient(
        access_token=settings.whatsapp_access_token,
        phone_number_id=settings.whatsapp_phone_number_id,
        api_version=settings.whatsapp_api_version,
        dry_run=dry_run,
    )


@lru_cache
def get_deduplicator() -> MessageDeduplicator:
    return MessageDeduplicator()


SettingsDep = Annotated[Settings, Depends(get_settings)]
ClientDep = Annotated[WhatsAppClient, Depends(get_whatsapp_client)]
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]
DeduplicatorDep = Annotated[MessageDeduplicator, Depends(get_deduplicator)]


@router.get("/webhook")
def verify_webhook(
    settings: SettingsDep,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> PlainTextResponse:
    """Vérification demandée par Meta quand on enregistre l'URL du webhook.

    Meta attend le `hub.challenge` en texte brut (pas de JSON) si le jeton est le bon.
    """
    if (
        mode == "subscribe"
        and challenge is not None
        and tokens_match(token, settings.whatsapp_verify_token)
    ):
        logger.info("Webhook vérifié par Meta")
        return PlainTextResponse(challenge)
    logger.warning("Vérification du webhook refusée (mode ou jeton incorrect)")
    raise HTTPException(status_code=403, detail="Vérification refusée")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    client: ClientDep,
    session_factory: SessionFactoryDep,
    deduplicator: DeduplicatorDep,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> dict[str, str]:
    """Réception des messages. Répond 200 tout de suite : le traitement se fait ensuite."""
    body = await request.body()
    _authenticate(body, signature, settings)

    try:
        payload = WebhookPayload.model_validate_json(body)
    except ValidationError:
        # Requête authentique mais format inattendu : un 4xx ferait renvoyer Meta en boucle
        logger.warning("Notification WhatsApp ignorée : format inattendu")
        return {"status": "ignored"}

    for message in payload.incoming_messages():
        if deduplicator.is_duplicate(message.id):
            continue
        background_tasks.add_task(handle_incoming_message, message, client, session_factory)
    return {"status": "received"}


def _authenticate(body: bytes, signature: str | None, settings: Settings) -> None:
    """Refuse toute requête dont la signature (clé secrète de l'app Meta) est invalide."""
    if not settings.whatsapp_app_secret:
        if settings.is_production:
            logger.error("WHATSAPP_APP_SECRET manquant : requête refusée")
            raise HTTPException(status_code=403, detail="Signature impossible à vérifier")
        return  # développement : signature non vérifiée (avertissement au démarrage)
    if not is_valid_signature(body, signature, settings.whatsapp_app_secret):
        logger.warning("Requête refusée : signature invalide")
        raise HTTPException(status_code=403, detail="Signature invalide")
