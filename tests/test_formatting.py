from datetime import date

import pytest

from app.models import Verdict
from app.services.formatting import (
    DEFAULT_LANGUAGE,
    MESSAGES,
    Messages,
    format_response,
    format_unsupported,
    format_unverified,
    format_verification,
)
from app.services.matching import MatchResult
from tests.factories import make_verification

AUTOMATED_NOTICE = "🤖 Réponse automatique : ce robot n'est pas un journaliste."


def test_false_verdict_follows_the_specification_example() -> None:
    verification = make_verification()  # exemple du cahier des charges (§6.1)

    assert format_verification(verification) == (
        "🚫 FAUX\n\n"
        "Aucune attaque n'a été signalée à Doropo à cette date. "
        "Les autorités locales ont démenti l'information.\n\n"
        "Source : IvoireCheck, 12/10/2026\n"
        "Lien : https://example.org/verification/doropo\n\n"
        "Ne partagez pas ce message.\n\n"
        f"{AUTOMATED_NOTICE}"
    )


@pytest.mark.parametrize(
    ("verdict", "title", "closing"),
    [
        (Verdict.FAUX, "🚫 FAUX", "Ne partagez pas ce message."),
        (
            Verdict.TROMPEUR,
            "⚠️ TROMPEUR",
            "Ce message est à nuancer : vérifiez avant de le partager.",
        ),
        (Verdict.VRAI, "✅ VRAI", None),
        (
            Verdict.NON_VERIFIE,
            "❓ NON VÉRIFIÉ",
            "Ce message n'est pas confirmé : évitez de le partager.",
        ),
    ],
)
def test_each_verdict_has_its_title_and_closing_line(
    verdict: Verdict, title: str, closing: str | None
) -> None:
    text = format_verification(make_verification(verdict=verdict))

    assert text.startswith(title)
    if closing is None:
        assert "Ne partagez pas" not in text
        assert "vérifiez avant" not in text
        assert "évitez de le partager" not in text
    else:
        assert closing in text


def test_link_line_is_omitted_without_source_url() -> None:
    text = format_verification(make_verification(source_url=None))

    assert "Lien" not in text
    assert "Source : IvoireCheck, 12/10/2026" in text


def test_date_is_formatted_day_month_year() -> None:
    text = format_verification(make_verification(verified_at=date(2026, 3, 5)))

    assert "Source : IvoireCheck, 05/03/2026" in text


def test_explanation_is_trimmed() -> None:
    text = format_verification(make_verification(explanation="  Faux, démenti.\n"))

    assert "\n\nFaux, démenti.\n\n" in text


def test_every_verification_reply_says_it_is_automated() -> None:
    for verdict in Verdict:
        assert format_verification(make_verification(verdict=verdict)).endswith(AUTOMATED_NOTICE)


def test_format_response_uses_the_matched_verification() -> None:
    verification = make_verification(verdict=Verdict.TROMPEUR)
    match = MatchResult(verification, score=92.5, matched_text=verification.claim_text)

    assert format_response(match) == format_verification(verification)


def test_format_response_without_match_is_the_unverified_message() -> None:
    assert format_response(None) == format_unverified()


def test_unverified_message_does_not_invent_a_verdict() -> None:
    text = format_unverified()

    assert text.startswith("❓ NON VÉRIFIÉ POUR L'INSTANT")
    assert "pas encore été vérifié" in text
    assert "Africa Check" in text
    assert "FAUX" not in text
    assert "VRAI" not in text
    assert text.endswith(AUTOMATED_NOTICE)


def test_unsupported_message_is_polite_and_asks_for_a_message_to_check() -> None:
    text = format_unsupported()

    assert "ne peux pas traiter" in text
    assert "message suspect" in text


def test_unknown_language_falls_back_to_french() -> None:
    verification = make_verification()

    assert format_verification(verification, language="yo") == format_verification(verification)
    assert format_unverified("yo") == format_unverified()
    assert format_unsupported("yo") == format_unsupported()


def test_a_new_language_only_needs_a_new_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    english = Messages(
        verdict_titles={verdict: f"EN {verdict.name}" for verdict in Verdict},
        verdict_closings={},
        source_label="Source",
        link_label="Link",
        unverified_title="NOT VERIFIED",
        unverified_body="Not verified yet.",
        unsupported="Cannot process this.",
        automated_notice="Automated reply.",
    )
    monkeypatch.setitem(MESSAGES, "en", english)

    assert format_verification(make_verification(), language="en").startswith("EN FAUX")
    assert format_unsupported("en") == "Cannot process this."


def test_every_language_covers_every_verdict() -> None:
    for language, messages in MESSAGES.items():
        missing = [verdict for verdict in Verdict if verdict not in messages.verdict_titles]
        assert not missing, f"{language}: titres manquants pour {missing}"


def test_default_language_is_available() -> None:
    assert DEFAULT_LANGUAGE in MESSAGES
