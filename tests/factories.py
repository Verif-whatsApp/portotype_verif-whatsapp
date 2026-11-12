"""Fabriques d'objets pour les tests."""

from datetime import date
from typing import Any

from app.models import Verdict, Verification


def make_verification(**overrides: Any) -> Verification:
    """Crée une `Verification` valide (non enregistrée) ; chaque champ est surchargeable."""
    fields: dict[str, Any] = {
        "claim_text": "ALERTE : Attaque à Doropo, ne sortez pas",
        "claim_variants": [],
        "verdict": Verdict.FAUX,
        "explanation": (
            "Aucune attaque n'a été signalée à Doropo à cette date. "
            "Les autorités locales ont démenti l'information."
        ),
        "source_name": "IvoireCheck",
        "source_url": "https://example.org/verification/doropo",
        "verified_at": date(2026, 10, 12),
        "language": "fr",
    }
    fields.update(overrides)
    return Verification(**fields)


SENDER = "22997001234"


def text_message(
    body: str, *, message_id: str = "wamid.TEXT1", sender: str = SENDER
) -> dict[str, Any]:
    """Message texte tel que Meta le notifie."""
    return {
        "from": sender,
        "id": message_id,
        "timestamp": "1760000000",
        "type": "text",
        "text": {"body": body},
    }


def image_message(
    media_id: str = "MEDIA1", *, message_id: str = "wamid.IMG1", sender: str = SENDER
) -> dict[str, Any]:
    return {
        "from": sender,
        "id": message_id,
        "timestamp": "1760000000",
        "type": "image",
        "image": {"id": media_id, "mime_type": "image/jpeg", "sha256": "abc"},
    }


def other_message(
    message_type: str, *, message_id: str = "wamid.OTHER1", sender: str = SENDER
) -> dict[str, Any]:
    return {"from": sender, "id": message_id, "timestamp": "1760000000", "type": message_type}


def webhook_payload(*messages: dict[str, Any]) -> dict[str, Any]:
    """Notification complète (enveloppe Meta) contenant les messages donnés."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "123456",
                            },
                            "contacts": [{"profile": {"name": "Test"}, "wa_id": SENDER}],
                            "messages": list(messages),
                        },
                    }
                ],
            }
        ],
    }


def status_payload() -> dict[str, Any]:
    """Accusé de livraison : Meta en envoie après chaque message envoyé par le robot."""
    payload = webhook_payload()
    value = payload["entry"][0]["changes"][0]["value"]
    del value["messages"]
    value["statuses"] = [{"id": "wamid.OUT", "status": "delivered", "recipient_id": SENDER}]
    return payload
