"""Conversation state handling for multi-step assistant flows."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from models import ConversationSession
from repositories import RepositoryBundle
from services.entity_parser import EntityParser


class ConversationService:
    def __init__(self, repos: RepositoryBundle, workflow_engine=None):
        self.repos = repos
        self.workflow_engine = workflow_engine
        self.entity_parser = EntityParser()

    def _ensure_state(self, session_id: str) -> ConversationSession:
        state = self.repos.conversation_sessions.get_by_session(session_id)
        if state:
            return state
        return self.repos.conversation_sessions.create(
            session_id=session_id,
            current_flow=None,
            current_step=None,
            context_json=json.dumps({}),
        )

    def _context(self, state: ConversationSession) -> Dict[str, object]:
        try:
            return json.loads(state.context_json or "{}")
        except Exception:
            return {}

    def _save_context(self, state: ConversationSession, context: Dict[str, object], current_flow: Optional[str], current_step: Optional[str]):
        updated = self.repos.conversation_sessions.update(
            state,
            context_json=json.dumps(context),
            current_flow=current_flow,
            current_step=current_step,
        )
        return updated

    def handle(self, session_id: str, text: str, intent: Dict[str, object], product_names: Optional[List[str]] = None, customer_names: Optional[List[str]] = None) -> Dict[str, object]:
        if self.workflow_engine:
            return self.workflow_engine.process(
                session_id=session_id,
                text=text,
                parsed=intent,
                product_names=product_names,
                customer_names=customer_names,
            )

        state = self._ensure_state(session_id)
        context = self._context(state)
        entities = intent.get("entities", {}) if isinstance(intent, dict) else {}
        detected_intent = intent.get("intent", "general") if isinstance(intent, dict) else "general"

        context.setdefault("last_intent", detected_intent)
        self._save_context(state, context, None, None)
        return {"conversation_state": {"flow": None, "step": None}}
