"""
Background tasks for invoice retries and scheduled operations.
"""
import threading
import time


class BackgroundTaskManager:
    """Manages background tasks like invoice retry loops."""

    def __init__(self, invoice_service):
        self.invoice = invoice_service
        self.threads = []

    def start_retry_loop(self, interval: int = 60):
        """Start background thread for retrying pending invoices.

        Args:
            interval: seconds between retry attempts
        """
        def retry_loop():
            while True:
                try:
                    self.invoice.process_pending()
                except Exception as e:
                    print(f"Error in retry loop: {e}")
                time.sleep(interval)

        t = threading.Thread(target=retry_loop, daemon=True)
        t.start()
        self.threads.append(t)

    def stop_all(self):
        """Stop all background tasks."""
        # Daemon threads will stop when app exits
        pass
