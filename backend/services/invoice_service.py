"""Invoice service for persistence and Tally sync."""

from __future__ import annotations

from datetime import date
import json
import os

from database import session_scope
from models import Customer, Invoice, InvoiceItem, Product, SyncLog, Transaction


class InvoiceService:
    def __init__(self, tally_service, repos=None, base_dir: str = None):
        self.tally = tally_service
        self.repos = repos
        self.base_dir = base_dir or os.path.dirname(__file__)
        self.pending_file = os.path.join(self.base_dir, "invoices_pending.jsonl")

    def _find_or_create_customer(self, session, customer_name: str):
        customer = session.query(Customer).filter(Customer.customer_name == customer_name).one_or_none()
        if customer:
            return customer
        customer = Customer(customer_name=customer_name, pending_due=0.0)
        session.add(customer)
        session.flush()
        return customer

    def _find_product(self, session, item_name: str):
        return session.query(Product).filter(Product.item_name == item_name).one_or_none()

    def save_invoice(self, invoice_data: dict) -> dict:
        try:
            invoice_number = invoice_data.get("invoice_no") or invoice_data.get("invoice_number") or f"INV-{date.today().strftime('%Y%m%d')}-{os.urandom(2).hex().upper()}"
            customer_name = invoice_data.get("party_name") or invoice_data.get("customer_name") or "Walk-in Customer"
            items = invoice_data.get("items", [])
            total = float(invoice_data.get("total", invoice_data.get("total_amount", 0)) or 0)

            with session_scope() as session:
                customer = self._find_or_create_customer(session, customer_name)
                invoice = Invoice(
                    invoice_number=invoice_number,
                    customer_id=customer.id,
                    total_amount=total,
                    invoice_date=date.today(),
                    sync_status="draft",
                )
                session.add(invoice)
                session.flush()

                calculated_total = 0.0
                for item in items:
                    product = self._find_product(session, item.get("name", ""))
                    qty = float(item.get("qty", item.get("quantity", 1)) or 1)
                    rate = float(item.get("rate", item.get("price", 0)) or 0)
                    discount = float(item.get("discount", item.get("discount_percent", 0)) or 0)
                    line_total = qty * rate * (1 - discount / 100)
                    calculated_total += line_total
                    invoice.items.append(
                        InvoiceItem(
                            product_id=product.id if product else None,
                            qty=qty,
                            rate=rate,
                            discount=discount,
                            total=line_total,
                        )
                    )

                invoice.total_amount = total or calculated_total
                session.flush()
                return {"status": "saved", "invoice": invoice.to_dict()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def send_invoice(self, invoice_data: dict) -> dict:
        saved = self.save_invoice(invoice_data)
        if saved.get("status") == "error":
            return saved

        invoice = saved.get("invoice", {})
        res = self.tally.post_invoice(invoice_data)
        if res.get("status") == "sent":
            with session_scope() as session:
                stored = session.query(Invoice).filter(Invoice.invoice_number == invoice.get("invoice_number")).one_or_none()
                if stored:
                    stored.sync_status = "synced"
                    stored.tally_reference = invoice_data.get("tally_reference") or invoice.get("invoice_number")
                session.add(Transaction(transaction_type="invoice", amount=float(invoice.get("total_amount", 0) or 0), reference=invoice.get("invoice_number")))
            return {"status": "sent", "resp": res.get("response"), "invoice": invoice}

        with session_scope() as session:
            stored = session.query(Invoice).filter(Invoice.invoice_number == invoice.get("invoice_number")).one_or_none()
            if stored:
                stored.sync_status = "pending"
            session.add(SyncLog(sync_type="invoice", status="pending", message=res.get("error"), payload_json=json.dumps(invoice_data)))

        try:
            record = {"invoice": invoice_data, "error": res.get("error")}
            with open(self.pending_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return {"status": "pending", "error": res.get("error"), "invoice": invoice}

    def process_pending(self) -> dict:
        with session_scope() as session:
            pending_invoices = session.query(Invoice).filter(Invoice.sync_status == "pending").all()
            processed = 0
            succeeded = 0
            failed = 0
            for invoice in pending_invoices:
                processed += 1
                payload = invoice.to_dict()
                res = self.tally.post_invoice(payload)
                if res.get("status") == "sent":
                    succeeded += 1
                    invoice.sync_status = "synced"
                    invoice.tally_reference = payload.get("invoice_number")
                else:
                    failed += 1
            return {"processed": processed, "succeeded": succeeded, "failed": failed}

    def get_pending_count(self) -> int:
        with session_scope() as session:
            return session.query(Invoice).filter(Invoice.sync_status == "pending").count()
