"""Simule un message WhatsApp entrant, signé comme le fait Meta, vers un serveur local.

Usage :
    python scripts/simulate_webhook.py "texte du message à vérifier"
    python scripts/simulate_webhook.py --sender 22997000000 "..."
    python scripts/simulate_webhook.py --url http://localhost:8000/webhook "..."

Sans compte Meta, lancez le serveur sans WHATSAPP_ACCESS_TOKEN : la réponse du robot
s'affiche alors dans les logs du serveur (mode simulation, `[simulation] réponse pour ...`).
"""

import argparse
import json
import sys
import uuid
from collections.abc import Sequence
from typing import Any

import httpx

from app.config import get_settings
from app.security import compute_signature

DEFAULT_URL = "http://localhost:8000/webhook"
DEFAULT_SENDER = "22900000000"


def build_payload(text: str, sender: str) -> dict[str, Any]:
    """Notification au format Meta avec un message texte (identifiant unique à chaque appel)."""
    message = {
        "from": sender,
        "id": f"wamid.SIMULATION.{uuid.uuid4().hex[:12]}",
        "timestamp": "1760000000",
        "type": "text",
        "text": {"body": text},
    }
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "SIMULATION",
                "changes": [{"field": "messages", "value": {"messages": [message]}}],
            }
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("text", help="texte du message à vérifier")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"adresse du webhook ({DEFAULT_URL})")
    parser.add_argument("--sender", default=DEFAULT_SENDER, help="numéro de l'expéditeur fictif")
    parser.add_argument(
        "--secret",
        default=None,
        help="clé secrète de l'app Meta (défaut : WHATSAPP_APP_SECRET du .env)",
    )
    args = parser.parse_args(argv)

    secret = args.secret if args.secret is not None else get_settings().whatsapp_app_secret
    body = json.dumps(build_payload(args.text, args.sender)).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Hub-Signature-256"] = compute_signature(body, secret)

    try:
        response = httpx.post(args.url, content=body, headers=headers, timeout=10)
    except httpx.HTTPError as exc:
        print(f"❌ Serveur injoignable ({type(exc).__name__}) : {args.url}", file=sys.stderr)
        return 1

    print(f"HTTP {response.status_code} : {response.text}")
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
