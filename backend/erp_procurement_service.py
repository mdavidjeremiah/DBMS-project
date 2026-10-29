from __future__ import annotations
"""Focused ERP workflow service functions."""

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

def create_goods_received_note(
    payload: schemas.GoodsReceivedNoteCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.GoodsReceivedNote:
    """Receive delivery, increase stock balances, and log movement."""
    if not auth.has_permission(db, current_user, "procurement:grn"):
        raise HTTPException(status_code=403, detail="Goods receipt permission required.")
    po = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.po_id == payload.po_id
    ).with_for_update().first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found.")
    require_branch_access(db, current_user, po.branch_id)
    if po.status not in (models.POStatus.APPROVED, models.POStatus.PARTIALLY_RECEIVED):
        raise HTTPException(status_code=400, detail=f"Cannot receive goods for PO with status {po.status.value}")

    require_warehouse_access(db, current_user, payload.warehouse_id, po.branch_id)
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one received item is required.")

    po_items = {item.item_id: item for item in po.items}
    requested_quantities: Dict[int, Decimal] = {}
    for item in payload.items:
        if item.quantity_received <= 0 or item.item_id not in po_items:
            raise HTTPException(status_code=400, detail="Received items must be positive quantities on the purchase order.")
        requested_quantities[item.item_id] = requested_quantities.get(item.item_id, Decimal("0")) + item.quantity_received
    for item_id, quantity in requested_quantities.items():
        po_item = po_items[item_id]
        remaining = po_item.quantity - (po_item.received_quantity or Decimal("0"))
        if quantity > remaining:
            raise HTTPException(status_code=400, detail=f"Received quantity exceeds the open quantity for item {item_id}.")

    grn_number = payload.grn_number or f"GRN-{po.po_id}-{int(datetime.utcnow().timestamp())}"
    grn = models.GoodsReceivedNote(
        po_id=po.po_id,
        warehouse_id=payload.warehouse_id,
        reference=grn_number,
        branch_id=po.branch_id,
        received_by=current_user.employeeid,
        created_at=datetime.utcnow(),
        status="CONFIRMED",
    )
    db.add(grn)
    db.flush()

    for item in payload.items:
        product = db.get(models.Product, item.item_id)
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.item_id} was not found.")
        po_item = po_items[product.itemid]
        unit_cost = item.unit_cost if item.unit_cost is not None else (product.costprice or Decimal("0"))
        if item.unit_cost is None:
            unit_cost = po_item.unit_price
        if unit_cost != po_item.unit_price:
            raise HTTPException(status_code=409, detail=f"Unit cost does not match the approved PO price for item {item.item_id}.")

        db.add(models.GoodsReceivedNoteItem(
            grn_id=grn.id,
            po_item_id=po_item.id,
            quantity=item.quantity_received,
        ))
        po_item.received_quantity = (po_item.received_quantity or Decimal("0")) + item.quantity_received

        # Update or create InventoryBalance
        bal = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == payload.warehouse_id
        ).with_for_update().first()
        if not bal:
            bal = models.InventoryBalance(
                item_id=product.itemid,
                warehouse_id=payload.warehouse_id,
                available_stock=item.quantity_received,
                reserved_stock=Decimal("0"),
            )
            db.add(bal)
        else:
            bal.available_stock += item.quantity_received
            bal.last_updated = datetime.utcnow()

        # Record movement
        db.add(models.InventoryMovement(
            item_id=product.itemid,
            warehouse_id=payload.warehouse_id,
            movement_type="PURCHASE_IN",
            quantity=item.quantity_received,
            unit_cost=unit_cost,
            reference_type="GRN",
            reference_id=grn.id,
            performed_by=current_user.employeeid,
            notes=f"Received against PO #{po.po_id}",
            created_at=datetime.utcnow(),
        ))

    po.status = (
        models.POStatus.RECEIVED
        if all(item.received_quantity >= item.quantity for item in po.items)
        else models.POStatus.PARTIALLY_RECEIVED
    )
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="GRN_CONFIRMED",
        module="procurement",
        entity_type="goods_received_note",
        entity_id=grn.id,
        reference_number=grn_number,
        warehouse_id=payload.warehouse_id,
        details=f"Goods Received Note #{grn_number} confirmed for PO #{po.po_id}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(grn)
    return grn

def process_supplier_invoice(
    payload: schemas.SupplierInvoiceCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.SupplierInvoice:
    """Record supplier invoice with 3-way match and post AP journal."""
    if not auth.has_permission(db, current_user, "finance:invoice"):
        raise HTTPException(status_code=403, detail="Supplier invoice permission required.")
    if not payload.po_id or not payload.grn_id:
        raise HTTPException(status_code=400, detail="A purchase order and goods receipt are required for invoice matching.")
    po = db.get(models.PurchaseOrder, payload.po_id)
    grn = db.query(models.GoodsReceivedNote).filter_by(id=payload.grn_id).with_for_update().first()
    if not po or not grn:
        raise HTTPException(status_code=404, detail="Purchase order or goods receipt not found.")
    require_branch_access(db, current_user, po.branch_id)
    if po.supplierid != po.supplierid or grn.po_id != po.po_id or grn.status != "CONFIRMED":
        raise HTTPException(status_code=409, detail="Supplier invoice, purchase order, and goods receipt do not match.")
    if db.query(models.SupplierInvoice).filter_by(grn_id=grn.id).first():
        raise HTTPException(409, "This goods receipt already has an invoice")
    if not db.query(models.GoodsReceivedNoteItem).filter_by(grn_id=grn.id).all():
        raise HTTPException(status_code=409, detail="The goods receipt has no received items to match.")
    po_items = {item.item_id: item for item in po.items}
    expected_amount = Decimal("0")
    for received in db.query(models.GoodsReceivedNoteItem).filter_by(grn_id=grn.id).all():
        po_item = po_items.get(db.get(models.PurchaseOrderItem, received.po_item_id).itemid)
        if not po_item:
            raise HTTPException(status_code=409, detail="Goods receipt contains an item absent from the purchase order.")
        expected_amount += received.quantity * po_item.unit_price
    if payload.amount.quantize(Decimal("0.01")) != expected_amount.quantize(Decimal("0.01")):
        raise HTTPException(status_code=409, detail="Invoice amount does not match the received PO quantities and prices.")
    duplicate = db.query(models.SupplierInvoice).filter(
        models.SupplierInvoice.po_id == po.po_id,
        models.SupplierInvoice.invoice_number == payload.invoice_number,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This supplier invoice number has already been recorded.")

    invoice = models.SupplierInvoice(
        po_id=payload.po_id,
        grn_id=payload.grn_id,
        invoice_number=payload.invoice_number,
        amount=payload.amount,
        status="MATCHED",
        branch_id=po.branch_id,
        created_by=current_user.employeeid,
        created_at=datetime.utcnow(),
    )
    db.add(invoice)
    db.flush()

    # Finance General Journal: Debit Inventory Asset, Credit Accounts Payable
    journal = models.JournalEntry(
        entry_number=f"JRN-INV-{invoice.id}",
        entry_date=datetime.utcnow(),
        description=f"Supplier Invoice #{invoice.invoice_number}",
        reference_type="INVOICE",
        reference_id=invoice.id,
        total_amount=payload.amount,
        created_by=current_user.employeeid,
    )
    db.add(journal)
    db.flush()

    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="1050", # Inventory Asset
        debit=payload.amount,
        credit=Decimal("0"),
        description=f"Invoice #{payload.invoice_number} Goods Value",
    ))
    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="2010", # Accounts Payable
        debit=Decimal("0"),
        credit=payload.amount,
        description=f"AP to Supplier #{po.supplierid}",
    ))

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="SUPPLIER_INVOICE_MATCHED",
        module="finance",
        entity_type="supplier_invoice",
        entity_id=invoice.id,
        reference_number=invoice.invoice_number,
        details=f"Supplier invoice #{invoice.invoice_number} matched and recorded: UGX {payload.amount:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(invoice)
    return invoice

def record_supplier_payment(
    payload: schemas.SupplierPaymentCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.SupplierPayment:
    """Disburse supplier payment, reduce AP, and credit Bank."""
    if not auth.has_permission(db, current_user, "finance:payment"):
        raise HTTPException(status_code=403, detail="Supplier payment permission required.")
    invoice = db.query(models.SupplierInvoice).filter(
        models.SupplierInvoice.id == payload.invoice_id
    ).with_for_update().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Supplier invoice not found.")
    if invoice.status not in {"MATCHED", "PARTIAL"}:
        raise HTTPException(409, "Only matched unpaid invoices can be paid")
    if not invoice.po_id:
        raise HTTPException(status_code=409, detail="Supplier invoice is not linked to a purchase order.")
    po = db.get(models.PurchaseOrder, invoice.po_id)
    if not po:
        raise HTTPException(status_code=409, detail="Supplier invoice purchase order no longer exists.")
    require_branch_access(db, current_user, po.branch_id)

    paid_to_date = db.query(func.coalesce(func.sum(models.SupplierPayment.amount), 0)).filter(
        models.SupplierPayment.invoice_id == invoice.id
    ).scalar() or Decimal("0")
    outstanding = invoice.amount - paid_to_date
    if payload.amount <= 0 or payload.amount > outstanding:
        raise HTTPException(status_code=400, detail=f"Payment exceeds the outstanding invoice balance of {outstanding}.")

    payment = models.SupplierPayment(
        invoice_id=invoice.id,
        amount=payload.amount,
        payment_method=payload.payment_method or "BANK",
        paid_by=current_user.employeeid,
        created_at=datetime.utcnow(),
        branch_id=po.branch_id,
    )
    db.add(payment)
    invoice.status = "PAID" if payload.amount == outstanding else "PARTIAL"
    db.flush()

    # Finance Journal: Debit Accounts Payable, Credit Bank Account
    journal = models.JournalEntry(
        entry_number=f"JRN-SPAY-{payment.id}",
        entry_date=datetime.utcnow(),
        description=f"Payment for Supplier Invoice #{invoice.invoice_number}",
        reference_type="PAYMENT",
        reference_id=payment.id,
        total_amount=payload.amount,
        created_by=current_user.employeeid,
    )
    db.add(journal)
    db.flush()

    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="2010", # Accounts Payable
        debit=payload.amount,
        credit=Decimal("0"),
        description=f"Settlement of invoice #{invoice.invoice_number}",
    ))
    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code={"cash":"1010", "bank":"1020", "mobile_money":"1030"}[payload.payment_method], # Tender account
        debit=Decimal("0"),
        credit=payload.amount,
        description="Bank disbursement",
    ))

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="SUPPLIER_PAYMENT_APPROVED",
        module="finance",
        entity_type="supplier_payment",
        entity_id=payment.id,
        reference_number=str(payment.id),
        details=f"Paid supplier invoice #{invoice.invoice_number}: UGX {payload.amount:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(payment)
    return payment

# =====================================================================
# 4. HR & Payroll Workflows
# =====================================================================
