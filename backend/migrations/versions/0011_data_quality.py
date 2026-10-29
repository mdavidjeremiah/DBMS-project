"""Stock quality guards, transactional change log, and reporting views.

Revision ID: 0011_data_quality
"""
from alembic import op
import sqlalchemy as sa
revision = "0011_data_quality"
down_revision = "0010_pos_sale_context"
branch_labels = depends_on = None

def upgrade():
    bind = op.get_bind()
    op.create_table("stock_transaction_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("balance_id", sa.Integer, nullable=False),
        sa.Column("old_quantity", sa.Numeric(15,3), nullable=False),
        sa.Column("new_quantity", sa.Numeric(15,3), nullable=False),
        sa.Column("changed_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False))
    for event in ("INSERT", "UPDATE"):
        name = "stock_quality_" + event.lower()
        old = "0" if event == "INSERT" else "OLD.available_stock"
        if bind.dialect.name == "sqlite":
            op.execute(f"CREATE TRIGGER {name} BEFORE {event} ON inventory_balances WHEN NEW.available_stock < 0 OR NEW.reserved_stock < 0 BEGIN SELECT RAISE(ABORT, 'Stock cannot be negative'); END")
            op.execute(f"CREATE TRIGGER stock_log_{event.lower()} AFTER {event} ON inventory_balances BEGIN INSERT INTO stock_transaction_log(balance_id,old_quantity,new_quantity) VALUES(NEW.balance_id,{old},NEW.available_stock); END")
        elif bind.dialect.name == "mysql":
            op.execute(f"CREATE TRIGGER {name} BEFORE {event} ON inventory_balances FOR EACH ROW BEGIN IF NEW.available_stock < 0 OR NEW.reserved_stock < 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock cannot be negative'; END IF; END")
            op.execute(f"CREATE TRIGGER stock_log_{event.lower()} AFTER {event} ON inventory_balances FOR EACH ROW INSERT INTO stock_transaction_log(balance_id,old_quantity,new_quantity) VALUES(NEW.balance_id,{old},NEW.available_stock)")
    op.execute("CREATE VIEW vw_inventory_position AS SELECT b.balance_id,b.item_id,p.itemname,b.warehouse_id,w.branch_id,b.available_stock,b.reserved_stock,b.available_stock * COALESCE(p.costprice,0) AS stock_value FROM inventory_balances b JOIN product p ON p.itemid=b.item_id JOIN warehouses w ON w.warehouse_id=b.warehouse_id")
    op.execute("CREATE VIEW vw_trial_balance AS SELECT a.account_code,a.account_name,COALESCE(SUM(l.debit),0) AS debits,COALESCE(SUM(l.credit),0) AS credits,COALESCE(SUM(l.debit-l.credit),0) AS balance FROM chart_of_accounts a LEFT JOIN journal_entry_lines l ON l.account_code=a.account_code GROUP BY a.account_code,a.account_name")

def downgrade():
    op.execute("DROP VIEW vw_trial_balance")
    op.execute("DROP VIEW vw_inventory_position")
    for event in ("insert", "update"):
        op.execute(f"DROP TRIGGER stock_quality_{event}")
        op.execute(f"DROP TRIGGER stock_log_{event}")
    op.drop_table("stock_transaction_log")
