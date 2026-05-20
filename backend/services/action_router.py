"""Lightweight routing of assistant intents into workflow actions."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from services.assistant_context import AssistantContext


class ActionRouter:
    def normalize(
        self,
        *,
        session_context: AssistantContext,
        text: str,
        parsed: Dict[str, Any],
        product_names: Optional[Iterable[str]] = None,
        customer_names: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        entities = dict(parsed.get("entities", {}) or {})
        entities = session_context.apply_relative_context(text, entities)

        intent = parsed.get("intent") or "general"
        lowered = text.lower().strip()

        if intent == "general" and session_context.last_intent == "low_stock" and entities.get("quantity") is not None:
            intent = "add_inventory"

        if intent == "general" and session_context.active_products and any(word in lowered for word in ("more", "restock", "order")):
            intent = "add_inventory"

        if intent == "general" and any(word in lowered for word in ("summary", "status", "today", "pending", "overdue", "sales")):
            if "sales" in lowered:
                intent = "today_sales"
            elif "pending" in lowered or "due" in lowered:
                intent = "pending_dues"
            elif "overdue" in lowered:
                intent = "overdue_customers"

        if intent == "create_invoice" and not entities.get("customer_name") and session_context.active_customer:
            entities["customer_name"] = session_context.active_customer

        if intent in {"add_inventory", "update_inventory", "delete_inventory", "search_inventory"} and not entities.get("product_name") and session_context.active_products:
            entities["product_name"] = session_context.active_products[0]

        return {
            "intent": intent,
            "entities": entities,
            "session_context": session_context,
        }

    def workflow_key(self, intent: str) -> str:
        if intent in {"create_invoice", "record_payment", "add_inventory", "update_inventory", "delete_inventory"}:
            return intent
        return "query"
