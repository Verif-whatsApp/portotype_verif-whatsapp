"""Vérifications de sécurité sur les requêtes reçues de Meta."""

import hashlib
import hmac

SIGNATURE_PREFIX = "sha256="


def compute_signature(body: bytes, app_secret: str) -> str:
    """Valeur attendue de l'en-tête `X-Hub-Signature-256` pour ce corps de requête."""
    digest = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}"


def is_valid_signature(body: bytes, header: str | None, app_secret: str) -> bool:
    """Vrai si l'en-tête correspond à la signature HMAC-SHA256 du corps brut."""
    if not app_secret or not header:
        return False
    expected = compute_signature(body, app_secret)
    return hmac.compare_digest(expected.encode(), header.encode())


def tokens_match(received: str | None, expected: str) -> bool:
    """Compare deux jetons en temps constant ; un jeton attendu vide n'est jamais valide."""
    if not expected or received is None:
        return False
    return hmac.compare_digest(received.encode(), expected.encode())
