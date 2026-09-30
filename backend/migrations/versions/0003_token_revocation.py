"""Add employee token versions for logout and password revocation.

Revision ID: 0003_token_revocation
Revises: 0002_full_erp_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_token_revocation"
down_revision = "0002_full_erp_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    employee_columns = {column["name"] for column in inspector.get_columns("employee")}
    if "token_version" not in employee_columns:
        op.add_column(
            "employee",
            sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        )

    invoice_constraints = {
        tuple(constraint.get("column_names") or ())
        for constraint in inspector.get_unique_constraints("supplier_invoices")
    }
    invoice_key = ("supplier_id", "invoice_number")
    if invoice_key not in invoice_constraints:
        with op.batch_alter_table("supplier_invoices") as batch_op:
            batch_op.create_unique_constraint("uq_supplier_invoice_number", list(invoice_key))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    invoice_constraints = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints("supplier_invoices")
    }
    if "uq_supplier_invoice_number" in invoice_constraints:
        with op.batch_alter_table("supplier_invoices") as batch_op:
            batch_op.drop_constraint("uq_supplier_invoice_number", type_="unique")
    employee_columns = {column["name"] for column in inspector.get_columns("employee")}
    if "token_version" in employee_columns:
        op.drop_column("employee", "token_version")