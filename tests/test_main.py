import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.main import create_app

CACHED = (get_settings, get_engine, get_session_factory)


@pytest.fixture
def in_memory_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    for cached in CACHED:
        cached.cache_clear()
    yield  # type: ignore[misc]
    for cached in CACHED:
        cached.cache_clear()


@pytest.mark.usefixtures("in_memory_database")
def test_startup_creates_the_database_tables() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        assert "verifications" in inspect(get_engine()).get_table_names()


@pytest.mark.usefixtures("in_memory_database")
def test_webhook_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]

    assert set(paths) >= {"/health", "/webhook"}
    assert set(paths["/webhook"]) == {"get", "post"}


def clear_whatsapp_settings(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for name in (
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
    ):
        monkeypatch.setenv(name, values.get(name, ""))
    get_settings.cache_clear()


@pytest.mark.usefixtures("in_memory_database")
def test_startup_warns_about_incomplete_whatsapp_configuration(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    clear_whatsapp_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING, logger="app.main"), TestClient(create_app()):
        pass

    assert "variables absentes" in caplog.text
    assert "WHATSAPP_APP_SECRET" in caplog.text
    assert "écrites dans les logs" in caplog.text
    assert "non vérifiée" in caplog.text


@pytest.mark.usefixtures("in_memory_database")
def test_startup_in_production_warns_that_requests_will_be_refused(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    clear_whatsapp_settings(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING, logger="app.main"), TestClient(create_app()):
        pass

    assert "seront refusées" in caplog.text


@pytest.mark.usefixtures("in_memory_database")
def test_startup_is_quiet_when_everything_is_configured(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    clear_whatsapp_settings(
        monkeypatch,
        WHATSAPP_VERIFY_TOKEN="v",
        WHATSAPP_ACCESS_TOKEN="a",
        WHATSAPP_PHONE_NUMBER_ID="1",
        WHATSAPP_APP_SECRET="s",
    )

    with caplog.at_level(logging.WARNING, logger="app.main"), TestClient(create_app()):
        pass

    assert caplog.text == ""
