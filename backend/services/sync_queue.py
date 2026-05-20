"""Durable offline sync queue for Tally actions."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class SyncQueueService:
    def __init__(self, repos):
        self.repos = repos

    def enqueue(
        self,
        *,
        action_type: str,
        entity_type: str,
        payload: Dict[str, Any],
        reference: Optional[str] = None,
        status: str = "pending",
        next_retry_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ):
        return self.repos.sync_queue.create(
            action_type=action_type,
            entity_type=entity_type,
            payload_json=json.dumps(payload or {}),
            status=status,
            retry_count=0,
            next_retry_at=next_retry_at,
            last_error=last_error,
            reference=reference,
        )

    def list_pending(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self.repos.sync_queue.pending(limit=limit)]

    def list_due(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self.repos.sync_queue.due(limit=limit)]

    def get_pending_count(self) -> int:
        return len(self.repos.sync_queue.pending(limit=500))

    def get_failed_count(self) -> int:
        return self._count_status("failed")

    def _count_status(self, status: str) -> int:
        from database import session_scope
        from models import SyncQueueItem

        with session_scope() as session:
            return session.query(SyncQueueItem).filter(SyncQueueItem.status == status).count()

    def mark_success(self, item_id: int, reference: Optional[str] = None):
        item = self.repos.sync_queue.get(item_id)
        if not item:
            return None
        return self.repos.sync_queue.update(
            item,
            status="synced",
            processed_at=datetime.utcnow(),
            last_error=None,
            reference=reference or item.reference,
        )

    def mark_failure(self, item_id: int, error: str, retry_delay_minutes: int = 15):
        from datetime import timedelta

        item = self.repos.sync_queue.get(item_id)
        if not item:
            return None
        return self.repos.sync_queue.update(
            item,
            status="retrying",
            retry_count=int(item.retry_count or 0) + 1,
            last_error=error,
            next_retry_at=datetime.utcnow() + timedelta(minutes=retry_delay_minutes),
        )
