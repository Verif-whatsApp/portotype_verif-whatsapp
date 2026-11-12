"""Format des notifications envoyées par Meta au webhook (seuls les champs utiles)."""

from pydantic import BaseModel, ConfigDict, Field

MESSAGES_FIELD = "messages"
WHATSAPP_OBJECT = "whatsapp_business_account"


class _Payload(BaseModel):
    # Meta ajoute régulièrement des champs : on ignore ce qu'on ne connaît pas
    model_config = ConfigDict(extra="ignore")


class TextContent(_Payload):
    body: str


class ImageContent(_Payload):
    id: str


class IncomingMessage(_Payload):
    id: str
    sender: str = Field(alias="from")
    type: str
    text: TextContent | None = None
    image: ImageContent | None = None


class ChangeValue(_Payload):
    # Les accusés de livraison arrivent dans `statuses` : ignorés ici
    messages: list[IncomingMessage] = Field(default_factory=list)


class Change(_Payload):
    field: str = ""
    value: ChangeValue = Field(default_factory=ChangeValue)


class Entry(_Payload):
    changes: list[Change] = Field(default_factory=list)


class WebhookPayload(_Payload):
    object: str
    entry: list[Entry] = Field(default_factory=list)

    def incoming_messages(self) -> list[IncomingMessage]:
        """Tous les messages reçus, dans l'ordre (une notification peut en contenir plusieurs)."""
        if self.object != WHATSAPP_OBJECT:
            return []
        return [
            message
            for entry in self.entry
            for change in entry.changes
            if change.field == MESSAGES_FIELD
            for message in change.value.messages
        ]
