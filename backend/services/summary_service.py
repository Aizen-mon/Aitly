"""Daily business summaries and assistant alerts."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from database import session_scope
from models import Invoice


class SummaryService:
    def __init__(self, dashboard_service, connector_service=None):
        self.dashboard = dashboard_service
        self.connector = connector_service

    def get_alerts(self) -> Dict[str, Any]:
        low_stock = self.dashboard.get_low_stock()
        overdue = self.dashboard.get_overdue_customers()
        sync = self.connector.get_status() if self.connector else {"connected": False, "pending_count": 0, "failed_count": 0}

        alerts: List[Dict[str, Any]] = []
        for item in (low_stock.get("items", []) or [])[:5]:
            alerts.append({
                "type": "low_stock",
                "severity": "warning",
                "message": f"{item.get('name')} is low on stock.",
            })

        for customer in (overdue.get("customers", []) or [])[:5]:
            pending_due = float(customer.get("pending_due", 0) or 0)
            alerts.append({
                "type": "overdue_customer",
                "severity": "critical",
                "message": f"{customer.get('customer_name')} payment overdue with ₹{pending_due:,.0f} pending.",
            })

        if sync.get("failed_count", 0):
            alerts.append({
                "type": "sync_failure",
                "severity": "warning",
                "message": f"{sync['failed_count']} sync jobs failed and need attention.",
            })

        return {"alerts": alerts, "count": len(alerts), "sync": sync}

    def generate_morning_summary(self) -> Dict[str, Any]:
        yesterday = date.today() - timedelta(days=1)
        with session_scope() as session:
            invoices = session.query(Invoice).filter(Invoice.invoice_date == yesterday).all()
            sales_total = sum(float(invoice.total_amount or 0) for invoice in invoices)
        low_stock = self.dashboard.get_low_stock()
        overdue = self.dashboard.get_overdue_customers()
        alerts = self.get_alerts()

        summary = [
            "Good morning.",
            f"Yesterday sales were ₹{sales_total:,.0f}.",
            f"{len(low_stock.get('items', []))} products are low on stock.",
            f"{len(overdue.get('customers', []))} customers have overdue payments.",
        ]
        if self.connector:
            sync_status = self.connector.get_status()
            summary.append(
                "Tally is connected." if sync_status.get("connected") else "Tally is currently offline; changes will queue locally."
            )

        return {
            "date": date.today().isoformat(),
            "summary": " ".join(summary),
            "metrics": {
                "yesterday_sales": float(sales_total),
                "low_stock_count": len(low_stock.get("items", [])),
                "overdue_customers": len(overdue.get("customers", [])),
            },
            "alerts": alerts.get("alerts", []),
        }
