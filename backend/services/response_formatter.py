"""Business-friendly response formatting for assistant output."""


class ResponseFormatter:
    @staticmethod
    def format_response(intent, data=None):
        data = data or {}

        if intent == "today_sales":
            total = float(data.get("total", data.get("total_amount", 0)) or 0)
            count = int(data.get("count", data.get("invoice_count", 0)) or 0)
            return {
                "intent": "today_sales",
                "title": "Today's Sales Summary",
                "message": f"Today you've made ₹{total:,.0f} in sales with {count} invoices.",
                "details": {
                    "total": f"₹{total:,.0f}",
                    "invoice_count": count,
                    "avg_value": f"₹{(total / count):,.0f}" if count else "₹0",
                },
                "action": "view_invoices",
                "icon": "trending_up",
                "color": "blue",
            }

        if intent == "low_stock":
            items = data.get("items", [])
            return {
                "intent": "low_stock",
                "title": "Low Stock Alert",
                "message": f"You have {len(items)} items running low on stock.",
                "details": {"items": items},
                "action": "view_low_stock",
                "icon": "warning",
                "color": "red",
            }

        if intent == "pending_dues":
            total_due = float(data.get("total_due", 0) or 0)
            customer_count = int(data.get("customer_count", 0) or 0)
            return {
                "intent": "pending_dues",
                "title": "Pending Receivables",
                "message": f"You have ₹{total_due:,.0f} pending from {customer_count} customers.",
                "details": {
                    "total_due": f"₹{total_due:,.0f}",
                    "customer_count": customer_count,
                    "customers": data.get("customers", []),
                },
                "action": "view_pending",
                "icon": "account_balance_wallet",
                "color": "orange",
            }

        if intent == "recent_transactions":
            return {
                "intent": "recent_transactions",
                "title": "Recent Transactions",
                "message": f"Loaded {len(data.get('transactions', []))} recent transactions.",
                "details": {"transactions": data.get("transactions", [])},
                "action": "view_recent_transactions",
                "icon": "receipt_long",
                "color": "blue",
            }

        if intent == "top_products":
            return {
                "intent": "top_products",
                "title": "Top Products",
                "message": f"Here are the top {len(data.get('products', []))} products.",
                "details": {"products": data.get("products", [])},
                "action": "view_top_products",
                "icon": "star",
                "color": "green",
            }

        if intent == "inventory_summary":
            return {
                "intent": "inventory_summary",
                "title": "Inventory Summary",
                "message": f"Your inventory value is ₹{float(data.get('total_value', 0) or 0):,.0f}.",
                "details": data,
                "action": "view_inventory",
                "icon": "inventory_2",
                "color": "green",
            }

        if intent == "customer_dues":
            return {
                "intent": "customer_dues",
                "title": "Customer Dues",
                "message": f"Found {len(data.get('customers', []))} customers with pending dues.",
                "details": data,
                "action": "view_pending",
                "icon": "person",
                "color": "orange",
            }

        if intent == "sales_summary":
            return {
                "intent": "sales_summary",
                "title": "Sales Summary",
                "message": f"Sales summary for {data.get('period', 'today')} is ready.",
                "details": data,
                "action": "view_sales_summary",
                "icon": "bar_chart",
                "color": "blue",
            }

        if intent == "create_invoice":
            next_step = data.get("next_step", "customer_name")
            return {
                "intent": "create_invoice",
                "title": data.get("title", "Create New Invoice"),
                "message": data.get("message", "Please provide the next invoice detail."),
                "next_step": next_step,
                "details": data.get("details", {}),
                "action": data.get("action", "show_invoice_form"),
                "icon": "receipt",
                "color": "green",
            }

        if intent == "ocr_confirmation":
            items = data.get("items", [])
            return {
                "intent": "ocr_confirmation",
                "title": "Confirm Bill Scan",
                "message": f"I found {len(items)} item(s) in the bill. Should I add them to inventory?",
                "details": data,
                "action": "confirm_ocr_items",
                "icon": "document_scanner",
                "color": "teal",
            }

        if intent == "sync_status":
            connected = bool(data.get("connected"))
            return {
                "intent": "sync_status",
                "title": "Tally Sync Status",
                "message": "Connected to Tally." if connected else "Tally is disconnected. Changes are queued locally.",
                "details": data,
                "action": "show_sync_status",
                "icon": "cloud_done" if connected else "cloud_off",
                "color": "green" if connected else "orange",
            }

        if intent == "business_summary":
            return {
                "intent": "business_summary",
                "title": data.get("title", "Business Summary"),
                "message": data.get("message", "Your daily summary is ready."),
                "details": data,
                "action": "show_summary",
                "icon": "summarize",
                "color": "blue",
            }

        if intent == "assistant_alerts":
            return {
                "intent": "assistant_alerts",
                "title": "Smart Alerts",
                "message": data.get("message", "Here are the latest business alerts."),
                "details": data,
                "action": "show_alerts",
                "icon": "notifications_active",
                "color": "red",
            }

        if intent == "record_payment":
            return {
                "intent": "record_payment",
                "title": data.get("title", "Record Payment"),
                "message": data.get("message", "Please provide payment details."),
                "details": data.get("details", {}),
                "action": data.get("action", "show_payment_form"),
                "icon": "payments",
                "color": "purple",
            }

        if intent == "overdue_customers":
            return {
                "intent": "overdue_customers",
                "title": "Overdue Customers",
                "message": f"Found {len(data.get('customers', []))} overdue customers.",
                "details": data,
                "action": "view_pending",
                "icon": "schedule",
                "color": "orange",
            }

        if intent in ("search_inventory", "update_inventory", "delete_inventory"):
            return {
                "intent": intent,
                "title": data.get("title", "Inventory Action"),
                "message": data.get("message", "Inventory action completed."),
                "details": data.get("details", data),
                "action": data.get("action", "view_inventory"),
                "icon": "inventory_2",
                "color": "teal",
            }

        if intent == "add_inventory":
            return {
                "intent": "add_inventory",
                "title": "Add Inventory",
                "message": data.get("message", "Please share product details to add stock."),
                "details": data,
                "action": "open_inventory",
                "icon": "inventory",
                "color": "teal",
            }

        return {
            "intent": "general",
            "title": "How can I help?",
            "message": "I can help with sales, stock, dues, invoices, payments, OCR scans, and sync status.",
            "suggestions": [
                "Show today's sales",
                "Check low stock items",
                "Show pending dues",
                "Create new invoice",
            ],
            "action": "show_suggestions",
            "icon": "help",
            "color": "blue",
        }

    @staticmethod
    def get_suggested_prompts():
        return [
            {"text": "Today's Sales", "intent": "today_sales", "icon": "trending_up"},
            {"text": "Low Stock", "intent": "low_stock", "icon": "warning"},
            {"text": "Pending Dues", "intent": "pending_dues", "icon": "account_balance"},
            {"text": "Record Payment", "intent": "record_payment", "icon": "payments"},
            {"text": "Create Invoice", "intent": "create_invoice", "icon": "receipt"},
            {"text": "Inventory Summary", "intent": "inventory_summary", "icon": "inventory_2"},
            {"text": "Overdue Customers", "intent": "overdue_customers", "icon": "schedule"},
        ]
