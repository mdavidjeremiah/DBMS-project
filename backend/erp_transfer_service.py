from __future__ import annotations
"""Focused ERP workflow service functions."""

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

def execute_stock_transfer(
    payload: schemas.StockTransferCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Transfer stock from one warehouse to another."""
    if payload.from_warehouse_id == payload.to_warehouse_id:
        raise HTTPException(422, "Choose different source and destination warehouses")
    for warehouse_id in (payload.from_warehouse_id, payload.to_warehouse_id):
        warehouse = db.get(models.Warehouse, warehouse_id)
        if not warehouse:
            raise HTTPException(404, "Warehouse not found")
        require_warehouse_access(db, current_user, warehouse_id, warehouse.branch_id)
    if not payload.items:
        raise HTTPException(422, "At least one transfer item is required")
    transferred = []
    for item in payload.items:
        product = db.get(models.Product, item.item_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.item_id} not found.")

        from_bal = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == item.item_id,
            models.InventoryBalance.warehouse_id == payload.from_warehouse_id,
        ).with_for_update().first()
        if not from_bal or from_bal.available_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{product.itemname}' in source warehouse.",
            )

        from_bal.available_stock -= item.quantity
        from_bal.last_updated = datetime.utcnow()

        to_bal = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == item.item_id,
            models.InventoryBalance.warehouse_id == payload.to_warehouse_id,
        ).with_for_update().first()
        if to_bal:
            to_bal.available_stock += item.quantity
            to_bal.last_updated = datetime.utcnow()
        else:
            to_bal = models.InventoryBalance(
                item_id=item.item_id,
                warehouse_id=payload.to_warehouse_id,
                available_stock=item.quantity,
                reserved_stock=Decimal("0"),
            )
            db.add(to_bal)

        unit_cost = product.costprice or Decimal("0")
        ts = datetime.utcnow()
        db.add(models.InventoryMovement(
            item_id=item.item_id,
            warehouse_id=payload.from_warehouse_id,
            movement_type="TRANSFER_OUT",
            quantity=-item.quantity,
            unit_cost=unit_cost,
            reference_type="TRANSFER",
            performed_by=current_user.employeeid,
            notes=payload.notes,
            created_at=ts,
        ))
        db.add(models.InventoryMovement(
            item_id=item.item_id,
            warehouse_id=payload.to_warehouse_id,
            movement_type="TRANSFER_IN",
            quantity=item.quantity,
            unit_cost=unit_cost,
            reference_type="TRANSFER",
            performed_by=current_user.employeeid,
            notes=payload.notes,
            created_at=ts,
        ))
        transferred.append({"item_id": item.item_id, "quantity": float(item.quantity)})

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="STOCK_TRANSFERRED",
        module="inventory",
        entity_type="stock_transfer",
        details=f"Transferred {len(transferred)} products from WH#{payload.from_warehouse_id} to WH#{payload.to_warehouse_id}",
        ip_address=ip_address,
    ))
    db.commit()
    return {"transferred": transferred, "count": len(transferred)}
