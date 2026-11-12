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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Verdict, Verification

REQUIRED_FIELDS = ("claim_text", "verdict", "explanation", "source_name", "verified_at")


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


def import_verifications(session: Session, entries: Sequence[object]) -> ImportReport:
    """Ajoute les entrées absentes de la base (clé : texte de l'affirmation).

    Tout ou rien : si une entrée est invalide, rien n'est importé.
    """
    parsed = [parse_entry(entry, position) for position, entry in enumerate(entries, start=1)]

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
