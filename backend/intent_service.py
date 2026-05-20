"""Rule-based intent detection for the local AI assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from entity_parser import EntityParser


@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: Dict[str, object]
    matched: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload = {
            "intent": self.intent,
            "confidence": round(self.confidence, 2),
            "entities": self.entities,
        }
        if self.matched:
            payload["matched"] = self.matched
        return payload


class IntentService:
    def __init__(self):
        self.entity_parser = EntityParser()
        self.intent_keywords = {
            "today_sales": ["today sales", "sales today", "today's sales", "todays sales"],
            "low_stock": ["low stock", "stock low", "inventory low", "reorder items"],
            "pending_dues": ["pending dues", "pending dues", "customer dues", "pending payments", "receivables"],
            "overdue_customers": ["overdue customers", "payment reminder", "7 days overdue", "overdue dues"],
            "create_invoice": ["create invoice", "new invoice", "invoice create", "generate invoice"],
            "record_payment": ["record payment", "payment received", "received payment", "clear due", "settle due"],
            "add_inventory": ["add inventory", "new stock", "inventory add", "stock entry"],
            "update_inventory": ["update quantity", "update stock", "set stock", "quantity to"],
            "delete_inventory": ["delete stock", "remove stock", "delete inventory", "damaged stock"],
            "search_inventory": ["search inventory", "find product", "search stock"],
            "recent_transactions": ["recent transactions", "recent sales", "latest transactions", "latest sales"],
            "top_products": ["top products", "best products", "best selling products", "top sellers"],
            "inventory_summary": ["inventory summary", "stock summary", "inventory status"],
            "customer_dues": ["customer dues", "dues by customer", "customer pending"],
            "sales_summary": ["sales summary", "sales report", "monthly sales", "weekly sales"],
        }

    def detect(self, text: str, product_names: Optional[Iterable[str]] = None, customer_names: Optional[Iterable[str]] = None) -> Dict[str, object]:
        normalized = text.strip().lower()
        entities = self.entity_parser.extract(text, product_names=product_names, customer_names=customer_names)

        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in normalized:
                    return IntentResult(intent=intent, confidence=0.95, entities=entities, matched=keyword).to_dict()

        if any(word in normalized for word in ("sales", "sale")):
            return IntentResult(intent="today_sales", confidence=0.6, entities=entities).to_dict()
        if any(word in normalized for word in ("stock", "inventory")):
            return IntentResult(intent="inventory_summary", confidence=0.6, entities=entities).to_dict()
        if any(word in normalized for word in ("due", "receivable", "pending")):
            return IntentResult(intent="pending_dues", confidence=0.6, entities=entities).to_dict()
        if any(word in normalized for word in ("payment", "paid", "received")):
            return IntentResult(intent="record_payment", confidence=0.55, entities=entities).to_dict()
        if any(word in normalized for word in ("invoice", "bill", "quotation")):
            return IntentResult(intent="create_invoice", confidence=0.55, entities=entities).to_dict()

        if entities.get("items"):
            return IntentResult(intent="create_invoice", confidence=0.5, entities=entities).to_dict()

        return IntentResult(intent="general", confidence=0.1, entities=entities).to_dict()
