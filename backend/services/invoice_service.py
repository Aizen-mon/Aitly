"""
Invoice service for handling invoice persistence and Tally integration.
"""
import json
import os


class InvoiceService:
    """Service for managing invoice creation, persistence, and Tally integration."""

    def __init__(self, tally_service, base_dir: str = None):
        self.tally = tally_service
        self.base_dir = base_dir or os.path.dirname(__file__)
        self.invoices_file = os.path.join(self.base_dir, "invoices.jsonl")
        self.pending_file = os.path.join(self.base_dir, "invoices_pending.jsonl")

    def save_invoice(self, invoice_data: dict) -> dict:
        """Save invoice locally."""
        try:
            with open(self.invoices_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(invoice_data, ensure_ascii=False) + "\n")
            return {"status": "saved"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def send_invoice(self, invoice_data: dict) -> dict:
        """Try sending invoice to Tally, save as pending if fails."""
        res = self.tally.post_invoice(invoice_data)
        if res.get("status") == "sent":
            return {"status": "sent", "resp": res.get("response")}

        # Fallback: save locally as pending
        try:
            record = {"invoice": invoice_data, "error": res.get("error")}
            with open(self.pending_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return {"status": "pending", "error": res.get("error")}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def process_pending(self) -> dict:
        """Retry sending all pending invoices."""
        if not os.path.exists(self.pending_file):
            return {"processed": 0, "succeeded": 0, "failed": 0}

        processed = 0
        succeeded = 0
        failed = 0
        remaining = []

        with open(self.pending_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    invoice = rec.get("invoice") or rec
                    processed += 1
                    res = self.tally.post_invoice(invoice)
                    if res.get("status") == "sent":
                        succeeded += 1
                    else:
                        failed += 1
                        rec["error"] = res.get("error")
                        remaining.append(rec)
                except Exception as e:
                    failed += 1
                    remaining.append({"invoice": None, "error": str(e)})

        # Overwrite file with remaining
        with open(self.pending_file, "w", encoding="utf-8") as f:
            for r in remaining:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        return {"processed": processed, "succeeded": succeeded, "failed": failed}

    def get_pending_count(self) -> int:
        """Get count of pending invoices."""
        if not os.path.exists(self.pending_file):
            return 0
        try:
            with open(self.pending_file, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0
