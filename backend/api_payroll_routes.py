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
# /api/payroll/payslips (Payslip access with privacy enforcement)
# =====================================================================

@router.get("/payroll/payslips", tags=["HR & Payroll"])
def get_payslips(
    run_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rule 9 privacy enforcement:
    - Employees may only see their own payslip.
    - HR and Finance see all payslips.
    - Other roles receive 403.
    """
    can_view_all = auth.has_permission(db, current_user, "payroll:view")
    can_view_own = (employee_id == current_user.employeeid)

    if not can_view_all and not can_view_own:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You may only view your own payslip.",
        )

    q = db.query(models.Payslip)
    if run_id:
        q = q.filter(models.Payslip.payroll_run_id == run_id)

    # Non-privileged users can only see their own payslip
    if not can_view_all:
        q = q.filter(models.Payslip.employee_id == current_user.employeeid)
    elif employee_id:
        q = q.filter(models.Payslip.employee_id == employee_id)

    slips = q.all()
    result = []
    for s in slips:
        emp = db.get(models.Employee, s.employee_id)
        run = db.get(models.PayrollRun, s.payroll_run_id)
        result.append({
            "payslip_id": s.payslip_id,
            "employee_id": s.employee_id,
            "employee_name": emp.name if emp else "Unknown",
            "month": run.month if run else "Unknown",
            "basic_salary": float(s.basic_salary),
            "allowances": float(s.allowances or 0),
            "overtime": float(s.overtime or 0),
            "deductions": float(s.deductions or 0),
            "gross_pay": float(s.gross_pay),
            "net_pay": float(s.net_pay),
            "payment_status": s.payment_status,
        })
    return result
