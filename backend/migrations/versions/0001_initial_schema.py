"""Initial schema for AI Tally."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="staff"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=30)),
        sa.Column("address", sa.Text()),
        sa.Column("gst_number", sa.String(length=30)),
        sa.Column("pending_due", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_percent", sa.Float(), nullable=False, server_default="18"),
        sa.Column("supplier", sa.String(length=200)),
        sa.Column("reorder_level", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_number", sa.String(length=120), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="SET NULL")),
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("sync_status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("tally_reference", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL")),
        sa.Column("qty", sa.Float(), nullable=False, server_default="1"),
        sa.Column("rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_type", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reference", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "voice_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("detected_intent", sa.String(length=120)),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "query_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("response", sa.Text()),
        sa.Column("intent", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "conversation_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=120), nullable=False),
        sa.Column("current_flow", sa.String(length=120)),
        sa.Column("pending_field", sa.String(length=120)),
        sa.Column("context_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sync_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text()),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("sync_logs")
    op.drop_table("conversation_state")
    op.drop_table("query_history")
    op.drop_table("voice_history")
    op.drop_table("transactions")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("products")
    op.drop_table("customers")
    op.drop_table("users")