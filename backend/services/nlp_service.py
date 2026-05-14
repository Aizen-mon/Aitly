from typing import Dict
import re
from datetime import datetime, timedelta


class SimpleNLP:
    """Rule-based intent recognizer for common commands.

    Recognizes intents: today_sales, low_stock, pending_dues, create_invoice
    """

    def __init__(self):
        # simple keyword -> intent mapping
        self.rules = {
            "today sales": "today_sales",
            "sales today": "today_sales",
            "low stock": "low_stock",
            "stock low": "low_stock",
            "pending dues": "pending_dues",
            "pending payments": "pending_dues",
            "create invoice": "create_invoice",
            "new invoice": "create_invoice",
        }

    def parse(self, text: str) -> Dict:
        t = text.strip().lower()
        # direct rule matches
        for key, intent in self.rules.items():
            if key in t:
                parsed = {"intent": intent, "confidence": 0.9, "matched": key}
                # extract simple parameters
                parsed.update(self._extract_params(t))
                return parsed

        # fallback heuristics
        if "sales" in t:
            parsed = {"intent": "today_sales", "confidence": 0.5}
            parsed.update(self._extract_params(t))
            return parsed
        if "stock" in t:
            parsed = {"intent": "low_stock", "confidence": 0.5}
            parsed.update(self._extract_params(t))
            return parsed
        if "due" in t or "pending" in t or "payment" in t:
            parsed = {"intent": "pending_dues", "confidence": 0.6}
            parsed.update(self._extract_params(t))
            return parsed
        return {"intent": "unknown", "confidence": 0.0}

    def _extract_params(self, text: str) -> Dict:
        """Extract simple params: 'threshold' numbers and relative dates like 'yesterday' or explicit YYYY-MM-DD."""
        params = {}
        # threshold: look for 'less than 5', '<5', 'below 10', 'under 3', or '5'
        m = re.search(r'(?:less than|below|under)\s*(\d+)', text)
        if not m:
            m = re.search(r'<\s*(\d+)', text)
        if m:
            try:
                params['threshold'] = int(m.group(1))
            except:
                pass

        # explicit number stand-alone for stock threshold: 'low stock 5'
        if 'threshold' not in params:
            m2 = re.search(r'low stock\s*(\d+)', text)
            if m2:
                params['threshold'] = int(m2.group(1))

        # date parsing: 'yesterday', 'today', or YYYY-MM-DD / DD-MM-YYYY
        if 'yesterday' in text:
            params['date'] = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')
        elif 'today' in text:
            params['date'] = datetime.utcnow().strftime('%Y%m%d')
        else:
            m3 = re.search(r'([0-9]{4})[-/]?([0-9]{2})[-/]?([0-9]{2})', text)
            if m3:
                params['date'] = f"{m3.group(1)}{m3.group(2)}{m3.group(3)}"

        return params
