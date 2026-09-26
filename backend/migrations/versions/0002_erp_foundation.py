"""Additive ERP foundation for RBAC, inventory, payments, and audit.

Revision ID: 0002_erp_foundation
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa
import models

revision = "0002_erp_foundation"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Create only newly declared tables; checkfirst preserves all legacy tables.
    models.Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    product_columns = {column["name"] for column in inspector.get_columns("product")}
    if "is_active" not in product_columns:
        op.add_column("product", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    sale_columns = {column["name"] for column in inspector.get_columns("sale")}
    if "status" not in sale_columns:
        op.add_column("sale", sa.Column("status", sa.String(length=20), nullable=False, server_default="COMPLETED"))
    if "idempotency_key" not in sale_columns:
        op.add_column("sale", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
        op.create_index("ix_sale_idempotency_key", "sale", ["idempotency_key"], unique=True)
    item_type = next(column["type"] for column in sa.inspect(bind).get_columns("sale_item") if column["name"] == "quantity")
    if isinstance(item_type, sa.Integer):
        op.alter_column("sale_item", "quantity", existing_type=sa.Integer(), type_=sa.Numeric(15, 3), existing_nullable=False)
    po_columns = {column["name"] for column in sa.inspect(bind).get_columns("purchase_order")}
    if "branch_id" not in po_columns:
        op.add_column("purchase_order", sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branch.branchid"), nullable=True))
        op.create_index("ix_purchase_order_branch_id", "purchase_order", ["branch_id"])
    if "requisition_id" not in po_columns:
        op.add_column("purchase_order", sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("purchase_requisitions.id"), nullable=True))
        op.create_index("ix_purchase_order_requisition_id", "purchase_order", ["requisition_id"], unique=True)
    if bind.dialect.name == "mysql":
        op.execute("ALTER TABLE purchase_order MODIFY COLUMN status ENUM('PENDING','APPROVED','RECEIVED','CANCELLED','PARTIALLY_RECEIVED') NOT NULL DEFAULT 'PENDING'")


def downgrade() -> None:
    raise RuntimeError("ERP foundation tables contain business records and must not be dropped.")
