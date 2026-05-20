#!/usr/bin/env python3
"""Simple smoke test script for backend API routes.

Run from the repository root with the project's Python environment.
"""
import base64
import json
import os
import sys

# Ensure repo root is on sys.path so tests can import application package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


def run():
    app = create_app()
    client = app.test_client()

    # Create a product
    prod_payload = {
        "item_name": "Smoke Widget",
        "quantity": 7,
        "rate": 99.5,
        "discount": 0,
        "tax_percent": 18,
        "supplier": "Smoke Supplier",
        "reorder_level": 5,
    }
    r = client.post('/api/products', json=prod_payload)
    print('POST /api/products ->', r.status_code, r.get_json())

    # List products
    r = client.get('/api/products?per_page=10')
    print('GET /api/products ->', r.status_code, r.get_json())

    # Create a customer
    cust_payload = {
        "customer_name": "Test Customer",
        "phone": "9999999999",
        "address": "123 Test Lane",
        "gst_number": "",
        "pending_due": 0,
    }
    r = client.post('/api/customers', json=cust_payload)
    print('POST /api/customers ->', r.status_code, r.get_json())

    # List customers
    r = client.get('/api/customers?per_page=10')
    print('GET /api/customers ->', r.status_code, r.get_json())

    # Call OCR with a small base64 payload (may return dependency error)
    sample = base64.b64encode(b'not-a-real-image').decode('ascii')
    r = client.post('/api/ocr/extract', json={"image_base64": sample})
    print('POST /api/ocr/extract ->', r.status_code, r.get_json())


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        print('Error during smoke test:', exc)
        sys.exit(2)
