from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Verdict
from app.services.matching import (
    best_match,
    find_best_match,
    normalize_text,
    similarity,
)
from tests.factories import make_verification

CLAIM = "ALERTE : Attaque à Doropo, ne sortez pas"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ALERTE : Attaque à Doropo !", "alerte attaque a doropo"),
        ("  Élèves   de l'École  ", "eleves de l ecole"),
        ("Ça coûte 500 F", "ca coute 500 f"),
        ("Voir https://example.org/x?y=1 maintenant", "voir maintenant"),
        ("Voir www.example.org/page maintenant", "voir maintenant"),
        ("🚨🚨 Urgent 🚨", "urgent"),
        ("...", ""),
        ("", ""),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_similarity_of_identical_texts_is_100() -> None:
    assert similarity("attaque a doropo", "attaque a doropo") == 100


def test_similarity_with_empty_text_is_0() -> None:
    assert similarity("", "attaque a doropo") == 0
    assert similarity("attaque a doropo", "") == 0


def test_exact_claim_matches_with_score_100() -> None:
    verification = make_verification(claim_text=CLAIM)

    result = best_match(CLAIM, [verification], threshold=85)

    assert result is not None
    assert result.verification is verification
    assert result.score == 100
    assert result.matched_text == CLAIM


def test_match_ignores_case_accents_and_punctuation() -> None:
    verification = make_verification(claim_text=CLAIM)

    result = best_match("alerte!!! attaque a doropo ne sortez pas", [verification], 85)

    assert result is not None


def test_match_ignores_word_order() -> None:
    verification = make_verification(claim_text=CLAIM)

    result = best_match("Attaque à Doropo ALERTE ne sortez pas", [verification], 85)

    assert result is not None


def test_match_tolerates_a_typo() -> None:
    verification = make_verification(claim_text=CLAIM)

    result = best_match("ALERTE : Atack à Doropo, ne sortez pas", [verification], 85)

    assert result is not None
    assert 85 <= result.score < 100


def test_match_finds_claim_buried_in_a_long_forwarded_message() -> None:
    verification = make_verification(claim_text=CLAIM)
    forwarded = (
        "🚨🚨 URGENT à partager à tous vos contacts !!! ALERTE : Attaque à Doropo, "
        "ne sortez pas. Prévenez vos proches avant qu'il ne soit trop tard. Merci 🙏"
    )

    result = best_match(forwarded, [verification], threshold=85)

    assert result is not None
    assert result.score == 100


def test_match_uses_variants_and_reports_which_one_matched() -> None:
    variant = "Attaque terroriste à Doropo, restez chez vous"
    verification = make_verification(claim_text=CLAIM, claim_variants=[variant])

    result = best_match("attaque terroriste a doropo restez chez vous", [verification], 85)

    assert result is not None
    assert result.matched_text == variant


def test_unrelated_message_does_not_match() -> None:
    verification = make_verification(claim_text=CLAIM)

    result = best_match("Le marché de Cotonou ouvre à 7 heures ce samedi", [verification], 85)

    assert result is None


@pytest.mark.parametrize("short_message", ["Doropo", "Attaque à Doropo", "ne sortez pas"])
def test_short_message_sharing_a_few_words_does_not_match(short_message: str) -> None:
    verification = make_verification(claim_text=CLAIM)

    assert best_match(short_message, [verification], threshold=85) is None


@pytest.mark.parametrize("empty_message", ["", "   ", "!!! ???", "🚨🚨"])
def test_empty_message_does_not_match(empty_message: str) -> None:
    verification = make_verification(claim_text=CLAIM)

    assert best_match(empty_message, [verification], threshold=0) is None


def test_no_verification_means_no_match() -> None:
    assert best_match(CLAIM, [], threshold=85) is None


def test_threshold_is_respected() -> None:
    verification = make_verification(claim_text=CLAIM)
    typo_message = "ALERTE : Atack à Doropo, ne sortez pas"

    assert best_match(typo_message, [verification], threshold=85) is not None
    assert best_match(typo_message, [verification], threshold=100) is None


def test_best_score_wins_over_more_recent_verification() -> None:
    close = make_verification(claim_text=CLAIM, verified_at=date(2026, 1, 1))
    approximate = make_verification(
        claim_text="ALERTE : Atack à Doropo, ne sortez pa", verified_at=date(2026, 11, 1)
    )

    result = best_match(CLAIM, [approximate, close], threshold=80)

    assert result is not None
    assert result.verification is close


def test_most_recent_verification_wins_on_equal_score() -> None:
    older = make_verification(claim_text=CLAIM, verdict=Verdict.FAUX, verified_at=date(2026, 1, 1))
    newer = make_verification(claim_text=CLAIM, verdict=Verdict.VRAI, verified_at=date(2026, 6, 1))

    for candidates in ([older, newer], [newer, older]):
        result = best_match(CLAIM, candidates, threshold=85)

        assert result is not None
        assert result.verification is newer


def test_find_best_match_reads_the_database(session: Session) -> None:
    session.add_all(
        [
            make_verification(claim_text=CLAIM),
            make_verification(claim_text="Le vaccin contient une puce électronique"),
        ]
    )
    session.commit()

    result = find_best_match(session, "le vaccin contient une puce electronique !!", 85)

    assert result is not None
    assert result.verification.claim_text == "Le vaccin contient une puce électronique"


def test_find_best_match_returns_none_on_empty_database(session: Session) -> None:
    assert find_best_match(session, CLAIM, threshold=85) is None


def test_find_best_match_uses_configured_threshold_by_default(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session.add(make_verification(claim_text=CLAIM))
    session.commit()
    typo_message = "ALERTE : Atack à Doropo, ne sortez pas"

    monkeypatch.setenv("MATCHING_THRESHOLD", "100")
    get_settings.cache_clear()
    try:
        assert find_best_match(session, typo_message) is None
        monkeypatch.setenv("MATCHING_THRESHOLD", "85")
        get_settings.cache_clear()
        assert find_best_match(session, typo_message) is not None
    finally:
        get_settings.cache_clear()
