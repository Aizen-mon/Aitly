"""Seed a small persistent business dataset for local development."""

from __future__ import annotations

from datetime import date

from repositories import RepositoryBundle


def seed_database(repos: RepositoryBundle) -> None:
    if repos.users.list(page=1, per_page=1)["total"] == 0:
        repos.users.create(name="Admin User", role="admin")

    if repos.customers.list(page=1, per_page=1)["total"] == 0:
        for row in [
            {"customer_name": "ABC Traders", "phone": "9876543210", "address": "Mumbai", "gst_number": "27AAAAA0000A1Z5", "pending_due": 8750.0},
            {"customer_name": "XYZ Suppliers", "phone": "9898989898", "address": "Pune", "gst_number": "27BBBBB1111B1Z6", "pending_due": 3200.0},
            {"customer_name": "Retail Hub", "phone": "9765432109", "address": "Nashik", "gst_number": "27CCCCC2222C1Z7", "pending_due": 0.0},
        ]:
            repos.customers.create(**row)

    if repos.products.list(page=1, per_page=1)["total"] == 0:
        for row in [
            {"item_name": "Coke", "quantity": 48, "rate": 20.0, "discount": 0.0, "tax_percent": 5.0, "supplier": "ABC Traders", "reorder_level": 24},
            {"item_name": "Maggi", "quantity": 36, "rate": 15.0, "discount": 0.0, "tax_percent": 5.0, "supplier": "XYZ Suppliers", "reorder_level": 18},
            {"item_name": "Parle-G", "quantity": 60, "rate": 10.0, "discount": 0.0, "tax_percent": 5.0, "supplier": "Retail Hub", "reorder_level": 30},
            {"item_name": "Premium Widget", "quantity": 12, "rate": 250.0, "discount": 10.0, "tax_percent": 18.0, "supplier": "XYZ Suppliers", "reorder_level": 20},
            {"item_name": "Standard Component", "quantity": 4, "rate": 500.0, "discount": 5.0, "tax_percent": 18.0, "supplier": "ABC Traders", "reorder_level": 10},
            {"item_name": "Deluxe Package", "quantity": 2, "rate": 800.0, "discount": 0.0, "tax_percent": 18.0, "supplier": "Retail Hub", "reorder_level": 5},
        ]:
            repos.products.create(**row)

    if repos.transactions.list(page=1, per_page=1)["total"] == 0:
        repos.transactions.create(transaction_type="sales", amount=4234.5, reference="S001")
        repos.transactions.create(transaction_type="sales", amount=3000.0, reference="S002")
        repos.transactions.create(transaction_type="stock_adjustment", amount=-500.0, reference="ADJ001")

    if repos.invoices.list(page=1, per_page=1)["total"] == 0:
        customer = repos.customers.search("ABC Traders", limit=1)[0]
        product = repos.products.search("Premium Widget", limit=1)[0]
        invoice = repos.invoices.create(
            invoice_number="INV-20260518-0001",
            customer_id=customer.id,
            total_amount=4516.0,
            invoice_date=date.today(),
            sync_status="synced",
            tally_reference="TALLY-1001",
        )
        from database import session_scope
        from models import InvoiceItem

        with session_scope() as session:
            session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    qty=5,
                    rate=250.0,
                    discount=10.0,
                    total=1125.0,
                )
            )

        repos.transactions.create(transaction_type="invoice", amount=invoice.total_amount, reference=invoice.invoice_number)


