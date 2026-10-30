"""Repair customer email even if an older migration was already stamped.

Never drop customer contact data during downgrade.
"""
from alembic import op
import sqlalchemy as sa
revision="0013_customer_email_repair"
down_revision="d2934db5301e"
branch_labels=depends_on=None

def repair_stock_triggers(bind):
    dialect=bind.dialect.name
    if dialect not in {"sqlite", "mysql"}:
        return
    if "stock_transaction_log" not in sa.inspect(bind).get_table_names():
        op.create_table("stock_transaction_log",
            sa.Column("id",sa.Integer,primary_key=True,autoincrement=True),
            sa.Column("balance_id",sa.Integer,nullable=False),
            sa.Column("old_quantity",sa.Numeric(15,3),nullable=False),
            sa.Column("new_quantity",sa.Numeric(15,3),nullable=False),
            sa.Column("changed_at",sa.DateTime,nullable=False,server_default=sa.func.current_timestamp()))
    if dialect=="sqlite":
        existing={r[0] for r in bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='trigger'"))}
    else:
        existing={r[0] for r in bind.execute(sa.text("SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()"))}
    for event in ("INSERT","UPDATE"):
        quality="stock_quality_"+event.lower()
        log="stock_log_"+event.lower()
        old="0" if event=="INSERT" else "OLD.available_stock"
        if quality not in existing:
            if dialect=="sqlite":
                op.execute(f"CREATE TRIGGER {quality} BEFORE {event} ON inventory_balances WHEN NEW.available_stock < 0 OR NEW.reserved_stock < 0 BEGIN SELECT RAISE(ABORT, 'Stock cannot be negative'); END")
            else:
                op.execute(f"CREATE TRIGGER {quality} BEFORE {event} ON inventory_balances FOR EACH ROW BEGIN IF NEW.available_stock < 0 OR NEW.reserved_stock < 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock cannot be negative'; END IF; END")
        if log not in existing:
            if dialect=="sqlite":
                op.execute(f"CREATE TRIGGER {log} AFTER {event} ON inventory_balances BEGIN INSERT INTO stock_transaction_log(balance_id,old_quantity,new_quantity) VALUES(NEW.balance_id,{old},NEW.available_stock); END")
            else:
                op.execute(f"CREATE TRIGGER {log} AFTER {event} ON inventory_balances FOR EACH ROW INSERT INTO stock_transaction_log(balance_id,old_quantity,new_quantity) VALUES(NEW.balance_id,{old},NEW.available_stock)")

def upgrade():
    columns={c["name"] for c in sa.inspect(op.get_bind()).get_columns("customer")}
    if "email" not in columns:
        op.add_column("customer",sa.Column("email",sa.String(150),nullable=True))

    repair_stock_triggers(op.get_bind())

def downgrade():
    pass
