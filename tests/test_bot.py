import logging

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.whatsapp import IncomingMessage
from app.services import bot
from app.services.bot import MessageDeduplicator, handle_incoming_message, mask_phone_number
from tests.factories import (
    SENDER,
    image_message,
    make_verification,
    other_message,
    text_message,
)
from tests.fakes import FakeGateway, whatsapp_error

CLAIM = "ALERTE : Attaque à Doropo, ne sortez pas"


def incoming(raw: dict[str, object]) -> IncomingMessage:
    return IncomingMessage.model_validate(raw)


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def knowledge_base(session_factory: sessionmaker[Session]) -> sessionmaker[Session]:
    with session_factory() as session:
        session.add(make_verification(claim_text=CLAIM))
        session.commit()
    return session_factory


# --- doublons -----------------------------------------------------------------------------


def test_first_sight_is_not_a_duplicate_second_is() -> None:
    deduplicator = MessageDeduplicator()

    assert deduplicator.is_duplicate("wamid.1") is False
    assert deduplicator.is_duplicate("wamid.1") is True
    assert deduplicator.is_duplicate("wamid.2") is False


def test_deduplicator_forgets_the_oldest_ids_beyond_its_capacity() -> None:
    deduplicator = MessageDeduplicator(capacity=2)
    for message_id in ("a", "b", "c"):
        deduplicator.is_duplicate(message_id)

    assert deduplicator.is_duplicate("a") is False  # oublié
    assert deduplicator.is_duplicate("c") is True  # encore connu


def test_recently_seen_id_is_kept_longer() -> None:
    deduplicator = MessageDeduplicator(capacity=2)
    deduplicator.is_duplicate("a")
    deduplicator.is_duplicate("b")
    deduplicator.is_duplicate("a")  # « a » redevient récent
    deduplicator.is_duplicate("c")  # évince « b »

    assert deduplicator.is_duplicate("a") is True
    assert deduplicator.is_duplicate("b") is False


@pytest.mark.parametrize(
    ("number", "masked"),
    [("22997123456", "***3456"), ("1234", "***"), ("", "***")],
)
def test_mask_phone_number(number: str, masked: str) -> None:
    assert mask_phone_number(number) == masked


# --- messages texte -----------------------------------------------------------------------


async def test_known_claim_gets_its_verdict(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session]
) -> None:
    await handle_incoming_message(incoming(text_message(CLAIM)), gateway, knowledge_base)

    assert gateway.read == ["wamid.TEXT1"]
    ((recipient, reply),) = gateway.sent
    assert recipient == SENDER
    assert reply.startswith("🚫 FAUX")
    assert "IvoireCheck" in reply


async def test_unknown_text_gets_the_unverified_message(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session]
) -> None:
    message = incoming(text_message("Le marché de Cotonou ouvre à 7 heures ce samedi"))

    await handle_incoming_message(message, gateway, knowledge_base)

    assert gateway.sent[0][1].startswith("❓ NON VÉRIFIÉ POUR L'INSTANT")


@pytest.mark.parametrize("body", ["", "   \n "])
async def test_blank_text_gets_the_unsupported_message(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session], body: str
) -> None:
    await handle_incoming_message(incoming(text_message(body)), gateway, knowledge_base)

    assert "ne peux pas traiter" in gateway.sent[0][1]


@pytest.mark.parametrize("message_type", ["audio", "video", "document", "sticker", "location"])
async def test_unsupported_types_get_a_polite_reply(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session], message_type: str
) -> None:
    await handle_incoming_message(incoming(other_message(message_type)), gateway, knowledge_base)

    assert "ne peux pas traiter" in gateway.sent[0][1]


@pytest.mark.parametrize("message_type", ["reaction", "system"])
async def test_reactions_and_system_messages_are_ignored(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session], message_type: str
) -> None:
    await handle_incoming_message(incoming(other_message(message_type)), gateway, knowledge_base)

    assert gateway.sent == []
    assert gateway.read == []


# --- images (OCR) -------------------------------------------------------------------------


async def test_image_text_is_extracted_then_verified(
    gateway: FakeGateway,
    knowledge_base: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extracted: list[bytes] = []

    def fake_ocr(image_bytes: bytes) -> str:
        extracted.append(image_bytes)
        return CLAIM

    monkeypatch.setattr(bot, "extract_text_from_image", fake_ocr)

    await handle_incoming_message(incoming(image_message("MEDIA9")), gateway, knowledge_base)

    assert gateway.downloaded == ["MEDIA9"]
    assert extracted == [b"image-bytes"]
    assert gateway.sent[0][1].startswith("🚫 FAUX")


async def test_image_without_readable_text_gets_a_helpful_reply(
    gateway: FakeGateway,
    knowledge_base: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bot, "extract_text_from_image", lambda _image: None)

    await handle_incoming_message(incoming(image_message()), gateway, knowledge_base)

    assert "pas réussi à lire" in gateway.sent[0][1]
    assert "copier-coller" in gateway.sent[0][1]


async def test_image_download_failure_gets_an_image_error_reply(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session]
) -> None:
    gateway.media_error = whatsapp_error("média expiré")

    await handle_incoming_message(incoming(image_message()), gateway, knowledge_base)

    assert gateway.sent[0][1] == "📸 Une erreur est survenue lors de l'analyse de l'image."


async def test_image_message_without_image_data_is_unsupported(
    gateway: FakeGateway, knowledge_base: sessionmaker[Session]
) -> None:
    await handle_incoming_message(incoming(other_message("image")), gateway, knowledge_base)

    assert "ne peux pas traiter" in gateway.sent[0][1]


# --- pannes -------------------------------------------------------------------------------


async def test_failed_read_receipt_does_not_block_the_reply(
    gateway: FakeGateway,
    knowledge_base: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gateway.read_error = whatsapp_error("lecture refusée")

    with caplog.at_level(logging.WARNING, logger="app.services.bot"):
        await handle_incoming_message(incoming(text_message(CLAIM)), gateway, knowledge_base)

    assert len(gateway.sent) == 1
    assert "Accusé de lecture impossible" in caplog.text


async def test_failed_send_is_logged_and_never_raised(
    gateway: FakeGateway,
    knowledge_base: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gateway.send_error = whatsapp_error("token expiré")

    with caplog.at_level(logging.ERROR, logger="app.services.bot"):
        await handle_incoming_message(incoming(text_message(CLAIM)), gateway, knowledge_base)

    assert "token expiré" in caplog.text
    assert "***1234" in caplog.text


async def test_unexpected_error_sends_a_generic_apology(gateway: FakeGateway) -> None:
    def broken_session_factory() -> Session:
        raise RuntimeError("base de données indisponible")

    await handle_incoming_message(incoming(text_message(CLAIM)), gateway, broken_session_factory)

    assert gateway.sent == [
        (SENDER, "Désolé, une erreur technique est survenue. Veuillez réessayer plus tard.")
    ]


async def test_unexpected_error_and_failed_apology_still_do_not_raise(
    gateway: FakeGateway,
) -> None:
    def broken_session_factory() -> Session:
        raise RuntimeError("base de données indisponible")

    original_send = gateway.send_text
    calls = 0

    async def failing_send(to: str, body: str) -> None:
        nonlocal calls
        calls += 1
        raise whatsapp_error("réseau coupé")

    gateway.send_text = failing_send  # type: ignore[method-assign]

    await handle_incoming_message(incoming(text_message(CLAIM)), gateway, broken_session_factory)

    assert calls == 1
    gateway.send_text = original_send  # type: ignore[method-assign]


# --- confidentialité ----------------------------------------------------------------------


async def test_logs_never_contain_message_text_or_full_phone_number(
    gateway: FakeGateway,
    knowledge_base: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gateway.read_error = whatsapp_error("lecture refusée")
    gateway.send_error = whatsapp_error("envoi refusé")

    with caplog.at_level(logging.DEBUG):
        await handle_incoming_message(incoming(text_message(CLAIM)), gateway, knowledge_base)

    assert caplog.text  # des logs ont bien été produits
    assert "Doropo" not in caplog.text
    assert SENDER not in caplog.text
