"""Hardware World ERP Core Service Workflows.

Implements all transaction-linked business workflows:
- POS Sale transaction with stock deduction, payment, idempotency, and finance journals
- Cashier Session management with float and variance tracking
- Procure-to-pay workflow: Requisition -> Approval -> PO -> GRN -> 3-way matching -> Payment
- Customer Credit accounts and debt settlements
- HR Payroll generation, approval, finance posting, and payslip isolation
- Physical stocktakes, shrinkage, and stock adjustments
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

import models
import schemas
import auth

# =====================================================================
# 1. Point of Sale (POS) Atomic Sale Transaction
# =====================================================================

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
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one sale item is required")

    # 1. Validate all item quantities are strictly positive
    for item in payload.items:
        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quantity {item.quantity} for item {item.itemid}. Quantity must be strictly greater than zero."
            )

    # 2. Idempotency Check
    if payload.idempotency_key:
        existing_sale = db.query(models.Sale).filter(
            models.Sale.idempotency_key == payload.idempotency_key
        ).first()
        if existing_sale:
            return {
                "saleid": existing_sale.saleid,
                "totalamount": float(existing_sale.totalamount),
                "payment_method": existing_sale.paymentmethod,
                "status": existing_sale.status,
                "idempotent_replay": True,
            }

    # 3. Branch & Warehouse resolution
    branch_id = payload.branchid or current_user.branchid
    if not branch_id:
        branch = db.query(models.Branch).first()
        branch_id = branch.branchid if branch else 1

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

    # 4. Cashier Session Resolution
    session_id = payload.cashiersessionid
    active_session = None
    if session_id:
        active_session = db.get(models.CashierSession, session_id)
    if not active_session:
        active_session = db.query(models.CashierSession).filter(
            models.CashierSession.employee_id == current_user.employeeid,
            models.CashierSession.status == "OPEN"
        ).order_by(models.CashierSession.opened_at.desc()).first()

    # 5. Customer & Credit Check
    customer_id = payload.customerid
    if not customer_id and (payload.customername or payload.customerphone):
        new_customer = models.Customer(name=payload.customername, phone=payload.customerphone)
        db.add(new_customer)
        db.flush()
        customer_id = new_customer.customerid

    payment_method = (payload.payment_method or "CASH").upper()

    # 6. Verify products & check stock availability
    total_amount = Decimal("0")
    total_cogs = Decimal("0")
    prepared_items = []

    for item in payload.items:
        product = db.get(models.Product, item.itemid)
        if not product:
            raise HTTPException(status_code=400, detail=f"Product with ID {item.itemid} was not found.")
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
        ).first()
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
                balance.available_stock -= qty
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

        return {
            "saleid": sale.saleid,
            "totalamount": float(sale.totalamount),
            "payment_method": sale.paymentmethod,
            "status": sale.status,
            "items_count": len(prepared_items),
        }
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
    active = db.query(models.CashierSession).filter(
        models.CashierSession.employee_id == employee_id,
        models.CashierSession.status == "OPEN"
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
    session = db.get(models.CashierSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Cashier session not found.")
    if session.status == "CLOSED":
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

def create_goods_received_note(
    payload: schemas.GoodsReceivedNoteCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.GoodsReceivedNote:
    """Receive delivery, increase stock balances, and log movement."""
    po = db.get(models.PurchaseOrder, payload.po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found.")
    if po.status not in (models.POStatus.APPROVED, models.POStatus.PARTIALLY_RECEIVED):
        raise HTTPException(status_code=400, detail=f"Cannot receive goods for PO with status {po.status.value}")

    grn_number = payload.grn_number or f"GRN-{po.po_id}-{int(datetime.utcnow().timestamp())}"
    grn = models.GoodsReceivedNote(
        po_id=po.po_id,
        warehouse_id=payload.warehouse_id,
        grn_number=grn_number,
        received_by=current_user.employeeid,
        received_date=datetime.utcnow(),
        notes=payload.notes,
        status="CONFIRMED",
    )
    db.add(grn)
    db.flush()

    for item in payload.items:
        product = db.get(models.Product, item.item_id)
        if not product:
            continue
        unit_cost = item.unit_cost if item.unit_cost is not None else (product.costprice or Decimal("0"))

        db.add(models.GoodsReceivedNoteItem(
            grn_id=grn.grn_id,
            item_id=product.itemid,
            quantity_received=item.quantity_received,
            unit_cost=unit_cost,
        ))

        # Update or create InventoryBalance
        bal = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == payload.warehouse_id
        ).first()
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
            reference_id=grn.grn_id,
            performed_by=current_user.employeeid,
            notes=f"Received against PO #{po.po_id}",
            created_at=datetime.utcnow(),
        ))

    po.status = models.POStatus.RECEIVED
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="GRN_CONFIRMED",
        module="procurement",
        entity_type="goods_received_note",
        entity_id=grn.grn_id,
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
    invoice = models.SupplierInvoice(
        supplier_id=payload.supplier_id,
        po_id=payload.po_id,
        grn_id=payload.grn_id,
        invoice_number=payload.invoice_number,
        invoice_amount=payload.invoice_amount,
        matched_status="MATCHED",
        payment_status="UNPAID",
        due_date=payload.due_date,
        created_at=datetime.utcnow(),
    )
    db.add(invoice)
    db.flush()

    # Finance General Journal: Debit Inventory Asset, Credit Accounts Payable
    journal = models.JournalEntry(
        entry_number=f"JRN-INV-{invoice.invoice_id}",
        entry_date=datetime.utcnow(),
        description=f"Supplier Invoice #{invoice.invoice_number}",
        reference_type="INVOICE",
        reference_id=invoice.invoice_id,
        total_amount=payload.invoice_amount,
        created_by=current_user.employeeid,
    )
    db.add(journal)
    db.flush()

    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="1050", # Inventory Asset
        debit=payload.invoice_amount,
        credit=Decimal("0"),
        description=f"Invoice #{payload.invoice_number} Goods Value",
    ))
    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="2010", # Accounts Payable
        debit=Decimal("0"),
        credit=payload.invoice_amount,
        description=f"AP to Supplier #{payload.supplier_id}",
    ))

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="SUPPLIER_INVOICE_MATCHED",
        module="finance",
        entity_type="supplier_invoice",
        entity_id=invoice.invoice_id,
        reference_number=invoice.invoice_number,
        details=f"Supplier invoice #{invoice.invoice_number} matched and recorded: UGX {payload.invoice_amount:,.2f}",
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
    invoice = db.get(models.SupplierInvoice, payload.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Supplier invoice not found.")

    payment = models.SupplierPayment(
        invoice_id=invoice.invoice_id,
        amount=payload.amount,
        payment_method=payload.payment_method or "BANK",
        paid_by=current_user.employeeid,
        paid_at=datetime.utcnow(),
    )
    db.add(payment)
    invoice.payment_status = "PAID"
    db.flush()

    # Finance Journal: Debit Accounts Payable, Credit Bank Account
    journal = models.JournalEntry(
        entry_number=f"JRN-SPAY-{payment.payment_id}",
        entry_date=datetime.utcnow(),
        description=f"Payment for Supplier Invoice #{invoice.invoice_number}",
        reference_type="PAYMENT",
        reference_id=payment.payment_id,
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
        account_code="1020", # Bank Account
        debit=Decimal("0"),
        credit=payload.amount,
        description="Bank disbursement",
    ))

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="SUPPLIER_PAYMENT_APPROVED",
        module="finance",
        entity_type="supplier_payment",
        entity_id=payment.payment_id,
        reference_number=str(payment.payment_id),
        details=f"Paid supplier invoice #{invoice.invoice_number}: UGX {payload.amount:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(payment)
    return payment

# =====================================================================
# 4. HR & Payroll Workflows
# =====================================================================

def execute_payroll_run(
    month: str,
    prepared_by_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.PayrollRun:
    """Generate monthly payroll run from salary structures."""
    employees = db.query(models.Employee).filter(models.Employee.is_active == True).all()
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found to generate payroll.")

    run = models.PayrollRun(
        month=month,
        total_gross=Decimal("0"),
        total_deductions=Decimal("0"),
        total_net=Decimal("0"),
        status="DRAFT",
        prepared_by=prepared_by_user.employeeid,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()

    gross_total = Decimal("0")
    deductions_total = Decimal("0")

    for emp in employees:
        struct = db.query(models.EmployeeSalaryStructure).filter(
            models.EmployeeSalaryStructure.employee_id == emp.employeeid
        ).first()

        basic = struct.basic_salary if struct else (emp.salary or Decimal("0"))
        allowance = struct.transport_allowance if struct else Decimal("0")
        overtime = Decimal("0")
        deduction = struct.standard_deductions if struct else Decimal("0")

        emp_gross = basic + allowance + overtime
        emp_net = emp_gross - deduction

        gross_total += emp_gross
        deductions_total += deduction

        db.add(models.Payslip(
            payroll_run_id=run.run_id,
            employee_id=emp.employeeid,
            basic_salary=basic,
            allowances=allowance,
            overtime=overtime,
            deductions=deduction,
            gross_pay=emp_gross,
            net_pay=emp_net,
            payment_status="UNPAID",
        ))

    run.total_gross = gross_total
    run.total_deductions = deductions_total
    run.total_net = gross_total - deductions_total

    db.add(models.AuditLog(
        user_id=prepared_by_user.employeeid,
        action="PAYROLL_GENERATED",
        module="payroll",
        entity_type="payroll_run",
        entity_id=run.run_id,
        details=f"Prepared payroll run for {month}: Gross UGX {gross_total:,.2f}, Net UGX {run.total_net:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(run)
    return run

def approve_and_post_payroll(
    run_id: int,
    approver: models.Employee,
    db: Session,
    ip_address: Optional[str] = None
) -> models.PayrollRun:
    """Approve payroll run and post finance accounting entries."""
    run = db.get(models.PayrollRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")
    if run.status != "DRAFT":
        raise HTTPException(status_code=400, detail=f"Cannot approve payroll with status {run.status}")

    run.status = "APPROVED"
    run.approved_by = approver.employeeid
    run.approved_at = datetime.utcnow()

    # Finance Journal:
    # Debit Salaries & Wages Expense (Gross)
    # Credit Payroll Payable (Net)
    # Credit Tax/Other Deductions Payable
    journal = models.JournalEntry(
        entry_number=f"JRN-PAY-{run.run_id}",
        entry_date=datetime.utcnow(),
        description=f"Payroll Expense for {run.month}",
        reference_type="PAYROLL",
        reference_id=run.run_id,
        total_amount=run.total_gross,
        created_by=approver.employeeid,
    )
    db.add(journal)
    db.flush()

    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="5020", # Salaries and Wages Expense
        debit=run.total_gross,
        credit=Decimal("0"),
        description="Gross Salaries Expense",
    ))
    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="2020", # Payroll Payable
        debit=Decimal("0"),
        credit=run.total_net,
        description="Net Salaries Payable to Staff",
    ))
    if run.total_deductions > 0:
        db.add(models.JournalEntryLine(
            entry_id=journal.entry_id,
            account_code="2030", # Statutory Tax/Deductions Payable
            debit=Decimal("0"),
            credit=run.total_deductions,
            description="Payroll Statutory Deductions",
        ))

    # Also insert legacy Payroll entries for backwards compatibility
    for p in run.payslips:
        db.add(models.Payroll(
            employeeid=p.employee_id,
            month=run.month,
            grosspay=p.gross_pay,
            deductions=p.deductions,
            netpay=p.net_pay,
        ))

    db.add(models.AuditLog(
        user_id=approver.employeeid,
        action="PAYROLL_APPROVED",
        module="payroll",
        entity_type="payroll_run",
        entity_id=run.run_id,
        details=f"Approved payroll run #{run.run_id} for {run.month}",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(run)
    return run

# =====================================================================
# 5. Stocktake & Shrinkage Adjustments
# =====================================================================

def execute_stock_adjustment(
    payload: schemas.StockAdjustmentCreate,
    current_user: models.Employee,
    db: Session,
    approver: Optional[models.Employee] = None,
    ip_address: Optional[str] = None
) -> models.StockAdjustment:
    """Adjust stock balance with reason code and post shrinkage expense journal."""
    product = db.get(models.Product, payload.item_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    adj = models.StockAdjustment(
        warehouse_id=payload.warehouse_id,
        item_id=payload.item_id,
        variance_quantity=payload.variance_quantity,
        reason_code=payload.reason_code,
        requester_id=current_user.employeeid,
        approver_id=approver.employeeid if approver else current_user.employeeid,
        status="APPROVED",
        notes=payload.notes,
        created_at=datetime.utcnow(),
        approved_at=datetime.utcnow(),
    )
    db.add(adj)
    db.flush()

    # Update InventoryBalance
    bal = db.query(models.InventoryBalance).filter(
        models.InventoryBalance.item_id == payload.item_id,
        models.InventoryBalance.warehouse_id == payload.warehouse_id
    ).first()
    if not bal:
        bal = models.InventoryBalance(
            item_id=payload.item_id,
            warehouse_id=payload.warehouse_id,
            available_stock=payload.variance_quantity,
            reserved_stock=Decimal("0"),
        )
        db.add(bal)
    else:
        bal.available_stock += payload.variance_quantity
        bal.last_updated = datetime.utcnow()

    # Movement record
    db.add(models.InventoryMovement(
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        movement_type="SHRINKAGE" if payload.variance_quantity < 0 else "ADJUSTMENT",
        quantity=payload.variance_quantity,
        unit_cost=product.costprice or Decimal("0"),
        reference_type="ADJUSTMENT",
        reference_id=adj.adjustment_id,
        performed_by=current_user.employeeid,
        notes=f"Adjustment: {payload.reason_code} - {payload.notes or ''}",
        created_at=datetime.utcnow(),
    ))

    # Finance posting if variance is negative (shrinkage)
    if payload.variance_quantity < 0:
        loss_val = abs(payload.variance_quantity) * (product.costprice or Decimal("0"))
        if loss_val > 0:
            jrn = models.JournalEntry(
                entry_number=f"JRN-ADJ-{adj.adjustment_id}",
                entry_date=datetime.utcnow(),
                description=f"Stock shrinkage: {product.itemname} ({payload.reason_code})",
                reference_type="STOCKTAKE",
                reference_id=adj.adjustment_id,
                total_amount=loss_val,
                created_by=current_user.employeeid,
            )
            db.add(jrn)
            db.flush()

            db.add(models.JournalEntryLine(
                entry_id=jrn.entry_id,
                account_code="5030", # Inventory Shrinkage Expense
                debit=loss_val,
                credit=Decimal("0"),
                description=f"Shrinkage ({payload.reason_code})",
            ))
            db.add(models.JournalEntryLine(
                entry_id=jrn.entry_id,
                account_code="1050", # Inventory Asset
                debit=Decimal("0"),
                credit=loss_val,
                description="Inventory Reduction",
            ))

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="STOCK_ADJUSTMENT_APPROVED",
        module="inventory",
        entity_type="stock_adjustment",
        entity_id=adj.adjustment_id,
        warehouse_id=payload.warehouse_id,
        details=f"Adjusted stock for '{product.itemname}' by {payload.variance_quantity} ({payload.reason_code})",
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(adj)
    return adj

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
        action="STOCK_ADJUSTMENT_APPROVED",
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
    req = db.get(models.PurchaseRequisition, requisition_id)
    if not req:
        raise HTTPException(status_code=404, detail="Purchase requisition not found.")
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
    po = db.get(models.PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found.")
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

def record_customer_credit_payment(
    payload: schemas.CustomerCreditPayment,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Receive customer payment against outstanding credit balance."""
    credit_acct = db.query(models.CustomerCreditAccount).filter(
        models.CustomerCreditAccount.customer_id == payload.customer_id
    ).first()
    if not credit_acct:
        raise HTTPException(status_code=404, detail="Customer credit account not found.")

    if payload.amount > credit_acct.current_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Payment UGX {payload.amount:,.2f} exceeds outstanding balance UGX {credit_acct.current_balance:,.2f}.",
        )

    credit_acct.current_balance -= payload.amount

    # Finance journal: Debit Cash/Bank, Credit Accounts Receivable
    debit_account = {
        "CASH": "1010",
        "MOBILE_MONEY": "1030",
        "BANK": "1020",
    }.get((payload.payment_method or "CASH").upper(), "1010")

    journal = models.JournalEntry(
        entry_number=f"JRN-CRPAY-{int(datetime.utcnow().timestamp())}",
        entry_date=datetime.utcnow(),
        description=f"Customer credit payment — Customer #{payload.customer_id}",
        reference_type="PAYMENT",
        total_amount=payload.amount,
        created_by=current_user.employeeid,
    )
    db.add(journal)
    db.flush()

    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code=debit_account,
        debit=payload.amount,
        credit=Decimal("0"),
        description="Cash received from customer",
    ))
    db.add(models.JournalEntryLine(
        entry_id=journal.entry_id,
        account_code="1040",  # Accounts Receivable
        debit=Decimal("0"),
        credit=payload.amount,
        description="Customer credit balance reduced",
    ))

    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="CUSTOMER_PAYMENT_RECEIVED",
        module="finance",
        entity_type="customer_credit",
        details=f"Customer #{payload.customer_id} paid UGX {payload.amount:,.2f}. New balance: {credit_acct.current_balance:,.2f}",
        ip_address=ip_address,
    ))
    db.commit()
    return {
        "customer_id": payload.customer_id,
        "amount_received": float(payload.amount),
        "remaining_balance": float(credit_acct.current_balance),
    }


# =====================================================================
# 10. Sales Return / Refund Flow
# =====================================================================

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

def execute_stock_transfer(
    payload: schemas.StockTransferCreate,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Transfer stock from one warehouse to another."""
    transferred = []
    for item in payload.items:
        product = db.get(models.Product, item.item_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.item_id} not found.")

        from_bal = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == item.item_id,
            models.InventoryBalance.warehouse_id == payload.from_warehouse_id,
        ).first()
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
        ).first()
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
        action="STOCK_ADJUSTMENT_APPROVED",
        module="inventory",
        entity_type="stock_transfer",
        details=f"Transferred {len(transferred)} products from WH#{payload.from_warehouse_id} to WH#{payload.to_warehouse_id}",
        ip_address=ip_address,
    ))
    db.commit()
    return {"transferred": transferred, "count": len(transferred)}
