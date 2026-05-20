"""SQLAlchemy ORM models for the AI Tally assistant."""

from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def _base_dict(self):
        return {"created_at": self.created_at.isoformat() if self.created_at else None}


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    role = Column(String(50), nullable=False, default="staff")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "role": self.role, **self._base_dict()}


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    customer_name = Column(String(200), nullable=False, index=True)
    phone = Column(String(30))
    address = Column(Text)
    gst_number = Column(String(30), index=True)
    pending_due = Column(Float, default=0.0, nullable=False)
    last_payment_date = Column(Date, nullable=True)
    last_payment_amount = Column(Float, default=0.0, nullable=False)

    invoices = relationship("Invoice", back_populates="customer")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "phone": self.phone,
            "address": self.address,
            "gst_number": self.gst_number,
            "pending_due": float(self.pending_due or 0),
            "last_payment_date": self.last_payment_date.isoformat() if self.last_payment_date else None,
            "last_payment_amount": float(self.last_payment_amount or 0),
            **self._base_dict(),
        }


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    item_name = Column(String(200), nullable=False, index=True)
    quantity = Column(Float, default=0.0, nullable=False)
    rate = Column(Float, default=0.0, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    tax_percent = Column(Float, default=18.0, nullable=False)
    supplier = Column(String(200))
    reorder_level = Column(Float, default=0.0, nullable=False)

    invoice_items = relationship("InvoiceItem", back_populates="product")

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "quantity": float(self.quantity or 0),
            "rate": float(self.rate or 0),
            "discount": float(self.discount or 0),
            "tax_percent": float(self.tax_percent or 0),
            "supplier": self.supplier,
            "reorder_level": float(self.reorder_level or 0),
            **self._base_dict(),
        }


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(120), nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    total_amount = Column(Float, default=0.0, nullable=False)
    invoice_date = Column(Date, nullable=False, default=date.today)
    sync_status = Column(String(30), default="draft", nullable=False)
    tally_reference = Column(String(120))

    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.customer_name if self.customer else None,
            "total_amount": float(self.total_amount or 0),
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "sync_status": self.sync_status,
            "tally_reference": self.tally_reference,
            "items": [item.to_dict() for item in self.items],
            **self._base_dict(),
        }


class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    qty = Column(Float, nullable=False, default=1)
    rate = Column(Float, nullable=False, default=0.0)
    discount = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "product_id": self.product_id,
            "product_name": self.product.item_name if self.product else None,
            "qty": float(self.qty or 0),
            "rate": float(self.rate or 0),
            "discount": float(self.discount or 0),
            "total": float(self.total or 0),
            **self._base_dict(),
        }


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_type = Column(String(80), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    reference = Column(String(120), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount or 0),
            "reference": self.reference,
            **self._base_dict(),
        }


class VoiceHistory(Base, TimestampMixin):
    __tablename__ = "voice_history"

    id = Column(Integer, primary_key=True)
    transcript = Column(Text, nullable=False)
    detected_intent = Column(String(120), index=True)
    confidence = Column(Float, default=0.0, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "transcript": self.transcript,
            "detected_intent": self.detected_intent,
            "confidence": float(self.confidence or 0),
            **self._base_dict(),
        }


class QueryHistory(Base, TimestampMixin):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True)
    query = Column(Text, nullable=False)
    response = Column(Text)
    intent = Column(String(120), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "query": self.query,
            "response": self.response,
            "intent": self.intent,
            **self._base_dict(),
        }


class ConversationState(Base):
    __tablename__ = "conversation_state"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(120), nullable=False, unique=True, index=True)
    current_flow = Column(String(120))
    pending_field = Column(String(120))
    context_json = Column(Text, default="{}", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        try:
            context = json.loads(self.context_json or "{}")
        except Exception:
            context = {}
        return {
            "id": self.id,
            "session_id": self.session_id,
            "current_flow": self.current_flow,
            "pending_field": self.pending_field,
            "context": context,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(120), nullable=False, unique=True, index=True)
    current_flow = Column(String(120))
    current_step = Column(String(120))
    previous_entities = Column(Text, default="{}", nullable=False)
    active_customer = Column(String(200))
    active_products = Column(Text, default="[]", nullable=False)
    last_intent = Column(String(120))
    context_json = Column(Text, default="{}", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        try:
            previous_entities = json.loads(self.previous_entities or "{}")
        except Exception:
            previous_entities = {}
        try:
            active_products = json.loads(self.active_products or "[]")
        except Exception:
            active_products = []
        try:
            context = json.loads(self.context_json or "{}")
        except Exception:
            context = {}
        return {
            "id": self.id,
            "session_id": self.session_id,
            "current_flow": self.current_flow,
            "current_step": self.current_step,
            "previous_entities": previous_entities,
            "active_customer": self.active_customer,
            "active_products": active_products,
            "last_intent": self.last_intent,
            "context": context,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SyncQueueItem(Base, TimestampMixin):
    __tablename__ = "sync_queue_items"

    id = Column(Integer, primary_key=True)
    action_type = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    payload_json = Column(Text, default="{}", nullable=False)
    status = Column(String(40), default="pending", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    last_error = Column(Text)
    reference = Column(String(120))
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        try:
            payload = json.loads(self.payload_json or "{}")
        except Exception:
            payload = {}
        return {
            "id": self.id,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "payload": payload,
            "status": self.status,
            "retry_count": int(self.retry_count or 0),
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "last_error": self.last_error,
            "reference": self.reference,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            **self._base_dict(),
        }


class SyncLog(Base, TimestampMixin):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    sync_type = Column(String(120), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    message = Column(Text)
    payload_json = Column(Text, default="{}", nullable=False)

    def to_dict(self):
        try:
            payload = json.loads(self.payload_json or "{}")
        except Exception:
            payload = {}
        return {
            "id": self.id,
            "sync_type": self.sync_type,
            "status": self.status,
            "message": self.message,
            "payload": payload,
            **self._base_dict(),
        }


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    payment_date = Column(Date, nullable=False, default=date.today)
    notes = Column(Text)

    customer = relationship("Customer", back_populates="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "amount": float(self.amount or 0),
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "notes": self.notes,
            **self._base_dict(),
        }
