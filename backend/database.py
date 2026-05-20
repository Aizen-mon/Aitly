"""Database engine, session factory, and helpers."""

from contextlib import contextmanager
from typing import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL


Base = declarative_base()


def _build_engine():
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


engine = _build_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@contextmanager
def session_scope() -> Generator:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session():
    return SessionLocal()


def init_db():
    """Import models and create all tables."""
    from models import (  # noqa: F401
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

    Base.metadata.create_all(bind=engine)
    # Ensure schema additions (for dev environments where alembic was not run)
    ensure_schema()


def _has_column(table_name: str, column_name: str) -> bool:
    with engine.connect() as conn:
        res = conn.execute(f"PRAGMA table_info('{table_name}')")
        cols = [row[1] for row in res.fetchall()]
        return column_name in cols


def ensure_schema():
    """Add missing columns used by newer models when running without alembic upgrades.

    This is a safe, idempotent helper for development environments.
    """
    with engine.begin() as conn:
        # conversation_sessions columns
        try:
            if not _has_column("conversation_sessions", "previous_entities"):
                conn.execute("ALTER TABLE conversation_sessions ADD COLUMN previous_entities TEXT NOT NULL DEFAULT '{}'")
            if not _has_column("conversation_sessions", "active_customer"):
                conn.execute("ALTER TABLE conversation_sessions ADD COLUMN active_customer VARCHAR(200)")
            if not _has_column("conversation_sessions", "active_products"):
                conn.execute("ALTER TABLE conversation_sessions ADD COLUMN active_products TEXT NOT NULL DEFAULT '[]'")
            if not _has_column("conversation_sessions", "last_intent"):
                conn.execute("ALTER TABLE conversation_sessions ADD COLUMN last_intent VARCHAR(120)")
        except Exception:
            # ignore if table doesn't exist yet or operation unsupported
            pass

        # sync_queue_items columns
        try:
            if not _has_column("sync_queue_items", "updated_at"):
                conn.execute("ALTER TABLE sync_queue_items ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
        except Exception:
            pass
