"""Point d'entrée FastAPI de Vérif'WhatsApp."""

import logging

from fastapi import FastAPI

from app import __version__
from app.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Construit l'application FastAPI."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    application = FastAPI(
        title="Vérif'WhatsApp",
        version=__version__,
        description="Robot de fact-checking WhatsApp pour l'Afrique de l'Ouest.",
    )

    @application.get("/health", tags=["monitoring"])
    def health() -> dict[str, str]:
        """Vérifie que le service répond."""
        return {"status": "ok"}

    logger.info("Application démarrée (env=%s)", settings.app_env)
    return application


app = create_app()
