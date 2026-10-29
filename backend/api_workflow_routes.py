"""Interactive workflow read models and till reconciliation."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import auth
import models
from database import get_db
from api_helpers import employee_branch_ids
from erp_service_support import require_branch_access

router = APIRouter()

def permitted(db, user, permission):
    if not auth.has_permission(db,user,permission):
        raise HTTPException(403, "This action is not permitted")

@router.get("/operations/context")
def context(user=Depends(auth.get_current_user), db: Session=Depends(get_db)):
    permissions = set(auth.get_user_permissions(db,user))
    branches = employee_branch_ids(db,user)
    def allowed(*codes): return bool(permissions.intersection(codes))
    result = {"products": [], "warehouses": [], "orders": [], "receipts": [], "invoices": [], "runs": [], "sessions": [], "employees": [], "customers": [], "sales": []}
    if allowed("inventory:view","inventory:manage","procurement:grn","procurement:requisition","sales:refund"):
        result["products"] = [{"id":p.itemid,"name":p.itemname} for p in db.query(models.Product).filter_by(is_active=True).order_by(models.Product.itemname)]
        result["warehouses"] = [{"id":w.warehouse_id,"name":w.warehouse_name} for w in db.query(models.Warehouse).filter(models.Warehouse.branch_id.in_(branches),models.Warehouse.is_active == True).limit(200)]
    if allowed("procurement:grn","finance:invoice","procurement:po_approve"):
        orders=db.query(models.PurchaseOrder).filter(models.PurchaseOrder.branch_id.in_(branches)).order_by(models.PurchaseOrder.po_id.desc()).limit(200).all()
        result["orders"]=[{"id":o.po_id,"status":o.status.value,"items":[{"item_id":i.itemid,"quantity":str(i.quantity-i.received_quantity),"unit_cost":str(i.unit_cost)} for i in o.items]} for o in orders]
    if allowed("finance:invoice","finance:payment"):
        result["receipts"]=[{"id":g.id,"po_id":g.po_id,"name":g.reference} for g in db.query(models.GoodsReceivedNote).filter(models.GoodsReceivedNote.branch_id.in_(branches)).order_by(models.GoodsReceivedNote.id.desc()).limit(200)]
        result["invoices"]=[{"id":i.id,"name":i.invoice_number,"amount":str(i.amount),"status":i.status} for i in db.query(models.SupplierInvoice).filter(models.SupplierInvoice.branch_id.in_(branches)).order_by(models.SupplierInvoice.id.desc()).limit(200)]
    if allowed("payroll:view","payroll:approve","payroll:prepare","finance:payment"):
        runs=db.query(models.PayrollRun).join(models.Employee,models.Employee.employeeid==models.PayrollRun.prepared_by).filter(models.Employee.branchid.in_(branches)).order_by(models.PayrollRun.run_id.desc()).limit(200)
        result["runs"]=[{"id":r.run_id,"month":r.month,"status":r.status,"total":str(r.total_net)} for r in runs]
    if allowed("sales:pos","sales:approve"):
        sessions=db.query(models.CashierSession).filter(models.CashierSession.branch_id.in_(branches),models.CashierSession.status.in_(["OPEN","PENDING_REVIEW"]))
        if not allowed("sales:approve"): sessions=sessions.filter_by(employee_id=user.employeeid)
        result["sessions"]=[{"id":s.session_id,"status":s.status,"expected":str(s.expected_cash),"variance":str(s.variance or 0)} for s in sessions.limit(200)]
    if allowed("hr:attendance", "hr:leave"):
        result["employees"] = [{"id": e.employeeid, "name": e.name} for e in db.query(models.Employee).filter(models.Employee.branchid.in_(branches), models.Employee.is_active == True).order_by(models.Employee.name).all()]
    if allowed("sales:refund", "sales:approve"):
        sales = db.query(models.Sale).filter(models.Sale.branchid.in_(branches), models.Sale.status == "COMPLETED").order_by(models.Sale.saleid.desc()).limit(200).all()
        result["sales"] = [{"id": sale.saleid, "name": f"Receipt #{sale.saleid}", "items": [{"item_id": i.itemid, "quantity": str(i.quantity)} for i in sale.sale_items]} for sale in sales]
    if allowed("finance:payment"):
        customer_ids = db.query(models.Sale.customerid).filter(models.Sale.branchid.in_(branches), models.Sale.customerid.isnot(None))
        result["customers"] = [{"id": c.customerid, "name": c.name} for c in db.query(models.Customer).filter(models.Customer.customerid.in_(customer_ids)).order_by(models.Customer.name).all()]
    return result

@router.post("/cashier-sessions/{session_id}/review")
def review(session_id:int,user=Depends(auth.get_current_user),db:Session=Depends(get_db)):
    permitted(db,user,"sales:approve")
    session=db.query(models.CashierSession).filter_by(session_id=session_id).with_for_update().first()
    if not session: raise HTTPException(404,"Session not found")
    require_branch_access(db,user,session.branch_id)
    if session.employee_id == user.employeeid: raise HTTPException(403,"A different manager must review this till")
    if session.status != "PENDING_REVIEW": raise HTTPException(409,"This till is not awaiting review")
    session.status="CLOSED"
    db.add(models.AuditLog(user_id=user.employeeid,action="CASHIER_SESSION_REVIEWED",module="sales",entity_type="cashier_session",entity_id=session_id,branch_id=session.branch_id,details=f"Reviewed variance {session.variance}"))
    db.commit()
    return {"session_id":session_id,"status":"CLOSED"}

@router.get("/catalogue/pricing")
def catalogue_pricing(user=Depends(auth.get_current_user),db:Session=Depends(get_db)):
    if not (auth.has_permission(db,user,"procurement:supplier") or auth.has_permission(db,user,"inventory:manage")):
        raise HTTPException(403,"Catalogue permission required")
    return [{"id":p.itemid,"name":p.itemname,"unitprice":str(p.unitprice),"costprice":str(p.costprice or 0),"is_active":p.is_active} for p in db.query(models.Product).order_by(models.Product.itemname).all()]

import schemas
@router.patch("/products/{product_id}/pricing")
def product_pricing(product_id:int,payload:schemas.ProductPricingUpdate,user=Depends(auth.get_current_user),db:Session=Depends(get_db)):
    if not (auth.has_permission(db,user,"procurement:supplier") or auth.has_permission(db,user,"inventory:manage")):
        raise HTTPException(403,"Catalogue permission required")
    product=db.get(models.Product,product_id)
    if not product: raise HTTPException(404,"Product not found")
    product.unitprice=payload.unitprice
    product.costprice=payload.costprice
    product.is_active=payload.is_active
    db.add(models.AuditLog(user_id=user.employeeid,action="PRODUCT_PRICING_UPDATED",module="inventory",entity_type="product",entity_id=product_id))
    db.commit()
    return {"itemid":product_id,"is_active":product.is_active,"unitprice":str(product.unitprice),"costprice":str(product.costprice)}

@router.post("/payroll/{run_id}/pay")
def pay_payroll(run_id:int,user=Depends(auth.get_current_user),db:Session=Depends(get_db)):
    from decimal import Decimal
    from datetime import datetime
    permitted(db,user,"finance:payment")
    run=db.query(models.PayrollRun).filter_by(run_id=run_id).with_for_update().first()
    if not run: raise HTTPException(404,"Payroll run not found")
    preparer=db.get(models.Employee,run.prepared_by)
    require_branch_access(db,user,preparer.branchid)
    if run.status!="APPROVED": raise HTTPException(409,"Only approved and unpaid payroll can be paid")
    journal=models.JournalEntry(entry_number=f"JRN-PAYMENT-PAYROLL-{run_id}",description=f"Payroll payment {run.month}",reference_type="PAYROLL_PAYMENT",reference_id=run_id,total_amount=run.total_net,created_by=user.employeeid)
    db.add(journal);db.flush()
    db.add_all([models.JournalEntryLine(entry_id=journal.entry_id,account_code="2020",debit=run.total_net,credit=Decimal(0)),models.JournalEntryLine(entry_id=journal.entry_id,account_code="1020",debit=Decimal(0),credit=run.total_net)])
    for slip in run.payslips: slip.payment_status="PAID"
    run.status="PAID";run.paid_at=datetime.utcnow()
    db.add(models.AuditLog(user_id=user.employeeid,action="PAYROLL_PAID",module="payroll",entity_type="payroll_run",entity_id=run_id))
    db.commit()
    return {"run_id":run_id,"status":run.status,"total_paid":str(run.total_net)}
