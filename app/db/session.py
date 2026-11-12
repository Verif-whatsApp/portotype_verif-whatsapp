"""Connexion à la base de données et sessions SQLAlchemy."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (enregistre les modèles dans Base.metadata)
from app.config import get_settings
from app.db.base import Base


def build_engine(database_url: str) -> Engine:
    """Crée le moteur SQLAlchemy adapté au type de base."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        options: dict[str, Any] = {
            # FastAPI traite les requêtes dans plusieurs threads
            "connect_args": {"check_same_thread": False},
        }
        if url.database in (None, "", ":memory:"):
            # Une base SQLite en mémoire doit partager une seule connexion
            options["poolclass"] = StaticPool
        return create_engine(database_url, **options)
    return create_engine(database_url, pool_pre_ping=True)


@lru_cache
def get_engine() -> Engine:
    """Moteur de l'application, construit à partir de `DATABASE_URL`."""
    return build_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : fournit une session et la ferme à la fin de la requête."""
    with get_session_factory()() as session:
        yield session


def init_db(engine: Engine | None = None) -> None:
    """Crée les tables manquantes (suffisant pour le MVP, pas de migrations)."""
    Base.metadata.create_all(engine or get_engine())
