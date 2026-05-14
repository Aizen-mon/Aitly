# AI Assistant for Tally Users - Backend

Flask backend for Tally integration, rule-based NLP, and dashboard APIs.

Run (recommended in virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export FLASK_APP=app.py
flask run --port 5000
```

Key files:

- `app.py` - Flask entrypoint and routes
- `services/tally_service.py` - Tally XML integration
- `services/nlp_service.py` - Rule-based intent recognition
- `services/dashboard_service.py` - Aggregation of data
- `models.py` - SQLAlchemy models (SQLite by default)
