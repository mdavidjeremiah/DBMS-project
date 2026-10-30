from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import models,schemas
from accounting_setup import ensure_accounts
from erp_pos_service import process_pos_sale


def test_two_cashiers_cannot_sell_the_last_unit(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'stock.sqlite'),connect_args={'check_same_thread':False,'timeout':30})
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        b=models.Branch(branchname='Concurrency test',location='Test');db.add(b);db.flush()
        w=models.Warehouse(branch_id=b.branchid,warehouse_name='Test');db.add(w)
        p=models.Product(itemname='Last unit',unitprice=200,costprice=100,is_active=True);db.add(p);db.flush()
        users=[]
        for index in range(2):
            u=models.Employee(name=f'Cashier {index}',nin=f'CONC-{index}',roletype=models.RoleType.CASHIER,branchid=b.branchid);db.add(u);db.flush()
            till=models.CashierSession(employee_id=u.employeeid,branch_id=b.branchid,warehouse_id=w.warehouse_id,status='OPEN',opening_float=0,cash_sales=0,cash_refunds=0,expected_cash=0);db.add(till);db.flush();users.append((u.employeeid,till.session_id))
        db.add(models.InventoryBalance(item_id=p.itemid,warehouse_id=w.warehouse_id,available_stock=1,reserved_stock=0));ensure_accounts(db);db.commit()
        product_id,warehouse_id,branch_id=p.itemid,w.warehouse_id,b.branchid
    barrier=Barrier(2)
    def sell(pair):
        with Session(engine) as db:
            user=db.get(models.Employee,pair[0]);barrier.wait(timeout=10)
            try:
                result=process_pos_sale(schemas.SaleCreate(branchid=branch_id,warehouseid=warehouse_id,cashiersessionid=pair[1],idempotency_key=f'last-unit-{pair[0]}',items=[{'itemid':product_id,'quantity':1}]),user,db)
                return result['saleid']
            except HTTPException as error:
                db.rollback()
                assert error.status_code in (400,409)
                return None
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(sell,users))
    assert sum(result is not None for result in results)==1
    with Session(engine) as db:
        assert db.query(models.Sale).count()==1
        assert db.query(models.InventoryBalance).one().available_stock==Decimal(0)
        assert db.query(models.InventoryMovement).count()==1
    engine.dispose()
