"""Point d'entrée FastAPI de Vérif'WhatsApp."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.webhook import router as webhook_router
from app.config import Settings, get_settings
from app.db.session import init_db

logger = logging.getLogger(__name__)


def log_configuration_warnings(settings: Settings) -> None:
    """Signale au démarrage une configuration WhatsApp incomplète."""
    missing = settings.missing_whatsapp_settings
    if missing:
        logger.warning(
            "Configuration WhatsApp incomplète, variables absentes : %s", ", ".join(missing)
        )
    if not settings.whatsapp_access_token and not settings.is_production:
        logger.warning("WHATSAPP_ACCESS_TOKEN absent : les réponses sont écrites dans les logs")
    if not settings.whatsapp_app_secret:
        logger.warning(
            "WHATSAPP_APP_SECRET absent : %s",
            "toutes les requêtes du webhook seront refusées"
            if settings.is_production
            else "signature des requêtes non vérifiée (développement uniquement)",
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prépare la base de données et contrôle la configuration au démarrage."""
    init_db()
    log_configuration_warnings(get_settings())
    yield


def create_app() -> FastAPI:
    """Construit l'application FastAPI."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    application = FastAPI(
        title="Vérif'WhatsApp",
        version=__version__,
        description="Robot de fact-checking WhatsApp pour l'Afrique de l'Ouest.",
        lifespan=lifespan,
    )

    @application.get("/health", tags=["monitoring"])
    def health() -> dict[str, str]:
        """Vérifie que le service répond."""
        return {"status": "ok"}

    application.include_router(webhook_router)

    logger.info("Application démarrée (env=%s)", settings.app_env)
    return application


app = create_app()
