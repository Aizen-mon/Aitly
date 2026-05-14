"""
AI Assistant for Tally Users - Flask Backend
Main application entry point with service initialization and configuration.
"""
from flask import Flask
from flask_cors import CORS

from services.tally_service import TallyService
from services.nlp_service import SimpleNLP
from services.dashboard_service import DashboardService
from services.invoice_service import InvoiceService
from services.cache_service import CacheService
from routes import init_routes
from background_tasks import BackgroundTaskManager


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    CORS(app)

    # Initialize services
    tally = TallyService()
    nlp = SimpleNLP()
    dashboard = DashboardService(tally)
    invoice = InvoiceService(tally)
    cache = CacheService()

    # Initialize routes with services
    services = {
        "tally": tally,
        "nlp": nlp,
        "dashboard": dashboard,
        "invoice": invoice,
        "cache": cache
    }
    init_routes(app, services)

    # Start background tasks
    task_manager = BackgroundTaskManager(invoice)
    task_manager.start_retry_loop(interval=60)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
