import base64
import io
import unittest
from unittest.mock import patch


class OCRIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Prevent background threads from starting during app creation
        bg_patcher = patch("background_tasks.BackgroundTaskManager.start_retry_loop", return_value=None)
        cls.bg_patcher = bg_patcher
        cls.bg_mock = bg_patcher.start()

        # Create Flask app
        from app import create_app

        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_real_ocr_on_generated_image(self):
        try:
            import pytesseract
            # ensure tesseract binary is available
            pytesseract.get_tesseract_version()
        except Exception as exc:  # pragma: no cover - environment dependent
            self.skipTest(f"Tesseract/pytesseract not available: {exc}")

        try:
            from PIL import Image, ImageDraw
        except Exception as exc:  # pragma: no cover - environment dependent
            self.skipTest(f"Pillow not available: {exc}")

        # Generate a simple invoice-like image in-memory
        img = Image.new("RGB", (600, 120), color="white")
        draw = ImageDraw.Draw(img)
        text = "2 Premium Widget\n1 Standard Component"
        draw.text((10, 10), text, fill="black")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        b64 = base64.b64encode(img_bytes).decode()

        resp = self.client.post("/api/ocr/extract", json={"image_base64": b64})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "ok")
        ocr_text = (data.get("text") or "").lower()
        self.assertIn("premium", ocr_text)
        self.assertIn("standard", ocr_text)


if __name__ == "__main__":
    unittest.main()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.bg_patcher.stop()
        except Exception:
            pass
