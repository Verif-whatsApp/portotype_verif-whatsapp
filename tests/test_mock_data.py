from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Verification
from app.services.importer import (
    KnowledgeBaseError,
    import_verifications,
    is_placeholder,
    load_entries,
    parse_entry,
    validate_entries,
)
from scripts.generate_mock_data import FICTIVE_SOURCE, TEST_NOTICE, generate_mock_data, main

REPOSITORY = Path(__file__).resolve().parent.parent
MOCK_FILE = REPOSITORY / "data" / "verifications.mock.json"
REAL_FILE = REPOSITORY / "data" / "verifications.json"
REAL_ORGANISATIONS = ("Africa Check", "IvoireCheck", "FactSpace", "NigerCheck", "Capp Check")


def test_every_generated_claim_is_distinct() -> None:
    data = generate_mock_data(500)

    claims = [entry["claim_text"] for entry in data]
    assert len(claims) == len(set(claims)) == 110  # toutes les combinaisons possibles


def test_one_claim_never_gets_two_verdicts() -> None:
    assert validate_entries(generate_mock_data(500)) == []


def test_generation_is_reproducible() -> None:
    assert generate_mock_data(50, seed=1) == generate_mock_data(50, seed=1)
    assert generate_mock_data(50, seed=1) != generate_mock_data(50, seed=2)


def test_count_limits_the_number_of_entries() -> None:
    assert len(generate_mock_data(10)) == 10


def test_generated_entries_are_valid_for_the_importer() -> None:
    for position, entry in enumerate(generate_mock_data(500), start=1):
        parse_entry(entry, position)


def test_generated_data_is_clearly_fictional_and_names_no_real_organisation() -> None:
    for entry in generate_mock_data(500):
        assert entry["source_name"] == FICTIVE_SOURCE
        assert entry["explanation"].startswith(TEST_NOTICE)
        assert "example.org" in entry["source_url"]
        assert not any(name in str(entry) for name in REAL_ORGANISATIONS)


def test_variants_are_distinct_and_differ_from_the_claim() -> None:
    for entry in generate_mock_data(500):
        variants = entry["claim_variants"]
        assert len(variants) == len(set(variants))
        assert entry["claim_text"] not in variants


def test_generated_data_is_refused_in_production(session: Session) -> None:
    with pytest.raises(KnowledgeBaseError, match="refusée.* en production"):
        import_verifications(session, generate_mock_data(20), allow_placeholder_sources=False)

    assert session.scalar(select(func.count()).select_from(Verification)) == 0


def test_generated_data_is_accepted_in_development(session: Session) -> None:
    report = import_verifications(session, generate_mock_data(20))

    assert report.added == 20


def test_command_writes_the_file_and_explains_a_shortfall(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "mock.json"

    assert main(["--count", "500", "--output", str(output)]) == 0

    assert len(load_entries(output)) == 110
    printed = capsys.readouterr().out
    assert "110 vérifications FICTIVES" in printed
    assert "ne permettent que 110" in printed


def test_command_does_not_mention_a_shortfall_when_count_is_met(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["--count", "5", "--output", str(tmp_path / "mock.json")])

    assert "ne permettent" not in capsys.readouterr().out


# --- fichiers présents dans le dépôt ------------------------------------------------------


def test_committed_mock_file_is_valid_and_fictional() -> None:
    entries = load_entries(MOCK_FILE)

    assert validate_entries(entries) == []
    assert all(
        is_placeholder(parse_entry(entry, position)) for position, entry in enumerate(entries, 1)
    )


@pytest.mark.skipif(not REAL_FILE.exists(), reason="pas encore de vraies données")
def test_real_data_file_contains_no_fictional_entry() -> None:
    """Empêche de commiter des données de test sous le nom de la vraie base."""
    entries = load_entries(REAL_FILE)

    assert validate_entries(entries) == []
    fictional = [
        position
        for position, entry in enumerate(entries, 1)
        if is_placeholder(parse_entry(entry, position))
    ]
    assert fictional == []
