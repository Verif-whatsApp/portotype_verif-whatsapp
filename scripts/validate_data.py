"""Contrôle un fichier de vérifications sans rien importer.

Usage :
    python scripts/validate_data.py                       # data/verifications.json
    python scripts/validate_data.py data/autre_fichier.json

Applique exactement les règles de l'import (champs obligatoires, verdict, date AAAA-MM-JJ,
affirmations en double avec verdicts contradictoires) et affiche TOUTES les erreurs d'un coup.
Code de sortie : 0 si le fichier est valide, 1 sinon.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from app.services.importer import KnowledgeBaseError, load_entries, parse_entry, validate_entries

DEFAULT_FILE = Path("data/verifications.json")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("file", nargs="?", type=Path, default=DEFAULT_FILE, help="fichier JSON")
    args = parser.parse_args(argv)

    try:
        entries = load_entries(args.file)
    except KnowledgeBaseError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    errors = validate_entries(entries)
    if errors:
        for error in errors:
            print(f"❌ {error}", file=sys.stderr)
        print(
            f"⚠️ {len(errors)} erreur(s) : corrigez le fichier avant de l'importer.", file=sys.stderr
        )
        return 1

    claims = {parse_entry(entry, position).claim_text for position, entry in enumerate(entries, 1)}
    duplicates = len(entries) - len(claims)
    print(f"✅ {len(entries)} entrée(s) valides, {len(claims)} affirmation(s) distincte(s).")
    if duplicates:
        print(f"ℹ️ {duplicates} doublon(s) exact(s) : ils seront ignorés à l'import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
