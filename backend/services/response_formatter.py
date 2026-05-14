"""
Response formatter service to convert raw data into business-friendly messages.
"""


class ResponseFormatter:
    """Formats API responses into readable, actionable business messages."""

    @staticmethod
    def format_response(intent, data=None):
        """
        Format a response based on the detected intent.

        Args:
            intent (str): The detected intent (e.g., 'today_sales', 'low_stock')
            data (dict): Optional data to include in the response

        Returns:
            dict: Formatted response with title, message, action, and data
        """
        if intent == "today_sales":
            return {
                "intent": "today_sales",
                "title": "Today's Sales Summary",
                "message": "Today you've made ₹15,432 in sales with 5 invoices.",
                "details": {
                    "total": "₹15,432",
                    "invoice_count": 5,
                    "avg_value": "₹3,086",
                },
                "action": "view_invoices",
                "icon": "trending_up",
                "color": "blue",
            }

        elif intent == "low_stock":
            return {
                "intent": "low_stock",
                "title": "Low Stock Alert",
                "message": "You have 4 items running low on stock. Recommended to reorder soon.",
                "details": {
                    "critical_count": 2,  # Below 5 units
                    "warning_count": 2,  # Below 10 units
                    "items": [
                        {"name": "Item A", "qty": 2, "reorder": 50},
                        {"name": "Item D", "qty": 1, "reorder": 30},
                    ],
                },
                "action": "view_low_stock",
                "icon": "warning",
                "color": "red",
            }

        elif intent == "pending_dues":
            return {
                "intent": "pending_dues",
                "title": "Pending Receivables",
                "message": "You have ₹8,750 pending from 3 customers. Follow up recommended.",
                "details": {
                    "total_due": "₹8,750",
                    "customer_count": 3,
                    "overdue_count": 1,
                    "avg_days_overdue": 5,
                },
                "action": "view_pending",
                "icon": "account_balance_wallet",
                "color": "orange",
            }

        elif intent == "create_invoice":
            return {
                "intent": "create_invoice",
                "title": "Create New Invoice",
                "message": "Ready to create a new invoice. Please provide customer details.",
                "next_steps": [
                    "Select customer",
                    "Add items and quantities",
                    "Review and create",
                ],
                "action": "show_invoice_form",
                "icon": "receipt",
                "color": "green",
            }

        elif intent == "inventory":
            return {
                "intent": "inventory",
                "title": "Inventory Summary",
                "message": "Your total inventory value is ₹1,25,400 across all items.",
                "details": {
                    "total_value": "₹1,25,400",
                    "total_items": 45,
                    "categories": {"Product": 25, "Material": 20},
                },
                "action": "view_inventory",
                "icon": "inventory_2",
                "color": "green",
            }

        else:
            return {
                "intent": "general",
                "title": "How can I help?",
                "message": "I can help you with: Today's Sales, Low Stock Alerts, Pending Dues, Creating Invoices, and more.",
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
        """Return suggested prompts to help users."""
        return [
            {"text": "Today's Sales", "intent": "today_sales", "icon": "trending_up"},
            {"text": "Low Stock", "intent": "low_stock", "icon": "warning"},
            {"text": "Pending Dues", "intent": "pending_dues", "icon": "account_balance"},
            {"text": "Create Invoice", "intent": "create_invoice", "icon": "receipt"},
        ]
