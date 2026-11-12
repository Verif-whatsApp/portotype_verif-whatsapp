from datetime import date

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import (
    build_engine,
    get_engine,
    get_session,
    get_session_factory,
    init_db,
)
from app.models import Verdict, Verification
from tests.factories import make_verification


def test_init_db_creates_verifications_table() -> None:
    engine = build_engine("sqlite://")

    init_db(engine)

    assert "verifications" in inspect(engine).get_table_names()


def test_verification_round_trip(session: Session) -> None:
    session.add(
        make_verification(
            claim_variants=["Attaque terroriste à Doropo, restez chez vous"],
            verdict=Verdict.TROMPEUR,
            verified_at=date(2026, 10, 12),
        )
    )
    session.commit()
    session.expire_all()

    saved = session.scalars(select(Verification)).one()

    assert saved.id is not None
    assert saved.verdict is Verdict.TROMPEUR
    assert saved.verified_at == date(2026, 10, 12)
    assert saved.claim_variants == ["Attaque terroriste à Doropo, restez chez vous"]
    assert saved.source_url == "https://example.org/verification/doropo"


def test_verdict_is_stored_as_its_value(session: Session) -> None:
    session.add(make_verification(verdict=Verdict.NON_VERIFIE))
    session.commit()

    stored = session.execute(text("SELECT verdict FROM verifications")).scalar_one()

    assert stored == "non_verifie"


def test_defaults_when_optional_fields_are_omitted(session: Session) -> None:
    session.add(
        Verification(
            claim_text="Une rumeur",
            verdict=Verdict.FAUX,
            explanation="Faux.",
            source_name="Africa Check",
            verified_at=date(2026, 11, 1),
        )
    )
    session.commit()
    session.expire_all()

    saved = session.scalars(select(Verification)).one()

    assert saved.language == "fr"
    assert saved.claim_variants == []
    assert saved.source_url is None


def test_formulations_lists_claim_then_variants() -> None:
    verification = make_verification(claim_text="A", claim_variants=["B", "C"])

    assert verification.formulations == ["A", "B", "C"]


def test_repr_mentions_verdict_and_source() -> None:
    representation = repr(make_verification(source_name="Africa Check"))

    assert "Africa Check" in representation
    assert "faux" in representation


def test_formulations_without_variants_on_unsaved_object() -> None:
    verification = Verification(claim_text="A")

    assert verification.formulations == ["A"]


def test_get_session_yields_a_working_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    for cached in (get_settings, get_engine, get_session_factory):
        cached.cache_clear()
    try:
        init_db()
        generator = get_session()
        db_session = next(generator)

        assert isinstance(db_session, Session)
        assert db_session.scalars(select(Verification)).all() == []

        generator.close()
    finally:
        for cached in (get_settings, get_engine, get_session_factory):
            cached.cache_clear()
