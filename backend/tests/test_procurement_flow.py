from decimal import Decimal
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import models
import schemas
import erp_procurement_service as service


def test_receipt_invoice_payment_use_real_models_and_same_stock():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    with Session(engine) as db, patch("auth.has_permission", return_value=True):
        branch = models.Branch(branchname="Test", location="Test")
        db.add(branch); db.flush()
        user = models.Employee(name="Tester", nin="TEST", roletype=models.RoleType.PROCUREMENT_OFFICER, branchid=branch.branchid)
        wh = models.Warehouse(branch_id=branch.branchid, warehouse_name="Test")
        product = models.Product(itemname="Cement", unitprice=200, costprice=100)
        supplier = models.Supplier(suppliername="Supplier")
        db.add_all([user,wh,product,supplier]); db.flush()
        po = models.PurchaseOrder(branch_id=branch.branchid, supplierid=supplier.supplierid, employeeid=user.employeeid,status=models.POStatus.APPROVED)
        db.add(po); db.flush()
        db.add(models.PurchaseOrderItem(po_id=po.po_id,itemid=product.itemid,quantity=2,unit_cost=100))
        db.commit()
        grn = service.create_goods_received_note(schemas.GoodsReceivedNoteCreate(po_id=po.po_id,warehouse_id=wh.warehouse_id,items=[dict(item_id=product.itemid,quantity_received=2,unit_cost=100)]),user,db)
        assert db.query(models.InventoryBalance).one().available_stock == Decimal("2")
        invoice = service.process_supplier_invoice(schemas.SupplierInvoiceCreate(po_id=po.po_id,grn_id=grn.id,invoice_number="TEST-1",amount=200),user,db)
        service.record_supplier_payment(schemas.SupplierPaymentCreate(invoice_id=invoice.id,amount=200),user,db)
        assert invoice.status == "PAID"
        assert sum((line.debit-line.credit for line in db.query(models.JournalEntryLine)), Decimal(0)) == 0
