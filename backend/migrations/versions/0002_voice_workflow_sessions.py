"""Add conversation sessions and payment tracking columns.

Revision ID: 0002_voice_workflow_sessions
Revises: 0001_initial_schema
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_voice_workflow_sessions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customers") as batch:
        batch.add_column(sa.Column("last_payment_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("last_payment_amount", sa.Float(), nullable=False, server_default="0"))

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("current_flow", sa.String(length=120)),
        sa.Column("current_step", sa.String(length=120)),
        sa.Column("context_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("conversation_sessions")
    op.drop_table("payments")
    with op.batch_alter_table("customers") as batch:
        batch.drop_column("last_payment_amount")
        batch.drop_column("last_payment_date")
