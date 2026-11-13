"""Import de la base de connaissances depuis un fichier JSON.

Format d'une entrée (voir `data/verifications.example.json`) :
`claim_text`, `verdict` (faux, trompeur, vrai, non_verifie), `explanation`, `source_name`
et `verified_at` (AAAA-MM-JJ) sont obligatoires ; `claim_variants`, `source_url` et
`language` (défaut « fr ») sont facultatifs.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Verdict, Verification

REQUIRED_FIELDS = ("claim_text", "verdict", "explanation", "source_name", "verified_at")

# Adresses réservées aux exemples : une entrée qui les utilise n'est pas une vraie vérification
PLACEHOLDER_HOSTS = frozenset({"example.org", "example.com", "example.net"})


class KnowledgeBaseError(Exception):
    """Fichier ou entrée invalide : rien n'est importé."""


@dataclass(frozen=True, slots=True)
class ImportReport:
    added: int
    skipped: int  # déjà présentes en base (ou en double dans le fichier)


def load_entries(path: Path) -> list[Any]:
    """Lit le fichier JSON : une liste d'entrées, à valider avec `import_verifications`."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise KnowledgeBaseError(f"Fichier introuvable : {path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KnowledgeBaseError(f"JSON invalide dans {path} : {exc}") from exc
    if not isinstance(data, list):
        raise KnowledgeBaseError("Le fichier doit contenir une liste de vérifications")
    return data


def parse_entry(entry: object, position: int) -> Verification:
    """Valide une entrée et la convertit en `Verification`."""
    label = f"Entrée n°{position}"
    if not isinstance(entry, dict):
        raise KnowledgeBaseError(f"{label} : objet JSON attendu")

    missing = [
        field
        for field in REQUIRED_FIELDS
        if not isinstance(entry.get(field), str) or not entry[field].strip()
    ]
    if missing:
        raise KnowledgeBaseError(f"{label} : champs manquants ou vides : {', '.join(missing)}")

    try:
        verdict = Verdict(entry["verdict"])
    except ValueError as exc:
        allowed = ", ".join(member.value for member in Verdict)
        raise KnowledgeBaseError(
            f"{label} : verdict « {entry['verdict']} » inconnu (valeurs : {allowed})"
        ) from exc

    try:
        verified_at = date.fromisoformat(entry["verified_at"])
    except ValueError as exc:
        raise KnowledgeBaseError(
            f"{label} : verified_at « {entry['verified_at']} » invalide (format AAAA-MM-JJ)"
        ) from exc

    variants = entry.get("claim_variants", [])
    if not isinstance(variants, list) or not all(isinstance(item, str) for item in variants):
        raise KnowledgeBaseError(f"{label} : claim_variants doit être une liste de textes")
    for optional in ("source_url", "language"):
        if entry.get(optional) is not None and not isinstance(entry[optional], str):
            raise KnowledgeBaseError(f"{label} : {optional} doit être un texte")

    return Verification(
        claim_text=entry["claim_text"],
        claim_variants=variants,
        verdict=verdict,
        explanation=entry["explanation"],
        source_name=entry["source_name"],
        source_url=entry.get("source_url"),
        verified_at=verified_at,
        language=entry.get("language") or "fr",
    )


def is_placeholder(verification: Verification) -> bool:
    """Vrai pour une entrée de démonstration (adresse d'exemple ou source se disant fictive)."""
    host = urlparse(verification.source_url or "").hostname or ""
    fake_host = any(host == known or host.endswith(f".{known}") for known in PLACEHOLDER_HOSTS)
    name = verification.source_name.lower()
    return fake_host or "fictif" in name or "fictive" in name


def _conflict_errors(parsed: Sequence[tuple[int, Verification]]) -> list[str]:
    """Une même affirmation donnée avec deux verdicts différents est une erreur de données."""
    first_seen: dict[str, tuple[int, Verdict]] = {}
    errors: list[str] = []
    for position, verification in parsed:
        known = first_seen.setdefault(verification.claim_text, (position, verification.verdict))
        if known[1] is not verification.verdict:
            errors.append(
                f"Entrées n°{known[0]} et n°{position} : même affirmation avec des verdicts "
                f"différents ({known[1].value} / {verification.verdict.value})"
            )
    return errors


def validate_entries(entries: Sequence[object]) -> list[str]:
    """Toutes les erreurs du fichier, pas seulement la première (liste vide si tout est valide)."""
    errors: list[str] = []
    parsed: list[tuple[int, Verification]] = []
    for position, entry in enumerate(entries, start=1):
        try:
            parsed.append((position, parse_entry(entry, position)))
        except KnowledgeBaseError as exc:
            errors.append(str(exc))
    return errors + _conflict_errors(parsed)


def import_verifications(
    session: Session, entries: Sequence[object], *, allow_placeholder_sources: bool = True
) -> ImportReport:
    """Ajoute les entrées absentes de la base (clé : texte de l'affirmation).

    Tout ou rien : si une entrée est invalide, ou si une même affirmation reçoit deux verdicts
    différents, rien n'est importé. Avec `allow_placeholder_sources=False` (production), les
    entrées de démonstration (sources fictives, adresses example.org) sont refusées.
    """
    parsed = [parse_entry(entry, position) for position, entry in enumerate(entries, start=1)]
    numbered = list(enumerate(parsed, start=1))

    conflicts = _conflict_errors(numbered)
    if conflicts:
        raise KnowledgeBaseError("\n".join(conflicts))

    if not allow_placeholder_sources:
        fake = [position for position, verification in numbered if is_placeholder(verification)]
        if fake:
            shown = ", ".join(f"n°{position}" for position in fake[:5])
            more = f" (et {len(fake) - 5} autres)" if len(fake) > 5 else ""
            raise KnowledgeBaseError(
                f"{len(fake)} entrée(s) de démonstration refusée(s) en production : {shown}{more}. "
                "Elles ont une source fictive ou une adresse example.org : ce ne sont pas de "
                "vraies vérifications."
            )

    known = set(session.scalars(select(Verification.claim_text)))
    added = skipped = 0
    for verification in parsed:
        if verification.claim_text in known:
            skipped += 1
            continue
        session.add(verification)
        known.add(verification.claim_text)
        added += 1
    session.commit()
    return ImportReport(added=added, skipped=skipped)
