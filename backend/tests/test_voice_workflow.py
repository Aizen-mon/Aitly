import unittest
from unittest.mock import patch


class VoiceWorkflowTest(unittest.TestCase):
    def setUp(self):
        bg_patcher = patch("background_tasks.BackgroundTaskManager.start_retry_loop", return_value=None)
        self.bg_patcher = bg_patcher
        bg_patcher.start()

        from app import create_app

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.bg_patcher.stop()

    def test_invoice_conversation_flow(self):
        session_id = "voice-flow-invoice"

        start = self.client.post("/api/parse", json={"text": "Create invoice", "session_id": session_id})
        self.assertEqual(start.status_code, 200)
        self.assertEqual(start.get_json()["intent"], "create_invoice")

        customer = self.client.post("/api/parse", json={"text": "ABC Traders", "session_id": session_id})
        self.assertEqual(customer.status_code, 200)
        self.assertEqual(customer.get_json()["intent"], "create_invoice")

        items = self.client.post("/api/parse", json={"text": "5 Coke bottles", "session_id": session_id})
        self.assertEqual(items.status_code, 200)
        self.assertEqual(items.get_json()["intent"], "create_invoice")

        confirm = self.client.post("/api/parse", json={"text": "yes", "session_id": session_id})
        self.assertEqual(confirm.status_code, 200)
        payload = confirm.get_json()
        self.assertEqual(payload["intent"], "create_invoice")
        self.assertIn("successfully", payload["message"].lower())

    def test_payment_conversation_flow(self):
        session_id = "voice-flow-payment"

        start = self.client.post("/api/parse", json={"text": "Record payment from ABC Traders", "session_id": session_id})
        self.assertEqual(start.status_code, 200)
        self.assertEqual(start.get_json()["intent"], "record_payment")

        amount = self.client.post("/api/parse", json={"text": "500", "session_id": session_id})
        self.assertEqual(amount.status_code, 200)
        payload = amount.get_json()
        self.assertEqual(payload["intent"], "record_payment")
        self.assertIn("recorded successfully", payload["message"].lower())


if __name__ == "__main__":
    unittest.main()
