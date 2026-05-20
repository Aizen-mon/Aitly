"""Assistant memory and conversational context helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class AssistantContext:
    session_id: str
    current_flow: Optional[str] = None
    previous_entities: Dict[str, Any] = field(default_factory=dict)
    active_customer: Optional[str] = None
    active_products: List[str] = field(default_factory=list)
    last_intent: Optional[str] = None
    last_text: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_session(cls, session_state) -> "AssistantContext":
        try:
            previous_entities = json.loads(getattr(session_state, "previous_entities", "{}") or "{}")
        except Exception:
            previous_entities = {}
        try:
            active_products = json.loads(getattr(session_state, "active_products", "[]") or "[]")
        except Exception:
            active_products = []

        return cls(
            session_id=getattr(session_state, "session_id", "default"),
            current_flow=getattr(session_state, "current_flow", None),
            previous_entities=previous_entities if isinstance(previous_entities, dict) else {},
            active_customer=getattr(session_state, "active_customer", None),
            active_products=[item for item in active_products if item],
            last_intent=getattr(session_state, "last_intent", None),
            updated_at=getattr(session_state, "updated_at", datetime.utcnow()) or datetime.utcnow(),
        )

    def to_session_payload(self) -> Dict[str, str]:
        return {
            "previous_entities": json.dumps(self.previous_entities or {}),
            "active_customer": self.active_customer,
            "active_products": json.dumps(self.active_products or []),
            "last_intent": self.last_intent,
            "context_json": json.dumps(self.to_dict()),
            "current_flow": self.current_flow,
            "updated_at": datetime.utcnow(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_flow": self.current_flow,
            "previous_entities": self.previous_entities,
            "active_customer": self.active_customer,
            "active_products": self.active_products,
            "last_intent": self.last_intent,
            "last_text": self.last_text,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def remember(self, *, intent: Optional[str] = None, text: Optional[str] = None, entities: Optional[Dict[str, Any]] = None) -> None:
        if intent:
            self.last_intent = intent
        if text:
            self.last_text = text
        if entities:
            self.previous_entities.update({key: value for key, value in entities.items() if value is not None})
            customer_name = entities.get("customer_name")
            if customer_name:
                self.active_customer = customer_name
            items = entities.get("items") or []
            if items:
                names = []
                for item in items:
                    name = item.get("name") or item.get("product_name")
                    if name and name not in names:
                        names.append(name)
                if names:
                    self.active_products = names
            product_name = entities.get("product_name")
            if product_name and product_name not in self.active_products:
                self.active_products = [product_name] + self.active_products[:2]
        self.updated_at = datetime.utcnow()

    def apply_relative_context(self, text: str, entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        entities = dict(entities or {})
        lowered = text.lower().strip()

        if not entities.get("customer_name") and self.active_customer and any(word in lowered for word in ("customer", "party", "them", "him", "her")):
            entities["customer_name"] = self.active_customer

        if entities.get("quantity") is not None and not entities.get("product_name") and self.active_products:
            if any(word in lowered for word in ("more", "again", "same", "them", "those")):
                entities["product_name"] = self.active_products[0]

        if "follow_up_target" in entities and not entities.get("items") and self.active_products:
            entities["items"] = [{"name": product, "qty": entities.get("quantity", 1), "quantity": entities.get("quantity", 1)} for product in self.active_products]

        return entities


def merge_known_names(items: Iterable[str]) -> List[str]:
    return [item for item in {value.strip() for value in items if value} if item]