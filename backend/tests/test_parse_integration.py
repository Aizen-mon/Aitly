import unittest
from unittest.mock import patch


class ParseIntegrationTest(unittest.TestCase):
    def setUp(self):
        bg_patcher = patch("background_tasks.BackgroundTaskManager.start_retry_loop", return_value=None)
        self.bg_patcher = bg_patcher
        bg_patcher.start()

        from app import create_app

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.bg_patcher.stop()

    def test_today_sales_parse(self):
        response = self.client.post("/api/parse", json={"text": "today sales", "session_id": "parse-sales"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["intent"], "today_sales")
        self.assertEqual(payload["title"], "Today's Sales Summary")
        self.assertEqual(payload["action"], "view_invoices")
        self.assertIn("sales", payload["message"].lower())

    def test_low_stock_parse(self):
        response = self.client.post("/api/parse", json={"text": "low stock", "session_id": "parse-stock"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["intent"], "low_stock")
        self.assertEqual(payload["title"], "Low Stock Alert")
        self.assertEqual(payload["action"], "view_low_stock")
        self.assertIn("stock", payload["message"].lower())

    def test_create_invoice_parse_prompts_for_flow(self):
        response = self.client.post("/api/parse", json={"text": "create invoice", "session_id": "parse-invoice"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["intent"], "create_invoice")
        self.assertEqual(payload["title"], "Create Invoice")
        self.assertEqual(payload["action"], "show_conversation_prompt")
        self.assertEqual(payload["conversation_state"]["flow"], "create_invoice")
        self.assertIn(payload["conversation_state"]["step"], {"customer_name", "items"})
        self.assertTrue(
            any(keyword in payload["message"].lower() for keyword in ("customer name", "items")),
            payload["message"],
        )


if __name__ == "__main__":
    unittest.main()