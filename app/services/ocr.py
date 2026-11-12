import io
import logging

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_image(image_bytes: bytes) -> str | None:
    """Extrait le texte d'une image en utilisant Tesseract OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("L")
        text = pytesseract.image_to_string(image, lang="fra+eng")
        text = text.strip()

        if not text:
            logger.warning("Aucun texte détecté dans l'image.")
            return None

        logger.info(f"Texte extrait de l'image ({len(text)} caractères).")
        return text
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction OCR : {e}")
        return None
