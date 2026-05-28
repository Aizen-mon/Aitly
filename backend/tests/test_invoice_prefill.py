"""Tests for the invoice prefill endpoint."""

from __future__ import annotations

from app import create_app


def test_invoice_prefill_basic():
    app = create_app()
    client = app.test_client()

    resp = client.post('/api/invoice/prefill', json={'text': 'create invoice for ABC Traders for 2 Coke'})
    assert resp.status_code == 200
    data = resp.get_json() or {}
    # Endpoint should respond with a draft_invoice key (may be empty) or assistant payload
    assert isinstance(data, dict)
    assert 'draft_invoice' in data or 'assistant' in data
