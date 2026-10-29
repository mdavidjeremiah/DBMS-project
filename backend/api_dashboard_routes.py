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
# /api/dashboard (Specialized for all 6 Department Dashboards)
# =====================================================================

@router.get("/dashboard", tags=["Dashboards"])
def get_department_dashboard(
    branch_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    date_filter: Optional[str] = "today", # today, week, month
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Aggregate live operational data structured for the 6 departmental dashboards."""
    active_branch_id = branch_id or current_user.branchid or 1
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Date range filter
    if date_filter == "week":
        filter_start = today_start - timedelta(days=7)
    elif date_filter == "month":
        filter_start = today_start - timedelta(days=30)
    else:
        filter_start = today_start

    # Common metrics
    sales_q = db.query(models.Sale).filter(models.Sale.status == "COMPLETED")
    if branch_id:
        sales_q = sales_q.filter(models.Sale.branchid == active_branch_id)

    sales_today = sales_q.filter(models.Sale.saledate >= filter_start).all()
    today_revenue = sum([Decimal(str(s.totalamount or 0)) for s in sales_today], Decimal("0"))
    today_tx_count = len(sales_today)

    # COGS & Gross profit
    cogs_today = Decimal("0")
    for s in sales_today:
        for itm in s.sale_items:
            cogs_today += (itm.unitcost or Decimal("0")) * itm.quantity
    gross_profit = today_revenue - cogs_today
    gross_margin = float((gross_profit / today_revenue * 100)) if today_revenue > 0 else 0.0

    # Low stock & out of stock
    balances = db.query(models.InventoryBalance).all()
    out_of_stock_count = 0
    low_stock_count = 0
    total_inventory_val = Decimal("0")
    for b in balances:
        reorder = b.product.reorderlevel or 0
        avail = b.available_stock or Decimal("0")
        cost = b.product.costprice or Decimal("0")
        total_inventory_val += avail * cost
        if avail <= 0:
            out_of_stock_count += 1
        elif avail <= reorder:
            low_stock_count += 1

    # 1. Sales & POS Dashboard
    active_session = db.query(models.CashierSession).filter(
        models.CashierSession.employee_id == current_user.employeeid,
        models.CashierSession.status == "OPEN"
    ).first()

    sales_dashboard = {
        "today_revenue": float(today_revenue),
        "target_progress": min(100.0, float(today_revenue / Decimal("5000000") * 100)) if today_revenue > 0 else 0.0,
        "transaction_count": today_tx_count,
        "average_basket": float(today_revenue / today_tx_count) if today_tx_count > 0 else 0.0,
        "cashier_session": {
            "is_open": active_session is not None,
            "session_id": active_session.session_id if active_session else None,
            "opened_at": active_session.opened_at if active_session else None,
            "opening_float": float(active_session.opening_float) if active_session else 0.0,
            "expected_cash": float(active_session.expected_cash) if active_session else 0.0,
        },
        "recent_sales": [
            {
                "saleid": s.saleid,
                "saledate": s.saledate,
                "totalamount": float(s.totalamount or 0),
                "customer": s.customer.name if s.customer else "Walk-in",
                "payment_method": s.paymentmethod,
            }
            for s in sales_today[:8]
        ],
    }

    # 2. Procurement & Inventory Dashboard
    pending_pos = db.query(func.count()).select_from(models.PurchaseOrder).filter(
        models.PurchaseOrder.status == models.POStatus.PENDING
    ).scalar() or 0
    pending_reqs = db.query(func.count()).select_from(models.PurchaseRequisition).filter(
        models.PurchaseRequisition.status == "PENDING"
    ).scalar() or 0

    procurement_dashboard = {
        "inventory_health": {
            "out_of_stock_count": out_of_stock_count,
            "low_stock_count": low_stock_count,
            "total_inventory_value": float(total_inventory_val),
            "pending_requisitions": pending_reqs,
            "pending_pos": pending_pos,
        },
        "critical_items": [
            {
                "item_id": b.item_id,
                "item_name": b.product.itemname if b.product else "Unknown",
                "available_stock": float(b.available_stock),
                "reorder_level": b.product.reorderlevel or 0,
                "warehouse_name": b.warehouse.warehouse_name if b.warehouse else "Unknown",
            }
            for b in balances if (b.available_stock or 0) <= (b.product.reorderlevel or 0)
        ][:10],
    }

    # 3. Human Resources Dashboard
    staff_count = db.query(func.count()).select_from(models.Employee).filter(
        models.Employee.is_active == True
    ).scalar() or 0
    pending_leaves = db.query(func.count()).select_from(models.LeaveRequest).filter(
        models.LeaveRequest.status == "PENDING"
    ).scalar() or 0
    latest_payroll_run = db.query(models.PayrollRun).order_by(models.PayrollRun.created_at.desc()).first()

    hr_dashboard = {
        "workforce_today": {
            "active_headcount": staff_count,
            "present_count": staff_count, # baseline
            "on_leave_count": 0,
            "pending_leave_requests": pending_leaves,
        },
        "payroll_cycle": {
            "month": latest_payroll_run.month if latest_payroll_run else "2026-09",
            "status": latest_payroll_run.status if latest_payroll_run else "READY_FOR_RUN",
            "total_gross": float(latest_payroll_run.total_gross) if latest_payroll_run else 0.0,
            "total_net": float(latest_payroll_run.total_net) if latest_payroll_run else 0.0,
        }
    }

    # 4. Finance & Accounting Dashboard
    fin_accts = db.query(models.FinancialAccount).all()
    cash_pos = sum([a.balance for a in fin_accts], Decimal("0"))
    ar_total = db.query(func.sum(models.CustomerCreditAccount.current_balance)).scalar() or Decimal("0")
    invoice_table = Table("supplier_invoices", MetaData(), autoload_with=db.get_bind())
    payment_table = Table("supplier_payments", MetaData(), autoload_with=db.get_bind())
    invoice_amount = invoice_table.c.get("amount")
    if invoice_amount is None:
        invoice_amount = invoice_table.c.get("invoice_amount")
    if invoice_amount is None:
        raise RuntimeError("Supplier invoices table has no recognized amount column.")
    payment_amount = payment_table.c.get("amount")
    if payment_amount is None:
        raise RuntimeError("Supplier payments table has no amount column.")
    invoice_total = db.query(func.coalesce(func.sum(invoice_amount), 0)).select_from(invoice_table).scalar() or Decimal("0")
    payment_total = db.query(func.coalesce(func.sum(payment_amount), 0)).select_from(payment_table).scalar() or Decimal("0")
    unpaid_ap = max(Decimal("0"), invoice_total - payment_total)

    finance_dashboard = {
        "cash_position": {
            "total_cash": float(cash_pos),
            "accounts": [{"name": a.account_name, "type": a.account_type, "balance": float(a.balance)} for a in fin_accts],
        },
        "receivables_total": float(ar_total),
        "payables_total": float(unpaid_ap),
        "today_revenue": float(today_revenue),
        "gross_profit": float(gross_profit),
        "gross_margin": gross_margin,
    }

    # 5. Operations & Branch Management Dashboard
    branch_rankings = []
    for br in db.query(models.Branch).all():
        b_rev = db.query(func.sum(models.Sale.totalamount)).filter(
            models.Sale.branchid == br.branchid,
            models.Sale.status == "COMPLETED"
        ).scalar() or Decimal("0")
        branch_rankings.append({
            "branchid": br.branchid,
            "branchname": br.branchname,
            "total_revenue": float(b_rev),
        })

    operations_dashboard = {
        "business_health": {
            "total_revenue": float(today_revenue),
            "gross_profit": float(gross_profit),
            "gross_margin": gross_margin,
            "cash_position": float(cash_pos),
        },
        "branch_rankings": branch_rankings,
        "risks": {
            "out_of_stock_count": out_of_stock_count,
            "pending_approvals": pending_reqs + pending_pos,
            "overdue_debt": float(ar_total),
        }
    }

    # 6. System Administrator Dashboard
    now = datetime.utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    temporary_password_cutoff = now + timedelta(hours=24)
    active_accounts = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        models.Employee.hashed_password.isnot(None),
    )
    pending_setup = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        models.Employee.hashed_password.is_(None),
    )
    expiring_passwords = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        models.Employee.must_change_password == True,
        models.Employee.temporary_password_expires_at.isnot(None),
        models.Employee.temporary_password_expires_at <= temporary_password_cutoff,
    ).order_by(models.Employee.temporary_password_expires_at.asc())
    locked_accounts = db.query(models.Employee).filter(
        models.Employee.is_active == True,
        models.Employee.locked_until > now,
    ).order_by(models.Employee.locked_until.asc())
    login_failures_today = db.query(models.AuditLog).filter(
        models.AuditLog.action.in_(("FAILED_LOGIN", "LOGIN_FAILED")),
        models.AuditLog.timestamp >= day_start,
    )
    failed_logins = login_failures_today.count()
    accounts_affected_today = login_failures_today.with_entities(
        func.count(func.distinct(models.AuditLog.username_or_email))
    ).scalar() or 0
    privilege_changes = db.query(func.count()).select_from(models.AuditLog).filter(
        models.AuditLog.action.in_((
            "ROLE_ASSIGNED", "ROLE_REMOVED", "DEPARTMENT_ASSIGNED",
            "BRANCH_SCOPE_CHANGED", "WAREHOUSE_SCOPE_CHANGED",
        )),
        models.AuditLog.timestamp >= week_start,
    ).scalar() or 0
    suspicious_ips = db.query(models.AuditLog.ip_address).filter(
        models.AuditLog.action.in_(("FAILED_LOGIN", "LOGIN_FAILED")),
        models.AuditLog.timestamp >= day_start,
        models.AuditLog.ip_address.isnot(None),
    ).group_by(models.AuditLog.ip_address).having(func.count() >= 3).count()

    action_queue = []
    for employee in pending_setup.order_by(models.Employee.name.asc()).limit(5).all():
        action_queue.append({
            "action": "Create account",
            "employee": employee.name,
            "details": employee.department.departmentname if employee.department else "Department not assigned",
            "href": "employees.html",
        })
    for employee in expiring_passwords.limit(5).all():
        expires = employee.temporary_password_expires_at
        action_queue.append({
            "action": "Temporary password expired" if expires <= now else "Temporary password expiring",
            "employee": employee.name,
            "details": f"{employee.department.departmentname if employee.department else 'Department not assigned'} · {expires.strftime('%Y-%m-%d %H:%M UTC')}",
            "href": "employees.html",
        })
    for employee in locked_accounts.limit(5).all():
        action_queue.append({
            "action": "Review locked account",
            "employee": employee.name,
            "details": f"{employee.failed_login_attempts or 0} failed sign-in attempts",
            "href": "audit-logs.html",
        })

    admin_dashboard = {
        "system_status": "OPERATIONAL",
        "database_connected": True,
        "active_users_count": active_accounts.count(),
        "active_accounts_count": active_accounts.count(),
        "pending_account_setup_count": pending_setup.count(),
        "password_actions_count": expiring_passwords.count(),
        "locked_accounts_count": locked_accounts.count(),
        "failed_logins_today": failed_logins,
        "accounts_affected_today": accounts_affected_today,
        "privilege_changes_week": privilege_changes,
        "suspicious_access_count": suspicious_ips,
        "action_queue": action_queue[:12],
        "recent_audit_events": [
            {
                "id": a.auditlogid,
                "action": a.action,
                "user": a.username_or_email or "System",
                "timestamp": a.timestamp,
                "details": a.details,
            }
            for a in db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(10).all()
        ],
    } if current_user.roletype == models.RoleType.ADMIN else None

    return {
        "department": current_user.department.departmentname if current_user.department else "Administration",
        "roletype": current_user.roletype.value,
        "date_filter": date_filter,
        "active_branch": active_branch_id,
        "sales": sales_dashboard if (
            auth.has_any_role(current_user, models.RoleType.CASHIER)
            or auth.has_permission(db, current_user, "sales:view")
            or auth.has_permission(db, current_user, "sales:pos")
        ) else None,
        "procurement": procurement_dashboard if (
            auth.has_any_role(current_user, models.RoleType.PROCUREMENT_OFFICER)
            or auth.has_permission(db, current_user, "inventory:view")
            or auth.has_permission(db, current_user, "procurement:view")
        ) else None,
        "hr": hr_dashboard if (
            auth.has_any_role(current_user, models.RoleType.HR_STAFF)
            or auth.has_permission(db, current_user, "hr:view")
        ) else None,
        "finance": finance_dashboard if (
            auth.has_any_role(current_user, models.RoleType.ACCOUNTANT)
            or auth.has_permission(db, current_user, "finance:view")
        ) else None,
        "operations": operations_dashboard if (
            auth.has_any_role(current_user, models.RoleType.BRANCH_MANAGER)
            or auth.has_permission(db, current_user, "reports:view")
        ) else None,
        "admin": admin_dashboard,
    }

# =====================================================================
