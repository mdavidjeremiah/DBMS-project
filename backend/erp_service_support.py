"""Shared imports and access checks for ERP transaction services."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import auth
import models
import schemas

def require_branch_access(db: Session, employee: models.Employee, branch_id: int) -> None:
    assignments = db.query(models.UserBranchAssignment.branch_id).filter(
        models.UserBranchAssignment.user_id == employee.employeeid
    ).all()
    branch_ids = {assignment[0] for assignment in assignments}
    if not branch_ids:
        branch_ids = {employee.branchid} if employee.branchid else set()
    if branch_id not in branch_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this branch.")


def require_warehouse_access(
    db: Session,
    employee: models.Employee,
    warehouse_id: int,
    branch_id: int,
) -> models.Warehouse:
    warehouse = db.get(models.Warehouse, warehouse_id)
    if not warehouse or not warehouse.is_active:
        raise HTTPException(status_code=404, detail="Active warehouse not found.")
    if warehouse.branch_id != branch_id:
        raise HTTPException(status_code=403, detail="Warehouse does not belong to the selected branch.")
    require_branch_access(db, employee, branch_id)
    assignments = db.query(models.UserWarehouseAssignment.warehouse_id).filter(
        models.UserWarehouseAssignment.user_id == employee.employeeid
    ).all()
    warehouse_ids = {assignment[0] for assignment in assignments}
    if warehouse_ids and warehouse_id not in warehouse_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this warehouse.")
    return warehouse

# =====================================================================
# 1. Point of Sale (POS) Atomic Sale Transaction
# =====================================================================
