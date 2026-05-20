"""Local OCR extraction using pytesseract when available."""

from __future__ import annotations

from io import BytesIO
from typing import Optional


class OCRService:
    def extract_text(self, image_bytes: bytes) -> dict:
        try:
            from PIL import Image
            import pytesseract
        except Exception as exc:
            return {
                "status": "error",
                "message": "OCR dependencies are not installed locally.",
                "error": str(exc),
            }

        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return {"status": "ok", "text": text}
        except Exception as exc:
            return {"status": "error", "message": "Unable to process image.", "error": str(exc)}
