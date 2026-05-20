"""Local entity extraction and lightweight intent hints for retailer commands."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional


class EntityParser:
    def extract(
        self,
        text: str,
        product_names: Optional[Iterable[str]] = None,
        customer_names: Optional[Iterable[str]] = None,
        context: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        lowered = text.lower().strip()
        context = context or {}
        entities: Dict[str, object] = {}

        customer = self._match_known_name(
            lowered,
            customer_names or [],
            fallback_patterns=(r"(?:customer|from|for)\s+([a-z][a-z\s&.-]{2,})",),
        )
        if customer:
            entities["customer_name"] = customer

        product = self._match_known_name(
            lowered,
            product_names or [],
            fallback_patterns=(
                r"(?:item|product|stock|add|update|delete|remove|search|order|buy)\s+([a-z][a-z0-9\s&.-]{1,})",
            ),
        )
        if product:
            entities["product_name"] = product

        quantity = self._extract_quantity(lowered)
        if quantity is not None:
            entities["quantity"] = quantity

        amount = self._extract_amount(lowered)
        if amount is not None:
            entities["amount"] = amount

        items = self._extract_line_items(lowered, product_names or [])
        if items:
            entities["items"] = items

        if self._is_affirmative(lowered):
            entities["confirmation"] = True
        if self._is_negative(lowered):
            entities["confirmation"] = False

        if any(keyword in lowered for keyword in ("low stock", "stock low", "inventory low")):
            entities["inventory_alert"] = True

        if "more" in lowered and context.get("last_low_stock_items"):
            entities["follow_up_target"] = context.get("last_low_stock_items")

        return entities

    def infer_intent(self, text: str) -> str:
        lowered = text.lower().strip()

        if any(keyword in lowered for keyword in ("create invoice", "new invoice", "invoice create", "generate invoice")):
            return "create_invoice"
        if any(keyword in lowered for keyword in ("record payment", "payment received", "received payment", "clear due", "settle due")):
            return "record_payment"
        if any(keyword in lowered for keyword in ("add inventory", "new stock", "stock add", "add ")):
            return "add_inventory"
        if any(keyword in lowered for keyword in ("update quantity", "set stock", "update stock", "quantity to")):
            return "update_inventory"
        if any(keyword in lowered for keyword in ("delete", "remove", "damaged stock")):
            return "delete_inventory"
        if any(keyword in lowered for keyword in ("search inventory", "find product", "search stock")):
            return "search_inventory"
        if any(keyword in lowered for keyword in ("today sales", "sales today", "today's sales")):
            return "today_sales"
        if any(keyword in lowered for keyword in ("low stock", "stock low", "inventory low", "reorder items")):
            return "low_stock"
        if any(keyword in lowered for keyword in ("pending dues", "pending due", "customer dues", "receivables")):
            return "pending_dues"
        if any(keyword in lowered for keyword in ("overdue customers", "overdue customer", "7 days", "reminder")):
            return "overdue_customers"
        if any(keyword in lowered for keyword in ("inventory summary", "stock summary", "inventory status")):
            return "inventory_summary"
        if any(keyword in lowered for keyword in ("top products", "best products", "top sellers")):
            return "top_products"
        if any(keyword in lowered for keyword in ("recent transactions", "recent sales", "latest sales")):
            return "recent_transactions"
        if any(keyword in lowered for keyword in ("sales summary", "sales report", "monthly sales", "weekly sales")):
            return "sales_summary"

        return "general"

    def _extract_quantity(self, text: str) -> Optional[int]:
        patterns = [
            r"(?:qty|quantity|stock)\s*[:=]??\s*(\d+)",
            r"(\d+)\s*(?:pcs|pieces|units|nos|no\.?|bottles?|packets?|boxes?|items?|cartons?)\b",
            r"add\s+(\d+)\s+[a-z]",
            r"update\s+[a-z0-9\s&.-]+\s+(?:to|=)\s+(\d+)",
            # Voice-specific patterns for Indian English
            r"(?:packet|dozen|score|hundred)\s+(\d+)",  # Common quantity units
            r"(\d+)\s*(?:only|ka)\b",  # Indian English: "5 only", "10 ka"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        # Enhanced pattern for Indian currency
        match = re.search(
            r"(?:₹|rs\.?|rupee|inr|paisa)?\s*(\d+(?:\.\d{1,2})?)\s*(?:rupees?|rs\.?|only)?",
            text,
            re.IGNORECASE
        )
        if match and any(
            keyword in text
            for keyword in (
                "amount", "total", "price", "rate", "due", "payment", "paid",
                "rupees", "rs", "₹"
            )
        ):
            return float(match.group(1))
        return None

    def _match_known_name(
        self, text: str, names: Iterable[str], fallback_patterns: Iterable[str]
    ) -> Optional[str]:
        known = sorted({name.strip() for name in names if name}, key=len, reverse=True)
        for name in known:
            if name and name.lower() in text:
                return name

        for pattern in fallback_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(
                    r"\b(today|please|show|create|new|invoice|item|product|customer|from|for|add|update|delete|remove|search|order|buy)\b.*$",
                    "",
                    candidate,
                    flags=re.IGNORECASE,
                ).strip()
                if candidate:
                    return candidate.title()
        return None

    def _extract_line_items(self, text: str, product_names: Iterable[str]) -> List[Dict[str, object]]:
        items: List[Dict[str, object]] = []
        if not text:
            return items

        for product_name in sorted({name.strip() for name in product_names if name}, key=len, reverse=True):
            if product_name.lower() in text:
                quantity = self._extract_quantity(text) or 1
                items.append({"name": product_name, "qty": quantity, "quantity": quantity})

        if items:
            return items

        # Voice-specific pattern: "5 coke and 2 maggi"
        for qty_text, name in re.findall(
            r"(\d+)\s+(?:of\s+)?([a-z][a-z0-9& .-]{1,}?)(?:\s+and|\s*,|\s+or|\s*$)",
            text,
            re.IGNORECASE,
        ):
            cleaned = name.strip().rstrip(".,")
            if cleaned:
                items.append({
                    "name": cleaned.title(),
                    "qty": int(qty_text),
                    "quantity": int(qty_text),
                })
        
        return items

    def _is_affirmative(self, text: str) -> bool:
        tokens = {token.strip().lower() for token in re.split(r"[\s,.;!?]+", text) if token.strip()}
        return bool(tokens & {"yes", "confirm", "ok", "okay", "done", "sure", "proceed", "go"})

    def _is_negative(self, text: str) -> bool:
        tokens = {token.strip().lower() for token in re.split(r"[\s,.;!?]+", text) if token.strip()}
        return bool(tokens & {"no", "cancel", "stop", "abort", "not"})