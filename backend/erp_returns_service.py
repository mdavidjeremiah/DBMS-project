"""Focused ERP workflow service functions."""

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

def process_sales_return(
    payload: schemas.SalesReturnFullCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Process a sales return: reverse inventory and post refund journal."""
    sale = db.get(models.Sale, payload.sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found.")
    if sale.status not in ("COMPLETED",):
        raise HTTPException(status_code=400, detail="Only COMPLETED sales can have returns.")

    total_refund = Decimal("0")

    # Create return header
    sales_return = models.SalesReturn(
        sale_id=payload.sale_id,
        reason=payload.reason,
        status="APPROVED",
        requester_id=current_user.employeeid,
        created_at=datetime.utcnow(),
    )
    db.add(sales_return)
    db.flush()

    for item in payload.items:
        product = db.get(models.Product, item.item_id)
        if not product:
            continue

        # Find original sale item to get sell price
        original_item = db.query(models.SaleItem).filter(
            models.SaleItem.saleid == payload.sale_id,
            models.SaleItem.itemid == item.item_id,
        ).first()
        unit_price = original_item.unitpriceatsale if original_item else product.unitprice
        unit_cost = original_item.unitcost if original_item else (product.costprice or Decimal("0"))
        line_refund = unit_price * item.quantity
        total_refund += line_refund

        # Return to stock only if condition is GOOD
        if item.condition == "GOOD" and sale.warehouseid:
            bal = db.query(models.InventoryBalance).filter(
                models.InventoryBalance.item_id == item.item_id,
                models.InventoryBalance.warehouse_id == sale.warehouseid,
            ).first()
            if bal:
                bal.available_stock += item.quantity
                bal.last_updated = datetime.utcnow()

            db.add(models.InventoryMovement(
                item_id=item.item_id,
                warehouse_id=sale.warehouseid,
                movement_type="RETURN_IN",
                quantity=item.quantity,
                unit_cost=unit_cost,
                reference_type="RETURN",
                reference_id=sales_return.return_id,
                performed_by=current_user.employeeid,
                notes=f"Return from Sale #{payload.sale_id}: {payload.reason}",
                created_at=datetime.utcnow(),
            ))

    sales_return.total_refund_amount = total_refund

    # Finance journal: Debit Sales Revenue, Credit Cash
    refund_account = {
        "CASH": "1010",
        "MOBILE_MONEY": "1030",
        "STORE_CREDIT": "1040",
    }.get((payload.refund_method or "CASH").upper(), "1010")

    journal = models.JournalEntry(
        entry_number=f"JRN-RET-{sales_return.return_id}",
        entry_date=datetime.utcnow(),
        description=f"Sales Return for Sale #{payload.sale_id}",
        reference_type="RETURN",
        reference_id=sales_return.return_id,
        total_amount=total_refund,
        created_by=current_user.employeeid,
    )
    db.add(journal)
    db.flush()

    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="4010",  # Sales Revenue (reversed)
        debit=total_refund,
        credit=Decimal("0"),
        description="Sales revenue reversed on return",
    ))
    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code=refund_account,
        debit=Decimal("0"),
        credit=total_refund,
        description="Refund paid to customer",
    ))

    # Update cashier session if open
    if sale.cashiersessionid:
        session = db.get(models.CashierSession, sale.cashiersessionid)
        if session and session.status == "OPEN":
            session.cash_refunds = (session.cash_refunds or Decimal("0")) + total_refund
            session.expected_cash = (
                (session.opening_float or Decimal("0"))
                + (session.cash_sales or Decimal("0"))
                - session.cash_refunds
            )

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="RETURN_COMPLETED",
        module="sales",
        entity_type="sales_return",
        entity_id=sales_return.return_id,
        branch_id=sale.branchid,
        warehouse_id=sale.warehouseid,
        details=f"Return #{sales_return.return_id} processed for Sale #{payload.sale_id}. Refund: UGX {total_refund:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    return {
        "return_id": sales_return.return_id,
        "sale_id": payload.sale_id,
        "total_refund": float(total_refund),
        "status": sales_return.status,
    }


# =====================================================================
# 11. Stock Transfer Between Warehouses
# =====================================================================
