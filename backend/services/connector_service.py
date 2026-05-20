"""Local-first Tally connector with queue-backed offline sync."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional


class ConnectorService:
    def __init__(self, tally_service, sync_queue_service):
        self.tally = tally_service
        self.sync_queue = sync_queue_service
        self._last_sync_at: Optional[datetime] = None

    def is_connected(self) -> bool:
        return bool(self.tally and self.tally.is_tally_available())

    def sync_invoice(self, invoice_payload: Dict[str, Any], reference: Optional[str] = None) -> Dict[str, Any]:
        return self._sync_action("invoice", invoice_payload, reference=reference)

    def sync_payment(self, payment_payload: Dict[str, Any], reference: Optional[str] = None) -> Dict[str, Any]:
        return self._sync_action("payment", payment_payload, reference=reference)

    def sync_inventory_change(self, inventory_payload: Dict[str, Any], reference: Optional[str] = None) -> Dict[str, Any]:
        return self._sync_action("inventory", inventory_payload, reference=reference)

    def _sync_action(self, action_type: str, payload: Dict[str, Any], reference: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_connected():
            queued = self.sync_queue.enqueue(
                action_type=action_type,
                entity_type=action_type,
                payload=payload,
                reference=reference,
                status="pending",
                last_error="Tally disconnected",
            )
            return {"status": "queued", "message": "Tally is offline. Action queued for retry.", "queue_item": queued.to_dict()}

        try:
            if action_type == "invoice":
                result = self.tally.post_invoice(payload)
            else:
                result = self.tally.post_invoice(payload)

            if result.get("status") == "sent":
                self._last_sync_at = datetime.utcnow()
                return {"status": "sent", "response": result.get("response"), "reference": reference}

            queued = self.sync_queue.enqueue(
                action_type=action_type,
                entity_type=action_type,
                payload=payload,
                reference=reference,
                status="retrying",
                last_error=result.get("error", "Unknown sync error"),
            )
            return {"status": "queued", "message": result.get("error", "Sync failed"), "queue_item": queued.to_dict()}
        except Exception as exc:
            queued = self.sync_queue.enqueue(
                action_type=action_type,
                entity_type=action_type,
                payload=payload,
                reference=reference,
                status="retrying",
                last_error=str(exc),
            )
            return {"status": "queued", "message": str(exc), "queue_item": queued.to_dict()}

    def process_due_jobs(self, limit: int = 10) -> Dict[str, int]:
        due_items = self.sync_queue.list_due(limit=limit)
        processed = 0
        succeeded = 0
        failed = 0

        if not self.is_connected():
            return {"processed": 0, "succeeded": 0, "failed": 0}

        for item in due_items:
            processed += 1
            payload = item.get("payload", {})
            action_type = item.get("action_type", "invoice")

            try:
                result = self.tally.post_invoice(payload) if action_type == "invoice" else self.tally.post_invoice(payload)
                if result.get("status") == "sent":
                    succeeded += 1
                    self.sync_queue.mark_success(item["id"], reference=item.get("reference"))
                else:
                    failed += 1
                    self.sync_queue.mark_failure(item["id"], result.get("error", "Sync failed"))
            except Exception as exc:
                failed += 1
                self.sync_queue.mark_failure(item["id"], str(exc))

        return {"processed": processed, "succeeded": succeeded, "failed": failed}

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected(),
            "last_sync_at": self._last_sync_at.isoformat() if self._last_sync_at else None,
            "pending_count": self.sync_queue.get_pending_count(),
            "failed_count": self.sync_queue._count_status("failed"),
        }
