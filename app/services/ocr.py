import io
import logging
from typing import Optional

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_image(image_bytes: bytes) -> Optional[str]:
    """Extrait le texte d'une image en utilisant Tesseract OCR."""
    try:
        # Utilisation explicite de Image.open dans une variable temporaire
        img_file = Image.open(io.BytesIO(image_bytes))
        # On convertit en niveaux de gris (renvoie une image standard, pas un ImageFile)
        img = img_file.convert("L")

        text = pytesseract.image_to_string(img, lang="fra+eng")
        text = text.strip()

        if not text:
            logger.warning("Aucun texte détecté dans l'image.")
            return None

        logger.info(f"Texte extrait de l'image ({len(text)} caractères).")
        return str(text)  # Force le type str pour Mypy
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction OCR : {e}")
        return None
