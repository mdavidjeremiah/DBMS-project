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

# /api/approvals (Requisitions, POs, Leave, General)
# =====================================================================

@router.get("/approvals", tags=["Approvals"])
def get_pending_approvals(
    module: Optional[str] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Return all pending approval requests visible to this user's role."""
    result = []
    can_approve_all = auth.has_permission(db, current_user, "approvals:approve")

    # Purchase Requisitions
    branch_ids = employee_branch_ids(db, current_user)
    if (not module or module == "REQUISITION") and (
        can_approve_all or auth.has_permission(db, current_user, "procurement:approve_req")
    ):
        reqs = db.query(models.PurchaseRequisition).filter(
            models.PurchaseRequisition.status == "PENDING",
            models.PurchaseRequisition.branch_id.in_(branch_ids) if branch_ids else models.PurchaseRequisition.branch_id.is_(None),
        ).all()
        for r in reqs:
            requester = db.get(models.Employee, r.requester_id)
            result.append({
                "type": "REQUISITION",
                "id": r.requisition_id,
                "description": f"Purchase Requisition — {len(r.items)} item(s)",
                "requester": requester.name if requester else "Unknown",
                "created_at": r.created_at,
                "status": r.status,
                "notes": r.notes,
            })

    # Purchase Orders
    if (not module or module == "PO") and (
        can_approve_all or auth.has_permission(db, current_user, "procurement:po_approve")
    ):
        pos = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.status == models.POStatus.PENDING,
            models.PurchaseOrder.branch_id.in_(branch_ids) if branch_ids else models.PurchaseOrder.branch_id.is_(None),
        ).all()
        for p in pos:
            supplier = db.get(models.Supplier, p.supplierid)
            result.append({
                "type": "PO",
                "id": p.po_id,
                "description": f"Purchase Order — {supplier.suppliername if supplier else 'Supplier'} — UGX {float(p.total_amount or 0):,.0f}",
                "requester": employee_name(db, p.employeeid),
                "created_at": p.orderdate,
                "status": p.status.value,
                "total_amount": float(p.total_amount or 0),
            })

    # Leave Requests
    if (not module or module == "LEAVE") and (
        can_approve_all or auth.has_permission(db, current_user, "hr:leave")
    ):
        leaves = db.query(models.LeaveRequest).join(
            models.Employee, models.Employee.employeeid == models.LeaveRequest.employee_id
        ).filter(
            models.LeaveRequest.status == "PENDING",
            models.Employee.branchid.in_(branch_ids) if branch_ids else models.Employee.branchid.is_(None),
        ).all()
        for lv in leaves:
            emp = db.get(models.Employee, lv.employee_id)
            result.append({
                "type": "LEAVE",
                "id": lv.leave_id,
                "description": f"{lv.leave_type} leave — {lv.start_date} to {lv.end_date}",
                "requester": emp.name if emp else "Unknown",
                "created_at": lv.created_at,
                "status": lv.status,
            })

    # Stock Adjustments
    if (not module or module == "ADJUSTMENT") and (
        can_approve_all or auth.has_permission(db, current_user, "inventory:approve_adjust")
    ):
        adjs = db.query(models.StockAdjustment).join(
            models.Warehouse, models.Warehouse.warehouse_id == models.StockAdjustment.warehouse_id
        ).filter(
            models.StockAdjustment.status == "PENDING",
            models.Warehouse.branch_id.in_(branch_ids) if branch_ids else models.Warehouse.branch_id.is_(None),
        ).all()
        for a in adjs:
            requester = db.get(models.Employee, a.requester_id)
            result.append({
                "type": "ADJUSTMENT",
                "id": a.adjustment_id,
                "description": f"Stock Adjustment — {a.product.itemname if a.product else 'Product'} ({a.variance_quantity})",
                "requester": requester.name if requester else "Unknown",
                "created_at": a.created_at,
                "status": a.status,
                "reason_code": a.reason_code,
            })

    return sorted(result, key=lambda x: x["created_at"] or "", reverse=True)


@router.post("/approvals/stock-adjustment", tags=["Approvals"])
def approve_stock_adjustment(
    payload: schemas.StockAdjustmentApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.has_permission(db, current_user, "inventory:approve_adjust"):
        raise HTTPException(status_code=403, detail="You do not have stock adjustment approval permission.")
    adjustment = db.get(models.StockAdjustment, payload.adjustment_id)
    if not adjustment:
        raise HTTPException(status_code=404, detail="Stock adjustment not found.")
    warehouse = db.get(models.Warehouse, adjustment.warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found.")
    erp_service.require_warehouse_access(db, current_user, adjustment.warehouse_id, warehouse.branch_id)
    result = erp_service.approve_or_reject_stock_adjustment(
        adjustment_id=payload.adjustment_id,
        action=payload.action,
        approver=current_user,
        notes=payload.notes,
        db=db,
        ip_address=request_ip(request),
    )
    return {"adjustment_id": result.adjustment_id, "status": result.status}


@router.post("/approvals/requisition", tags=["Approvals"])
def approve_requisition(
    payload: schemas.RequisitionApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "procurement:approve_req"):
        raise HTTPException(status_code=403, detail="You do not have requisition approval permission.")
    req = erp_service.approve_or_reject_requisition(
        requisition_id=payload.requisition_id,
        action=payload.action,
        approver=current_user,
        notes=payload.notes,
        db=db,
        ip_address=request_ip(request),
    )
    return {"requisition_id": req.requisition_id, "status": req.status}


@router.post("/approvals/purchase-order", tags=["Approvals"])
def approve_purchase_order(
    payload: schemas.POApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "procurement:po_approve"):
        raise HTTPException(status_code=403, detail="You do not have PO approval permission.")
    po = erp_service.approve_or_reject_po(
        po_id=payload.po_id,
        action=payload.action,
        approver=current_user,
        notes=payload.notes,
        db=db,
        ip_address=request_ip(request),
    )
    return {"po_id": po.po_id, "status": po.status.value}


@router.post("/approvals/leave", tags=["Approvals"])
def approve_leave(
    payload: schemas.LeaveApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "hr:leave"):
        raise HTTPException(status_code=403, detail="You do not have leave approval permission.")
    lv = db.get(models.LeaveRequest, payload.leave_id)
    if not lv:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if lv.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Leave request is already {lv.status}.")
    if lv.employee_id == current_user.employeeid:
        raise HTTPException(status_code=403, detail="You cannot approve your own leave request.")
    lv.status = "APPROVED" if payload.action.upper() == "APPROVE" else "REJECTED"
    lv.approved_by = current_user.employeeid
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="LEAVE_APPROVED" if lv.status == "APPROVED" else "LEAVE_REJECTED",
        module="hr",
        entity_type="leave_request",
        entity_id=lv.leave_id,
        details=f"Leave request #{lv.leave_id} {lv.status}. Notes: {payload.notes or ''}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {"leave_id": lv.leave_id, "status": lv.status}


# =====================================================================
