"""Background tasks for invoice retries and scheduled operations."""

import threading
import time


class BackgroundTaskManager:
    def __init__(self, invoice_service):
        self.invoice = invoice_service
        self.threads = []

    def start_retry_loop(self, interval: int = 300):
        def retry_loop():
            while True:
                try:
                    self.invoice.process_pending()
                except Exception as exc:
                    print(f"Error in retry loop: {exc}")
                time.sleep(interval)

        thread = threading.Thread(target=retry_loop, daemon=True)
        thread.start()
        self.threads.append(thread)

    def stop_all(self):
        pass
