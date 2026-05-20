"""Voice command routing and execution."""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CommandRouter:
    """
    Route voice commands to appropriate handlers.
    Supports inventory, invoicing, payments, and dashboard queries.
    """
    
    def __init__(self):
        """Initialize command router."""
        self.handlers: Dict[str, Callable] = {}
        self.intent_to_handlers: Dict[str, list[str]] = {}
        self._register_default_handlers()
    
    def register_handler(
        self,
        command_name: str,
        handler: Callable,
        intents: Optional[list[str]] = None,
    ) -> None:
        """
        Register a command handler.
        
        Args:
            command_name: Unique handler name
            handler: Handler function
            intents: List of intents this handler can handle
        """
        self.handlers[command_name] = handler
        
        if intents:
            for intent in intents:
                if intent not in self.intent_to_handlers:
                    self.intent_to_handlers[intent] = []
                if command_name not in self.intent_to_handlers[intent]:
                    self.intent_to_handlers[intent].append(command_name)
    
    def _register_default_handlers(self) -> None:
        """Register placeholder handlers for default commands."""
        # These will be overridden by actual service handlers
        default_handlers = {
            "handle_today_sales": ["today_sales"],
            "handle_low_stock": ["low_stock"],
            "handle_pending_dues": ["pending_dues"],
            "handle_overdue_customers": ["overdue_customers"],
            "handle_create_invoice": ["create_invoice"],
            "handle_record_payment": ["record_payment"],
            "handle_add_inventory": ["add_inventory"],
            "handle_update_inventory": ["update_inventory"],
            "handle_delete_inventory": ["delete_inventory"],
            "handle_search_inventory": ["search_inventory"],
            "handle_recent_transactions": ["recent_transactions"],
            "handle_top_products": ["top_products"],
            "handle_inventory_summary": ["inventory_summary"],
            "handle_customer_dues": ["customer_dues"],
            "handle_sales_summary": ["sales_summary"],
            "handle_general": ["general"],
        }
        
        for handler_name, intents in default_handlers.items():
            # Create a placeholder function
            def placeholder_handler(intent, entities, **kwargs):
                return {
                    "status": "not_implemented",
                    "intent": intent,
                    "message": f"Handler not yet implemented for {intent}",
                }
            
            self.register_handler(handler_name, placeholder_handler, intents)
    
    def get_handler(self, intent: str) -> Optional[Callable]:
        """Get the primary handler for an intent."""
        handler_names = self.intent_to_handlers.get(intent, [])
        if handler_names:
            return self.handlers.get(handler_names[0])
        return None
    
    def get_handlers(self, intent: str) -> list[Callable]:
        """Get all handlers for an intent."""
        handler_names = self.intent_to_handlers.get(intent, [])
        return [self.handlers[name] for name in handler_names if name in self.handlers]
    
    def execute(
        self,
        intent: str,
        entities: Dict[str, object],
        session_id: Optional[str] = None,
        **context,
    ) -> Dict[str, object]:
        """
        Execute command for an intent.
        
        Args:
            intent: Detected intent
            entities: Extracted entities
            session_id: User session ID
            **context: Additional context
            
        Returns:
            Command execution result
        """
        handler = self.get_handler(intent)
        
        if not handler:
            logger.warning(f"No handler found for intent: {intent}")
            return {
                "status": "error",
                "intent": intent,
                "message": f"No handler for intent: {intent}",
            }
        
        try:
            result = handler(intent, entities, session_id=session_id, **context)
            result.setdefault("intent", intent)
            result.setdefault("status", "success")
            return result
        
        except Exception as e:
            logger.error(f"Handler execution failed for {intent}: {e}")
            return {
                "status": "error",
                "intent": intent,
                "message": str(e),
            }
    
    def get_available_intents(self) -> list[str]:
        """Get list of available intents."""
        return sorted(list(self.intent_to_handlers.keys()))
    
    def get_available_commands(self) -> Dict[str, list[str]]:
        """Get mapping of intents to available commands."""
        return {
            intent: handlers
            for intent, handlers in sorted(self.intent_to_handlers.items())
        }


# Voice command patterns for Indian retailer use cases
INVENTORY_COMMANDS = {
    "add_inventory": [
        "add 20 coke bottles",
        "add 5 maggi",
        "stock 10 parle-g",
        "add inventory",
    ],
    "update_inventory": [
        "update parle-g quantity to 50",
        "set coke stock to 25",
        "update quantity",
    ],
    "search_inventory": [
        "search maggi stock",
        "find coke",
        "check inventory",
    ],
    "low_stock": [
        "show low stock items",
        "items to reorder",
        "low inventory",
    ],
}

INVOICE_COMMANDS = {
    "create_invoice": [
        "create invoice",
        "new invoice",
        "add 5 coke and 2 maggi",
    ],
    "show_recent_invoices": [
        "recent invoices",
        "last invoices",
        "show bills",
    ],
}

PAYMENT_COMMANDS = {
    "record_payment": [
        "record payment from abc traders",
        "payment received",
        "clear due",
    ],
    "pending_dues": [
        "show pending dues",
        "customer receivables",
        "what do customers owe",
    ],
    "overdue_customers": [
        "show overdue customers",
        "overdue payments",
        "payment reminders",
    ],
}

DASHBOARD_COMMANDS = {
    "today_sales": [
        "today sales",
        "sales today",
        "how much sold",
    ],
    "top_products": [
        "top products",
        "best selling",
        "popular items",
    ],
    "inventory_summary": [
        "inventory summary",
        "stock status",
        "total inventory",
    ],
    "sales_summary": [
        "sales summary",
        "sales report",
        "monthly sales",
    ],
}

# Combined for reference
ALL_VOICE_COMMANDS = {
    **INVENTORY_COMMANDS,
    **INVOICE_COMMANDS,
    **PAYMENT_COMMANDS,
    **DASHBOARD_COMMANDS,
}
