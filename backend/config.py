import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'ai_tally.db')}"
TALLY_HOST = os.environ.get("TALLY_HOST", "http://localhost:9000")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
