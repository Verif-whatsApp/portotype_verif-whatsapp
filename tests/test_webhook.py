import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.webhook import get_deduplicator, get_whatsapp_client
from app.config import Settings, get_settings
from app.db.session import get_session_factory
from app.main import create_app
from app.security import compute_signature
from app.services.bot import MessageDeduplicator
from app.services.whatsapp import WhatsAppError
from tests.factories import (
    SENDER,
    image_message,
    make_verification,
    other_message,
    status_payload,
    text_message,
    webhook_payload,
)
from tests.fakes import FakeGateway, whatsapp_error

VERIFY_TOKEN = "verify-me"
APP_SECRET = "app-secret"
CLAIM = "ALERTE : Attaque à Doropo, ne sortez pas"


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "whatsapp_verify_token": VERIFY_TOKEN,
        "whatsapp_app_secret": APP_SECRET,
        "whatsapp_access_token": "access-token",
        "whatsapp_phone_number_id": "123456",
        "app_env": "development",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def client_for(gateway: FakeGateway, session_factory: sessionmaker[Session]) -> Any:
    """Fabrique un client de test dont les dépendances (config, WhatsApp, base) sont doublées."""
    with session_factory() as session:
        session.add(make_verification(claim_text=CLAIM))
        session.commit()

    def build(settings: Settings | None = None) -> TestClient:
        chosen = settings or make_settings()
        deduplicator = MessageDeduplicator()
        application = create_app()
        application.dependency_overrides[get_settings] = lambda: chosen
        application.dependency_overrides[get_whatsapp_client] = lambda: gateway
        application.dependency_overrides[get_session_factory] = lambda: session_factory
        application.dependency_overrides[get_deduplicator] = lambda: deduplicator
        return TestClient(application)

    return build


@pytest.fixture
def client(client_for: Any) -> TestClient:
    return client_for()  # type: ignore[no-any-return]


def post_signed(client: TestClient, payload: dict[str, Any], *, secret: str = APP_SECRET) -> Any:
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": compute_signature(body, secret),
    }
    return client.post("/webhook", content=body, headers=headers)


# --- GET : vérification par Meta ----------------------------------------------------------


def verification_params(**overrides: str) -> dict[str, str]:
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": VERIFY_TOKEN,
        "hub.challenge": "1158201444",
    }
    params.update(overrides)
    return params


def test_meta_verification_echoes_the_challenge_as_plain_text(client: TestClient) -> None:
    response = client.get("/webhook", params=verification_params())

    assert response.status_code == 200
    assert response.text == "1158201444"
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize(
    "overrides",
    [
        {"hub.verify_token": "mauvais"},
        {"hub.mode": "unsubscribe"},
        {"hub.verify_token": ""},
    ],
)
def test_meta_verification_is_refused_on_wrong_values(
    client: TestClient, overrides: dict[str, str]
) -> None:
    response = client.get("/webhook", params=verification_params(**overrides))

    assert response.status_code == 403


@pytest.mark.parametrize("missing", ["hub.mode", "hub.verify_token", "hub.challenge"])
def test_meta_verification_is_refused_when_a_parameter_is_missing(
    client: TestClient, missing: str
) -> None:
    params = verification_params()
    del params[missing]

    assert client.get("/webhook", params=params).status_code == 403


def test_meta_verification_never_accepts_an_unset_verify_token(client_for: Any) -> None:
    client = client_for(make_settings(whatsapp_verify_token=""))

    response = client.get("/webhook", params=verification_params(**{"hub.verify_token": ""}))

    assert response.status_code == 403


# --- POST : réception des messages ---------------------------------------------------------


def test_text_message_is_verified_and_answered(client: TestClient, gateway: FakeGateway) -> None:
    response = post_signed(client, webhook_payload(text_message(CLAIM)))

    assert response.status_code == 200
    assert response.json() == {"status": "received"}
    assert gateway.read == ["wamid.TEXT1"]
    ((recipient, reply),) = gateway.sent
    assert recipient == SENDER
    assert reply.startswith("🚫 FAUX")


def test_unknown_message_gets_the_unverified_reply(
    client: TestClient, gateway: FakeGateway
) -> None:
    post_signed(client, webhook_payload(text_message("Le marché ouvre à 7 heures ce samedi")))

    assert gateway.sent[0][1].startswith("❓ NON VÉRIFIÉ POUR L'INSTANT")


def test_unsupported_message_type_gets_a_polite_reply(
    client: TestClient, gateway: FakeGateway
) -> None:
    post_signed(client, webhook_payload(other_message("audio")))

    assert "ne peux pas traiter" in gateway.sent[0][1]


def test_image_is_downloaded_through_the_gateway(
    client: TestClient, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import bot

    monkeypatch.setattr(bot, "extract_text_from_image", lambda _image: CLAIM)

    post_signed(client, webhook_payload(image_message("MEDIA7")))

    assert gateway.downloaded == ["MEDIA7"]
    assert gateway.sent[0][1].startswith("🚫 FAUX")


def test_every_message_of_a_notification_is_handled(
    client: TestClient, gateway: FakeGateway
) -> None:
    payload = webhook_payload(
        text_message(CLAIM, message_id="wamid.A", sender="22997000001"),
        text_message(
            "Autre message sans rapport avec la base", message_id="wamid.B", sender="22997000002"
        ),
    )

    post_signed(client, payload)

    assert [to for to, _ in gateway.sent] == ["22997000001", "22997000002"]


def test_redelivered_message_is_answered_once(client: TestClient, gateway: FakeGateway) -> None:
    payload = webhook_payload(text_message(CLAIM))

    first = post_signed(client, payload)
    second = post_signed(client, payload)

    assert first.status_code == second.status_code == 200
    assert len(gateway.sent) == 1


def test_status_notifications_are_acknowledged_without_reply(
    client: TestClient, gateway: FakeGateway
) -> None:
    response = post_signed(client, status_payload())

    assert response.status_code == 200
    assert gateway.sent == []


def test_reactions_get_no_reply(client: TestClient, gateway: FakeGateway) -> None:
    post_signed(client, webhook_payload(other_message("reaction")))

    assert gateway.sent == []


def test_notification_for_another_object_is_ignored(
    client: TestClient, gateway: FakeGateway
) -> None:
    payload = webhook_payload(text_message(CLAIM))
    payload["object"] = "page"

    response = post_signed(client, payload)

    assert response.status_code == 200
    assert gateway.sent == []


@pytest.mark.parametrize("raw_body", [b"pas du json", b"[]", b'{"entry": "x"}', b"{}"])
def test_authentic_but_malformed_notification_is_ignored_with_200(
    client: TestClient, gateway: FakeGateway, raw_body: bytes
) -> None:
    headers = {"X-Hub-Signature-256": compute_signature(raw_body, APP_SECRET)}

    response = client.post("/webhook", content=raw_body, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    assert gateway.sent == []


def test_a_failing_send_does_not_break_the_webhook_response(
    client: TestClient, gateway: FakeGateway
) -> None:
    gateway.send_error = whatsapp_error("token expiré")

    response = post_signed(client, webhook_payload(text_message(CLAIM)))

    assert response.status_code == 200


# --- POST : authenticité ------------------------------------------------------------------


def test_invalid_signature_is_refused(client: TestClient, gateway: FakeGateway) -> None:
    response = post_signed(client, webhook_payload(text_message(CLAIM)), secret="autre-secret")

    assert response.status_code == 403
    assert gateway.sent == []


def test_missing_signature_is_refused(client: TestClient, gateway: FakeGateway) -> None:
    body = json.dumps(webhook_payload(text_message(CLAIM)))

    response = client.post("/webhook", content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 403
    assert gateway.sent == []


def test_body_modified_after_signing_is_refused(client: TestClient, gateway: FakeGateway) -> None:
    signed = json.dumps(webhook_payload(text_message("message inoffensif"))).encode()
    forged = json.dumps(webhook_payload(text_message(CLAIM))).encode()
    headers = {"X-Hub-Signature-256": compute_signature(signed, APP_SECRET)}

    response = client.post("/webhook", content=forged, headers=headers)

    assert response.status_code == 403
    assert gateway.sent == []


def test_unsigned_requests_are_accepted_in_development_without_app_secret(
    client_for: Any, gateway: FakeGateway
) -> None:
    client = client_for(make_settings(whatsapp_app_secret="", app_env="development"))
    body = json.dumps(webhook_payload(text_message(CLAIM)))

    response = client.post("/webhook", content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 200
    assert len(gateway.sent) == 1


def test_production_without_app_secret_refuses_everything(
    client_for: Any, gateway: FakeGateway
) -> None:
    client = client_for(make_settings(whatsapp_app_secret="", app_env="production"))
    body = json.dumps(webhook_payload(text_message(CLAIM)))

    response = client.post("/webhook", content=body, headers={"Content-Type": "application/json"})

    assert response.status_code == 403
    assert gateway.sent == []


# --- dépendances --------------------------------------------------------------------------


async def test_development_without_credentials_runs_in_simulation_mode(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = get_whatsapp_client(make_settings(whatsapp_access_token="", app_env="development"))

    with caplog.at_level(logging.INFO, logger="app.services.whatsapp"):
        await client.send_text(SENDER, "Réponse de test")

    assert "[simulation]" in caplog.text


async def test_production_without_credentials_refuses_to_send() -> None:
    client = get_whatsapp_client(make_settings(whatsapp_access_token="", app_env="production"))

    with pytest.raises(WhatsAppError, match="non configuré"):
        await client.send_text(SENDER, "Réponse de test")


def test_deduplicator_is_shared_between_requests() -> None:
    assert get_deduplicator() is get_deduplicator()
