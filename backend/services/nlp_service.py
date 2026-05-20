"""Backward-compatible wrapper around the local intent engine."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from intent_service import IntentService


class SimpleNLP:
    def __init__(self):
        self.intent_service = IntentService()

    def parse(self, text: str, product_names: Optional[Iterable[str]] = None, customer_names: Optional[Iterable[str]] = None) -> Dict:
        return self.intent_service.detect(text, product_names=product_names, customer_names=customer_names)
