"""Importe la base de connaissances de vérification dans la base de données.

Usage :
    python scripts/import_verifications.py                      # data/verifications.json
    python scripts/import_verifications.py data/autre_fichier.json

L'import est répétable : les affirmations déjà présentes sont ignorées. En production
(APP_ENV=production), les données de démonstration sont refusées.
Pour contrôler un fichier sans rien importer : python scripts/validate_data.py <fichier>.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from app.config import get_settings
from app.db.session import get_session_factory, init_db
from app.services.importer import KnowledgeBaseError, import_verifications, load_entries

DEFAULT_FILE = Path("data/verifications.json")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("file", nargs="?", type=Path, default=DEFAULT_FILE, help="fichier JSON")
    args = parser.parse_args(argv)

    try:
        entries = load_entries(args.file)
        init_db()
        with get_session_factory()() as session:
            report = import_verifications(
                session, entries, allow_placeholder_sources=not get_settings().is_production
            )
    except KnowledgeBaseError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print(f"✅ {report.added} vérification(s) importée(s), {report.skipped} déjà présente(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
