from decimal import Decimal
from sqlalchemy import create_engine,event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import models, main, auth
from database import get_db
from accounting_setup import ensure_accounts


def test_api_purchase_receive_sell_invoice_pay_and_close_till():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    @event.listens_for(engine,"connect")
    def foreign_keys(connection,record): connection.execute("PRAGMA foreign_keys=ON")
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        b=models.Branch(branchname="Flow",location="Test");db.add(b);db.flush()
        procurement=models.Employee(name="Buyer",nin="BUY",email="buyer@example.com",roletype=models.RoleType.PROCUREMENT_OFFICER,branchid=b.branchid)
        manager=models.Employee(name="Manager",nin="MGR",email="manager@example.com",roletype=models.RoleType.BRANCH_MANAGER,branchid=b.branchid)
        cashier=models.Employee(name="Cashier",nin="CASH",email="cashier@example.com",roletype=models.RoleType.CASHIER,branchid=b.branchid)
        finance=models.Employee(name="Finance",nin="FIN",email="finance@example.com",roletype=models.RoleType.ACCOUNTANT,branchid=b.branchid)
        p=models.Product(itemname="Flow cement",unitprice=200,costprice=100,is_active=True)
        w=models.Warehouse(branch_id=b.branchid,warehouse_name="Flow warehouse")
        supplier=models.Supplier(suppliername="Flow supplier")
        db.add_all([procurement,manager,cashier,finance,p,w,supplier]);db.flush();ensure_accounts(db);db.commit()
        current=[procurement]
        main.app.dependency_overrides[auth.get_current_user]=lambda:current[0]
        main.app.dependency_overrides[get_db]=lambda:db
        try:
            with TestClient(main.app) as client:
                def post(path,body,**kwargs):
                    r=client.post(path,json=body,**kwargs)
                    assert r.status_code==200,(path,r.status_code,r.text)
                    return r.json()
                req=post('/api/purchase-requisitions',{'items':[{'itemid':p.itemid,'quantity':'2','estimated_unit_cost':'100'}]})
                current[0]=manager
                post('/api/approvals/requisition',{'requisition_id':req['requisition_id'],'action':'APPROVE'})
                current[0]=procurement
                po=post('/api/purchase-orders',{'supplierid':supplier.supplierid,'requisition_id':req['requisition_id']})
                current[0]=manager
                post('/api/approvals/purchase-order',{'po_id':po['po_id'],'action':'APPROVE'})
                current[0]=procurement
                grn=post('/api/goods-receipts',{'po_id':po['po_id'],'warehouse_id':w.warehouse_id,'items':[{'item_id':p.itemid,'quantity_received':'2','unit_cost':'100'}]})
                assert db.query(models.InventoryBalance).one().available_stock==Decimal('2')
                current[0]=cashier
                session=post('/api/cashier-sessions/open',{'warehouse_id':w.warehouse_id,'opening_float':'0'})
                body={'warehouseid':w.warehouse_id,'cashiersessionid':session['session_id'],'payment_method':'cash','items':[{'itemid':p.itemid,'quantity':'1'}]}
                sale=post('/api/sales',body,headers={'Idempotency-Key':'flow-sale-0001'})
                repeat=post('/api/sales',body,headers={'Idempotency-Key':'flow-sale-0001'})
                assert repeat['saleid']==sale['saleid'] and repeat['idempotent_replay']
                assert db.query(models.InventoryBalance).one().available_stock==Decimal('1')
                assert client.get('/api/products').json()[0]['available_stock']==1
                post(f"/api/cashier-sessions/{session['session_id']}/close",{'actual_cash':'200'})
                current[0]=finance
                invoice=post('/api/supplier-invoices',{'po_id':po['po_id'],'grn_id':grn['grn_id'],'invoice_number':'FLOW-1','amount':'200'})
                post('/api/supplier-payments',{'invoice_id':invoice['invoice_id'],'amount':'200','payment_method':'bank'})
                assert db.query(models.SupplierInvoice).one().status=='PAID'
                assert db.query(models.Sale).count()==1
                for journal in db.query(models.JournalEntry):
                    assert sum((line.debit-line.credit for line in journal.lines),Decimal(0))==0
        finally:
            main.app.dependency_overrides.clear()


def test_payroll_payment_posts_balanced_journal_and_rejects_replay():
    from api_workflow_routes import pay_payroll
    from erp_payroll_service import execute_payroll_run, approve_and_post_payroll
    from fastapi import HTTPException
    import pytest
    engine=create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        b=models.Branch(branchname="Payroll",location="Test");db.add(b);db.flush()
        hr=models.Employee(name="HR",nin="HR-PAY",roletype=models.RoleType.HR_STAFF,branchid=b.branchid,salary=100)
        manager=models.Employee(name="Manager",nin="M-PAY",roletype=models.RoleType.BRANCH_MANAGER,branchid=b.branchid,salary=200)
        finance=models.Employee(name="Finance",nin="F-PAY",roletype=models.RoleType.ACCOUNTANT,branchid=b.branchid,salary=300)
        db.add_all([hr,manager,finance]);db.flush();ensure_accounts(db);db.commit()
        run=execute_payroll_run("2026-10",hr,db)
        approve_and_post_payroll(run.run_id,manager,db)
        result=pay_payroll(run.run_id,finance,db)
        assert result['status']=='PAID'
        assert all(s.payment_status=='PAID' for s in run.payslips)
        with pytest.raises(HTTPException) as failure:pay_payroll(run.run_id,finance,db)
        assert failure.value.status_code==409
        for journal in db.query(models.JournalEntry):
            assert sum((line.debit-line.credit for line in journal.lines),Decimal(0))==0
