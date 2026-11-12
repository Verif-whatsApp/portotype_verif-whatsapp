"""Formatage des réponses envoyées à l'utilisateur sur WhatsApp.

Les textes sont regroupés par langue dans `MESSAGES` : ajouter une langue locale
revient à ajouter une entrée, sans toucher à la logique (cahier des charges, F6).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from app.models import Verdict, Verification
from app.services.matching import MatchResult

DEFAULT_LANGUAGE = "fr"


@dataclass(frozen=True, slots=True)
class Messages:
    """Tous les textes d'une langue."""

    verdict_titles: Mapping[Verdict, str]
    verdict_closings: Mapping[Verdict, str]
    source_label: str
    link_label: str
    unverified_title: str
    unverified_body: str
    unsupported: str
    error: str
    unreadable_image: str
    image_error: str
    automated_notice: str


FRENCH = Messages(
    verdict_titles={
        Verdict.FAUX: "🚫 FAUX",
        Verdict.TROMPEUR: "⚠️ TROMPEUR",
        Verdict.VRAI: "✅ VRAI",
        Verdict.NON_VERIFIE: "❓ NON VÉRIFIÉ",
    },
    verdict_closings={
        Verdict.FAUX: "Ne partagez pas ce message.",
        Verdict.TROMPEUR: "Ce message est à nuancer : vérifiez avant de le partager.",
        Verdict.NON_VERIFIE: "Ce message n'est pas confirmé : évitez de le partager.",
    },
    source_label="Source",
    link_label="Lien",
    unverified_title="❓ NON VÉRIFIÉ POUR L'INSTANT",
    unverified_body=(
        "Ce message n'a pas encore été vérifié.\n"
        "Dans le doute, évitez de le partager et consultez les sources officielles "
        "ou des organisations de fact-checking comme Africa Check, IvoireCheck "
        "ou FactSpace West Africa."
    ),
    unsupported=(
        "Je ne peux pas traiter cette demande.\n"
        "Transférez-moi le message suspect que vous souhaitez vérifier."
    ),
    error="Désolé, une erreur technique est survenue. Veuillez réessayer plus tard.",
    unreadable_image=(
        "📸 Désolé, nous n'avons pas réussi à lire le texte de cette image.\n"
        "Vous pouvez aussi me copier-coller le texte du message."
    ),
    image_error="📸 Une erreur est survenue lors de l'analyse de l'image.",
    automated_notice="🤖 Réponse automatique : ce robot n'est pas un journaliste.",
)

MESSAGES: dict[str, Messages] = {DEFAULT_LANGUAGE: FRENCH}


def format_response(match: MatchResult | None, language: str = DEFAULT_LANGUAGE) -> str:
    """Réponse à envoyer : verdict de la correspondance, ou « non vérifié » sans correspondance."""
    if match is None:
        return format_unverified(language)
    return format_verification(match.verification, language)


def format_verification(verification: Verification, language: str = DEFAULT_LANGUAGE) -> str:
    """Verdict, explication courte, source avec date et lien, puis consigne finale."""
    messages = _messages_for(language)

    source_lines = [
        f"{messages.source_label} : {verification.source_name}, {verification.verified_at:%d/%m/%Y}"
    ]
    if verification.source_url:
        source_lines.append(f"{messages.link_label} : {verification.source_url}")

    blocks = [
        messages.verdict_titles[verification.verdict],
        verification.explanation.strip(),
        "\n".join(source_lines),
    ]
    closing = messages.verdict_closings.get(verification.verdict)
    if closing:
        blocks.append(closing)
    blocks.append(messages.automated_notice)
    return "\n\n".join(blocks)


def format_unverified(language: str = DEFAULT_LANGUAGE) -> str:
    """Aucune correspondance : ne rien inventer, orienter vers des sources fiables."""
    messages = _messages_for(language)
    return "\n\n".join(
        [messages.unverified_title, messages.unverified_body, messages.automated_notice]
    )


def format_unsupported(language: str = DEFAULT_LANGUAGE) -> str:
    """Message que le robot ne peut pas traiter (hors sujet, contenu non pris en charge)."""
    return _messages_for(language).unsupported


def format_error(language: str = DEFAULT_LANGUAGE) -> str:
    """Panne technique pendant le traitement."""
    return _messages_for(language).error


def format_unreadable_image(language: str = DEFAULT_LANGUAGE) -> str:
    """Aucun texte lisible n'a pu être extrait de l'image."""
    return _messages_for(language).unreadable_image


def format_image_error(language: str = DEFAULT_LANGUAGE) -> str:
    """L'image n'a pas pu être récupérée ou analysée."""
    return _messages_for(language).image_error


def _messages_for(language: str) -> Messages:
    return MESSAGES.get(language, MESSAGES[DEFAULT_LANGUAGE])
