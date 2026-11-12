"""Configuration de l'application, chargée depuis les variables d'environnement."""

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application.

    Les valeurs sont lues dans les variables d'environnement, puis dans le fichier
    `.env` s'il existe (voir `.env.example`). Les noms ne sont pas sensibles à la casse.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # WhatsApp Business API (Meta)
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"

    # Application
    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Base de données
    database_url: str = "sqlite:///./verif.db"

    # Matching : score de similarité minimal (0-100) pour retenir une correspondance
    matching_threshold: int = Field(default=85, ge=0, le=100)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        """Accepte `info`, `Info`, `INFO`... et normalise en majuscules."""
        return value.upper() if isinstance(value, str) else value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Retourne les paramètres (instance unique mise en cache)."""
    return Settings()
