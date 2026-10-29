"""Shared permission and branch-scope helpers for API route modules."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

import auth
import models


PROCUREMENT_READ_PERMISSIONS = (
    "procurement:view",
    "procurement:requisition",
    "procurement:po_create",
    "procurement:po_approve",
    "procurement:approve_req",
    "approvals:approve",
)


def employee_branch_ids(db: Session, employee: models.Employee) -> list[int]:
    assignments = db.query(models.UserBranchAssignment.branch_id).filter(
        models.UserBranchAssignment.user_id == employee.employeeid
    ).all()
    branch_ids = [branch_id for (branch_id,) in assignments]
    if not branch_ids and employee.branchid:
        branch_ids.append(employee.branchid)
    return branch_ids


def employee_name(db: Session, employee_id: Optional[int]) -> str:
    employee = db.get(models.Employee, employee_id) if employee_id else None
    return employee.name if employee else "Unknown employee"


def scope_sales_query(
    db: Session,
    employee: models.Employee,
    query,
    requested_branch_id: Optional[int] = None,
):
    branch_ids = employee_branch_ids(db, employee)
    if requested_branch_id is not None:
        if requested_branch_id not in branch_ids:
            raise HTTPException(status_code=403, detail="You do not have access to this branch.")
        query = query.filter(models.Sale.branchid == requested_branch_id)
    elif branch_ids:
        query = query.filter(models.Sale.branchid.in_(branch_ids))
    else:
        query = query.filter(models.Sale.branchid.is_(None))

    if employee.roletype == models.RoleType.CASHIER:
        query = query.filter(models.Sale.employeeid == employee.employeeid)
    return query


def can_view_procurement(db: Session, employee: models.Employee) -> bool:
    return any(auth.has_permission(db, employee, permission) for permission in PROCUREMENT_READ_PERMISSIONS)
