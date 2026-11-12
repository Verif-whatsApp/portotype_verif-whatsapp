import io

from PIL import Image, ImageDraw

from app.services.ocr import extract_text_from_image


def test_ocr_basic() -> None:
    img = Image.new("RGB", (300, 100), color="white")
    d = ImageDraw.Draw(img)
    d.text((10, 10), "FAUX", fill="black")

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    text = extract_text_from_image(buf.getvalue())
    assert text is not None
    assert "FAUX" in text
