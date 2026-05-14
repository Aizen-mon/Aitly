"""
API routes for the AI Tally Assistant.
"""
import datetime
from flask import Blueprint, jsonify, request
from services.nlp_service import SimpleNLP
from services.dashboard_service import DashboardService
from services.response_formatter import ResponseFormatter
from services.invoice_service import InvoiceService

# Create blueprint
api = Blueprint("api", __name__, url_prefix="/api")


def init_routes(flask_app, services):
    """
    Initialize routes with service dependencies.

    Args:
        flask_app: Flask app instance
        services: dict containing {tally, nlp, dashboard, invoice, cache}
    """
    tally = services["tally"]
    nlp = services["nlp"]
    dashboard = services["dashboard"]
    invoice = services["invoice"]
    cache = services.get("cache")  # Optional cache service

    # ==================== NLP & Chat Routes ====================

    @api.route("/parse", methods=["POST"])
    def parse_intent():
        """Parse user text and return formatted response."""
        data = request.json or {}
        text = data.get("text", "")
        result = nlp.parse(text)
        intent = result.get("intent", "general")
        
        # Log to cache/analytics
        if cache:
            cache.add_query(text, intent=intent, source="user")
        
        formatted = ResponseFormatter.format_response(intent)
        return jsonify(formatted)

    @api.route("/suggested_prompts", methods=["GET"])
    def suggested_prompts():
        """Return suggested chat prompts for users."""
        prompts = ResponseFormatter.get_suggested_prompts()
        return jsonify({"prompts": prompts})

    # ==================== Dashboard Routes ====================

    @api.route("/dashboard_summary", methods=["GET"])
    def dashboard_summary():
        """Return comprehensive KPI summary for dashboard display."""
        today = datetime.date.today().isoformat()
        return jsonify({
            "date": today,
            "kpis": {
                "today_sales": {
                    "value": 15432.50,
                    "currency": "₹",
                    "label": "Today's Sales",
                    "count": 5,
                    "unit": "invoices"
                },
                "low_stock_count": {
                    "value": 4,
                    "label": "Low Stock Items",
                    "threshold": 10,
                    "color": "warning"
                },
                "pending_due": {
                    "value": 8750.00,
                    "currency": "₹",
                    "label": "Pending Dues",
                    "count": 3,
                    "unit": "customers"
                },
                "inventory_value": {
                    "value": 125400.00,
                    "currency": "₹",
                    "label": "Total Inventory"
                }
            },
            "recent_activity": [
                {"time": "10:45 AM", "action": "Invoice S001", "amount": 4234.50},
                {"time": "09:30 AM", "action": "Invoice S002", "amount": 3000.00},
                {"time": "08:15 AM", "action": "Stock Return", "amount": -500.00}
            ],
            "low_stock_items": [
                {"name": "Item A", "qty": 2, "reorder_qty": 50},
                {"name": "Item D", "qty": 1, "reorder_qty": 30}
            ],
            "top_products": [
                {"name": "Product X", "qty": 12, "value": 3600},
                {"name": "Product Y", "qty": 8, "value": 2400}
            ]
        })

    @api.route("/today_sales", methods=["GET"])
    def today_sales():
        """Get today's sales from dashboard service."""
        res = dashboard.get_today_sales()
        return jsonify(res)

    @api.route("/low_stock", methods=["GET"])
    def low_stock():
        """Get low stock items."""
        threshold = int(request.args.get("threshold", 10))
        res = dashboard.get_low_stock(threshold=threshold)
        return jsonify(res)

    @api.route("/pending_dues", methods=["GET"])
    def pending_dues():
        """Get pending dues."""
        res = dashboard.get_pending_dues()
        return jsonify(res)

    @api.route("/tally_snapshot", methods=["GET"])
    def tally_snapshot():
        """Return a combined snapshot for quotation and invoice prep."""
        threshold = int(request.args.get("threshold", 10))
        limit = int(request.args.get("limit", 10))
        days = int(request.args.get("days", 30))
        period = request.args.get("period", "today")

        inventory = tally.fetch_inventory()
        customers = tally.fetch_customers()
        recent_transactions = tally.fetch_recent_transactions(limit=limit, days=days)
        top_products = tally.fetch_top_products(limit=limit)
        sales_summary = tally.fetch_sales_summary(period=period)
        accounts_summary = tally.fetch_accounts_summary()
        low_stock = tally.fetch_low_stock(threshold=threshold)
        pending_dues = dashboard.get_pending_dues()
        quotation_context = tally.fetch_quotation_context(limit=limit, days=days, threshold=threshold)

        return jsonify({
            "inventory": inventory,
            "customers": customers,
            "recent_transactions": recent_transactions,
            "top_products": top_products,
            "sales_summary": sales_summary,
            "accounts_summary": accounts_summary,
            "low_stock": low_stock,
            "pending_dues": pending_dues,
            "quotation_context": quotation_context,
            "filters": {
                "threshold": threshold,
                "limit": limit,
                "days": days,
                "period": period,
            },
        })

    @api.route("/quotation_context", methods=["GET"])
    def quotation_context():
        """Return quotation-ready Tally data in one payload."""
        threshold = int(request.args.get("threshold", 10))
        limit = int(request.args.get("limit", 10))
        days = int(request.args.get("days", 30))
        return jsonify(tally.fetch_quotation_context(limit=limit, days=days, threshold=threshold))

    # ==================== Mock Routes (Demo Data) ====================

    @api.route("/mock_today_sales", methods=["GET"])
    def mock_today_sales():
        """Mock data for today's sales (when Tally not available)."""
        return jsonify({
            "count": 5,
            "total": 15432.50,
            "items": [
                {"voucher_no": "S001", "amount": 4234.50},
                {"voucher_no": "S002", "amount": 3000.00},
                {"voucher_no": "S003", "amount": 3200.00},
                {"voucher_no": "S004", "amount": 2000.00},
                {"voucher_no": "S005", "amount": 1998.00}
            ],
            "note": "mock data - Tally not connected"
        })

    @api.route("/mock_low_stock", methods=["GET"])
    def mock_low_stock():
        """Mock data for low stock items."""
        threshold = int(request.args.get('threshold', 10))
        items = [
            {"name": "Item A", "qty": 2},
            {"name": "Item B", "qty": 8},
            {"name": "Item C", "qty": 15},
            {"name": "Item D", "qty": 1}
        ]
        low = [it for it in items if it['qty'] <= threshold]
        return jsonify({"items": low, "threshold": threshold, "note": "mock low stock"})

    # ==================== Extended Tally Integration Routes ====================

    @api.route("/inventory", methods=["GET"])
    def inventory():
        """Get complete inventory with stock levels."""
        data = tally.fetch_inventory()
        if cache:
            cache.set(f"inventory", data, ttl_seconds=600)  # Cache for 10 min
        return jsonify(data)

    @api.route("/customers", methods=["GET"])
    def customers():
        """Get customer list with pending amounts."""
        data = tally.fetch_customers()
        if cache:
            cache.set("customers", data, ttl_seconds=900)  # Cache for 15 min
        return jsonify(data)

    @api.route("/recent_transactions", methods=["GET"])
    def recent_transactions():
        """Get recent sales and purchase transactions."""
        limit = int(request.args.get("limit", 20))
        days = int(request.args.get("days", 30))
        data = tally.fetch_recent_transactions(limit=limit, days=days)
        if cache:
            cache.set(f"recent_txn_{limit}_{days}", data, ttl_seconds=300)
        return jsonify(data)

    @api.route("/top_products", methods=["GET"])
    def top_products():
        """Get best-selling products."""
        limit = int(request.args.get("limit", 5))
        data = tally.fetch_top_products(limit=limit)
        if cache:
            cache.set(f"top_products_{limit}", data, ttl_seconds=1800)  # Cache for 30 min
        return jsonify(data)

    @api.route("/sales_summary", methods=["GET"])
    def sales_summary():
        """Get sales summary for period (today/week/month)."""
        period = request.args.get("period", "today")
        data = tally.fetch_sales_summary(period=period)
        if cache:
            cache.set(f"sales_{period}", data, ttl_seconds=300)
        return jsonify(data)

    @api.route("/accounts_summary", methods=["GET"])
    def accounts_summary():
        """Get general ledger account summaries."""
        data = tally.fetch_accounts_summary()
        if cache:
            cache.set("accounts", data, ttl_seconds=900)
        return jsonify(data)

    @api.route("/health", methods=["GET"])
    def health():
        """Check backend and Tally connection status."""
        tally_available = tally.is_tally_available()
        return jsonify({
            "status": "ok",
            "backend": "running",
            "tally": "connected" if tally_available else "offline",
            "tally_url": tally.host
        })

    # ==================== Invoice Routes ====================

    @api.route("/create_invoice", methods=["POST"])
    def create_invoice():
        """Create and save invoice locally."""
        data = request.json or {}
        result = invoice.save_invoice(data)
        status_code = 200 if result.get("status") != "error" else 500
        return jsonify(result), status_code

    @api.route("/send_invoice", methods=["POST"])
    def send_invoice():
        """Send invoice to Tally."""
        data = request.json or {}
        result = invoice.send_invoice(data)
        status_code = 200 if result.get("status") != "error" else 500
        return jsonify(result), status_code

    @api.route("/retry_pending", methods=["POST"])
    def retry_pending():
        """Retry sending all pending invoices."""
        summary = invoice.process_pending()
        return jsonify(summary)

    @api.route("/pending_count", methods=["GET"])
    def pending_count():
        """Get count of pending invoices."""
        count = invoice.get_pending_count()
        return jsonify({"pending_count": count})

    # ==================== Cache & Analytics Routes ====================

    @api.route("/query_history", methods=["GET"])
    def query_history():
        """Get recent query history for analytics."""
        if not cache:
            return jsonify({"queries": [], "message": "Cache service not available"}), 200
        limit = int(request.args.get("limit", 20))
        queries = cache.get_query_history(limit=limit)
        return jsonify({"queries": queries, "count": len(queries)})

    @api.route("/recent_activity", methods=["GET"])
    def recent_activity():
        """Get recent transactions from cache."""
        if not cache:
            return jsonify({"transactions": [], "message": "Cache service not available"}), 200
        limit = int(request.args.get("limit", 10))
        hours = int(request.args.get("hours", 24))
        transactions = cache.get_recent_transactions(limit=limit, hours=hours)
        return jsonify({"transactions": transactions, "count": len(transactions)})

    @api.route("/cache_stats", methods=["GET"])
    def cache_stats():
        """Get cache statistics."""
        if not cache:
            return jsonify({"stats": {}, "message": "Cache service not available"}), 200
        stats = cache.get_cache_stats()
        return jsonify(stats)

    @api.route("/cache_clear", methods=["POST"])
    def cache_clear():
        """Clear expired cache entries."""
        if not cache:
            return jsonify({"status": "error", "message": "Cache service not available"}), 400
        cache.clear_expired()
        return jsonify({"status": "cleared"})

    # Register blueprint
    flask_app.register_blueprint(api)
