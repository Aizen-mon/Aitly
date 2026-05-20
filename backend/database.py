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
