"""Build conversational assistant responses with speech-friendly metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


class ResponseBuilder:
    def build(
        self,
        *,
        intent: str,
        title: str,
        message: str,
        action: str = "show_message",
        details: Optional[Dict[str, Any]] = None,
        session_state: Optional[Dict[str, Any]] = None,
        speech: Optional[str] = None,
        suggestions: Optional[list] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload = {
            "intent": intent,
            "title": title,
            "message": message,
            "speech": speech or message,
            "action": action,
            "details": details or {},
            "conversation_state": session_state or {"flow": None, "step": None},
            "timestamp": datetime.utcnow().isoformat(),
        }
        if suggestions:
            payload["suggestions"] = suggestions
        if confidence is not None:
            payload["confidence"] = confidence
        return payload

    def prompt(self, title: str, message: str, step: str, flow: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.build(
            intent=flow,
            title=title,
            message=message,
            action="show_conversation_prompt",
            details=details,
            session_state={"flow": flow, "step": step},
        )

    def error(self, message: str, intent: str = "general") -> Dict[str, Any]:
        return self.build(
            intent=intent,
            title="Something went wrong",
            message=message,
            action="show_error",
            session_state={"flow": None, "step": None},
        )
