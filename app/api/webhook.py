import logging

import httpx
from app.services.whatsapp import send_whatsapp_message
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response

from app.config import settings
from app.services.formatting import format_verdict_response
from app.services.matching import find_best_match
from app.services.ocr import extract_text_from_image

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_and_reply(text: str, sender: str) -> None:
    """Tâche de fond pour traiter le message et envoyer la réponse."""
    try:
        match_result = find_best_match(text)
        response_text = format_verdict_response(match_result)
        await send_whatsapp_message(sender, response_text)
    except Exception as e:
        logger.error(f"Erreur lors du traitement du message : {e}")
        error_msg = "Désolé, une erreur technique est survenue. Veuillez réessayer plus tard."
        await send_whatsapp_message(sender, error_msg)


async def handle_image_message(media_id: str, sender: str) -> None:
    """Télécharge l'image depuis Meta, extrait le texte, et lance le matching."""
    url_info = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        async with httpx.AsyncClient() as client:
            res_info = await client.get(url_info, headers=headers)
            res_info.raise_for_status()
            media_url = res_info.json().get("url")

            if not media_url:
                raise ValueError("URL de l'image introuvable.")

            res_img = await client.get(media_url, headers=headers)
            res_img.raise_for_status()

            text = extract_text_from_image(res_img.content)

            if not text:
                await send_whatsapp_message(
                    sender,
                    "📸 Désolé, nous n'avons pas réussi à lire le texte de cette image.",
                )
                return

            await process_and_reply(text, sender)

    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'image : {e}")
        await send_whatsapp_message(
            sender, "📸 Une erreur est survenue lors de l'analyse de l'image."
        )


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    """Vérification du webhook par Meta."""
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook vérifié avec succès par Meta.")
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token de vérification invalide")


@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Réception des messages entrants de WhatsApp."""
    body = await request.json()

    if body.get("object") == "whatsapp_business_account":
        try:
            entry = body.get("entry", [])[0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})

            if "messages" in value:
                message = value["messages"][0]
                sender = message.get("from")
                msg_type = message.get("type")

                if msg_type == "text":
                    text_content = message["text"]["body"]
                    logger.info(f"Message reçu de {sender} : {text_content}")
                    background_tasks.add_task(process_and_reply, text_content, sender)

                elif msg_type == "image":
                    media_id = message["image"]["id"]
                    logger.info(f"Image reçue de {sender} (ID: {media_id})")
                    background_tasks.add_task(handle_image_message, media_id, sender)

        except (IndexError, KeyError) as e:
            logger.error(f"Erreur de parsing du payload WhatsApp : {e}")
            return {"status": "ok"}

    return {"status": "ok"}
