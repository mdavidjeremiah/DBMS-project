import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text
from alembic.migration import MigrationContext
from alembic.operations import Operations


def migration(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).parents[1]/"migrations/versions"/name)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

@pytest.mark.parametrize("has_email",[False,True])
def test_customer_email_upgrade_is_safe_and_preserves_contacts(has_email):
    engine=create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE customer(customerid INTEGER PRIMARY KEY,name TEXT"+(",email VARCHAR(150)" if has_email else "")+")"))
        c.execute(text("INSERT INTO customer(customerid,name) VALUES(1,'Existing customer')"))
        with Operations.context(MigrationContext.configure(c)):
            mod=migration('d2934db5301e_add_email_to_customer.py')
            mod.upgrade();mod.upgrade();mod.downgrade()
        assert c.execute(text("SELECT name,email FROM customer")).one()==('Existing customer',None)


def test_repair_reinstalls_missing_triggers_and_rolls_back_log():
    engine=create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE customer(customerid INTEGER PRIMARY KEY,name TEXT)"))
        c.execute(text("CREATE TABLE inventory_balances(balance_id INTEGER PRIMARY KEY,available_stock NUMERIC,reserved_stock NUMERIC)"))
        with Operations.context(MigrationContext.configure(c)):
            mod=migration('0013_customer_email_repair.py');mod.upgrade();mod.upgrade()
        c.execute(text("INSERT INTO inventory_balances VALUES(1,1,0)"))
        assert c.execute(text("SELECT count(*) FROM stock_transaction_log")).scalar()==1
        with pytest.raises(Exception):c.execute(text("UPDATE inventory_balances SET available_stock=-1"))
        assert c.execute(text("SELECT available_stock FROM inventory_balances")).scalar()==1
