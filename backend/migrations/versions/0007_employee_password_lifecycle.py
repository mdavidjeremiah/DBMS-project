"""Add employee password lifecycle and password event history.

Revision ID: 0007_password_lifecycle
Revises: 0006_cashier_sessions
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_password_lifecycle"
down_revision = "0006_cashier_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("employee")}
    additions = (
        ("must_change_password", sa.Boolean(), False, sa.text("0")),
        ("temporary_password_expires_at", sa.DateTime(), True, None),
        ("password_changed_at", sa.DateTime(), True, None),
        ("failed_login_attempts", sa.Integer(), False, sa.text("0")),
        ("last_failed_login_at", sa.DateTime(), True, None),
        ("locked_until", sa.DateTime(), True, None),
        ("last_login_at", sa.DateTime(), True, None),
    )
    for name, column_type, nullable, server_default in additions:
        if name not in columns:
            op.add_column(
                "employee",
                sa.Column(name, column_type, nullable=nullable, server_default=server_default),
            )

    if not inspector.has_table("password_events"):
        op.create_table(
            "password_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("employee.employeeid", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("initiated_by_user_id", sa.Integer(), sa.ForeignKey("employee.employeeid", ondelete="SET NULL"), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("reason", sa.String(length=255), nullable=True),
        )
        op.create_index("ix_password_events_id", "password_events", ["id"], unique=False)
        op.create_index("ix_password_events_user_id", "password_events", ["user_id"], unique=False)
        op.create_index("ix_password_events_event_type", "password_events", ["event_type"], unique=False)
        op.create_index("ix_password_events_timestamp", "password_events", ["timestamp"], unique=False)


def downgrade() -> None:
    raise RuntimeError("Password lifecycle data must not be removed by downgrading.")
