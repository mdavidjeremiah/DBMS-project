"""Create ERP role and permission tables.

Revision ID: 0005_erp_role_tables
Revises: 0004_merge_erp_heads
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_erp_role_tables"
down_revision = "0004_merge_erp_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "erp_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_roles_id", "erp_roles", ["id"], unique=False)
    op.create_index("ix_erp_roles_name", "erp_roles", ["name"], unique=True)

    op.create_table(
        "erp_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_permissions_id", "erp_permissions", ["id"], unique=False)
    op.create_index("ix_erp_permissions_code", "erp_permissions", ["code"], unique=True)
    op.create_index("ix_erp_permissions_module", "erp_permissions", ["module"], unique=False)

    op.create_table(
        "employee_erp_roles",
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.employeeid"]),
        sa.ForeignKeyConstraint(["role_id"], ["erp_roles.id"]),
        sa.PrimaryKeyConstraint("employee_id", "role_id"),
    )
    op.create_table(
        "erp_role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["erp_permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["erp_roles.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )


def downgrade() -> None:
    raise RuntimeError("ERP role assignments may contain live data and must not be dropped.")
