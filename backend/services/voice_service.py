"""Voice transcript processing for the assistant."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from services.entity_parser import EntityParser


class VoiceService:
    def __init__(self, repos, nlp_service, workflow_engine, response_builder=None):
        self.repos = repos
        self.nlp = nlp_service
        self.workflow = workflow_engine
        self.parser = EntityParser()
        self.response_builder = response_builder or getattr(workflow_engine, "builder", None)

    def process(self, session_id: str, transcript: str, product_names: Optional[Iterable[str]] = None, customer_names: Optional[Iterable[str]] = None) -> Dict[str, object]:
        product_names = list(product_names or [])
        customer_names = list(customer_names or [])
        parsed = self.nlp.parse(transcript, product_names=product_names, customer_names=customer_names)
        parsed["entities"] = parsed.get("entities", {}) or {}
        parsed["entities"].update(self.parser.extract(transcript, product_names=product_names, customer_names=customer_names))

        result = self.workflow.process(
            session_id=session_id,
            text=transcript,
            parsed=parsed,
            product_names=product_names,
            customer_names=customer_names,
        )

        result.setdefault("session_id", session_id)
        result.setdefault("transcript", transcript)
        return result
