"""Moteur de correspondance : retrouve la vérification qui répond à un message.

La comparaison est purement lexicale (similarité de texte avec RapidFuzz), pas
sémantique : elle ne comprend pas le sens des phrases. Une formulation inversée,
par exemple une négation, peut donc rester très proche de l'affirmation d'origine.
Le seuil de confiance (`MATCHING_THRESHOLD`) est à ajuster avec des messages réels.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Verification

# Une affirmation courte n'est cherchée *à l'intérieur* d'un message que si elle compte
# au moins ce nombre de mots : sinon un ou deux mots banals suffiraient à « matcher ».
MIN_PARTIAL_WORDS = 4

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_SEPARATORS_PATTERN = re.compile(r"[\W_]+")


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Meilleure correspondance trouvée pour un message."""

    verification: Verification
    score: float  # similarité de 0 à 100
    matched_text: str  # formulation de la base la plus proche du message


def normalize_text(text: str) -> str:
    """Met un texte sous une forme comparable.

    Minuscules, sans accents, sans liens, emojis ni ponctuation, espaces réduits.
    """
    without_urls = _URL_PATTERN.sub(" ", text)
    decomposed = unicodedata.normalize("NFKD", without_urls.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _SEPARATORS_PATTERN.sub(" ", without_accents).strip()


def similarity(first: str, second: str) -> float:
    """Score de similarité (0-100) entre deux textes déjà normalisés.

    - `token_sort_ratio` compare les textes entiers, quel que soit l'ordre des mots ;
    - `partial_ratio` détecte une affirmation noyée dans un long message transféré
      (« À partager à tous vos contacts ! ... »), sous réserve de `MIN_PARTIAL_WORDS`.
    """
    if not first or not second:
        return 0.0
    score = float(fuzz.token_sort_ratio(first, second))
    shorter = first if len(first) <= len(second) else second
    if len(shorter.split()) >= MIN_PARTIAL_WORDS:
        score = max(score, float(fuzz.partial_ratio(first, second)))
    return score


def best_match(
    text: str, verifications: Iterable[Verification], threshold: float
) -> MatchResult | None:
    """Retourne la meilleure correspondance d'au moins `threshold`, ou None.

    À score égal, la vérification la plus récente l'emporte.
    """
    query = normalize_text(text)
    if not query:
        return None

    best: MatchResult | None = None
    for verification in verifications:
        for formulation in verification.formulations:
            score = similarity(query, normalize_text(formulation))
            if score < threshold:
                continue
            candidate = MatchResult(verification, score, formulation)
            if best is None or _rank(candidate) > _rank(best):
                best = candidate
    return best


def find_best_match(
    session: Session, text: str, threshold: float | None = None
) -> MatchResult | None:
    """Cherche dans la base de connaissances la vérification qui correspond au message.

    Sans `threshold`, utilise `MATCHING_THRESHOLD` de la configuration.
    """
    if threshold is None:
        threshold = get_settings().matching_threshold
    return best_match(text, session.scalars(select(Verification)), threshold)


def _rank(result: MatchResult) -> tuple[float, object]:
    return (result.score, result.verification.verified_at)
