from __future__ import annotations
"""Focused ERP workflow service functions."""

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

def record_customer_credit_payment(
    payload: schemas.CustomerCreditPayment,
    current_user: models.Employee,
    db: Session,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Receive customer payment against outstanding credit balance."""
    credit_acct = db.query(models.CustomerCreditAccount).filter(
        models.CustomerCreditAccount.customer_id == payload.customer_id
    ).with_for_update().first()
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

    import uuid
    journal = models.JournalEntry(
        entry_number=f"JRN-CRPAY-{uuid.uuid4().hex}",
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
