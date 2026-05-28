import requests
from xml.etree import ElementTree as ET
from config import TALLY_HOST


class TallyService:
    """Handles sending XML requests to TallyPrime and returning parsed results.

    Usage:
        ts = TallyService()
        sales = ts.fetch_today_sales()
    """

    def __init__(self, host: str = None):
        self.host = host or TALLY_HOST

    def send_xml(self, xml: str) -> str:
        """POSTs XML to Tally and returns raw response text.

        If Tally isn't available, it raises requests exceptions.
        """
        headers = {"Content-Type": "application/xml"}
        resp = requests.post(self.host, data=xml.encode("utf-8"), headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text

    def fetch_today_sales(self) -> dict:
        """Builds a basic XML request to retrieve today's sales vouchers.

        Note: Tally XML requests vary by company and configuration. This is
        a starting example; adapt filters as needed.
        """
        xml = """
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Voucher</TYPE>
    <ID>All Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVFROMDATE>$$CurrentDate</SVFROMDATE>
        <SVTODATE>$$CurrentDate</SVTODATE>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>
"""
        try:
            raw = self.send_xml(xml)
        except Exception as e:
            return {"error": str(e), "data": []}

        # Minimal parsing: count voucher nodes and sum amounts when possible
        try:
            root = ET.fromstring(raw)
            vouchers = root.findall('.//VOUCHER')
            total = 0.0
            for v in vouchers:
                amt = v.find('.//AMOUNT')
                if amt is not None:
                    try:
                        total += float(amt.text)
                    except:
                        pass
            return {"count": len(vouchers), "total": total, "raw": raw}
        except ET.ParseError:
            return {"error": "invalid_xml", "raw": raw}

    def fetch_low_stock(self, threshold: int = 10) -> dict:
        """Example: request stock items and filter by quantity.

        This request may need adapting to the company's masters report.
        """
        xml = """
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Stock Summary</TYPE>
    <ID>All Items</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>
"""
        try:
            raw = self.send_xml(xml)
        except Exception as e:
            return {"error": str(e), "items": []}

        items = []
        try:
            root = ET.fromstring(raw)
            for it in root.findall('.//STOCKITEM'):
                name = it.find('NAME')
                closing = it.find('.//CLOSINGBALANCE')
                qty = 0.0
                if closing is not None:
                    try:
                        qty = float(closing.text)
                    except:
                        pass
                if qty <= threshold:
                    items.append({"name": name.text if name is not None else "", "qty": qty})
            return {"items": items, "raw": raw}
        except Exception:
            return {"error": "parse_error", "raw": raw}

    def build_invoice_xml(self, invoice: dict) -> str:
        """Constructs a simple Tally Voucher XML for an invoice dict.

        This is a basic template — adapt ledger/account names and masters as per company.
        """
        # Minimal fields: invoice_no, date (YYYYMMDD), party_name, items: [{name, qty, rate}]
        inv_no = invoice.get("invoice_no", "")
        date = invoice.get("date", "")
        party = invoice.get("party_name", "")
        items = invoice.get("items", [])

        lines = []
        for it in items:
            name = it.get("name", "")
            qty = it.get("qty", 1)
            rate = it.get("rate", 0)
            amt = float(qty) * float(rate)
            lines.append(f"<ALLINVENTORYENTRIES.LIST>\n<STOCKITEMNAME>{name}</STOCKITEMNAME>\n<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n<RATE>{rate}</RATE>\n<ACTUALQTY>{qty}</ACTUALQTY>\n<AMOUNT>{amt}</AMOUNT>\n</ALLINVENTORYENTRIES.LIST>")

        xml = f'''<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Sales" ACTION="Create">
            <DATE>{date}</DATE>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
            <PARTYLEDGERNAME>{party}</PARTYLEDGERNAME>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Sales</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            </ALLLEDGERENTRIES.LIST>
            {''.join(lines)}
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>'''
        return xml

    def post_invoice(self, invoice: dict) -> dict:
        """Build XML and POST to Tally; return dict with success or error."""
        xml = self.build_invoice_xml(invoice)
        try:
            resp = self.send_xml(xml)
            return {"status": "sent", "response": resp}
        except Exception as e:
            return {"status": "error", "error": str(e), "xml": xml}

    def post_payment(self, payment: dict) -> dict:
        return {
            "status": "not_implemented",
            "error": "Payment posting is not implemented yet.",
            "payload": payment,
        }

    def post_inventory_change(self, inventory_change: dict) -> dict:
        return {
            "status": "not_implemented",
            "error": "Inventory change posting is not implemented yet.",
            "payload": inventory_change,
        }

    # ==================== Extended Tally Integration ====================

    def fetch_inventory(self) -> dict:
        """Fetch complete inventory with stock levels and valuations."""
        # TODO: Implement real Tally XML request for stock items
        # For now, return mock data
        return {
            "status": "mock",
            "total_items": 45,
            "total_value": 125400.00,
            "items": [
                {"name": "Product X", "qty": 45, "value": 9000, "reorder": 20},
                {"name": "Product Y", "qty": 32, "value": 4800, "reorder": 15},
                {"name": "Item A", "qty": 2, "value": 100, "reorder": 50},
                {"name": "Item B", "qty": 8, "value": 240, "reorder": 30},
                {"name": "Item D", "qty": 1, "value": 50, "reorder": 30},
            ]
        }

    def fetch_customers(self) -> dict:
        """Fetch customer list with pending amounts and contact info."""
        # TODO: Implement real Tally XML request for parties/customers
        return {
            "status": "mock",
            "total_customers": 12,
            "total_receivable": 28500.00,
            "customers": [
                {"name": "ABC Corp", "pending": 5000, "credit_limit": 10000, "last_invoice": "INV-001"},
                {"name": "XYZ Ltd", "pending": 3750, "credit_limit": 8000, "last_invoice": "INV-002"},
                {"name": "Customer C", "pending": 0, "credit_limit": 5000, "last_invoice": "INV-003"},
            ]
        }

    def fetch_recent_transactions(self, limit: int = 20, days: int = 30) -> dict:
        """Fetch recent sales and purchase transactions."""
        # TODO: Implement real Tally XML request for vouchers with date filter
        return {
            "status": "mock",
            "limit": limit,
            "days": days,
            "transactions": [
                {"type": "Sales", "date": "2026-05-15", "invoice": "S001", "amount": 4234.50, "party": "ABC Corp"},
                {"type": "Sales", "date": "2026-05-15", "invoice": "S002", "amount": 3000.00, "party": "XYZ Ltd"},
                {"type": "Purchase", "date": "2026-05-14", "invoice": "P001", "amount": 2500.00, "party": "Supplier X"},
            ]
        }

    def fetch_top_products(self, limit: int = 5) -> dict:
        """Fetch best-selling products by quantity and value."""
        # TODO: Implement real Tally XML request with sales analysis
        return {
            "status": "mock",
            "limit": limit,
            "period": "this_month",
            "products": [
                {"name": "Product X", "qty_sold": 12, "revenue": 3600},
                {"name": "Product Y", "qty_sold": 8, "revenue": 2400},
                {"name": "Product Z", "qty_sold": 5, "revenue": 1500},
            ]
        }

    def fetch_sales_summary(self, period: str = "today") -> dict:
        """Fetch sales summary for specified period (today, week, month)."""
        # TODO: Implement real Tally XML request with date-based filtering
        periods = {
            "today": {"count": 5, "total": 15432.50},
            "week": {"count": 28, "total": 85000.00},
            "month": {"count": 95, "total": 450000.00},
        }
        return {
            "status": "mock",
            "period": period,
            **periods.get(period, periods["today"])
        }

    def fetch_accounts_summary(self) -> dict:
        """Fetch general ledger account summaries for financial overview."""
        # TODO: Implement real Tally XML request for ledger balances
        return {
            "status": "mock",
            "accounts": {
                "sales": 450000.00,
                "purchases": 280000.00,
                "receivable": 28500.00,
                "payable": 15000.00,
                "cash": 95000.00,
            }
        }

    def fetch_quotation_context(self, limit: int = 10, days: int = 30, threshold: int = 10) -> dict:
        """Return quotation-ready business data: stock, pricing, discounts, and prior sales."""
        inventory = self.fetch_inventory()
        recent_transactions = self.fetch_recent_transactions(limit=limit, days=days)
        top_products = self.fetch_top_products(limit=limit)
        customers = self.fetch_customers()

        catalog = []
        for item in inventory.get("items", []):
            name = item.get("name", "")
            qty = item.get("qty", 0)
            value = float(item.get("value", 0) or 0)
            rate = round(value / qty, 2) if qty else 0.0
            discount_percent = 5 if qty and qty <= threshold else 0
            dp = round(rate * (1 - (discount_percent / 100)), 2) if rate else 0.0
            catalog.append({
                "name": name,
                "stock_qty": qty,
                "unit": "Nos",
                "rate": rate,
                "discount_percent": discount_percent,
                "discount_amount": round(rate - dp, 2) if rate else 0.0,
                "dp": dp,
                "mrp": round(rate * 1.15, 2) if rate else 0.0,
                "tax_percent": 18,
                "warehouse": "Main Godown",
                "last_sold": "2026-05-15",
                "available": qty > 0,
                "hsn": "0000",
            })

        previous_sales = []
        for txn in recent_transactions.get("transactions", []):
            if txn.get("type") != "Sales":
                continue
            previous_sales.append({
                "invoice": txn.get("invoice", ""),
                "party": txn.get("party", ""),
                "date": txn.get("date", ""),
                "amount": txn.get("amount", 0),
            })

        return {
            "status": "mock",
            "company": "Demo Trading Co",
            "currency": "INR",
            "catalog": catalog,
            "previous_sales": previous_sales,
            "top_products": top_products.get("products", []),
            "customers": customers.get("customers", []),
            "inventory_summary": {
                "total_items": inventory.get("total_items", 0),
                "total_value": inventory.get("total_value", 0),
                "low_stock_count": len(self.fetch_low_stock(threshold=threshold).get("items", [])),
            },
            "pricing_notes": [
                "Suggested discount is derived from current stock pressure.",
                "DP is shown as a discounted selling price for fast quotation.",
                "MRP is estimated from the base rate when Tally data is unavailable.",
            ],
            "logistics": {
                "warehouses": ["Main Godown", "Secondary Godown"],
                "delivery_modes": ["Pickup", "Local Delivery", "Courier"],
                "lead_time_days": 2,
            },
            "filters": {
                "limit": limit,
                "days": days,
                "threshold": threshold,
            },
        }

    def is_tally_available(self) -> bool:
        """Check if Tally is running and reachable."""
        try:
            resp = requests.get(self.host, timeout=2)
            return resp.status_code < 500
        except Exception:
            return False
