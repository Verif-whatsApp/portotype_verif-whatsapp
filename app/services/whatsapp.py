"""Client de l'API WhatsApp Cloud (Meta) : envoi de messages, accusés de lecture, médias."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE_URL = "https://graph.facebook.com"
MAX_TEXT_LENGTH = 4096  # limite d'un message texte WhatsApp
MAX_MEDIA_BYTES = 10 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 15.0


class WhatsAppError(Exception):
    """Échec d'un appel à l'API WhatsApp (configuration, réseau ou refus de Meta)."""


class WhatsAppClient:
    """Appels à l'API Graph. Un client HTTP est ouvert par appel : simple et sans état.

    En mode `dry_run` (développement sans compte Meta), les réponses sont écrites dans
    les logs au lieu d'être envoyées.
    """

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        api_version: str,
        base_url: str = GRAPH_API_BASE_URL,
        dry_run: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._api_root = f"{base_url.rstrip('/')}/{api_version}"
        self._dry_run = dry_run
        self._transport = transport

    @property
    def messages_url(self) -> str:
        return f"{self._api_root}/{self._phone_number_id}/messages"

    async def send_text(self, to: str, body: str) -> None:
        """Envoie un message texte à un numéro (format international sans « + »)."""
        if self._dry_run:
            logger.info("[simulation] réponse pour ***%s :\n%s", to[-4:], body)
            return
        self._require_configuration(needs_phone_number_id=True)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": _truncate(body)},
        }
        async with self._http_client() as http:
            await self._request(http, "POST", self.messages_url, json=payload)

    async def mark_as_read(self, message_id: str) -> None:
        """Marque un message reçu comme lu (accusé de réception pour l'utilisateur)."""
        if self._dry_run:
            return
        self._require_configuration(needs_phone_number_id=True)
        payload = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
        async with self._http_client() as http:
            await self._request(http, "POST", self.messages_url, json=payload)

    async def download_media(self, media_id: str) -> bytes:
        """Télécharge un média reçu (image) : Meta donne d'abord une URL temporaire."""
        if self._dry_run:
            raise WhatsAppError("Téléchargement de médias indisponible en mode simulation")
        self._require_configuration(needs_phone_number_id=False)
        async with self._http_client() as http:
            info = await self._request(http, "GET", f"{self._api_root}/{media_id}")
            media_url = _read_json(info).get("url")
            if not isinstance(media_url, str) or not media_url.startswith("https://"):
                raise WhatsAppError("Meta n'a pas fourni d'URL valide pour ce média")
            media = await self._request(http, "GET", media_url)
        if len(media.content) > MAX_MEDIA_BYTES:
            raise WhatsAppError("Média trop volumineux")
        return media.content

    def _require_configuration(self, *, needs_phone_number_id: bool) -> None:
        if not self._access_token or (needs_phone_number_id and not self._phone_number_id):
            raise WhatsAppError(
                "Client WhatsApp non configuré (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID)"
            )

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, transport=self._transport)

    async def _request(
        self, http: httpx.AsyncClient, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            response = await http.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise WhatsAppError(_describe_meta_error(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise WhatsAppError(
                f"Appel à l'API WhatsApp impossible ({type(exc).__name__})"
            ) from exc
        return response


def _truncate(body: str) -> str:
    if len(body) <= MAX_TEXT_LENGTH:
        return body
    return body[: MAX_TEXT_LENGTH - 1] + "…"


def _read_json(response: httpx.Response) -> dict[str, Any]:
    """Corps JSON de la réponse ; lève `WhatsAppError` s'il est illisible."""
    try:
        data = response.json()
    except ValueError as exc:
        raise WhatsAppError("Réponse de Meta illisible") from exc
    return data if isinstance(data, dict) else {}


def _describe_meta_error(response: httpx.Response) -> str:
    """Message d'erreur lisible, sans jamais inclure le jeton d'accès."""
    try:
        error = _read_json(response).get("error")
    except WhatsAppError:  # corps non JSON (ex. page d'erreur d'un proxy)
        error = None
    if isinstance(error, dict):
        return (
            f"Meta a refusé la requête (HTTP {response.status_code}, "
            f"code {error.get('code')} : {error.get('message')})"
        )
    return f"Meta a refusé la requête (HTTP {response.status_code})"
