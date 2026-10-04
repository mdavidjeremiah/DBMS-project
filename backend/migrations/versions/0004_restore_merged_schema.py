"""Restore schema fields omitted by the ERP merge."""
from alembic import op
import sqlalchemy as sa
import models

revision = "0004_restore_merged_schema"
down_revision = ("0003_token_revocation", "0002_erp_foundation")
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind)
    additions = {
        "employee": [sa.Column("is_active", sa.Boolean(), server_default=sa.true())],
        "product": [sa.Column("base_unit", sa.String(20), server_default="Piece"), sa.Column("costprice", sa.Numeric(10, 2), server_default="0")],
        "purchase_order": [sa.Column("branchid", sa.Integer()), sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"), sa.Column("approved_by", sa.Integer()), sa.Column("approved_at", sa.DateTime())],
        "sale": [sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"), sa.Column("discountamount", sa.Numeric(12, 2), server_default="0"), sa.Column("taxamount", sa.Numeric(12, 2), server_default="0"), sa.Column("paymentmethod", sa.String(50), server_default="CASH"), sa.Column("cashiersessionid", sa.Integer()), sa.Column("warehouseid", sa.Integer())],
        "sale_item": [sa.Column("unitcost", sa.Numeric(10, 2), server_default="0"), sa.Column("discount", sa.Numeric(10, 2), server_default="0"), sa.Column("line_total", sa.Numeric(12, 2))],
    }
    for table, columns in additions.items():
        existing = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)


def downgrade():
    raise RuntimeError("Restore from backup to undo the additive schema repair.")
