# ... (garder le début du fichier intact : imports, process_and_reply, verify_webhook)
import httpx
from app.services.ocr import extract_text_from_image
from app.config import settings

async def handle_image_message(media_id: str, sender: str):
    """Télécharge l'image depuis Meta, extrait le texte, et lance le matching."""
    # 1. Récupérer l'URL de l'image
    url_info = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Obtenir l'URL
            res_info = await client.get(url_info, headers=headers)
            res_info.raise_for_status()
            media_url = res_info.json().get("url")
            
            if not media_url:
                raise ValueError("URL de l'image introuvable.")

            # Télécharger l'image
            res_img = await client.get(media_url, headers=headers)
            res_img.raise_for_status()
            
            # Extraire le texte
            text = extract_text_from_image(res_img.content)
            
            if not text:
                await send_whatsapp_message(sender, "📸 Désolé, nous n'avons pas réussi à lire le texte de cette image.")
                return
                
            # Traiter comme un message texte normal
            await process_and_reply(text, sender)
            
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'image : {e}")
        await send_whatsapp_message(sender, "📸 Une erreur est survenue lors de l'analyse de l'image.")

@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    # ... (garder la logique de parsing intacte)
            if "messages" in value:
                message = value["messages"][0]
                sender = message.get("from")
                msg_type = message.get("type")
                
                if msg_type == "text":
                    text_content = message["text"]["body"]
                    background_tasks.add_task(process_and_reply, text_content, sender)
                
                elif msg_type == "image":
                    media_id = message["image"]["id"]
                    logger.info(f"Image reçue de {sender} (ID: {media_id})")
                    background_tasks.add_task(handle_image_message, media_id, sender)
    # ...