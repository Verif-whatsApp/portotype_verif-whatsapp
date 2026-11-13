import json
from pathlib import Path
from typing import Any

import pytest

from scripts.validate_data import main


def entry(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "claim_text": "Une rumeur",
        "verdict": "faux",
        "explanation": "Faux.",
        "source_name": "Africa Check",
        "verified_at": "2026-10-12",
    }
    values.update(overrides)
    return values


def write(tmp_path: Path, entries: list[Any]) -> Path:
    file = tmp_path / "base.json"
    file.write_text(json.dumps(entries), encoding="utf-8")
    return file


def test_valid_file_returns_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    file = write(tmp_path, [entry(), entry(claim_text="Autre")])

    assert main([str(file)]) == 0
    assert "2 entrée(s) valides, 2 affirmation(s) distincte(s)" in capsys.readouterr().out


def test_exact_duplicates_are_reported_as_information(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = write(tmp_path, [entry(), entry()])

    assert main([str(file)]) == 0
    assert "1 doublon(s) exact(s)" in capsys.readouterr().out


def test_every_error_is_reported_at_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = write(
        tmp_path,
        [entry(verdict="peut-être"), entry(claim_text="B"), entry(claim_text="C", verified_at="x")],
    )

    assert main([str(file)]) == 1

    errors = capsys.readouterr().err
    assert "Entrée n°1" in errors
    assert "Entrée n°3" in errors
    assert "2 erreur(s)" in errors


def test_missing_date_is_caught_like_the_import_does(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    incomplete = entry()
    del incomplete["verified_at"]

    assert main([str(write(tmp_path, [incomplete]))]) == 1
    assert "verified_at" in capsys.readouterr().err


def test_contradictory_verdicts_for_one_claim_are_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = write(tmp_path, [entry(verdict="faux"), entry(verdict="vrai", source_name="Autre")])

    assert main([str(file)]) == 1
    assert "verdicts différents (faux / vrai)" in capsys.readouterr().err


def test_missing_file_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "absent.json")]) == 1
    assert "Fichier introuvable" in capsys.readouterr().err
