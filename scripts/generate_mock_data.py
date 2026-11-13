"""Génère des données FICTIVES pour tester le robot (correspondance, volumétrie).

Usage :
    python scripts/generate_mock_data.py                 # data/verifications.mock.json
    python scripts/generate_mock_data.py --count 50 --seed 7

⚠️ Ces entrées sont inventées : verdicts tirés au hasard, aucune vérification réelle. Elles
portent une source fictive et une adresse example.org, et l'import les refuse en production.
Ne jamais leur attribuer le nom d'une vraie organisation de fact-checking.
"""

import argparse
import json
import random
from collections.abc import Sequence
from datetime import date, timedelta
from itertools import product
from pathlib import Path
from typing import Any

# Listes de base pour générer des variations réalistes
LIEUX = [
    "Doropo", "Abidjan", "Dakar", "Cotonou", "Lomé",
    "Ouagadougou", "Bamako", "Niamey", "Kano", "Accra",
]  # fmt: skip
SUJETS_SECURITE = [
    "attaque", "enlèvement", "manifestation", "coupure d'électricité", "fermeture de frontière",
]  # fmt: skip
SUJETS_SANTE = [
    "vaccin contre la polio", "pilule contraceptive", "remède contre le paludisme",
    "test de dépistage", "traitement contre le COVID",
]  # fmt: skip
SUJETS_POLITIQUE = [
    "nouvelle loi", "augmentation des impôts", "report des élections", "nomination ministérielle",
    "budget de l'État",
]  # fmt: skip
SUJETS_ARNAQUES = [
    "billet de 10000 FCFA", "carte SIM gratuite", "subvention gouvernementale",
    "promotion Mobile Money", "tirage au sort",
]  # fmt: skip

FICTIVE_SOURCE = "Source fictive (données de test)"
TEST_NOTICE = "[Donnée fictive de test] "
OUTPUT_FILE = Path("data/verifications.mock.json")
# Date fixe : le fichier généré est identique d'une exécution à l'autre
REFERENCE_DATE = date(2026, 11, 1)


def _candidates() -> list[tuple[str, str, tuple[str, ...]]]:
    """Toutes les affirmations possibles : (affirmation, explication, verdicts possibles)."""
    candidates: list[tuple[str, str, tuple[str, ...]]] = []
    for sujet, lieu in product(SUJETS_SECURITE, LIEUX):
        candidates.append(
            (
                f"ALERTE : {sujet} à {lieu}, ne sortez pas",
                f"Aucune information officielle ne confirme une {sujet} à {lieu}. "
                "Les autorités ont démenti.",
                ("faux", "faux", "trompeur"),
            )
        )
    for sujet in SUJETS_SANTE:
        candidates.append(
            (
                f"Le {sujet} rend stérile / est dangereux selon une étude",
                f"Aucune étude scientifique sérieuse ne prouve cela concernant le {sujet}.",
                ("faux", "trompeur", "non_verifie"),
            )
        )
    for sujet, lieu in product(SUJETS_POLITIQUE, LIEUX):
        candidates.append(
            (
                f"Le gouvernement annonce {sujet} au {lieu}",
                f"Le communiqué officiel ne mentionne pas {sujet}. Il s'agit d'une fausse annonce.",
                ("faux", "trompeur"),
            )
        )
    for sujet in SUJETS_ARNAQUES:
        candidates.append(
            (
                f"Gagnez de l'argent avec {sujet} en cliquant sur ce lien",
                "Il s'agit d'une arnaque courante. Ne cliquez pas sur ce lien et ne partagez pas "
                "vos informations.",
                ("faux",),
            )
        )
    return candidates


def generate_mock_data(num_entries: int = 500, seed: int = 42) -> list[dict[str, Any]]:
    """Jusqu'à `num_entries` affirmations DISTINCTES (reproductibles avec la même `seed`).

    Les listes ci-dessus donnent au plus ~110 affirmations différentes : demander davantage
    n'en produit pas plus (avant, les doublons aléatoires donnaient des verdicts contradictoires
    pour une même affirmation).
    """
    rng = random.Random(seed)
    candidates = _candidates()
    rng.shuffle(candidates)

    data: list[dict[str, Any]] = []
    for index, (claim, explanation, verdicts) in enumerate(candidates[:num_entries], start=1):
        # Variantes pour tester la correspondance approximative (sans doublon ni l'original)
        variants = [claim.lower(), claim.replace("ALERTE : ", ""), f"Info : {claim}"]
        variants = [v for v in dict.fromkeys(variants) if v != claim]
        data.append(
            {
                "claim_text": claim,
                "claim_variants": variants,
                "verdict": rng.choice(verdicts),
                "explanation": TEST_NOTICE + explanation,
                "source_name": FICTIVE_SOURCE,
                "source_url": f"https://example.org/verification-fictive-{index}",
                "verified_at": (REFERENCE_DATE - timedelta(days=rng.randint(1, 365))).isoformat(),
                "language": "fr",
            }
        )
    return data


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--count", type=int, default=500, help="nombre maximal d'entrées")
    parser.add_argument("--seed", type=int, default=42, help="graine (résultat reproductible)")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="fichier de sortie")
    args = parser.parse_args(argv)

    data = generate_mock_data(args.count, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✅ {len(data)} vérifications FICTIVES générées dans {args.output}")
    if len(data) < args.count:
        print(f"ℹ️ Les listes actuelles ne permettent que {len(data)} affirmations distinctes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
