"""Add missing cashier-session dashboard columns.

Revision ID: 0006_cashier_sessions
Revises: 0005_erp_role_tables
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_cashier_sessions"
down_revision = "0005_erp_role_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("cashier_sessions"):
        raise RuntimeError("Expected cashier_sessions table is missing.")

    columns = {column["name"] for column in inspector.get_columns("cashier_sessions")}
    if "closing_float" not in columns:
        op.add_column(
            "cashier_sessions",
            sa.Column("closing_float", sa.Numeric(12, 2), nullable=True),
        )
    if "notes" not in columns:
        op.add_column(
            "cashier_sessions",
            sa.Column("notes", sa.String(255), nullable=True),
        )


def downgrade() -> None:
    raise RuntimeError("Cashier session data must not be removed by downgrading.")
