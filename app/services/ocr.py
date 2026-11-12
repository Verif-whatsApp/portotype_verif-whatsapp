import io
import logging
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

def extract_text_from_image(image_bytes: bytes) -> str | None:
    """
    Extrait le texte d'une image (capture d'écran) en utilisant Tesseract OCR.
    
    Args:
        image_bytes: Le contenu binaire de l'image.
        
    Returns:
        Le texte extrait, ou None en cas d'erreur.
    """
    try:
        # Ouvrir l'image depuis les bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convertir en niveaux de gris pour améliorer l'OCR
        image = image.convert("L")
        
        # Extraire le texte (français + anglais)
        text = pytesseract.image_to_string(image, lang="fra+eng")
        
        # Nettoyer le texte
        text = text.strip()
        if not text:
            logger.warning("Aucun texte détecté dans l'image.")
            return None
            
        logger.info(f"Texte extrait de l'image ({len(text)} caractères).")
        return text
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction OCR : {e}")
        return None