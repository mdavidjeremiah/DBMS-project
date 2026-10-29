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
# /api/users (User Management by Admin)
# =====================================================================

@router.get("/users", tags=["Administration"])
def list_users(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    employees = db.query(models.Employee).order_by(models.Employee.name).all()
    return [
        {
            "employeeid": e.employeeid,
            "name": e.name,
            "email": e.email,
            "roletype": e.roletype.value,
            "is_active": e.is_active,
            "account_status": (
                "INACTIVE" if not e.is_active
                else "LOCKED" if e.locked_until and e.locked_until > datetime.utcnow()
                else "PENDING_ACTIVATION" if not e.hashed_password
                else "PASSWORD_CHANGE_REQUIRED" if e.must_change_password
                else "ACTIVE"
            ),
            "locked_until": e.locked_until,
            "temporary_password_expires_at": e.temporary_password_expires_at,
            "department_name": e.department.departmentname if e.department else None,
            "branch_name": e.branch.branchname if e.branch else None,
            "roles": auth.get_user_roles(db, e),
        }
        for e in employees
    ]


@router.post("/users/assign-role", tags=["Administration"])
def assign_user_role(
    payload: schemas.UserRoleAssign,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    role = db.query(models.Role).filter(models.Role.role_name == payload.role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{payload.role_name}' not found.")
    existing = db.query(models.UserRole).filter(
        models.UserRole.user_id == payload.user_id,
        models.UserRole.role_id == role.role_id,
    ).first()
    if not existing:
        db.add(models.UserRole(user_id=payload.user_id, role_id=role.role_id))
        db.commit()
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="ROLE_ASSIGNED",
        module="admin",
        entity_type="user_role",
        entity_id=payload.user_id,
        details=f"Assigned role '{payload.role_name}' to user #{payload.user_id}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {"user_id": payload.user_id, "role_name": payload.role_name, "assigned": True}


@router.post("/users/toggle-active", tags=["Administration"])
def toggle_user_active(
    payload: schemas.UserActivateToggle,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    if payload.user_id == current_user.employeeid:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    emp = db.get(models.Employee, payload.user_id)
    if not emp:
        raise HTTPException(status_code=404, detail="User not found.")
    emp.is_active = payload.is_active
    emp.token_version = (emp.token_version or 0) + 1
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="USER_DEACTIVATED" if not payload.is_active else "USER_ACTIVATED",
        module="admin",
        entity_type="employee",
        entity_id=payload.user_id,
        details=f"User #{payload.user_id} ({emp.name}) {'deactivated' if not payload.is_active else 'activated'}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {"user_id": payload.user_id, "is_active": emp.is_active}


@router.post("/users/unlock", tags=["Administration"])
def unlock_user(
    payload: schemas.UserUnlock,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    employee = db.get(models.Employee, payload.user_id)
    if not employee:
        raise HTTPException(status_code=404, detail="User not found.")
    employee.failed_login_attempts = 0
    employee.last_failed_login_at = None
    employee.locked_until = None
    employee.token_version = (employee.token_version or 0) + 1
    db.add(models.PasswordEvent(
        user_id=employee.employeeid,
        event_type="ACCOUNT_UNLOCKED",
        initiated_by_user_id=current_user.employeeid,
        timestamp=datetime.utcnow(),
        ip_address=request_ip(request),
        reason="Account unlocked by administrator",
    ))
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="ACCOUNT_UNLOCKED",
        module="admin",
        entity_type="employee",
        entity_id=employee.employeeid,
        details=f"Unlocked account for employee #{employee.employeeid}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {"user_id": employee.employeeid, "unlocked": True}


@router.post("/users/reset-password", tags=["Administration"])
def reset_user_password(
    payload: schemas.PasswordReset,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    emp = db.get(models.Employee, payload.user_id)
    if not emp:
        raise HTTPException(status_code=404, detail="User not found.")
    temporary_password = payload.new_password or auth.generate_temporary_password()
    if len(temporary_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Use a password no longer than 72 UTF-8 bytes.")
    if temporary_password.casefold() in {
        (emp.name or "").casefold(),
        (emp.email or "").casefold(),
    } or auth.verify_password(temporary_password, emp.hashed_password or ""):
        raise HTTPException(status_code=422, detail="Choose a password different from the employee's name, email, and current password.")
    emp.hashed_password = auth.get_password_hash(temporary_password)
    emp.must_change_password = True
    emp.temporary_password_expires_at = auth.temporary_password_expiry()
    emp.password_changed_at = datetime.utcnow()
    emp.failed_login_attempts = 0
    emp.last_failed_login_at = None
    emp.locked_until = None
    emp.token_version = (emp.token_version or 0) + 1
    db.add(models.PasswordEvent(
        user_id=emp.employeeid,
        event_type="PASSWORD_RESET_BY_ADMIN",
        initiated_by_user_id=current_user.employeeid,
        timestamp=datetime.utcnow(),
        ip_address=request_ip(request),
        reason="Administrator issued a temporary reset password",
    ))
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="PASSWORD_RESET_BY_ADMIN",
        module="admin",
        entity_type="employee",
        entity_id=payload.user_id,
        details=f"Password reset for user #{payload.user_id} ({emp.name})",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {
        "user_id": payload.user_id,
        "message": "Password reset successfully. The employee must change it at next sign-in.",
        "temporary_password_expires_at": emp.temporary_password_expires_at.isoformat(),
        "temporary_password": temporary_password if payload.new_password is None else None,
    }
