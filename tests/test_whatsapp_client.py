import json
import logging

import httpx
import pytest

from app.services.whatsapp import MAX_TEXT_LENGTH, WhatsAppClient, WhatsAppError

TOKEN = "secret-access-token"


def make_client(handler: httpx.MockTransport | None = None, **overrides: object) -> WhatsAppClient:
    options: dict[str, object] = {
        "access_token": TOKEN,
        "phone_number_id": "123456",
        "api_version": "v25.0",
        "transport": handler,
    }
    options.update(overrides)
    return WhatsAppClient(**options)  # type: ignore[arg-type]


def recording_transport(
    requests: list[httpx.Request], response: httpx.Response | None = None
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response or httpx.Response(200, json={"messages": [{"id": "wamid.OUT"}]})

    return httpx.MockTransport(handler)


async def test_send_text_posts_the_expected_request() -> None:
    requests: list[httpx.Request] = []
    client = make_client(recording_transport(requests))

    await client.send_text("22997000000", "Bonjour")

    (request,) = requests
    assert request.method == "POST"
    assert str(request.url) == "https://graph.facebook.com/v25.0/123456/messages"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(request.content) == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "22997000000",
        "type": "text",
        "text": {"preview_url": False, "body": "Bonjour"},
    }


async def test_long_text_is_truncated_to_the_whatsapp_limit() -> None:
    requests: list[httpx.Request] = []
    client = make_client(recording_transport(requests))

    await client.send_text("22997000000", "a" * (MAX_TEXT_LENGTH + 500))

    body = json.loads(requests[0].content)["text"]["body"]
    assert len(body) == MAX_TEXT_LENGTH
    assert body.endswith("…")


async def test_mark_as_read_posts_the_read_status() -> None:
    requests: list[httpx.Request] = []
    client = make_client(recording_transport(requests))

    await client.mark_as_read("wamid.IN")

    assert json.loads(requests[0].content) == {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": "wamid.IN",
    }


async def test_meta_error_is_reported_without_leaking_the_token() -> None:
    error = {"error": {"message": "Invalid OAuth access token", "code": 190}}
    client = make_client(recording_transport([], httpx.Response(401, json=error)))

    with pytest.raises(WhatsAppError) as excinfo:
        await client.send_text("22997000000", "Bonjour")

    message = str(excinfo.value)
    assert "401" in message
    assert "190" in message
    assert "Invalid OAuth access token" in message
    assert TOKEN not in message


async def test_error_without_json_body_is_reported() -> None:
    client = make_client(recording_transport([], httpx.Response(502, text="Bad gateway")))

    with pytest.raises(WhatsAppError, match="HTTP 502"):
        await client.send_text("22997000000", "Bonjour")


async def test_network_failure_becomes_a_whatsapp_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(WhatsAppError, match="ConnectError"):
        await client.send_text("22997000000", "Bonjour")


@pytest.mark.parametrize("missing", ["access_token", "phone_number_id"])
async def test_unconfigured_client_refuses_to_send(missing: str) -> None:
    requests: list[httpx.Request] = []
    client = make_client(recording_transport(requests), **{missing: ""})

    with pytest.raises(WhatsAppError, match="non configuré"):
        await client.send_text("22997000000", "Bonjour")

    assert requests == []


async def test_download_media_fetches_url_then_content() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v25.0/MEDIA42":
            return httpx.Response(200, json={"url": "https://lookaside.example/file?id=42"})
        return httpx.Response(200, content=b"\x89PNG-bytes")

    client = make_client(httpx.MockTransport(handler))

    assert await client.download_media("MEDIA42") == b"\x89PNG-bytes"
    assert [str(r.url) for r in requests] == [
        "https://graph.facebook.com/v25.0/MEDIA42",
        "https://lookaside.example/file?id=42",
    ]
    assert all(r.headers["Authorization"] == f"Bearer {TOKEN}" for r in requests)


@pytest.mark.parametrize(
    "info",
    [{}, {"url": ""}, {"url": "http://insecure.example/file"}, {"url": 42}],
)
async def test_download_media_rejects_missing_or_insecure_url(info: dict[str, object]) -> None:
    client = make_client(recording_transport([], httpx.Response(200, json=info)))

    with pytest.raises(WhatsAppError, match="URL valide"):
        await client.download_media("MEDIA42")


async def test_download_media_rejects_unreadable_metadata() -> None:
    client = make_client(recording_transport([], httpx.Response(200, text="pas du json")))

    with pytest.raises(WhatsAppError, match="illisible"):
        await client.download_media("MEDIA42")


async def test_download_media_rejects_oversized_files() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "graph.facebook.com":
            return httpx.Response(200, json={"url": "https://lookaside.example/big"})
        return httpx.Response(200, content=b"x" * (10 * 1024 * 1024 + 1))

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(WhatsAppError, match="volumineux"):
        await client.download_media("MEDIA42")


async def test_dry_run_logs_instead_of_sending(caplog: pytest.LogCaptureFixture) -> None:
    requests: list[httpx.Request] = []
    client = make_client(recording_transport(requests), access_token="", dry_run=True)

    with caplog.at_level(logging.INFO, logger="app.services.whatsapp"):
        await client.send_text("22997001234", "Réponse de test")
        await client.mark_as_read("wamid.IN")

    assert requests == []
    assert "[simulation]" in caplog.text
    assert "Réponse de test" in caplog.text
    assert "***1234" in caplog.text
    assert "22997001234" not in caplog.text


async def test_dry_run_cannot_download_media() -> None:
    client = make_client(access_token="", dry_run=True)

    with pytest.raises(WhatsAppError, match="simulation"):
        await client.download_media("MEDIA42")
