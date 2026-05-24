import base64
import unittest
from unittest.mock import patch


class OCRParseCreateTest(unittest.TestCase):
    def setUp(self):
        # Prevent background threads from starting during app creation
        bg_patcher = patch("background_tasks.BackgroundTaskManager.start_retry_loop", return_value=None)
        self.bg_mock = bg_patcher.start()
        self.addCleanup(bg_patcher.stop)

        # Mock OCR to return deterministic invoice-like text
        ocr_patcher = patch("services.ocr_service.OCRService.extract_text", return_value={
            "status": "ok",
            "text": "2 Premium Widget\n1 Standard Component",
        })
        self.ocr_mock = ocr_patcher.start()
        self.addCleanup(ocr_patcher.stop)

        # Import and create the app after patching
        from app import create_app

        self.app = create_app()
        self.client = self.app.test_client()

    def test_ocr_parse_and_create_products(self):
        # Call OCR endpoint (payload can be any base64 since OCR is mocked)
        fake_b64 = base64.b64encode(b"fakeimagebytes").decode()
        resp = self.client.post("/api/ocr/extract", json={"image_base64": fake_b64})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("text", data)

        # Send the extracted text to the parse endpoint
        import uuid

        parse_resp = self.client.post(
            "/api/parse",
            json={"text": data["text"], "session_id": f"ocr-flow-{uuid.uuid4().hex}"},
        )
        self.assertEqual(parse_resp.status_code, 200)
        parsed = parse_resp.get_json()
        details = parsed.get("details", {}) or {}
        draft_invoice = details.get("draft_invoice", {}) if isinstance(details, dict) else {}
        items = draft_invoice.get("items", []) if isinstance(draft_invoice, dict) else []
        self.assertTrue(items, "Expected parsed items from OCR text")

        # Create products based on parsed items
        for item in items:
            create_resp = self.client.post(
                "/api/products",
                json={
                    "item_name": item["name"],
                    "quantity": float(item.get("qty", 1)),
                    "rate": 0.0,
                    "tax_percent": 0.0,
                    "reorder_level": 0.0,
                },
            )
            self.assertEqual(create_resp.status_code, 201)

        # Verify products exist in the inventory
        list_resp = self.client.get("/api/products?per_page=100")
        self.assertEqual(list_resp.status_code, 200)
        items_list = list_resp.get_json().get("items", [])
        names = [p.get("item_name") for p in items_list]
        self.assertIn("Premium Widget", names)
        self.assertIn("Standard Component", names)


if __name__ == "__main__":
    unittest.main()
