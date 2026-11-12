import pytest
from pydantic import ValidationError

from app.config import Settings


def make_settings() -> Settings:
    # _env_file=None : les tests ne dépendent pas d'un éventuel fichier .env local
    return Settings(_env_file=None)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APP_ENV", "APP_PORT", "LOG_LEVEL", "MATCHING_THRESHOLD", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)

    settings = make_settings()

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.log_level == "INFO"
    assert settings.matching_threshold == 85
    assert settings.database_url == "sqlite:///./verif.db"
    assert settings.is_production is False


def test_values_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_PORT", "9000")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret")

    settings = make_settings()

    assert settings.is_production is True
    assert settings.app_port == 9000
    assert settings.whatsapp_verify_token == "secret"


def test_log_level_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert make_settings().log_level == "DEBUG"


@pytest.mark.parametrize("value", ["-1", "101", "abc"])
def test_matching_threshold_must_be_between_0_and_100(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("MATCHING_THRESHOLD", value)

    with pytest.raises(ValidationError):
        make_settings()


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValidationError):
        make_settings()
