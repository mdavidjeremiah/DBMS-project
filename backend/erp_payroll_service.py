"""Focused ERP workflow service functions."""

from erp_service_support import (
    Any, Decimal, Dict, HTTPException, List, Optional, Session, auth, date,
    datetime, func, models, or_, require_branch_access,
    require_warehouse_access, schemas,
)

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
