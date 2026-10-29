"""Focused API route groups; endpoint paths and behavior are unchanged."""
from api_route_support import (
    Any, APIRouter, Decimal, Depends, Dict, File, FileResponse, Header,
    HTTPException, List, MetaData, Optional, Query, Request, Response,
    Session, Table, UploadFile, auth, can_view_procurement, datetime, date,
    desc, employee_branch_ids, employee_name, erp_service, func, get_db,
    models, or_, request_ip, schemas, scope_sales_query, status, timedelta,
    write_audit_log,
)

router = APIRouter()

# =====================================================================
# /api/reports (Department Report Endpoints)
# =====================================================================

@router.get("/reports/sales", tags=["Reports"])
def sales_report(
    branch_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:view"):
        raise HTTPException(status_code=403, detail="Sales view permission required.")
    q = scope_sales_query(
        db,
        current_user,
        db.query(models.Sale).filter(models.Sale.status == "COMPLETED"),
        branch_id,
    )
    if date_from:
        q = q.filter(models.Sale.saledate >= date_from)
    if date_to:
        q = q.filter(models.Sale.saledate <= date_to)
    sales = q.all()
    total_rev = sum([s.totalamount or Decimal("0") for s in sales], Decimal("0"))
    total_cogs = Decimal("0")
    for s in sales:
        for i in s.sale_items:
            total_cogs += (i.unitcost or Decimal("0")) * i.quantity
    return {
        "total_revenue": float(total_rev),
        "total_cogs": float(total_cogs),
        "gross_profit": float(total_rev - total_cogs),
        "gross_margin_pct": float((total_rev - total_cogs) / total_rev * 100) if total_rev > 0 else 0.0,
        "transaction_count": len(sales),
        "average_basket": float(total_rev / len(sales)) if sales else 0.0,
    }


@router.get("/reports/inventory", tags=["Reports"])
def inventory_report(
    warehouse_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "inventory:view"):
        raise HTTPException(status_code=403, detail="Inventory view permission required.")
    q = db.query(models.InventoryBalance)
    if warehouse_id:
        q = q.filter(models.InventoryBalance.warehouse_id == warehouse_id)
    balances = q.all()
    total_val = Decimal("0")
    out_stock = 0
    low_stock = 0
    for b in balances:
        cost = b.product.costprice or Decimal("0")
        avail = b.available_stock or Decimal("0")
        total_val += avail * cost
        reorder = b.product.reorderlevel or 0
        if avail <= 0:
            out_stock += 1
        elif avail <= reorder:
            low_stock += 1
    return {
        "total_inventory_value": float(total_val),
        "out_of_stock_count": out_stock,
        "low_stock_count": low_stock,
        "product_count": len(balances),
    }


@router.get("/reports/payroll", tags=["Reports"])
def payroll_report(
    month: Optional[str] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Rule 9: only HR/Finance/Admin
    if not auth.has_permission(db, current_user, "payroll:view"):
        raise HTTPException(status_code=403, detail="Payroll view permission required.")
    q = db.query(models.PayrollRun)
    if month:
        q = q.filter(models.PayrollRun.month == month)
    runs = q.order_by(models.PayrollRun.created_at.desc()).limit(12).all()
    return [
        {
            "run_id": r.run_id,
            "month": r.month,
            "status": r.status,
            "total_gross": float(r.total_gross),
            "total_deductions": float(r.total_deductions),
            "total_net": float(r.total_net),
            "created_at": r.created_at,
            "approved_at": r.approved_at,
        }
        for r in runs
    ]
