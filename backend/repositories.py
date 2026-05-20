"""Reusable repository helpers for database-backed CRUD and pagination."""

from __future__ import annotations

from math import ceil
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session, joinedload

from database import SessionLocal
from models import (
    ConversationState,
    ConversationSession,
    Customer,
    Invoice,
    InvoiceItem,
    Payment,
    Product,
    QueryHistory,
    SyncLog,
    SyncQueueItem,
    Transaction,
    User,
    VoiceHistory,
)


ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, session_factory: Callable[[], Session], model: Type[ModelT]):
        self.session_factory = session_factory
        self.model = model

    def _session(self) -> Session:
        return self.session_factory()

    def get(self, object_id: int) -> Optional[ModelT]:
        session = self._session()
        try:
            return session.get(self.model, object_id)
        finally:
            session.close()

    def create(self, **data) -> ModelT:
        session = self._session()
        try:
            instance = self.model(**data)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
        finally:
            session.close()

    def update(self, instance: ModelT, **data) -> ModelT:
        session = self._session()
        try:
            managed = session.merge(instance)
            for key, value in data.items():
                setattr(managed, key, value)
            session.commit()
            session.refresh(managed)
            return managed
        finally:
            session.close()

    def delete(self, instance: ModelT) -> None:
        session = self._session()
        try:
            managed = session.merge(instance)
            session.delete(managed)
            session.commit()
        finally:
            session.close()

    def list(self, page: int = 1, per_page: int = 20, order_desc: bool = True) -> Dict[str, Any]:
        session = self._session()
        try:
            query = session.query(self.model)
            total = query.count()
            order_col = getattr(self.model, "created_at", None)
            if order_col is not None:
                query = query.order_by(desc(order_col) if order_desc else order_col)
            items = query.offset((page - 1) * per_page).limit(per_page).all()
            return {
                "items": [item.to_dict() for item in items],
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": ceil(total / per_page) if per_page else 1,
            }
        finally:
            session.close()


class UserRepository(BaseRepository[User]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, User)


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, Customer)

    def search(self, term: str, limit: int = 10) -> List[Customer]:
        session = self._session()
        try:
            term = f"%{term.lower()}%"
            return (
                session.query(Customer)
                .filter(func.lower(Customer.customer_name).like(term))
                .order_by(desc(Customer.created_at))
                .limit(limit)
                .all()
            )
        finally:
            session.close()


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, Product)

    def search(self, term: str, limit: int = 10) -> List[Product]:
        session = self._session()
        try:
            term = f"%{term.lower()}%"
            return (
                session.query(Product)
                .filter(func.lower(Product.item_name).like(term))
                .order_by(desc(Product.created_at))
                .limit(limit)
                .all()
            )
        finally:
            session.close()


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, Invoice)

    def get_with_items(self, invoice_id: int) -> Optional[Invoice]:
        session = self._session()
        try:
            return (
                session.query(Invoice)
                .options(joinedload(Invoice.items).joinedload(InvoiceItem.product), joinedload(Invoice.customer))
                .filter(Invoice.id == invoice_id)
                .one_or_none()
            )
        finally:
            session.close()


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, Transaction)


class VoiceHistoryRepository(BaseRepository[VoiceHistory]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, VoiceHistory)


class QueryHistoryRepository(BaseRepository[QueryHistory]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, QueryHistory)


class ConversationStateRepository(BaseRepository[ConversationState]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, ConversationState)

    def get_by_session(self, session_id: str) -> Optional[ConversationState]:
        session = self._session()
        try:
            return (
                session.query(ConversationState)
                .filter(ConversationState.session_id == session_id)
                .one_or_none()
            )
        finally:
            session.close()


class ConversationSessionRepository(BaseRepository[ConversationSession]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, ConversationSession)

    def get_by_session(self, session_id: str) -> Optional[ConversationSession]:
        session = self._session()
        try:
            return (
                session.query(ConversationSession)
                .filter(ConversationSession.session_id == session_id)
                .one_or_none()
            )
        finally:
            session.close()


class SyncLogRepository(BaseRepository[SyncLog]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, SyncLog)


class SyncQueueRepository(BaseRepository[SyncQueueItem]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, SyncQueueItem)

    def pending(self, limit: int = 20):
        session = self._session()
        try:
            return (
                session.query(SyncQueueItem)
                .filter(SyncQueueItem.status.in_(["pending", "retrying"]))
                .order_by(SyncQueueItem.updated_at.asc(), SyncQueueItem.created_at.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def due(self, limit: int = 20):
        from datetime import datetime

        session = self._session()
        try:
            now = datetime.utcnow()
            query = session.query(SyncQueueItem).filter(
                SyncQueueItem.status.in_(["pending", "retrying"]),
                (SyncQueueItem.next_retry_at.is_(None)) | (SyncQueueItem.next_retry_at <= now),
            )
            return query.order_by(SyncQueueItem.updated_at.asc(), SyncQueueItem.created_at.asc()).limit(limit).all()
        finally:
            session.close()


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session_factory=SessionLocal):
        super().__init__(session_factory, Payment)

    def get_by_customer(self, customer_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get payment history for a specific customer."""
        session = self._session()
        try:
            query = session.query(Payment).filter(Payment.customer_id == customer_id)
            total = query.count()
            items = query.order_by(desc(Payment.payment_date)).offset((page - 1) * per_page).limit(per_page).all()
            return {
                "items": [item.to_dict() for item in items],
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": ceil(total / per_page) if per_page else 1,
            }
        finally:
            session.close()


class RepositoryBundle:
    def __init__(self, session_factory=SessionLocal):
        self.users = UserRepository(session_factory)
        self.customers = CustomerRepository(session_factory)
        self.products = ProductRepository(session_factory)
        self.invoices = InvoiceRepository(session_factory)
        self.transactions = TransactionRepository(session_factory)
        self.voice_history = VoiceHistoryRepository(session_factory)
        self.query_history = QueryHistoryRepository(session_factory)
        self.payments = PaymentRepository(session_factory)
        self.conversation_sessions = ConversationSessionRepository(session_factory)
        self.conversations = self.conversation_sessions
        self.conversation_states = ConversationStateRepository(session_factory)
        self.sync_logs = SyncLogRepository(session_factory)
        self.sync_queue = SyncQueueRepository(session_factory)
