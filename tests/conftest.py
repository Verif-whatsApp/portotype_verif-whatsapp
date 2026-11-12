from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db.session import build_engine, init_db


@pytest.fixture
def session() -> Iterator[Session]:
    """Session sur une base SQLite en mémoire, vide à chaque test."""
    engine = build_engine("sqlite://")
    init_db(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()
