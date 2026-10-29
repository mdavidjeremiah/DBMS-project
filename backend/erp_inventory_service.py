from __future__ import annotations
"""Focused ERP workflow service functions."""

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

def submit_stock_adjustment(
    payload: schemas.StockAdjustmentCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.StockAdjustment:
    """Record a stock adjustment request without changing inventory."""
    product = db.get(models.Product, payload.item_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    adj = models.StockAdjustment(
        warehouse_id=payload.warehouse_id,
        item_id=payload.item_id,
        variance_quantity=payload.variance_quantity,
        reason_code=payload.reason_code,
        requester_id=current_user.employeeid,
        status="PENDING",
        notes=payload.notes,
        created_at=datetime.utcnow(),
    )
    db.add(adj)
    db.flush()
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="STOCK_ADJUSTMENT_SUBMITTED",
        module="inventory",
        entity_type="stock_adjustment",
        entity_id=adj.adjustment_id,
        warehouse_id=payload.warehouse_id,
        details=f"Submitted stock adjustment for '{product.itemname}' by {payload.variance_quantity} ({payload.reason_code}).",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(adj)
    return adj


def approve_or_reject_stock_adjustment(
    adjustment_id: int,
    action: str,
    approver: models.Employee,
    notes: Optional[str],
    db: Session,
    ip_address: Optional[str] = None,
) -> models.StockAdjustment:
    """Approve and post, or reject, a pending stock adjustment."""
    normalized_action = action.upper()
    if normalized_action not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=422, detail="Action must be APPROVE or REJECT.")
    adjustment = db.query(models.StockAdjustment).filter(
        models.StockAdjustment.adjustment_id == adjustment_id
    ).with_for_update().first()
    if not adjustment:
        raise HTTPException(status_code=404, detail="Stock adjustment not found.")
    if adjustment.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Stock adjustment is already {adjustment.status}.")
    if adjustment.requester_id == approver.employeeid:
        raise HTTPException(status_code=403, detail="You cannot decide your own stock adjustment.")

    product = db.get(models.Product, adjustment.item_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    if normalized_action == "APPROVE":
        balance = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == adjustment.item_id,
            models.InventoryBalance.warehouse_id == adjustment.warehouse_id,
        ).with_for_update().first()
        if not balance:
            if adjustment.variance_quantity < 0:
                raise HTTPException(status_code=409, detail="Cannot reduce stock below the available balance.")
            balance = models.InventoryBalance(
                item_id=adjustment.item_id,
                warehouse_id=adjustment.warehouse_id,
                available_stock=Decimal("0"),
                reserved_stock=Decimal("0"),
            )
            db.add(balance)
        if balance.available_stock + adjustment.variance_quantity < 0:
            raise HTTPException(status_code=409, detail="Adjustment would reduce stock below zero.")
        balance.available_stock += adjustment.variance_quantity
        balance.last_updated = datetime.utcnow()
        db.add(models.InventoryMovement(
            item_id=adjustment.item_id,
            warehouse_id=adjustment.warehouse_id,
            movement_type="SHRINKAGE" if adjustment.variance_quantity < 0 else "ADJUSTMENT",
            quantity=adjustment.variance_quantity,
            unit_cost=product.costprice or Decimal("0"),
            reference_type="ADJUSTMENT",
            reference_id=adjustment.adjustment_id,
            performed_by=approver.employeeid,
            notes=f"Adjustment: {adjustment.reason_code} - {adjustment.notes or ''}",
            created_at=datetime.utcnow(),
        ))

        if adjustment.variance_quantity < 0:
            loss_val = abs(adjustment.variance_quantity) * (product.costprice or Decimal("0"))
        else:
            loss_val = Decimal("0")
        if loss_val > 0:
            jrn = models.JournalEntry(
                entry_number=f"JRN-ADJ-{adjustment.adjustment_id}",
                entry_date=datetime.utcnow(),
                description=f"Stock shrinkage: {product.itemname} ({adjustment.reason_code})",
                reference_type="STOCKTAKE",
                reference_id=adjustment.adjustment_id,
                total_amount=loss_val,
                created_by=approver.employeeid,
            )
            db.add(jrn)
            db.flush()

            db.add(models.JournalEntryLine(
                entry_id=jrn.entry_id,
                account_code="5030", # Inventory Shrinkage Expense
                debit=loss_val,
                credit=Decimal("0"),
                description=f"Shrinkage ({adjustment.reason_code})",
            ))
            db.add(models.JournalEntryLine(
                entry_id=jrn.entry_id,
                account_code="1050", # Inventory Asset
                debit=Decimal("0"),
                credit=loss_val,
                description="Inventory Reduction",
            ))
        adjustment.status = "APPROVED"
    else:
        adjustment.status = "REJECTED"

    adjustment.approver_id = approver.employeeid
    adjustment.approved_at = datetime.utcnow()
    db.add(models.AuditLog(
        user_id=approver.employeeid,
        action=f"STOCK_ADJUSTMENT_{adjustment.status}",
        module="inventory",
        entity_type="stock_adjustment",
        entity_id=adjustment.adjustment_id,
        warehouse_id=adjustment.warehouse_id,
        details=f"Stock adjustment #{adjustment.adjustment_id} {adjustment.status.lower()} by {approver.name}. Notes: {notes or ''}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(adjustment)
    return adjustment

# =====================================================================
# 6. Opening Stock Recording
# =====================================================================

def record_opening_stock(
    payload: schemas.OpeningStockCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """Post opening stock balances and matching inventory movements."""
    posted = []
    for item in payload.items:
        warehouse = db.get(models.Warehouse, item.warehouse_id)
        if not warehouse:
            raise HTTPException(404, "Warehouse not found")
        require_warehouse_access(db, current_user, item.warehouse_id, warehouse.branch_id)
        product = db.get(models.Product, item.item_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item.item_id} not found.")

        # Upsert balance
        bal = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == item.item_id,
            models.InventoryBalance.warehouse_id == item.warehouse_id,
        ).first()
        if bal:
            bal.available_stock += item.quantity
            bal.last_updated = datetime.utcnow()
        else:
            bal = models.InventoryBalance(
                item_id=item.item_id,
                warehouse_id=item.warehouse_id,
                available_stock=item.quantity,
                reserved_stock=Decimal("0"),
            )
            db.add(bal)

        db.add(models.InventoryMovement(
            item_id=item.item_id,
            warehouse_id=item.warehouse_id,
            movement_type="OPENING_STOCK",
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            reference_type="OPENING",
            performed_by=current_user.employeeid,
            notes=payload.notes or "Opening stock posting",
            created_at=datetime.utcnow(),
        ))
        posted.append({"item_id": item.item_id, "quantity": float(item.quantity)})

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="OPENING_STOCK_POSTED",
        module="inventory",
        entity_type="opening_stock",
        details=f"Opening stock posted for {len(posted)} products",
        ip_address=ip_address,
    ))
    db.commit()
    return {"posted": posted, "count": len(posted)}


# =====================================================================
# 7. Purchase Requisition Approval
# =====================================================================

def approve_or_reject_requisition(
    requisition_id: int,
    action: str,
    approver: models.Employee,
    notes: Optional[str],
    db: Session,
    ip_address: Optional[str] = None,
) -> models.PurchaseRequisition:
    """Branch manager or procurement manager approves/rejects a requisition."""
    req = db.query(models.PurchaseRequisition).filter_by(id=requisition_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Purchase requisition not found.")
    require_branch_access(db, approver, req.branch_id)
    if action.upper() not in {"APPROVE", "REJECT"}:
        raise HTTPException(422, "Invalid decision")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Requisition is already {req.status}.")
    # Separation of duties: requester cannot approve their own
    if req.requester_id == approver.employeeid:
        raise HTTPException(
            status_code=403,
            detail="Separation of duties violation: You cannot approve your own requisition.",
        )

    req.status = "APPROVED" if action.upper() == "APPROVE" else "REJECTED"
    req.approved_by = approver.employeeid

    db.add(models.AuditLog(
        user_id=approver.employeeid,
        action="PURCHASE_ORDER_APPROVED" if action.upper() == "APPROVE" else "PURCHASE_ORDER_REJECTED",
        module="procurement",
        entity_type="purchase_requisition",
        entity_id=req.requisition_id,
        details=f"Requisition #{requisition_id} {req.status} by approver. Notes: {notes or ''}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(req)
    return req


# =====================================================================
# 8. Purchase Order Approval
# =====================================================================

def approve_or_reject_po(
    po_id: int,
    action: str,
    approver: models.Employee,
    notes: Optional[str],
    db: Session,
    ip_address: Optional[str] = None,
) -> models.PurchaseOrder:
    """Approve or reject a purchase order, respecting ApprovalLimit."""
    po = db.query(models.PurchaseOrder).filter_by(po_id=po_id).with_for_update().first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found.")
    require_branch_access(db, approver, po.branch_id)
    if action.upper() not in {"APPROVE", "REJECT"}:
        raise HTTPException(422, "Invalid decision")
    if po.status != models.POStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"PO is already {po.status.value}.")
    # Separation of duties: creator cannot approve their own PO
    if po.employeeid == approver.employeeid:
        raise HTTPException(
            status_code=403,
            detail="Separation of duties: You cannot approve your own purchase order.",
        )

    # Check ApprovalLimit if approver is a Procurement Officer
    officer = db.get(models.ProcurementOfficer, approver.employeeid)
    if officer and po.total_amount and action.upper() == "APPROVE":
        if po.total_amount > officer.approvallimit:
            raise HTTPException(
                status_code=403,
                detail=f"PO amount UGX {po.total_amount:,.2f} exceeds your approval limit UGX {officer.approvallimit:,.2f}.",
            )

    if action.upper() == "APPROVE":
        po.status = models.POStatus.APPROVED
        po.approved_by = approver.employeeid
        po.approved_at = datetime.utcnow()
    else:
        po.status = models.POStatus.CANCELLED

    db.add(models.AuditLog(
        user_id=approver.employeeid,
        action="PURCHASE_ORDER_APPROVED" if action.upper() == "APPROVE" else "PURCHASE_ORDER_CANCELLED",
        module="procurement",
        entity_type="purchase_order",
        entity_id=po.po_id,
        details=f"PO #{po.po_id} {po.status.value}. Notes: {notes or ''}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(po)
    return po


# =====================================================================
# 9. Customer Credit Payment (Accounts Receivable settlement)
# =====================================================================
