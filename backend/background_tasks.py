"""Background tasks for invoice retries and scheduled operations."""

import threading
import time


class BackgroundTaskManager:
    def __init__(self, invoice_service, retry_manager=None):
        self.invoice = invoice_service
        self.retry_manager = retry_manager
        self.threads = []

    def start_retry_loop(self, interval: int = 300):
        def retry_loop():
            while True:
                try:
                    self.invoice.process_pending()
                    if self.retry_manager:
                        self.retry_manager.process_due_jobs()
                except Exception as exc:
                    print(f"Error in retry loop: {exc}")
                time.sleep(interval)

        thread = threading.Thread(target=retry_loop, daemon=True)
        thread.start()
        self.threads.append(thread)

    def stop_all(self):
        pass
