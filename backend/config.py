import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'ai_tally.db')}"
TALLY_HOST = os.environ.get("TALLY_HOST", "http://localhost:9000")
