"""Add ERP branch stock balances and inventory movements.

Revision ID: 0009_erp_stock_ledger
Revises: 0008_profile_photo
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_erp_stock_ledger"
down_revision = "0008_profile_photo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "erp_stock_balances" not in existing_tables:
        op.create_table(
            "erp_stock_balances",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("itemid", sa.Integer(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.Numeric(15, 3), server_default="0", nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["itemid"], ["product.itemid"]),
            sa.ForeignKeyConstraint(["branch_id"], ["branch.branchid"]),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.warehouse_id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("itemid", "warehouse_id", name="uq_erp_stock_item_warehouse"),
        )
        op.create_index("ix_erp_stock_balances_id", "erp_stock_balances", ["id"], unique=False)
        op.create_index("ix_erp_stock_balances_branch_id", "erp_stock_balances", ["branch_id"], unique=False)
        op.create_index("ix_erp_stock_balances_warehouse_id", "erp_stock_balances", ["warehouse_id"], unique=False)
        op.create_index("ix_erp_stock_branch_item", "erp_stock_balances", ["branch_id", "itemid"], unique=False)

    if "erp_inventory_movements" not in existing_tables:
        op.create_table(
            "erp_inventory_movements",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("itemid", sa.Integer(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), nullable=False),
            sa.Column("movement_type", sa.String(length=32), nullable=False),
            sa.Column("quantity", sa.Numeric(15, 3), nullable=False),
            sa.Column("reference_type", sa.String(length=32), nullable=True),
            sa.Column("reference_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["itemid"], ["product.itemid"]),
            sa.ForeignKeyConstraint(["branch_id"], ["branch.branchid"]),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.warehouse_id"]),
            sa.ForeignKeyConstraint(["created_by"], ["employee.employeeid"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_erp_inventory_movements_id", "erp_inventory_movements", ["id"], unique=False)
        op.create_index("ix_erp_inventory_movements_itemid", "erp_inventory_movements", ["itemid"], unique=False)
        op.create_index("ix_erp_inventory_movements_branch_id", "erp_inventory_movements", ["branch_id"], unique=False)
        op.create_index("ix_erp_inventory_movements_warehouse_id", "erp_inventory_movements", ["warehouse_id"], unique=False)
        op.create_index("ix_erp_inventory_movements_created_at", "erp_inventory_movements", ["created_at"], unique=False)


def downgrade() -> None:
    raise RuntimeError("ERP inventory history must not be removed by downgrading.")
