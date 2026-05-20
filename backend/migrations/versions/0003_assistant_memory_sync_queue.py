"""Add assistant memory fields and sync queue table.

Revision ID: 0003_assistant_memory_sync_queue
Revises: 0002_voice_workflow_sessions
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_assistant_memory_sync_queue"
down_revision = "0002_voice_workflow_sessions"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("conversation_sessions") as batch:
        batch.add_column(sa.Column("previous_entities", sa.Text(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("active_customer", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("active_products", sa.Text(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("last_intent", sa.String(length=120), nullable=True))

    op.create_table(
        "sync_queue_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("sync_queue_items")
    with op.batch_alter_table("conversation_sessions") as batch:
        batch.drop_column("last_intent")
        batch.drop_column("active_products")
        batch.drop_column("active_customer")
        batch.drop_column("previous_entities")
