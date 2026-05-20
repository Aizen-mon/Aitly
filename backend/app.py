"""
AI Assistant for Tally Users - Flask Backend
Main application entry point with service initialization and configuration.
"""
import logging
from flask import Flask
from flask_cors import CORS

from database import init_db, SessionLocal
from services.tally_service import TallyService
from services.nlp_service import SimpleNLP
from services.dashboard_service import DashboardService
from services.invoice_service import InvoiceService
from services.cache_service import CacheService
from routes import init_routes
from background_tasks import BackgroundTaskManager
from repositories import RepositoryBundle
from seed import seed_database
from services.conversation_service import ConversationService
from services.ocr_service import OCRService
from services.workflow_engine import WorkflowEngine
from services.voice_service import VoiceService
from services.stt_service import get_stt_service
from whisper_config import get_whisper_config

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    CORS(app)

    init_db()

    repos = RepositoryBundle(SessionLocal)
    seed_database(repos)

    # Initialize services
    tally = TallyService()
    nlp = SimpleNLP()
    dashboard = DashboardService(repos=repos, tally=tally)
    invoice = InvoiceService(tally, repos=repos)
    cache = CacheService()
    workflow = WorkflowEngine(repos=repos, invoice_service=invoice, dashboard_service=dashboard, tally_service=tally)
    conversation = ConversationService(repos, workflow_engine=workflow)
    voice = VoiceService(repos=repos, nlp_service=nlp, workflow_engine=workflow)
    ocr = OCRService()
    
    # Initialize STT service (Faster-Whisper)
    try:
        whisper_config = get_whisper_config()
        stt = get_stt_service(whisper_config)
        logger.info(f"Faster-Whisper initialized: {stt.get_model_info()}")
    except Exception as e:
        logger.warning(f"STT service initialization failed: {e}. Voice features may not work.")
        stt = None

    # Initialize routes with services
    services = {
        "repos": repos,
        "tally": tally,
        "nlp": nlp,
        "dashboard": dashboard,
        "invoice": invoice,
        "cache": cache,
        "conversation": conversation,
        "workflow": workflow,
        "voice": voice,
        "ocr": ocr,
        "stt": stt,
    }
    init_routes(app, services)

    # Start background tasks
    task_manager = BackgroundTaskManager(invoice)
    task_manager.start_retry_loop(interval=60)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
