"""Modèle de la base de connaissances de vérification (table `verifications`)."""

import enum
from datetime import date

from sqlalchemy import JSON, Date, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Verdict(enum.StrEnum):
    """Verdict d'une vérification. La valeur est celle stockée en base."""

    FAUX = "faux"
    TROMPEUR = "trompeur"
    VRAI = "vrai"
    NON_VERIFIE = "non_verifie"


def _verdict_values(enum_class: type[enum.Enum]) -> list[str]:
    """Stocke la valeur (`faux`) plutôt que le nom du membre (`FAUX`)."""
    return [str(member.value) for member in enum_class]


class Verification(Base):
    """Une affirmation qui circule, son verdict et la source qui l'a vérifiée."""

    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    # L'affirmation telle qu'elle circule
    claim_text: Mapped[str] = mapped_column(Text)
    # Autres formulations connues de la même affirmation (liste JSON)
    claim_variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    verdict: Mapped[Verdict] = mapped_column(
        SAEnum(
            Verdict,
            native_enum=False,
            length=20,
            values_callable=_verdict_values,
            validate_strings=True,
        )
    )
    # Explication courte (2-3 phrases)
    explanation: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(2048), default=None)
    verified_at: Mapped[date] = mapped_column(Date)
    language: Mapped[str] = mapped_column(String(8), default="fr")

    @property
    def formulations(self) -> list[str]:
        """Toutes les formulations à comparer : l'affirmation puis ses variantes."""
        # `claim_variants` vaut None tant que l'objet n'est pas enregistré en base
        return [self.claim_text, *(self.claim_variants or [])]

    def __repr__(self) -> str:
        return (
            f"Verification(id={self.id!r}, verdict={self.verdict!r}, source={self.source_name!r})"
        )
