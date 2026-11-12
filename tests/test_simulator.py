import json
from typing import Any

import httpx
import pytest

from app.schemas.whatsapp import WebhookPayload
from app.security import is_valid_signature
from scripts import simulate_webhook
from scripts.simulate_webhook import build_payload, main


def test_payload_is_understood_by_the_webhook_schema() -> None:
    payload = WebhookPayload.model_validate(build_payload("Bonjour", "22997001234"))

    (message,) = payload.incoming_messages()
    assert message.type == "text"
    assert message.sender == "22997001234"
    assert message.text is not None
    assert message.text.body == "Bonjour"


def test_each_payload_has_a_unique_message_id() -> None:
    ids = {
        WebhookPayload.model_validate(build_payload("x", "1")).incoming_messages()[0].id
        for _ in range(5)
    }

    assert len(ids) == 5


@pytest.fixture
def sent_requests(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        requests.append({"url": url, **kwargs})
        return httpx.Response(200, json={"status": "received"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(simulate_webhook.httpx, "post", fake_post)
    return requests


def test_request_is_signed_when_a_secret_is_given(
    sent_requests: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--secret", "s3cret", "Un message"]) == 0

    (request,) = sent_requests
    assert request["url"] == "http://localhost:8000/webhook"
    assert is_valid_signature(
        request["content"], request["headers"]["X-Hub-Signature-256"], "s3cret"
    )
    assert json.loads(request["content"])["object"] == "whatsapp_business_account"
    assert "HTTP 200" in capsys.readouterr().out


def test_request_is_unsigned_without_secret(
    sent_requests: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        assert main(["Un message"]) == 0
    finally:
        get_settings.cache_clear()

    assert "X-Hub-Signature-256" not in sent_requests[0]["headers"]


def test_custom_url_and_sender(sent_requests: list[dict[str, Any]]) -> None:
    main(["--secret", "x", "--url", "http://exemple.test/hook", "--sender", "22997000009", "Hi"])

    request = sent_requests[0]
    assert request["url"] == "http://exemple.test/hook"
    sender = json.loads(request["content"])["entry"][0]["changes"][0]["value"]["messages"][0][
        "from"
    ]
    assert sender == "22997000009"


def test_unreachable_server_is_reported(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse(url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("refusé")

    monkeypatch.setattr(simulate_webhook.httpx, "post", refuse)

    assert main(["--secret", "x", "Un message"]) == 1
    assert "injoignable" in capsys.readouterr().err


def test_refused_request_returns_an_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(403, request=httpx.Request("POST", url))

    monkeypatch.setattr(simulate_webhook.httpx, "post", refuse)

    assert main(["--secret", "x", "Un message"]) == 1
