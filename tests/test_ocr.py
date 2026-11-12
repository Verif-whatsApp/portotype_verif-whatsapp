from PIL import Image, ImageDraw
import io
from app.services.ocr import extract_text_from_image

def test_ocr_basic():
    # Créer une image avec du texte
    img = Image.new('RGB', (300, 100), color='white')
    d = ImageDraw.Draw(img)
    d.text((10, 10), "FAUX", fill='black')
    
    # Sauvegarder dans un buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    
    # Tester l'OCR
    text = extract_text_from_image(buf.getvalue())
    assert text is not None
    assert "FAUX" in text