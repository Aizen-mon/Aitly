"""Retry orchestration for offline sync jobs."""

from __future__ import annotations

import threading
import time
from typing import Dict


class RetryManager:
    def __init__(self, connector_service):
        self.connector = connector_service
        self._threads = []

    def process_due_jobs(self, limit: int = 10) -> Dict[str, int]:
        if not self.connector:
            return {"processed": 0, "succeeded": 0, "failed": 0}
        return self.connector.process_due_jobs(limit=limit)

    def start_loop(self, interval: int = 300):
        def _loop():
            while True:
                try:
                    self.process_due_jobs()
                except Exception:
                    pass
                time.sleep(interval)

        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        self._threads.append(thread)
