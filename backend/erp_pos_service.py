from __future__ import annotations
"""Focused ERP workflow service functions."""

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

def sale_result(sale, replay=False):
    """Receipt amounts and lines always come from committed sale snapshots."""
    return {
        "saleid":sale.saleid,"totalamount":str(sale.totalamount),
        "subtotal":str(sale.subtotal),"taxamount":str(sale.taxamount),
        "payment_method":sale.paymentmethod,"status":sale.status,
        "idempotent_replay":replay,"items_count":len(sale.sale_items),
        "saledate":sale.saledate.isoformat() if sale.saledate else None,
        "cashiersessionid":sale.cashiersessionid,"branchid":sale.branchid,"warehouseid":sale.warehouseid,
        "items":[{"itemid":line.itemid,"item_name":line.product.itemname if line.product else "Product", "quantity":str(line.quantity),"unitprice":str(line.unitpriceatsale),"line_total":str(line.line_total if line.line_total is not None else line.quantity * line.unitpriceatsale)} for line in sale.sale_items],
    }


def process_pos_sale(
    payload: schemas.SaleCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """Execute an atomic POS sale transaction.

    Enforces:
    - Quantity > 0 validation (Rule 1 & Critical Finding 2)
    - Concurrency-safe stock availability check
    - Active product verification
    - Cashier session verification
    - Credit account validation if credit sale
    - Single transaction creating: Sale, SaleItems, Payment, Inventory Movement,
      Ledger/Journals, and Audit log. Rollback on any failure.
    """
    if not auth.has_permission(db, current_user, "sales:pos"):
        raise HTTPException(status_code=403, detail="POS sales permission required.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one sale item is required")

    # 1. Validate all item quantities are strictly positive
    for item in payload.items:
        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quantity {item.quantity} for item {item.itemid}. Quantity must be strictly greater than zero."
            )

    if not payload.idempotency_key:
        raise HTTPException(400, "An idempotency key is required")
    payload = payload.model_copy(update={"idempotency_key": f"{current_user.employeeid}:" + payload.idempotency_key})
    if len({item.itemid for item in payload.items}) != len(payload.items):
        raise HTTPException(422, "Combine duplicate products into one line")

    # 2. Idempotency Check
    if payload.idempotency_key:
        existing_sale = db.query(models.Sale).filter(
            models.Sale.idempotency_key == payload.idempotency_key
        ).first()
        if existing_sale:
            return sale_result(existing_sale, replay=True)

    # 3. Branch & Warehouse resolution
    branch_id = payload.branchid or current_user.branchid
    if not branch_id:
        branch = db.query(models.Branch).first()
        branch_id = branch.branchid if branch else 1
    require_branch_access(db, current_user, branch_id)

    warehouse_id = payload.warehouseid
    if not warehouse_id:
        wh = db.query(models.Warehouse).filter(models.Warehouse.branch_id == branch_id).first()
        if not wh:
            wh = db.query(models.Warehouse).first()
        if not wh:
            wh = models.Warehouse(branch_id=branch_id, warehouse_name="Main Warehouse", is_active=True)
            db.add(wh)
            db.flush()
        warehouse_id = wh.warehouse_id
    require_warehouse_access(db, current_user, warehouse_id, branch_id)

    # 4. Cashier Session Resolution
    session_id = payload.cashiersessionid
    active_session = None
    if session_id:
        active_session = db.query(models.CashierSession).filter_by(session_id=session_id).with_for_update().populate_existing().first()
    if not active_session:
        active_session = db.query(models.CashierSession).filter(
            models.CashierSession.employee_id == current_user.employeeid,
            models.CashierSession.status == "OPEN"
        ).order_by(models.CashierSession.opened_at.desc()).with_for_update().populate_existing().first()
    if not active_session:
        raise HTTPException(status_code=409, detail="Open a cashier session before completing a sale.")
    if active_session.employee_id != current_user.employeeid:
        raise HTTPException(status_code=403, detail="A sale can only use your own cashier session.")
    if active_session.status != "OPEN":
        raise HTTPException(status_code=409, detail="The cashier session is not open.")
    if active_session.branch_id != branch_id or active_session.warehouse_id not in (None, warehouse_id):
        raise HTTPException(status_code=409, detail="The sale branch and warehouse must match the open cashier session.")

    # 5. Customer & Credit Check
    customer_id = payload.customerid
    if not customer_id and (payload.customername or payload.customerphone):
        new_customer = models.Customer(name=payload.customername or "Walk-in Customer", phone=payload.customerphone)
        db.add(new_customer)
        db.flush()
        customer_id = new_customer.customerid

    payment_method = (payload.payment_method or "CASH").upper()

    # 6. Verify products & check stock availability
    total_amount = Decimal("0")
    total_cogs = Decimal("0")
    prepared_items = []

    for item in sorted(payload.items, key=lambda row: row.itemid):
        product = db.get(models.Product, item.itemid)
        if not product:
            raise HTTPException(status_code=400, detail=f"Product with ID {item.itemid} was not found.")
        if product.unitprice is None or product.unitprice <= 0:
            raise HTTPException(409, "Set a valid selling price before selling this product")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product '{product.itemname}' is inactive and cannot be sold.")

        balance = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == warehouse_id
        ).first()

        if balance is None:
            balance = models.InventoryBalance(
                item_id=product.itemid,
                warehouse_id=warehouse_id,
                available_stock=Decimal("0"),
                reserved_stock=Decimal("0")
            )
            db.add(balance)
            db.flush()

        if balance.available_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock available for '{product.itemname}'. Available: {balance.available_stock}, Requested: {item.quantity}"
            )

        item_total = product.unitprice * item.quantity
        item_cost = (product.costprice or Decimal("0")) * item.quantity
        total_amount += item_total
        total_cogs += item_cost
        prepared_items.append((product, item.quantity, item_total, balance))

    # Credit sale verification
    if payment_method == "CREDIT":
        if not customer_id:
            raise HTTPException(status_code=400, detail="Credit sales require a registered customer.")
        credit_acct = db.query(models.CustomerCreditAccount).filter(
            models.CustomerCreditAccount.customer_id == customer_id
        ).with_for_update().first()
        if not credit_acct:
            raise HTTPException(status_code=400, detail="Customer does not have an approved credit account.")
        if credit_acct.is_blocked:
            raise HTTPException(status_code=400, detail="Customer credit account is blocked.")
        available_credit = credit_acct.credit_limit - credit_acct.current_balance
        if total_amount > available_credit:
            raise HTTPException(
                status_code=400,
                detail=f"Credit limit exceeded. Available credit: UGX {available_credit}, Sale total: UGX {total_amount}"
            )
        credit_acct.current_balance += total_amount

    try:
        # A. Create Sale Header
        sale = models.Sale(
            saledate=datetime.utcnow(),
            totalamount=total_amount,
            subtotal=total_amount,
            discountamount=Decimal("0"),
            taxamount=Decimal("0"),
            status="COMPLETED",
            paymentmethod=payment_method,
            idempotency_key=payload.idempotency_key,
            customerid=customer_id,
            employeeid=current_user.employeeid,
            branchid=branch_id,
            warehouseid=warehouse_id,
            cashiersessionid=active_session.session_id if active_session else None,
        )
        db.add(sale)
        db.flush()

        # B. Create Sale Items and Inventory Movements
        for product, qty, item_tot, balance in prepared_items:
            db.add(models.SaleItem(
                saleid=sale.saleid,
                itemid=product.itemid,
                quantity=qty,
                unitpriceatsale=product.unitprice,
                unitcost=product.costprice or Decimal("0"),
                line_total=item_tot,
            ))

            if balance and warehouse_id:
                changed = db.execute(update(models.InventoryBalance).where(
                    models.InventoryBalance.balance_id == balance.balance_id,
                    models.InventoryBalance.available_stock >= qty,
                ).values(available_stock=models.InventoryBalance.available_stock - qty))
                if changed.rowcount != 1:
                    raise HTTPException(409, "Stock changed; refresh and try again")
                balance.last_updated = datetime.utcnow()

                db.add(models.InventoryMovement(
                    item_id=product.itemid,
                    warehouse_id=warehouse_id,
                    movement_type="SALE_OUT",
                    quantity=-qty,
                    unit_cost=product.costprice or Decimal("0"),
                    reference_type="SALE",
                    reference_id=sale.saleid,
                    performed_by=current_user.employeeid,
                    notes=f"POS Sale #{sale.saleid}",
                    created_at=datetime.utcnow(),
                ))

        # C. Create Payment Record
        db.add(models.Payment(
            sale_id=sale.saleid,
            payment_method=payment_method,
            amount=total_amount,
            reference_number=f"PAY-{sale.saleid}",
            created_at=datetime.utcnow(),
        ))

        # D. Update Cashier Session
        if active_session and payment_method == "CASH":
            active_session.cash_sales = (active_session.cash_sales or Decimal("0")) + total_amount
            active_session.expected_cash = (
                (active_session.opening_float or Decimal("0"))
                + active_session.cash_sales
                - (active_session.cash_refunds or Decimal("0"))
            )

        # E. Create Financial Accounting Entries
        # 1) Legacy LedgerEntry
        db.add(models.LedgerEntry(
            entrydate=datetime.utcnow(),
            sourcetype=models.LedgerSourceType.SALE,
            saleid=sale.saleid,
            amount=total_amount,
            recordedby=current_user.employeeid,
        ))

        # 2) Full Double-Entry General Journal
        journal = models.JournalEntry(
            entry_number=f"JRN-SALE-{sale.saleid}",
            entry_date=datetime.utcnow(),
            description=f"Revenue and COGS for POS Sale #{sale.saleid}",
            reference_type="SALE",
            reference_id=sale.saleid,
            total_amount=total_amount,
            created_by=current_user.employeeid,
        )
        db.add(journal)
        db.flush()

        debit_account = {
            "CASH": "1010",
            "MOBILE_MONEY": "1030",
            "CARD": "1020",
            "CREDIT": "1040",
        }.get(payment_method, "1010")

        # Debit Cash/Bank/AR
        db.add(models.JournalEntryLine(
            entry_id=journal.entry_id,
            account_code=debit_account,
            debit=total_amount,
            credit=Decimal("0"),
            description=f"Received via {payment_method}",
        ))
        # Credit Sales Revenue
        db.add(models.JournalEntryLine(
            entry_id=journal.entry_id,
            account_code="4010",
            debit=Decimal("0"),
            credit=total_amount,
            description="Sales Revenue",
        ))

        # COGS and Inventory Reduction
        if total_cogs > 0:
            db.add(models.JournalEntryLine(
                entry_id=journal.entry_id,
                account_code="5010",
                debit=total_cogs,
                credit=Decimal("0"),
                description="Cost of Goods Sold",
            ))
            db.add(models.JournalEntryLine(
                entry_id=journal.entry_id,
                account_code="1050",
                debit=Decimal("0"),
                credit=total_cogs,
                description="Inventory Asset Reduction",
            ))

        # F. Audit Log
        db.add(models.AuditLog(
            user_id=current_user.employeeid,
            username_or_email=current_user.email or current_user.name,
            action="POS_SALE_COMPLETED",
            module="sales",
            entity_type="sale",
            entity_id=sale.saleid,
            reference_number=str(sale.saleid),
            branch_id=branch_id,
            warehouse_id=warehouse_id,
            details=f"Sale #{sale.saleid} completed ({payment_method}) for UGX {total_amount:,.2f}",
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        ))

        db.commit()
        db.refresh(sale)

        return sale_result(sale, replay=False)
    except IntegrityError:
        db.rollback()
        existing = db.query(models.Sale).filter_by(idempotency_key=payload.idempotency_key).first()
        if existing:
            return sale_result(existing, replay=True)
        raise HTTPException(409, "Conflicting transaction; refresh and retry")
    except Exception:
        db.rollback()
        raise

# =====================================================================
# 2. Cashier Session & Reconciliation Lifecycle
# =====================================================================

def open_cashier_session(
    employee_id: int,
    branch_id: int,
    warehouse_id: Optional[int],
    opening_float: Decimal,
    db: Session,
    ip_address: Optional[str] = None
) -> models.CashierSession:
    """Open a cashier shift till session."""
    user = db.query(models.Employee).filter_by(employeeid=employee_id).with_for_update().first()
    if not user or not auth.has_permission(db, user, "sales:pos"):
        raise HTTPException(status_code=403, detail="Cashier session permission required.")
    require_branch_access(db, user, branch_id)
    if warehouse_id:
        require_warehouse_access(db, user, warehouse_id, branch_id)
    active = db.query(models.CashierSession).filter(
        models.CashierSession.employee_id == employee_id,
        models.CashierSession.status.in_(("OPEN", "PENDING_REVIEW"))
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="An open cashier session already exists for this staff member.")

    session = models.CashierSession(
        employee_id=employee_id,
        branch_id=branch_id,
        warehouse_id=warehouse_id,
        opened_at=datetime.utcnow(),
        opening_float=opening_float,
        cash_sales=Decimal("0"),
        cash_refunds=Decimal("0"),
        expected_cash=opening_float,
        status="OPEN",
    )
    db.add(session)
    db.flush()

    db.add(models.AuditLog(
        user_id=employee_id,
        action="CASHIER_SESSION_OPENED",
        module="sales",
        entity_type="cashier_session",
        entity_id=session.session_id,
        details=f"Opened session #{session.session_id} with float UGX {opening_float:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(session)
    return session

def close_cashier_session(
    session_id: int,
    actual_cash: Decimal,
    closed_by_user: models.Employee,
    db: Session,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """Close cashier session and compute cash variance."""
    session = db.query(models.CashierSession).filter_by(session_id=session_id).with_for_update().populate_existing().first()
    if not session:
        raise HTTPException(status_code=404, detail="Cashier session not found.")
    if (
        session.employee_id != closed_by_user.employeeid
        and not auth.has_permission(db, closed_by_user, "sales:approve")
    ):
        raise HTTPException(status_code=403, detail="You may only close your own cashier session.")
    require_branch_access(db, closed_by_user, session.branch_id)
    if session.status != "OPEN":
        raise HTTPException(status_code=400, detail="This cashier session is already closed.")

    expected = (session.opening_float or Decimal("0")) + (session.cash_sales or Decimal("0")) - (session.cash_refunds or Decimal("0"))
    variance = actual_cash - expected

    session.actual_cash = actual_cash
    session.expected_cash = expected
    session.variance = variance
    session.closed_at = datetime.utcnow()
    session.closed_by = closed_by_user.employeeid
    session.status = "CLOSED" if variance == 0 else "PENDING_REVIEW"

    db.add(models.AuditLog(
        user_id=closed_by_user.employeeid,
        action="CASHIER_SESSION_CLOSED",
        module="sales",
        entity_type="cashier_session",
        entity_id=session.session_id,
        details=f"Closed session #{session.session_id}. Expected: {expected}, Counted: {actual_cash}, Variance: {variance}",
        ip_address=ip_address,
    ))
    db.commit()

    return {
        "session_id": session.session_id,
        "expected_cash": float(expected),
        "actual_cash": float(actual_cash),
        "variance": float(variance),
        "status": session.status,
    }

# =====================================================================
# 3. Procure-to-Pay Lifecycle
# =====================================================================
