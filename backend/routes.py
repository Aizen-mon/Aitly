"""API routes for the AI Tally Assistant."""

from __future__ import annotations

import base64
import datetime
import json

from flask import Blueprint, jsonify, request
from services.audio_processor import AudioProcessor

from services.response_formatter import ResponseFormatter




def _paginate_request(repo):
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
    return repo.list(page=page, per_page=per_page)


def init_routes(flask_app, services):
    # Create a fresh Blueprint per app instance to allow multiple app creations
    api = Blueprint("api", __name__, url_prefix="/api")

    tally = services["tally"]
    nlp = services["nlp"]
    dashboard = services["dashboard"]
    invoice = services["invoice"]
    cache = services.get("cache")
    repos = services["repos"]
    conversation = services.get("conversation")
    voice = services.get("voice")
    ocr = services.get("ocr")

    def _known_names(repo, attribute):
        data = repo.list(page=1, per_page=1000)
        return [item.get(attribute, "") for item in data.get("items", []) if item.get(attribute)]

    def _session_id():
        payload = request.json or {}
        return payload.get("session_id") or request.headers.get("X-Session-ID") or "default"

    def _log_query(text, intent, response):
        try:
            repos.query_history.create(query=text, response=json.dumps(response), intent=intent)
        except Exception:
            pass

    def _log_voice(text, intent, confidence=0.0):
        try:
            repos.voice_history.create(transcript=text, detected_intent=intent, confidence=float(confidence or 0))
        except Exception:
            pass

    def _dashboard_payload():
        sales = dashboard.get_today_sales()
        low_stock = dashboard.get_low_stock()
        dues = dashboard.get_pending_dues()
        inventory = dashboard.get_inventory()
        recent = dashboard.get_recent_transactions(limit=10, days=30)
        top_products = dashboard.get_top_products(limit=5)
        return {
            "date": datetime.date.today().isoformat(),
            "kpis": {
                "today_sales": {
                    "value": sales.get("total", 0),
                    "currency": "₹",
                    "label": "Today's Sales",
                    "count": sales.get("count", 0),
                    "unit": "invoices",
                },
                "low_stock_count": {
                    "value": low_stock.get("count", 0),
                    "label": "Low Stock Items",
                    "threshold": 10,
                    "color": "warning",
                },
                "pending_due": {
                    "value": dues.get("total_due", 0),
                    "currency": "₹",
                    "label": "Pending Dues",
                    "count": dues.get("customer_count", 0),
                    "unit": "customers",
                },
                "inventory_value": {
                    "value": inventory.get("total_value", 0),
                    "currency": "₹",
                    "label": "Total Inventory",
                },
            },
            "recent_activity": [
                {
                    "time": item.get("created_at", ""),
                    "action": item.get("reference") or item.get("transaction_type", "Transaction"),
                    "amount": item.get("amount", 0),
                }
                for item in recent.get("transactions", [])[:3]
            ],
            "low_stock_items": low_stock.get("items", [])[:5],
            "top_products": top_products.get("products", [])[:5],
        }

    @api.route("/parse", methods=["POST"])
    def parse_intent():
        data = request.json or {}
        text = data.get("text", "")
        product_names = _known_names(repos.products, "item_name")
        customer_names = _known_names(repos.customers, "customer_name")
        result = voice.process(_session_id(), text, product_names=product_names, customer_names=customer_names) if voice else nlp.parse(text, product_names=product_names, customer_names=customer_names)

        session_id = _session_id()
        if cache:
            cache.add_query(text, intent=result.get("intent", "general"), source="user")

        payload = dict(result or {})
        intent = payload.get("intent", "general")
        entities = payload.get("details", {}) if isinstance(payload.get("details"), dict) else payload.get("entities", {}) or {}

        if conversation and voice is None:
            conversation_result = conversation.handle(session_id, text, result, product_names=product_names, customer_names=customer_names)
            if conversation_result:
                payload.update(conversation_result)

        payload.setdefault("entities", entities)
        payload.setdefault("confidence", result.get("confidence", 0))
        payload.setdefault("session_id", session_id)
        formatted = payload

        _log_query(text, intent, formatted)
        _log_voice(text, intent, result.get("confidence", 0))
        return jsonify(formatted)

    @api.route("/suggested_prompts", methods=["GET"])
    def suggested_prompts():
        return jsonify({"prompts": ResponseFormatter.get_suggested_prompts()})

    @api.route("/dashboard_summary", methods=["GET"])
    def dashboard_summary():
        return jsonify(_dashboard_payload())

    @api.route("/today_sales", methods=["GET"])
    def today_sales():
        return jsonify(dashboard.get_today_sales())

    @api.route("/low_stock", methods=["GET"])
    def low_stock():
        threshold = int(request.args.get("threshold", 10))
        return jsonify(dashboard.get_low_stock(threshold=threshold))

    @api.route("/pending_dues", methods=["GET"])
    def pending_dues():
        return jsonify(dashboard.get_pending_dues())

    @api.route("/tally_snapshot", methods=["GET"])
    def tally_snapshot():
        threshold = int(request.args.get("threshold", 10))
        limit = int(request.args.get("limit", 10))
        days = int(request.args.get("days", 30))
        period = request.args.get("period", "today")
        quotation_context = dashboard.get_quotation_context(limit=limit, days=days, threshold=threshold)
        return jsonify({
            "inventory": dashboard.get_inventory(),
            "customers": dashboard.get_customers(),
            "recent_transactions": dashboard.get_recent_transactions(limit=limit, days=days),
            "top_products": dashboard.get_top_products(limit=limit),
            "sales_summary": dashboard.get_sales_summary(period=period),
            "accounts_summary": dashboard.get_accounts_summary(),
            "low_stock": dashboard.get_low_stock(threshold=threshold),
            "pending_dues": dashboard.get_pending_dues(),
            "quotation_context": quotation_context,
            "filters": {"threshold": threshold, "limit": limit, "days": days, "period": period},
        })

    @api.route("/quotation_context", methods=["GET"])
    def quotation_context():
        threshold = int(request.args.get("threshold", 10))
        limit = int(request.args.get("limit", 10))
        days = int(request.args.get("days", 30))
        return jsonify(dashboard.get_quotation_context(limit=limit, days=days, threshold=threshold))

    @api.route("/inventory", methods=["GET"])
    def inventory():
        return jsonify(dashboard.get_inventory())

    @api.route("/customers", methods=["GET", "POST"])
    def customers():
        if request.method == "GET":
            return jsonify(_paginate_request(repos.customers))
        customer = repos.customers.create(**(request.json or {}))
        return jsonify(customer.to_dict()), 201

    @api.route("/customers/<int:customer_id>", methods=["GET", "PUT", "DELETE"])
    def customer_detail(customer_id):
        customer = repos.customers.get(customer_id)
        if not customer:
            return jsonify({"status": "error", "message": "Customer not found"}), 404
        if request.method == "GET":
            return jsonify(customer.to_dict())
        if request.method == "DELETE":
            repos.customers.delete(customer)
            return jsonify({"status": "deleted"})
        updated = repos.customers.update(customer, **(request.json or {}))
        return jsonify(updated.to_dict())

    @api.route("/customers/<int:customer_id>/payments", methods=["GET", "POST"])
    def customer_payments(customer_id):
        customer = repos.customers.get(customer_id)
        if not customer:
            return jsonify({"status": "error", "message": "Customer not found"}), 404
        
        if request.method == "GET":
            page = max(int(request.args.get("page", 1)), 1)
            per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)
            return jsonify(repos.payments.get_by_customer(customer_id, page=page, per_page=per_page))
        
        # POST - record a payment
        data = request.json or {}
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"status": "error", "message": "Payment amount must be greater than 0"}), 400
        
        # Create payment record
        from datetime import date
        payment = repos.payments.create(
            customer_id=customer_id,
            amount=amount,
            payment_date=date.fromisoformat(data.get("payment_date", str(date.today()))),
            notes=data.get("notes", "")
        )
        
        # Update customer due
        new_due = max(float(customer.pending_due or 0) - amount, 0)
        customer = repos.customers.update(customer, pending_due=new_due, last_payment_date=payment.payment_date, last_payment_amount=amount)
        
        return jsonify({
            "status": "ok",
            "payment": payment.to_dict(),
            "customer": customer.to_dict(),
        }), 201

    @api.route("/customers/<int:customer_id>/due_reminder", methods=["GET"])
    def customer_due_reminder(customer_id):
        from datetime import date, timedelta
        customer = repos.customers.get(customer_id)
        if not customer:
            return jsonify({"status": "error", "message": "Customer not found"}), 404
        
        due_amount = float(customer.pending_due or 0)
        last_payment = customer.last_payment_date
        today = date.today()
        days_since_payment = (today - last_payment).days if last_payment else None
        
        # Reminder if due is unpaid and last payment was > 7 days ago
        reminder = None
        if due_amount > 0:
            if last_payment is None or days_since_payment > 7:
                reminder = {
                    "overdue": True,
                    "days_overdue": days_since_payment,
                    "message": f"Payment reminder: ₹{due_amount:.2f} pending for {days_since_payment} days" if days_since_payment else "Payment reminder: Due amount pending",
                }
        
        return jsonify({
            "customer_id": customer_id,
            "customer_name": customer.customer_name,
            "pending_due": due_amount,
            "last_payment_date": last_payment.isoformat() if last_payment else None,
            "last_payment_amount": float(customer.last_payment_amount or 0),
            "reminder": reminder,
        })

    @api.route("/products", methods=["GET", "POST"])
    def products():
        if request.method == "GET":
            return jsonify(_paginate_request(repos.products))
        product = repos.products.create(**(request.json or {}))
        return jsonify(product.to_dict()), 201

    @api.route("/products/<int:product_id>", methods=["GET", "PUT", "DELETE"])
    def product_detail(product_id):
        product = repos.products.get(product_id)
        if not product:
            return jsonify({"status": "error", "message": "Product not found"}), 404
        if request.method == "GET":
            return jsonify(product.to_dict())
        if request.method == "DELETE":
            repos.products.delete(product)
            return jsonify({"status": "deleted"})
        updated = repos.products.update(product, **(request.json or {}))
        return jsonify(updated.to_dict())

    @api.route("/invoices", methods=["GET", "POST"])
    def invoices():
        if request.method == "GET":
            return jsonify(_paginate_request(repos.invoices))
        result = invoice.save_invoice(request.json or {})
        status_code = 201 if result.get("status") != "error" else 500
        return jsonify(result), status_code

    @api.route("/invoices/<int:invoice_id>", methods=["GET", "PUT", "DELETE"])
    def invoice_detail(invoice_id):
        stored = repos.invoices.get_with_items(invoice_id)
        if not stored:
            return jsonify({"status": "error", "message": "Invoice not found"}), 404
        if request.method == "GET":
            return jsonify(stored.to_dict())
        if request.method == "DELETE":
            repos.invoices.delete(stored)
            return jsonify({"status": "deleted"})
        updated = repos.invoices.update(stored, **(request.json or {}))
        return jsonify(updated.to_dict())

    @api.route("/transactions", methods=["GET", "POST"])
    def transactions():
        if request.method == "GET":
            return jsonify(_paginate_request(repos.transactions))
        transaction = repos.transactions.create(**(request.json or {}))
        return jsonify(transaction.to_dict()), 201

    @api.route("/transactions/<int:transaction_id>", methods=["GET", "PUT", "DELETE"])
    def transaction_detail(transaction_id):
        transaction = repos.transactions.get(transaction_id)
        if not transaction:
            return jsonify({"status": "error", "message": "Transaction not found"}), 404
        if request.method == "GET":
            return jsonify(transaction.to_dict())
        if request.method == "DELETE":
            repos.transactions.delete(transaction)
            return jsonify({"status": "deleted"})
        updated = repos.transactions.update(transaction, **(request.json or {}))
        return jsonify(updated.to_dict())

    @api.route("/voice_history", methods=["GET"])
    def voice_history():
        return jsonify(_paginate_request(repos.voice_history))

    @api.route("/query_history", methods=["GET"])
    def query_history():
        return jsonify(_paginate_request(repos.query_history))

    @api.route("/recent_activity", methods=["GET"])
    def recent_activity():
        limit = int(request.args.get("limit", 10))
        hours = int(request.args.get("hours", 24))
        data = dashboard.get_recent_transactions(limit=limit, days=max(1, hours // 24 or 1))
        return jsonify({"transactions": data.get("transactions", []), "count": len(data.get("transactions", []))})

    @api.route("/cache_stats", methods=["GET"])
    def cache_stats():
        if not cache:
            return jsonify({"stats": {}, "message": "Cache service not available"}), 200
        return jsonify(cache.get_cache_stats())

    @api.route("/cache_clear", methods=["POST"])
    def cache_clear():
        if not cache:
            return jsonify({"status": "error", "message": "Cache service not available"}), 400
        cache.clear_expired()
        return jsonify({"status": "cleared"})

    @api.route("/send_invoice", methods=["POST"])
    def send_invoice():
        result = invoice.send_invoice(request.json or {})
        status_code = 200 if result.get("status") != "error" else 500
        return jsonify(result), status_code

    @api.route("/create_invoice", methods=["POST"])
    def create_invoice():
        result = invoice.save_invoice(request.json or {})
        status_code = 200 if result.get("status") != "error" else 500
        return jsonify(result), status_code

    @api.route("/retry_pending", methods=["POST"])
    def retry_pending():
        return jsonify(invoice.process_pending())

    @api.route("/pending_count", methods=["GET"])
    def pending_count():
        return jsonify({"pending_count": invoice.get_pending_count()})

    @api.route("/sales_summary", methods=["GET"])
    def sales_summary():
        period = request.args.get("period", "today")
        return jsonify(dashboard.get_sales_summary(period=period))

    @api.route("/accounts_summary", methods=["GET"])
    def accounts_summary():
        return jsonify(dashboard.get_accounts_summary())

    @api.route("/top_products", methods=["GET"])
    def top_products():
        limit = int(request.args.get("limit", 5))
        return jsonify(dashboard.get_top_products(limit=limit))

    @api.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "backend": "running",
            "tally": "connected" if tally.is_tally_available() else "offline",
            "tally_url": tally.host,
        })

    @api.route("/ocr/extract", methods=["POST"])
    def ocr_extract():
        payload = request.json or {}
        image_data = payload.get("image_base64")
        if not image_data:
            return jsonify({"status": "error", "message": "image_base64 is required"}), 400
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception:
            return jsonify({"status": "error", "message": "Invalid base64 image payload"}), 400
        return jsonify(ocr.extract_text(image_bytes) if ocr else {"status": "error", "message": "OCR service unavailable"})

    @api.route("/voice/transcribe", methods=["POST"])
    def voice_transcribe():
        """
        Transcribe audio to text using Faster-Whisper.
        Accepts audio file or base64-encoded audio.
        """
        stt = services.get("stt")
        if not stt:
            return jsonify({
                "status": "error",
                "message": "STT service not available. Ensure faster-whisper is installed."
            }), 503
        
        try:
            # Get audio data
            audio_data = None
            language = request.form.get("language", "en")
            
            # Check for file upload
            if "audio" in request.files:
                audio_file = request.files["audio"]
                audio_data = audio_file.read()
            else:
                # Check for base64 in JSON
                payload = request.json or {}
                audio_base64 = payload.get("audio_base64")
                if audio_base64:
                    import base64
                    audio_data = base64.b64decode(audio_base64)
            
            if not audio_data:
                return jsonify({
                    "status": "error",
                    "message": "No audio provided. Use 'audio' file upload or 'audio_base64' in JSON body."
                }), 400
            
            # Validate audio
            is_valid, validation_msg = AudioProcessor.validate_audio(audio_data)
            if not is_valid:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid audio: {validation_msg}"
                }), 400
            
            # Convert audio to WAV format
            wav_audio = AudioProcessor.convert_to_wav(audio_data, input_format="auto")
            
            # Transcribe
            result = stt.transcribe(wav_audio, language=language if language != "auto" else None)
            
            # Log transcription
            if result.get("success"):
                _log_voice(result.get("text", ""), "transcribed", result.get("confidence", 0))
            
            return jsonify(result)
        
        except Exception as e:
            import logging
            logging.error(f"Transcription error: {e}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "text": "",
                "success": False
            }), 500

    @api.route("/voice/process", methods=["POST"])
    def voice_process():
        payload = request.json or {}
        transcript = payload.get("transcript", "")
        if not transcript:
            return jsonify({"status": "error", "message": "transcript is required"}), 400
        session_id = payload.get("session_id") or _session_id()
        product_names = _known_names(repos.products, "item_name")
        customer_names = _known_names(repos.customers, "customer_name")
        result = voice.process(session_id, transcript, product_names=product_names, customer_names=customer_names) if voice else nlp.parse(transcript, product_names=product_names, customer_names=customer_names)
        result["session_id"] = session_id
        _log_voice(transcript, result.get("intent", "general"), result.get("confidence", 0))
        return jsonify(result)

    @api.route("/voice/models", methods=["GET"])
    def voice_models():
        """Get information about available STT models and current configuration."""
        stt = services.get("stt")
        if not stt:
            return jsonify({
                "status": "error",
                "message": "STT service not available"
            }), 503
        
        return jsonify({
            "status": "ok",
            "current_model": stt.get_model_info(),
            "available_models": ["tiny", "base", "small", "medium", "large-v3"],
            "devices": ["cpu", "cuda"],
            "default_language": "en"
        })

    flask_app.register_blueprint(api)