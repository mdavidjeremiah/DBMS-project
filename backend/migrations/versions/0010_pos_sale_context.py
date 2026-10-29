"""Persist the warehouse and cashier session attached to a POS sale.

Revision ID: 0010_pos_sale_context
Revises: 0009_erp_stock_ledger
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_pos_sale_context"
down_revision = "0009_erp_stock_ledger"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "sale" not in tables or "cashier_sessions" not in tables:
        raise RuntimeError("Run the existing ERP migrations before applying POS sale context.")

    sale_columns = _columns("sale")
    if "warehouseid" not in sale_columns:
        op.add_column("sale", sa.Column("warehouseid", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_sale_warehouseid_warehouses",
            "sale",
            "warehouses",
            ["warehouseid"],
            ["warehouse_id"],
        )
    if "cashiersessionid" not in sale_columns:
        op.add_column("sale", sa.Column("cashiersessionid", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_sale_cashiersessionid_cashier_sessions",
            "sale",
            "cashier_sessions",
            ["cashiersessionid"],
            ["session_id"],
        )

    session_columns = _columns("cashier_sessions")
    if "cash_refunds" not in session_columns:
        op.add_column(
            "cashier_sessions",
            sa.Column("cash_refunds", sa.Numeric(12, 2), nullable=True, server_default="0"),
        )
    if "closed_by" not in session_columns:
        op.add_column("cashier_sessions", sa.Column("closed_by", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_cashier_sessions_closed_by_employee",
            "cashier_sessions",
            "employee",
            ["closed_by"],
            ["employeeid"],
        )


def downgrade() -> None:
    session_columns = _columns("cashier_sessions")
    if "closed_by" in session_columns:
        op.drop_constraint("fk_cashier_sessions_closed_by_employee", "cashier_sessions", type_="foreignkey")
        op.drop_column("cashier_sessions", "closed_by")
    if "cash_refunds" in session_columns:
        op.drop_column("cashier_sessions", "cash_refunds")

    sale_columns = _columns("sale")
    if "cashiersessionid" in sale_columns:
        op.drop_constraint("fk_sale_cashiersessionid_cashier_sessions", "sale", type_="foreignkey")
        op.drop_column("sale", "cashiersessionid")
    if "warehouseid" in sale_columns:
        op.drop_constraint("fk_sale_warehouseid_warehouses", "sale", type_="foreignkey")
        op.drop_column("sale", "warehouseid")
