from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, desc

from database import session_scope
from models import Customer, Invoice, InvoiceItem, Product, Transaction
from .tally_service import TallyService


class DashboardService:
    def __init__(self, repos=None, tally: TallyService = None, connector_service=None):
        self.repos = repos
        self.tally = tally or TallyService()
        self.connector = connector_service

    def _db_available(self):
        return self.repos is not None

    def get_today_sales(self):
        today = date.today()
        with session_scope() as session:
            invoices = session.query(Invoice).filter(Invoice.invoice_date == today).all()
            total = sum(float(invoice.total_amount or 0) for invoice in invoices)
            return {
                "count": len(invoices),
                "total": total,
                "invoices": [invoice.to_dict() for invoice in invoices],
            }

    def get_low_stock(self, threshold=10):
        with session_scope() as session:
            products = (
                session.query(Product)
                .filter((Product.quantity <= threshold) | (Product.quantity <= Product.reorder_level))
                .order_by(Product.quantity.asc())
                .all()
            )
            items = [
                {
                    "id": product.id,
                    "name": product.item_name,
                    "qty": float(product.quantity or 0),
                    "reorder_qty": float(product.reorder_level or threshold),
                }
                for product in products
            ]
            return {"items": items, "threshold": threshold, "count": len(items)}

    def get_pending_dues(self):
        with session_scope() as session:
            customers = (
                session.query(Customer)
                .filter(Customer.pending_due > 0)
                .order_by(Customer.pending_due.desc())
                .all()
            )
            total_due = sum(float(customer.pending_due or 0) for customer in customers)
            return {
                "total_due": total_due,
                "customer_count": len(customers),
                "customers": [customer.to_dict() for customer in customers],
            }

    def get_overdue_customers(self, days: int = 7):
        cutoff = date.today() - timedelta(days=days)
        with session_scope() as session:
            customers = (
                session.query(Customer)
                .filter(Customer.pending_due > 0)
                .all()
            )
            overdue = []
            for customer in customers:
                last_payment = customer.last_payment_date
                if last_payment is None or last_payment <= cutoff:
                    overdue.append(customer.to_dict())
            return {
                "days": days,
                "count": len(overdue),
                "customers": overdue,
                "total_due": sum(float(customer.get("pending_due", 0) or 0) for customer in overdue),
            }

    def get_inventory(self):
        with session_scope() as session:
            products = session.query(Product).order_by(Product.created_at.desc()).all()
            total_value = sum(float(product.quantity or 0) * float(product.rate or 0) for product in products)
            return {
                "total_items": len(products),
                "total_value": total_value,
                "items": [
                    {
                        "name": product.item_name,
                        "qty": float(product.quantity or 0),
                        "value": float(product.quantity or 0) * float(product.rate or 0),
                        "reorder": float(product.reorder_level or 0),
                    }
                    for product in products
                ],
            }

    def get_customers(self):
        with session_scope() as session:
            customers = session.query(Customer).order_by(Customer.created_at.desc()).all()
            total_receivable = sum(float(customer.pending_due or 0) for customer in customers)
            return {
                "total_customers": len(customers),
                "total_receivable": total_receivable,
                "customers": [customer.to_dict() for customer in customers],
            }

    def get_recent_transactions(self, limit=20, days=30):
        cutoff = datetime.utcnow() - timedelta(days=days)
        with session_scope() as session:
            transactions = (
                session.query(Transaction)
                .filter(Transaction.created_at >= cutoff)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
                .all()
            )
            return {
                "limit": limit,
                "days": days,
                "transactions": [transaction.to_dict() for transaction in transactions],
            }

    def get_top_products(self, limit=5):
        with session_scope() as session:
            rows = (
                session.query(
                    Product.item_name.label("name"),
                    func.sum(InvoiceItem.qty).label("qty_sold"),
                    func.sum(InvoiceItem.total).label("revenue"),
                )
                .join(InvoiceItem, InvoiceItem.product_id == Product.id)
                .group_by(Product.id)
                .order_by(desc(func.sum(InvoiceItem.total)))
                .limit(limit)
                .all()
            )
            if rows:
                return {
                    "limit": limit,
                    "period": "local-db",
                    "products": [
                        {"name": row.name, "qty_sold": float(row.qty_sold or 0), "revenue": float(row.revenue or 0)}
                        for row in rows
                    ],
                }
        return self.tally.fetch_top_products(limit=limit)

    def get_sales_summary(self, period="today"):
        today = date.today()
        if period == "week":
            start_date = today - timedelta(days=7)
        elif period == "month":
            start_date = today - timedelta(days=30)
        else:
            start_date = today

        with session_scope() as session:
            invoices = session.query(Invoice).filter(Invoice.invoice_date >= start_date).all()
            total = sum(float(invoice.total_amount or 0) for invoice in invoices)
            return {"period": period, "count": len(invoices), "total": total, "invoices": [invoice.to_dict() for invoice in invoices]}

    def get_accounts_summary(self):
        with session_scope() as session:
            receivable = session.query(func.coalesce(func.sum(Customer.pending_due), 0.0)).scalar() or 0.0
            sales = session.query(func.coalesce(func.sum(Invoice.total_amount), 0.0)).scalar() or 0.0
            inventory = session.query(Product).all()
            inventory_value = sum(float(product.quantity or 0) * float(product.rate or 0) for product in inventory)
            return {
                "accounts": {
                    "sales": float(sales),
                    "purchases": 0.0,
                    "receivable": float(receivable),
                    "payable": 0.0,
                    "cash": float(max(sales - receivable, 0.0)),
                    "inventory_value": float(inventory_value),
                }
            }

    def get_sync_status(self):
        if self.connector:
            return self.connector.get_status()
        return {
            "connected": self.tally.is_tally_available(),
            "last_sync_at": None,
            "pending_count": 0,
            "failed_count": 0,
        }

    def get_assistant_alerts(self):
        low_stock = self.get_low_stock()
        overdue = self.get_overdue_customers()
        sync = self.get_sync_status()

        alerts = []
        for item in (low_stock.get("items", []) or [])[:5]:
            alerts.append({
                "type": "low_stock",
                "severity": "warning",
                "message": f"{item.get('name')} is low on stock.",
            })
        for customer in (overdue.get("customers", []) or [])[:5]:
            alerts.append({
                "type": "overdue_customer",
                "severity": "critical",
                "message": f"{customer.get('customer_name')} payment overdue by several days.",
            })
        if sync.get("failed_count", 0):
            alerts.append({
                "type": "sync_failure",
                "severity": "warning",
                "message": f"{sync['failed_count']} sync jobs failed.",
            })
        return {"alerts": alerts, "count": len(alerts), "sync": sync}

    def get_quotation_context(self, limit=10, days=30, threshold=10):
        inventory = self.get_inventory()
        recent_transactions = self.get_recent_transactions(limit=limit, days=days)
        top_products = self.get_top_products(limit=limit)
        customers = self.get_customers()

        catalog = []
        for item in inventory.get("items", []):
            qty = float(item.get("qty", 0) or 0)
            value = float(item.get("value", 0) or 0)
            rate = round(value / qty, 2) if qty else 0.0
            discount_percent = 5 if qty and qty <= threshold else 0
            dp = round(rate * (1 - (discount_percent / 100)), 2) if rate else 0.0
            catalog.append({
                "name": item.get("name", ""),
                "stock_qty": qty,
                "unit": "Nos",
                "rate": rate,
                "discount_percent": discount_percent,
                "discount_amount": round(rate - dp, 2) if rate else 0.0,
                "dp": dp,
                "mrp": round(rate * 1.15, 2) if rate else 0.0,
                "tax_percent": 18,
                "warehouse": "Main Godown",
                "last_sold": date.today().isoformat(),
                "available": qty > 0,
                "hsn": "0000",
            })

        previous_sales = []
        for txn in recent_transactions.get("transactions", []):
            if txn.get("transaction_type") == "sales" or txn.get("transaction_type") == "invoice":
                previous_sales.append({
                    "invoice": txn.get("reference", ""),
                    "party": "Local DB",
                    "date": txn.get("created_at", ""),
                    "amount": txn.get("amount", 0),
                })

        return {
            "status": "ok",
            "company": "Local SME",
            "currency": "INR",
            "catalog": catalog,
            "previous_sales": previous_sales,
            "top_products": top_products.get("products", []),
            "customers": customers.get("customers", []),
            "inventory_summary": {
                "total_items": inventory.get("total_items", 0),
                "total_value": inventory.get("total_value", 0),
                "low_stock_count": len(self.get_low_stock(threshold=threshold).get("items", [])),
            },
            "pricing_notes": [
                "Suggested discount is derived from stock pressure.",
                "DP is shown as a discounted selling price for fast quotation.",
                "MRP is estimated from the base rate when not synced from Tally.",
            ],
            "logistics": {
                "warehouses": ["Main Godown", "Secondary Godown"],
                "delivery_modes": ["Pickup", "Local Delivery", "Courier"],
                "lead_time_days": 2,
            },
            "filters": {"limit": limit, "days": days, "threshold": threshold},
        }
