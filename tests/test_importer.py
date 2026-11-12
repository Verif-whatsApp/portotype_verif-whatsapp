import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.models import Verdict, Verification
from app.services.formatting import format_response
from app.services.importer import (
    KnowledgeBaseError,
    import_verifications,
    load_entries,
    parse_entry,
)
from app.services.matching import find_best_match
from scripts.import_verifications import main

REPOSITORY = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = REPOSITORY / "data" / "verifications.example.json"


def valid_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "claim_text": "Une rumeur",
        "verdict": "faux",
        "explanation": "Faux : démenti officiel.",
        "source_name": "Africa Check",
        "verified_at": "2026-10-12",
    }
    entry.update(overrides)
    return entry


def count_rows(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Verification)) or 0


# --- lecture du fichier -------------------------------------------------------------------


def test_load_entries_reads_a_list(tmp_path: Path) -> None:
    file = tmp_path / "base.json"
    file.write_text(json.dumps([valid_entry()]), encoding="utf-8")

    assert load_entries(file) == [valid_entry()]


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(KnowledgeBaseError, match="Fichier introuvable"):
        load_entries(tmp_path / "absent.json")


def test_invalid_json_is_reported(tmp_path: Path) -> None:
    file = tmp_path / "base.json"
    file.write_text("{pas du json", encoding="utf-8")

    with pytest.raises(KnowledgeBaseError, match="JSON invalide"):
        load_entries(file)


def test_json_object_instead_of_list_is_reported(tmp_path: Path) -> None:
    file = tmp_path / "base.json"
    file.write_text("{}", encoding="utf-8")

    with pytest.raises(KnowledgeBaseError, match="liste"):
        load_entries(file)


# --- validation des entrées ---------------------------------------------------------------


def test_parse_entry_builds_a_verification() -> None:
    verification = parse_entry(
        valid_entry(
            claim_variants=["Autre formulation"],
            source_url="https://example.org/x",
            language="fon",
        ),
        position=1,
    )

    assert verification.claim_text == "Une rumeur"
    assert verification.verdict is Verdict.FAUX
    assert verification.verified_at == date(2026, 10, 12)
    assert verification.claim_variants == ["Autre formulation"]
    assert verification.source_url == "https://example.org/x"
    assert verification.language == "fon"


def test_parse_entry_defaults() -> None:
    verification = parse_entry(valid_entry(), position=1)

    assert verification.claim_variants == []
    assert verification.source_url is None
    assert verification.language == "fr"


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ("pas un objet", "objet JSON attendu"),
        ({}, "champs manquants ou vides : claim_text, verdict"),
        (valid_entry(claim_text="   "), "claim_text"),
        (valid_entry(source_name=None), "source_name"),
        (valid_entry(verdict="peut-être"), "verdict « peut-être » inconnu"),
        (valid_entry(verified_at="12/10/2026"), "verified_at « 12/10/2026 » invalide"),
        (valid_entry(claim_variants="pas une liste"), "claim_variants"),
        (valid_entry(claim_variants=[1, 2]), "claim_variants"),
        (valid_entry(source_url=42), "source_url"),
        (valid_entry(language=3), "language"),
    ],
)
def test_parse_entry_rejects_invalid_entries(entry: object, message: str) -> None:
    with pytest.raises(KnowledgeBaseError, match=message):
        parse_entry(entry, position=4)


def test_error_mentions_the_entry_position() -> None:
    with pytest.raises(KnowledgeBaseError, match="Entrée n°4"):
        parse_entry({}, position=4)


# --- import en base -----------------------------------------------------------------------


def test_import_adds_new_entries(session: Session) -> None:
    report = import_verifications(session, [valid_entry(), valid_entry(claim_text="Autre")])

    assert (report.added, report.skipped) == (2, 0)
    assert count_rows(session) == 2


def test_import_is_repeatable(session: Session) -> None:
    entries = [valid_entry(), valid_entry(claim_text="Autre")]
    import_verifications(session, entries)

    report = import_verifications(session, entries)

    assert (report.added, report.skipped) == (0, 2)
    assert count_rows(session) == 2


def test_duplicates_inside_the_file_are_imported_once(session: Session) -> None:
    report = import_verifications(session, [valid_entry(), valid_entry()])

    assert (report.added, report.skipped) == (1, 1)


def test_one_invalid_entry_imports_nothing(session: Session) -> None:
    entries = [valid_entry(), valid_entry(claim_text="Autre", verdict="inconnu")]

    with pytest.raises(KnowledgeBaseError, match="Entrée n°2"):
        import_verifications(session, entries)

    assert count_rows(session) == 0


def test_imported_values_are_stored_correctly(session: Session) -> None:
    import_verifications(session, [valid_entry(verdict="trompeur", verified_at="2026-03-05")])
    session.expire_all()

    saved = session.scalars(select(Verification)).one()

    assert saved.verdict is Verdict.TROMPEUR
    assert saved.verified_at == date(2026, 3, 5)


# --- fichier d'exemple fourni dans le dépôt -----------------------------------------------


def test_example_file_is_valid_and_clearly_fictional(session: Session) -> None:
    report = import_verifications(session, load_entries(EXAMPLE_FILE))

    assert report.added == 2
    for verification in session.scalars(select(Verification)):
        assert verification.claim_text.startswith("EXEMPLE FICTIF")
        assert "fictive" in verification.explanation


def test_example_claim_goes_from_import_to_reply(session: Session) -> None:
    import_verifications(session, load_entries(EXAMPLE_FILE))

    match = find_best_match(
        session,
        "Urgent ! EXEMPLE FICTIF : une rumeur inventée pour tester le robot "
        "de vérification WhatsApp. Partagez !",
        85,
    )

    assert match is not None
    assert format_response(match).startswith("🚫 FAUX")


# --- commande -----------------------------------------------------------------------------


@pytest.fixture
def database_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path}")
    for cached in (get_settings, get_engine, get_session_factory):
        cached.cache_clear()
    yield path  # type: ignore[misc]
    get_engine().dispose()
    for cached in (get_settings, get_engine, get_session_factory):
        cached.cache_clear()


def test_command_imports_the_file(database_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(EXAMPLE_FILE)]) == 0
    assert "2 vérification(s) importée(s), 0 déjà présente(s)" in capsys.readouterr().out

    assert main([str(EXAMPLE_FILE)]) == 0
    assert "0 vérification(s) importée(s), 2 déjà présente(s)" in capsys.readouterr().out
    assert database_file.exists()


def test_command_reports_errors_without_traceback(
    database_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "absent.json")]) == 1

    captured = capsys.readouterr()
    assert "Fichier introuvable" in captured.err
    assert captured.out == ""


def test_command_defaults_to_data_verifications_json(
    database_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)  # pas de data/verifications.json ici

    assert main([]) == 1
    assert "data/verifications.json" in capsys.readouterr().err
