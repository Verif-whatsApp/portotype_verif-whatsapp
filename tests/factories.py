"""Fabriques d'objets pour les tests."""

from datetime import date
from typing import Any

from app.models import Verdict, Verification


def make_verification(**overrides: Any) -> Verification:
    """Crée une `Verification` valide (non enregistrée) ; chaque champ est surchargeable."""
    fields: dict[str, Any] = {
        "claim_text": "ALERTE : Attaque à Doropo, ne sortez pas",
        "claim_variants": [],
        "verdict": Verdict.FAUX,
        "explanation": (
            "Aucune attaque n'a été signalée à Doropo à cette date. "
            "Les autorités locales ont démenti l'information."
        ),
        "source_name": "IvoireCheck",
        "source_url": "https://example.org/verification/doropo",
        "verified_at": date(2026, 10, 12),
        "language": "fr",
    }
    fields.update(overrides)
    return Verification(**fields)
