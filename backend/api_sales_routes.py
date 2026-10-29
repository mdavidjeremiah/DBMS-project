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
# /api/cashier-sessions
# =====================================================================

@router.post("/cashier-sessions/open", tags=["Sales & POS"])
def open_session(
    payload: schemas.CashierSessionCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:pos"):
        raise HTTPException(status_code=403, detail="Cashier session permission required.")
    # Use branch/warehouse from payload if supplied; fall back to user's assigned branch
    branch_id = payload.branch_id or current_user.branchid
    if not branch_id:
        raise HTTPException(status_code=422, detail="Your account must be assigned to a branch before opening a cashier session.")
    warehouse_id = payload.warehouse_id
    session = erp_service.open_cashier_session(
        employee_id=current_user.employeeid,
        branch_id=branch_id,
        warehouse_id=warehouse_id,
        opening_float=payload.opening_float,
        db=db,
        ip_address=request_ip(request),
    )
    return {
        "session_id": session.session_id,
        "status": session.status,
        "opened_at": session.opened_at,
        "opening_float": float(session.opening_float),
        "branch_id": session.branch_id,
        "warehouse_id": session.warehouse_id,
    }

@router.post("/cashier-sessions/{session_id}/close", tags=["Sales & POS"])
def close_session(
    session_id: int,
    payload: schemas.CashierSessionClose,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:pos") and not auth.has_permission(db, current_user, "sales:approve"):
        raise HTTPException(status_code=403, detail="Cashier session permission required.")
    return erp_service.close_cashier_session(
        session_id=session_id,
        actual_cash=payload.actual_cash,
        closed_by_user=current_user,
        db=db,
        notes=payload.notes,
        ip_address=request_ip(request),
    )

@router.get("/cashier-sessions/current", tags=["Sales & POS"])
def get_current_cashier_session(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(models.CashierSession).filter(
        models.CashierSession.employee_id == current_user.employeeid,
        models.CashierSession.status == "OPEN"
    ).order_by(models.CashierSession.opened_at.desc()).first()

    if not session:
        return {"has_active_session": False}

    return {
        "has_active_session": True,
        "session_id": session.session_id,
        "branch_id": session.branch_id,
        "warehouse_id": session.warehouse_id,
        "opened_at": session.opened_at,
        "opening_float": float(session.opening_float or 0),
        "cash_sales": float(session.cash_sales or 0),
        "expected_cash": float(session.expected_cash or 0),
        "status": session.status,
    }

# =====================================================================
# /api/sales & /api/payments
# =====================================================================

@router.get("/sales", tags=["Sales & POS"])
def get_api_sales(
    branch_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:view"):
        raise HTTPException(status_code=403, detail="Sales view permission required.")
    q = scope_sales_query(db, current_user, db.query(models.Sale), branch_id)

    sales = q.order_by(models.Sale.saledate.desc()).limit(limit).all()
    branch_ids = {sale.branchid for sale in sales if sale.branchid is not None}
    branch_names = {
        branch.branchid: branch.branchname
        for branch in db.query(models.Branch).filter(models.Branch.branchid.in_(branch_ids)).all()
    } if branch_ids else {}
    res = []
    for s in sales:
        cashier = db.get(models.Employee, s.employeeid)
        customer = db.get(models.Customer, s.customerid) if s.customerid else None
        res.append({
            "saleid": s.saleid,
            "saledate": s.saledate,
            "totalamount": float(s.totalamount or 0),
            "status": s.status,
            "payment_method": s.paymentmethod,
            "customer_name": customer.name if customer else "Walk-in Customer",
            "cashier_name": cashier.name if cashier else "Unknown Cashier",
            "branch_name": branch_names.get(s.branchid, "Unknown"),
            "items": [
                {
                    "itemid": i.itemid,
                    "item_name": i.product.itemname if i.product else "Unknown",
                    "quantity": float(i.quantity),
                    "unitpriceatsale": float(i.unitpriceatsale),
                    "line_total": float(i.line_total or (i.quantity * i.unitpriceatsale)),
                }
                for i in s.sale_items
            ],
        })
    return res

@router.post("/sales", tags=["Sales & POS"])
def create_api_sale(
    payload: schemas.SaleCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Atomic POS Sale creation with full validation and linked records."""
    if not auth.has_permission(db, current_user, "sales:pos"):
        raise HTTPException(status_code=403, detail="POS sales permission required.")
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key

    return erp_service.process_pos_sale(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request)
    )

# =====================================================================
# =====================================================================
# /api/returns (Sales Returns)
# =====================================================================

@router.post("/returns", tags=["Sales & POS"])
def create_sales_return(
    payload: schemas.SalesReturnFullCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:refund"):
        raise HTTPException(status_code=403, detail="Sales refund permission required.")
    return erp_service.process_sales_return(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request),
    )


@router.get("/returns", tags=["Sales & POS"])
def get_sales_returns(
    sale_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:view"):
        raise HTTPException(status_code=403, detail="Sales view permission required.")
    q = db.query(models.SalesReturn)
    if sale_id:
        q = q.filter(models.SalesReturn.sale_id == sale_id)
    returns = q.order_by(models.SalesReturn.created_at.desc()).limit(50).all()
    return [
        {
            "return_id": r.return_id,
            "sale_id": r.sale_id,
            "reason": r.reason,
            "status": r.status,
            "total_refund_amount": float(r.total_refund_amount or 0),
            "created_at": r.created_at,
        }
        for r in returns
    ]


# =====================================================================
# /api/customers (Customer Management)
# =====================================================================

@router.get("/customers", tags=["Sales & POS"])
def get_customers(
    search: Optional[str] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:view"):
        raise HTTPException(status_code=403, detail="Sales view permission required.")
    q = db.query(models.Customer)
    if search:
        q = q.filter(
            or_(
                models.Customer.name.ilike(f"%{search}%"),
                models.Customer.phone.ilike(f"%{search}%"),
            )
        )
    customers = q.order_by(models.Customer.name).limit(100).all()
    result = []
    for c in customers:
        credit = c.credit_account
        result.append({
            "customerid": c.customerid,
            "name": c.name,
            "phone": c.phone if auth.has_permission(db, current_user, "sales:pos") else None,
            "credit_limit": float(credit.credit_limit) if credit and auth.has_permission(db, current_user, "sales:credit") else None,
            "outstanding_balance": float(credit.current_balance) if credit and auth.has_permission(db, current_user, "sales:credit") else None,
            "is_blocked": credit.is_blocked if credit and auth.has_permission(db, current_user, "sales:credit") else None,
        })
    return result


@router.post("/customers", tags=["Sales & POS"])
def create_customer(
    payload: schemas.CustomerCreate,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:pos"):
        raise HTTPException(status_code=403, detail="Sales permission required.")
    existing = db.query(models.Customer).filter(models.Customer.phone == payload.phone).first() if payload.phone else None
    if existing:
        return {"customerid": existing.customerid, "name": existing.name, "existed": True}
    customer = models.Customer(name=payload.name, phone=payload.phone)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"customerid": customer.customerid, "name": customer.name, "existed": False}


@router.post("/customers/credit-account", tags=["Sales & POS"])
def create_customer_credit_account(
    payload: schemas.CustomerCreditAccountCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:credit"):
        raise HTTPException(status_code=403, detail="Credit sales permission required.")
    existing = db.query(models.CustomerCreditAccount).filter(
        models.CustomerCreditAccount.customer_id == payload.customer_id
    ).first()
    if existing:
        existing.credit_limit = payload.credit_limit
        db.commit()
        return {"account_id": existing.account_id, "credit_limit": float(existing.credit_limit)}
    acct = models.CustomerCreditAccount(
        customer_id=payload.customer_id,
        credit_limit=payload.credit_limit,
        current_balance=Decimal("0"),
        is_blocked=False,
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return {"account_id": acct.account_id, "credit_limit": float(acct.credit_limit)}


@router.post("/customers/credit-payment", tags=["Sales & POS"])
def record_customer_payment(
    payload: schemas.CustomerCreditPayment,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "finance:payment"):
        raise HTTPException(status_code=403, detail="Finance payment permission required.")
    return erp_service.record_customer_credit_payment(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request),
    )
