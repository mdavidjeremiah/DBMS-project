import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_stock_guards_views_and_transaction_rollback():
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE product(itemid INTEGER PRIMARY KEY,itemname TEXT,costprice NUMERIC)"))
        c.execute(text("CREATE TABLE warehouses(warehouse_id INTEGER PRIMARY KEY,branch_id INTEGER)"))
        c.execute(text("CREATE TABLE inventory_balances(balance_id INTEGER PRIMARY KEY,item_id INTEGER,warehouse_id INTEGER,available_stock NUMERIC,reserved_stock NUMERIC)"))
        c.execute(text("CREATE TABLE chart_of_accounts(account_code TEXT,account_name TEXT)"))
        c.execute(text("CREATE TABLE journal_entry_lines(account_code TEXT,debit NUMERIC,credit NUMERIC)"))
        spec = importlib.util.spec_from_file_location("quality", Path(__file__).parents[1] / "migrations/versions/0011_data_quality.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with Operations.context(MigrationContext.configure(c)):
            mod.upgrade()
        c.execute(text("INSERT INTO product VALUES(1,'Cement',100)"))
        c.execute(text("INSERT INTO warehouses VALUES(1,1)"))
        c.execute(text("INSERT INTO inventory_balances VALUES(1,1,1,2,0)"))
        assert c.execute(text("SELECT stock_value FROM vw_inventory_position")).scalar() == 200
    with engine.connect() as c:
        with pytest.raises(IntegrityError):
            c.execute(text("UPDATE inventory_balances SET available_stock=-1"))
        c.rollback()
        assert c.execute(text("SELECT available_stock FROM inventory_balances")).scalar() == 2
        c.rollback()
        with c.begin():
            c.execute(text("UPDATE inventory_balances SET available_stock=1"))
        assert c.execute(text("SELECT COUNT(*) FROM stock_transaction_log")).scalar() == 2
        c.rollback()
        trans = c.begin()
        c.execute(text("UPDATE inventory_balances SET available_stock=0"))
        trans.rollback()
        assert c.execute(text("SELECT COUNT(*) FROM stock_transaction_log")).scalar() == 2
