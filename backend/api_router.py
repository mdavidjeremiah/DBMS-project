"""Hardware World Grouped API Routers (/api/...)

Provides the full Section 8 grouped endpoint hierarchy:
/api/auth, /api/users, /api/roles, /api/permissions, /api/organization,
/api/branches, /api/warehouses, /api/departments, /api/employees,
/api/products, /api/categories, /api/units, /api/suppliers, /api/inventory,
/api/stock-movements, /api/stocktakes, /api/stock-adjustments, /api/transfers,
/api/customers, /api/cashier-sessions, /api/sales, /api/payments, /api/returns,
/api/discounts, /api/purchase-requisitions, /api/purchase-orders,
/api/goods-receipts, /api/supplier-invoices, /api/supplier-payments,
/api/payroll, /api/attendance, /api/leave, /api/finance, /api/journals,
/api/reports, /api/dashboard, /api/approvals, /api/audit-logs
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import MetaData, Table, func, or_, desc

import models
import schemas
import auth
import erp_service
from database import get_db
from audit import request_ip, write_audit_log

api_router = APIRouter(prefix="/api")
PROFILE_PHOTO_DIR = Path(__file__).resolve().parent / "uploads" / "profile-photos"
MAX_PROFILE_PHOTO_BYTES = 5 * 1024 * 1024
PROFILE_PHOTO_FORMATS = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}

# --- Helper: Permission Enforcer ---
def require_perm(perm_code: str):
    def dependency(
        current_user: models.Employee = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
    ):
        if not auth.has_permission(db, current_user, perm_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Missing permission '{perm_code}'."
            )
        return current_user
    return dependency


def employee_branch_ids(db: Session, employee: models.Employee) -> list[int]:
    assignments = db.query(models.UserBranchAssignment.branch_id).filter(
        models.UserBranchAssignment.user_id == employee.employeeid
    ).all()
    branch_ids = [branch_id for (branch_id,) in assignments]
    if not branch_ids and employee.branchid:
        branch_ids.append(employee.branchid)
    return branch_ids


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


PROCUREMENT_READ_PERMISSIONS = (
    "procurement:view",
    "procurement:requisition",
    "procurement:po_create",
    "procurement:po_approve",
    "procurement:approve_req",
    "approvals:approve",
)


def can_view_procurement(db: Session, employee: models.Employee) -> bool:
    return any(auth.has_permission(db, employee, permission) for permission in PROCUREMENT_READ_PERMISSIONS)

# =====================================================================
# /api/auth & /api/users
# =====================================================================

@api_router.get("/users/me", response_model=schemas.UserResponse, tags=["Authentication"])
def get_user_me(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    branch_assignments = db.query(models.UserBranchAssignment.branch_id).filter(
        models.UserBranchAssignment.user_id == current_user.employeeid
    ).all()
    warehouse_assignments = db.query(models.UserWarehouseAssignment.warehouse_id).filter(
        models.UserWarehouseAssignment.user_id == current_user.employeeid
    ).all()

    branch_ids = [b[0] for b in branch_assignments] or ([current_user.branchid] if current_user.branchid else [])
    warehouse_ids = [w[0] for w in warehouse_assignments]

    return {
        "employeeid": current_user.employeeid,
        "name": current_user.name,
        "email": current_user.email,
        "profile_photo_url": f"/api/users/{current_user.employeeid}/profile-photo" if current_user.profile_photo_filename else None,
        "roletype": current_user.roletype,
        "departmentid": current_user.departmentid,
        "department_name": current_user.department.departmentname if current_user.department else None,
        "branchid": current_user.branchid,
        "branch_name": current_user.branch.branchname if current_user.branch else None,
        "roles": auth.get_user_roles(db, current_user),
        "permissions": auth.get_user_permissions(db, current_user),
        "branch_ids": branch_ids,
        "warehouse_ids": warehouse_ids,
    }


@api_router.put("/users/{employee_id}/profile-photo", tags=["Authentication"])
def upload_employee_profile_photo(
    employee_id: int,
    file: UploadFile = File(...),
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not (
        auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF)
        or auth.has_permission(db, current_user, "admin:users")
        or auth.has_permission(db, current_user, "hr:manage")
    ):
        raise HTTPException(status_code=403, detail="Employee profile photo permission required.")

    employee = db.get(models.Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    content = file.file.read(MAX_PROFILE_PHOTO_BYTES + 1)
    if len(content) > MAX_PROFILE_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Profile photo must be 5 MB or smaller.")
    photo_format = PROFILE_PHOTO_FORMATS.get(file.content_type or "")
    if not photo_format or not photo_format[1](content):
        raise HTTPException(status_code=415, detail="Upload a valid JPEG, PNG, or WebP image.")

    extension = photo_format[0]
    PROFILE_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(24)}{extension}"
    photo_path = PROFILE_PHOTO_DIR / filename
    old_filename = employee.profile_photo_filename
    photo_path.write_bytes(content)
    try:
        employee.profile_photo_filename = filename
        db.commit()
    except Exception:
        db.rollback()
        photo_path.unlink(missing_ok=True)
        raise
    if old_filename:
        (PROFILE_PHOTO_DIR / Path(old_filename).name).unlink(missing_ok=True)
    return {"profile_photo_url": f"/api/users/{employee.employeeid}/profile-photo"}


@api_router.get("/users/{employee_id}/profile-photo", tags=["Authentication"])
def get_employee_profile_photo(
    employee_id: int,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    employee = db.get(models.Employee, employee_id)
    if not employee or not employee.profile_photo_filename:
        raise HTTPException(status_code=404, detail="Profile photo not found.")

    filename = Path(employee.profile_photo_filename).name
    photo_path = PROFILE_PHOTO_DIR / filename
    if not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Profile photo not found.")
    media_type = next(
        (content_type for content_type, (extension, _) in PROFILE_PHOTO_FORMATS.items() if filename.endswith(extension)),
        None,
    )
    if not media_type:
        raise HTTPException(status_code=404, detail="Profile photo not found.")
    return FileResponse(
        photo_path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@api_router.post("/auth/initial-password", tags=["Authentication"])
def change_initial_password(
    payload: schemas.InitialPasswordChange,
    request: Request,
    response: Response,
    current_user: models.Employee = Depends(auth.get_initial_password_change_user),
    db: Session = Depends(get_db),
):
    if not auth.verify_password(payload.current_password, current_user.hashed_password or ""):
        raise HTTPException(status_code=400, detail="The current temporary password is incorrect.")
    normalized_password = payload.new_password.casefold()
    if normalized_password in {
        (current_user.name or "").casefold(),
        (current_user.email or "").casefold(),
    } or auth.verify_password(payload.new_password, current_user.hashed_password or ""):
        raise HTTPException(status_code=422, detail="Choose a password different from your name, email, and temporary password.")
    try:
        password_hash = auth.get_password_hash(payload.new_password)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Use a password no longer than 72 UTF-8 bytes.") from error

    now = datetime.utcnow()
    current_user.hashed_password = password_hash
    current_user.must_change_password = False
    current_user.temporary_password_expires_at = None
    current_user.password_changed_at = now
    current_user.failed_login_attempts = 0
    current_user.last_failed_login_at = None
    current_user.locked_until = None
    current_user.last_login_at = now
    current_user.token_version = (current_user.token_version or 0) + 1
    db.add(models.PasswordEvent(
        user_id=current_user.employeeid,
        event_type="INITIAL_PASSWORD_CHANGED",
        timestamp=now,
        ip_address=request_ip(request),
        reason="Employee completed mandatory first-login password change",
    ))
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="INITIAL_PASSWORD_CHANGED",
        module="authentication",
        entity_type="employee",
        entity_id=current_user.employeeid,
        details="Employee changed their temporary password",
        ip_address=request_ip(request),
    ))
    db.commit()
    access_token = auth.create_access_token(
        data={
            "sub": current_user.email,
            "name": current_user.name,
            "role": current_user.roletype.value,
            "departmentid": current_user.departmentid,
            "departmentname": current_user.department.departmentname if current_user.department else "General",
            "branchid": current_user.branchid,
            "tv": current_user.token_version,
        },
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response.set_cookie(
        key="hw_access_token",
        value=access_token,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        secure=auth.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    return {"detail": "Password changed.", "next_route": "index.html"}

# =====================================================================
# /api/roles & /api/permissions
# =====================================================================

@api_router.get("/roles", tags=["Access Control"])
def list_roles(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    roles = db.query(models.Role).filter(models.Role.is_active == True).all()
    return [{"role_id": r.role_id, "role_name": r.role_name, "description": r.description} for r in roles]

@api_router.get("/permissions", tags=["Access Control"])
def list_permissions(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.roletype != models.RoleType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    perms = db.query(models.Permission).all()
    return [{"permission_id": p.permission_id, "code": p.code, "module": p.module, "action": p.action, "description": p.description} for p in perms]

# =====================================================================
# /api/organization, /api/branches, /api/warehouses, /api/departments
# =====================================================================

@api_router.get("/branches", response_model=List[schemas.BranchResponse], tags=["Organization"])
def get_api_branches(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Branch).all()

@api_router.post("/departments", tags=["Organization"])
def create_api_department(
    payload: schemas.DepartmentCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    branch = db.get(models.Branch, payload.branchid)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found.")
    department_name = payload.departmentname.strip()
    if not department_name:
        raise HTTPException(status_code=422, detail="Department name is required.")
    department = models.Department(departmentname=department_name, branchid=branch.branchid)
    db.add(department)
    db.flush()
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="DEPARTMENT_CREATED",
        module="admin",
        entity_type="department",
        entity_id=department.departmentid,
        details=f"Created department {department_name} for branch {branch.branchname}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {
        "departmentid": department.departmentid,
        "departmentname": department.departmentname,
        "branchid": department.branchid,
        "branch_name": branch.branchname,
    }

@api_router.post("/warehouses", response_model=schemas.WarehouseResponse, tags=["Organization"])
def create_api_warehouse(
    payload: schemas.WarehouseCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    branch = db.get(models.Branch, payload.branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found.")
    warehouse_name = payload.warehouse_name.strip()
    if not warehouse_name:
        raise HTTPException(status_code=422, detail="Warehouse name is required.")
    warehouse = models.Warehouse(
        warehouse_name=warehouse_name,
        branch_id=branch.branchid,
        location=payload.location,
        is_active=payload.is_active,
    )
    db.add(warehouse)
    db.flush()
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="WAREHOUSE_CREATED",
        module="admin",
        entity_type="warehouse",
        entity_id=warehouse.warehouse_id,
        details=f"Created warehouse {warehouse_name} for branch {branch.branchname}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return warehouse

@api_router.get("/warehouses", response_model=List[schemas.WarehouseResponse], tags=["Organization"])
def get_api_warehouses(
    branch_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(models.Warehouse).filter(models.Warehouse.is_active == True)
    if branch_id:
        q = q.filter(models.Warehouse.branch_id == branch_id)
    return q.all()

@api_router.get("/departments", tags=["Organization"])
def get_api_departments(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    depts = db.query(models.Department).order_by(models.Department.departmentname).all()
    return [
        {
            "departmentid": d.departmentid,
            "departmentname": d.departmentname,
            "branchid": d.branchid,
            "branch_name": d.branch.branchname if d.branch else None,
        }
        for d in depts
    ]

# =====================================================================
# /api/employees (With Payroll & Salary Privacy Isolation)
# =====================================================================

@api_router.get("/employees", tags=["Organization"])
def get_api_employees(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve employees. Enforces payroll/salary privacy (Rule 9)."""
    can_view_salary = (
        auth.has_any_role(current_user, models.RoleType.HR_STAFF, models.RoleType.ACCOUNTANT)
        or auth.has_permission(db, current_user, "payroll:view")
    )

    employees = db.query(models.Employee).order_by(models.Employee.name).all()
    result = []
    for e in employees:
        is_self = e.employeeid == current_user.employeeid
        salary_val = float(e.salary or 0) if (can_view_salary or is_self) else None

        result.append({
            "employeeid": e.employeeid,
            "name": e.name,
            "nin": e.nin if (can_view_salary or is_self) else "PROTECTED",
            "email": e.email,
            "phone": e.phone,
            "datehired": e.datehired,
            "salary": salary_val,
            "roletype": e.roletype.value,
            "departmentid": e.departmentid,
            "department_name": e.department.departmentname if e.department else None,
            "branchid": e.branchid,
            "branch_name": e.branch.branchname if e.branch else None,
        })
    return result

# =====================================================================
# /api/products, /api/categories, /api/suppliers
# =====================================================================

@api_router.get("/categories", tags=["Catalogue"])
def get_api_categories(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    cats = db.query(models.Category).order_by(models.Category.categoryname).all()
    return [{"categoryid": c.categoryid, "categoryname": c.categoryname} for c in cats]

@api_router.get("/products", tags=["Catalogue"])
def get_api_products(
    category_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.is_active == True)
    if category_id:
        query = query.filter(models.Product.categoryid == category_id)

    products = query.order_by(models.Product.itemname).all()
    res = []
    for p in products:
        # Stock calculation
        stock_query = db.query(func.sum(models.InventoryBalance.available_stock)).filter(
            models.InventoryBalance.item_id == p.itemid
        )
        if warehouse_id:
            stock_query = stock_query.filter(models.InventoryBalance.warehouse_id == warehouse_id)
        stock_val = stock_query.scalar() or Decimal("0")

        res.append({
            "itemid": p.itemid,
            "itemname": p.itemname,
            "description": p.description,
            "unitprice": float(p.unitprice),
            "costprice": float(p.costprice or 0) if (
                auth.has_any_role(current_user, models.RoleType.PROCUREMENT_OFFICER, models.RoleType.ACCOUNTANT)
                or auth.has_permission(db, current_user, "inventory:view")
                or auth.has_permission(db, current_user, "finance:view")
            ) else None,
            "reorderlevel": p.reorderlevel or 0,
            "base_unit": p.base_unit or "Piece",
            "categoryid": p.categoryid,
            "category_name": p.category.categoryname if p.category else "Uncategorized",
            "available_stock": float(stock_val),
            "is_active": p.is_active,
        })
    return res

@api_router.post("/products", tags=["Catalogue"])
def create_api_product(
    payload: schemas.ProductCreate,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized to create products.")

    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"itemid": product.itemid, "itemname": product.itemname}

@api_router.get("/suppliers", tags=["Procurement"])
def get_api_suppliers(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    suppliers = db.query(models.Supplier).order_by(models.Supplier.suppliername).all()
    return [{"supplierid": s.supplierid, "suppliername": s.suppliername, "contactperson": s.contactperson, "phone": s.phone, "address": s.address} for s in suppliers]

# =====================================================================
# /api/inventory, /api/stock-movements, /api/stock-adjustments
# =====================================================================

@api_router.get("/inventory", tags=["Inventory"])
def get_api_inventory(
    warehouse_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(models.InventoryBalance)
    if warehouse_id:
        q = q.filter(models.InventoryBalance.warehouse_id == warehouse_id)

    balances = q.all()
    res = []
    for b in balances:
        reorder = b.product.reorderlevel or 0
        critical = max(1, reorder // 2)
        avail = float(b.available_stock)

        res.append({
            "balance_id": b.balance_id,
            "item_id": b.item_id,
            "item_name": b.product.itemname if b.product else "Unknown",
            "warehouse_id": b.warehouse_id,
            "warehouse_name": b.warehouse.warehouse_name if b.warehouse else "Unknown",
            "available_stock": avail,
            "reserved_stock": float(b.reserved_stock),
            "reorder_level": reorder,
            "critical_level": critical,
            "is_low_stock": avail <= reorder,
            "is_critical": avail <= critical,
            "last_updated": b.last_updated,
        })
    return res

@api_router.get("/stock-movements", tags=["Inventory"])
def get_api_stock_movements(
    item_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    limit: int = 50,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(models.InventoryMovement)
    if item_id:
        q = q.filter(models.InventoryMovement.item_id == item_id)
    if warehouse_id:
        q = q.filter(models.InventoryMovement.warehouse_id == warehouse_id)

    movements = q.order_by(models.InventoryMovement.created_at.desc()).limit(limit).all()
    return [
        {
            "movement_id": m.movement_id,
            "item_name": m.product.itemname if m.product else "Unknown",
            "warehouse_name": m.warehouse.warehouse_name if m.warehouse else "Unknown",
            "movement_type": m.movement_type,
            "quantity": float(m.quantity),
            "reference_type": m.reference_type,
            "reference_id": m.reference_id,
            "notes": m.notes,
            "created_at": m.created_at,
        }
        for m in movements
    ]

@api_router.post("/stock-adjustments", tags=["Inventory"])
def create_stock_adjustment(
    payload: schemas.StockAdjustmentCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "inventory:adjust"):
        raise HTTPException(status_code=403, detail="Stock adjustment submission permission required.")
    warehouse = db.get(models.Warehouse, payload.warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found.")
    erp_service.require_warehouse_access(db, current_user, payload.warehouse_id, warehouse.branch_id)

    adj = erp_service.submit_stock_adjustment(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request)
    )
    return {"adjustment_id": adj.adjustment_id, "status": adj.status, "variance_quantity": float(adj.variance_quantity)}

# =====================================================================
# /api/cashier-sessions
# =====================================================================

@api_router.post("/cashier-sessions/open", tags=["Sales & POS"])
def open_session(
    payload: schemas.CashierSessionCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    session = erp_service.open_cashier_session(
        employee_id=current_user.employeeid,
        branch_id=payload.branch_id,
        warehouse_id=payload.warehouse_id,
        opening_float=payload.opening_float,
        db=db,
        ip_address=request_ip(request),
    )
    return {
        "session_id": session.session_id,
        "status": session.status,
        "opened_at": session.opened_at,
        "opening_float": float(session.opening_float),
    }

@api_router.post("/cashier-sessions/{session_id}/close", tags=["Sales & POS"])
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

@api_router.get("/cashier-sessions/current", tags=["Sales & POS"])
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
        "opened_at": session.opened_at,
        "opening_float": float(session.opening_float or 0),
        "cash_sales": float(session.cash_sales or 0),
        "expected_cash": float(session.expected_cash or 0),
        "status": session.status,
    }

# =====================================================================
# /api/sales & /api/payments
# =====================================================================

@api_router.get("/sales", tags=["Sales & POS"])
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

@api_router.post("/sales", tags=["Sales & POS"])
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
# /api/purchase-requisitions, /api/purchase-orders, /api/goods-receipts
# =====================================================================

@api_router.get("/purchase-requisitions", tags=["Procurement"])
def get_requisitions(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not can_view_procurement(db, current_user):
        raise HTTPException(status_code=403, detail="Procurement view permission required.")
    branch_ids = employee_branch_ids(db, current_user)
    req_query = db.query(models.PurchaseRequisition)
    req_query = req_query.filter(models.PurchaseRequisition.branch_id.in_(branch_ids)) if branch_ids else req_query.filter(models.PurchaseRequisition.branch_id.is_(None))
    reqs = req_query.order_by(models.PurchaseRequisition.created_at.desc()).all()
    res = []
    for r in reqs:
        requester = db.get(models.Employee, r.requester_id)
        res.append({
            "requisition_id": r.requisition_id,
            "status": r.status,
            "created_at": r.created_at,
            "notes": r.notes,
            "requester_name": requester.name if requester else "Unknown",
            "items": [
                {
                    "item_id": i.item_id,
                    "item_name": i.product.itemname if i.product else "Unknown",
                    "quantity": float(i.quantity),
                }
                for i in r.items
            ]
        })
    return res

@api_router.post("/purchase-requisitions", tags=["Procurement"])
def create_requisition(
    payload: schemas.PurchaseRequisitionCreate,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    req = models.PurchaseRequisition(
        requester_id=current_user.employeeid,
        branch_id=payload.branch_id,
        notes=payload.notes,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()

    for item in payload.items:
        db.add(models.PurchaseRequisitionItem(
            requisition_id=req.requisition_id,
            item_id=item.item_id,
            quantity=item.quantity,
            estimated_unit_price=item.estimated_unit_price or Decimal("0"),
        ))
    db.commit()
    db.refresh(req)
    return {"requisition_id": req.requisition_id, "status": req.status}

@api_router.post("/purchase-requisitions/{req_id}/approve", tags=["Procurement"])
def approve_requisition(
    req_id: int,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.BRANCH_MANAGER):
        raise HTTPException(status_code=403, detail="Manager approval required.")
    req = db.get(models.PurchaseRequisition, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found.")
    req.status = "APPROVED"
    req.approved_by = current_user.employeeid
    db.commit()
    return {"requisition_id": req.requisition_id, "status": req.status}

@api_router.get("/purchase-orders", tags=["Procurement"])
def get_api_purchase_orders(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not can_view_procurement(db, current_user):
        raise HTTPException(status_code=403, detail="Procurement view permission required.")
    branch_ids = employee_branch_ids(db, current_user)
    order_query = db.query(models.PurchaseOrder)
    order_query = order_query.filter(models.PurchaseOrder.branch_id.in_(branch_ids)) if branch_ids else order_query.filter(models.PurchaseOrder.branch_id.is_(None))
    orders = order_query.order_by(models.PurchaseOrder.orderdate.desc()).all()
    res = []
    for o in orders:
        supplier = db.get(models.Supplier, o.supplierid) if o.supplierid else None
        officer = db.get(models.Employee, o.employeeid)
        res.append({
            "po_id": o.po_id,
            "orderdate": o.orderdate,
            "status": o.status.value,
            "total_amount": float(o.total_amount or 0),
            "supplier_name": supplier.suppliername if supplier else "Unknown Supplier",
            "officer_name": officer.name if officer else "Unknown Officer",
        })
    return res

@api_router.post("/purchase-orders", tags=["Procurement"])
def create_api_purchase_order(
    payload: schemas.PurchaseOrderCreate,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER):
        raise HTTPException(status_code=403, detail="Not authorized to create purchase orders.")
    branch_id = payload.branchid or current_user.branchid
    if branch_id is None:
        raise HTTPException(status_code=400, detail="A branch must be assigned to create a purchase order.")
    if not db.get(models.Branch, branch_id):
        raise HTTPException(status_code=404, detail="Branch not found.")
    erp_service.require_branch_access(db, current_user, branch_id)

    total = Decimal("0")
    if payload.items:
        for itm in payload.items:
            total += itm.unit_price * itm.quantity

    # Check ProcurementOfficer approval limit
    officer_sub = db.get(models.ProcurementOfficer, current_user.employeeid)
    auto_approve = False
    if officer_sub and officer_sub.approvallimit >= total:
        auto_approve = True

    po = models.PurchaseOrder(
        supplierid=payload.supplierid,
        employeeid=current_user.employeeid,
        branch_id=branch_id,
        status=models.POStatus.APPROVED if auto_approve else models.POStatus.PENDING,
        total_amount=total,
        orderdate=datetime.utcnow(),
    )
    db.add(po)
    db.flush()

    if payload.items:
        for itm in payload.items:
            db.add(models.PurchaseOrderItem(
                po_id=po.po_id,
                item_id=itm.item_id,
                quantity=itm.quantity,
                unit_price=itm.unit_price,
            ))

    db.commit()
    db.refresh(po)
    return {"po_id": po.po_id, "status": po.status.value, "total_amount": float(total)}

@api_router.post("/goods-receipts", tags=["Procurement"])
def create_api_goods_receipt(
    payload: schemas.GoodsReceivedNoteCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "procurement:grn"):
        raise HTTPException(status_code=403, detail="Goods receipt permission required.")
    grn = erp_service.create_goods_received_note(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request)
    )
    return {"grn_id": grn.grn_id, "grn_number": grn.grn_number, "status": grn.status}

@api_router.post("/supplier-invoices", tags=["Procurement"])
def create_api_supplier_invoice(
    payload: schemas.SupplierInvoiceCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "finance:invoice"):
        raise HTTPException(status_code=403, detail="Supplier invoice permission required.")
    invoice = erp_service.process_supplier_invoice(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request)
    )
    return {"invoice_id": invoice.invoice_id, "invoice_number": invoice.invoice_number, "matched_status": invoice.matched_status}

@api_router.post("/supplier-payments", tags=["Procurement"])
def create_api_supplier_payment(
    payload: schemas.SupplierPaymentCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "finance:payment"):
        raise HTTPException(status_code=403, detail="Supplier payment permission required.")
    payment = erp_service.record_supplier_payment(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request)
    )
    return {"payment_id": payment.payment_id, "amount": float(payment.amount)}

# =====================================================================
# /api/payroll (Enforces Rule 9 Privacy)
# =====================================================================

@api_router.get("/payroll", tags=["HR & Payroll"])
def get_api_payroll(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Protected payroll list: only HR, Finance, or Admin may view."""
    can_view = (
        auth.has_any_role(current_user, models.RoleType.HR_STAFF, models.RoleType.ACCOUNTANT)
        or auth.has_permission(db, current_user, "payroll:view")
    )
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view organization payroll records."
        )

    records = db.query(models.Payroll).order_by(models.Payroll.month.desc()).all()
    res = []
    for p in records:
        emp = db.get(models.Employee, p.employeeid)
        res.append({
            "payrollid": p.payrollid,
            "employeeid": p.employeeid,
            "employee_name": emp.name if emp else "Unknown",
            "month": p.month,
            "grosspay": float(p.grosspay),
            "deductions": float(p.deductions or 0),
            "netpay": float(p.netpay),
        })
    return res

@api_router.post("/payroll/run", tags=["HR & Payroll"])
def create_payroll_run(
    payload: schemas.PayrollRunCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF):
        raise HTTPException(status_code=403, detail="Only HR Staff or Admin can prepare payroll runs.")

    run = erp_service.execute_payroll_run(
        month=payload.month,
        prepared_by_user=current_user,
        db=db,
        ip_address=request_ip(request)
    )
    return {"run_id": run.run_id, "month": run.month, "total_net": float(run.total_net), "status": run.status}

@api_router.post("/payroll/approve", tags=["HR & Payroll"])
def approve_payroll(
    payload: schemas.PayrollRunApprove,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT, models.RoleType.BRANCH_MANAGER):
        raise HTTPException(status_code=403, detail="Finance or Management authorization required.")

    run = erp_service.approve_and_post_payroll(
        run_id=payload.run_id,
        approver=current_user,
        db=db,
        ip_address=request_ip(request)
    )
    return {"run_id": run.run_id, "status": run.status, "approved_at": run.approved_at}

# =====================================================================
# /api/finance & /api/journals
# =====================================================================

@api_router.get("/finance/accounts", tags=["Finance"])
def get_chart_of_accounts(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not (
        auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
        or auth.has_permission(db, current_user, "finance:view")
    ):
        raise HTTPException(status_code=403, detail="Finance authorization required.")
    accts = db.query(models.ChartOfAccount).order_by(models.ChartOfAccount.account_code).all()
    return [{"account_code": a.account_code, "account_name": a.account_name, "account_type": a.account_type} for a in accts]

@api_router.get("/journals", tags=["Finance"])
def get_journal_entries(
    limit: int = 50,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not (
        auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
        or auth.has_permission(db, current_user, "finance:view")
    ):
        raise HTTPException(status_code=403, detail="Finance authorization required.")

    entries = db.query(models.JournalEntry).order_by(models.JournalEntry.entry_date.desc()).limit(limit).all()
    res = []
    for e in entries:
        res.append({
            "entry_id": e.entry_id,
            "entry_number": e.entry_number,
            "entry_date": e.entry_date,
            "description": e.description,
            "reference_type": e.reference_type,
            "reference_id": e.reference_id,
            "total_amount": float(e.total_amount),
            "lines": [
                {
                    "account_code": l.account_code,
                    "debit": float(l.debit),
                    "credit": float(l.credit),
                    "description": l.description,
                }
                for l in e.lines
            ]
        })
    return res

# =====================================================================
# /api/dashboard (Specialized for all 6 Department Dashboards)
# =====================================================================

@api_router.get("/dashboard", tags=["Dashboards"])
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
# /api/approvals (Requisitions, POs, Leave, General)
# =====================================================================

@api_router.get("/approvals", tags=["Approvals"])
def get_pending_approvals(
    module: Optional[str] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Return all pending approval requests visible to this user's role."""
    result = []
    can_approve_all = auth.has_permission(db, current_user, "approvals:approve")

    # Purchase Requisitions
    branch_ids = employee_branch_ids(db, current_user)
    if (not module or module == "REQUISITION") and (
        can_approve_all or auth.has_permission(db, current_user, "procurement:approve_req")
    ):
        reqs = db.query(models.PurchaseRequisition).filter(
            models.PurchaseRequisition.status == "PENDING",
            models.PurchaseRequisition.branch_id.in_(branch_ids) if branch_ids else models.PurchaseRequisition.branch_id.is_(None),
        ).all()
        for r in reqs:
            requester = db.get(models.Employee, r.requester_id)
            result.append({
                "type": "REQUISITION",
                "id": r.requisition_id,
                "description": f"Purchase Requisition — {len(r.items)} item(s)",
                "requester": requester.name if requester else "Unknown",
                "created_at": r.created_at,
                "status": r.status,
                "notes": r.notes,
            })

    # Purchase Orders
    if (not module or module == "PO") and (
        can_approve_all or auth.has_permission(db, current_user, "procurement:po_approve")
    ):
        pos = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.status == models.POStatus.PENDING,
            models.PurchaseOrder.branch_id.in_(branch_ids) if branch_ids else models.PurchaseOrder.branch_id.is_(None),
        ).all()
        for p in pos:
            supplier = db.get(models.Supplier, p.supplierid)
            result.append({
                "type": "PO",
                "id": p.po_id,
                "description": f"Purchase Order — {supplier.suppliername if supplier else 'Supplier'} — UGX {float(p.total_amount or 0):,.0f}",
                "requester": employee_name(db, p.employeeid),
                "created_at": p.orderdate,
                "status": p.status.value,
                "total_amount": float(p.total_amount or 0),
            })

    # Leave Requests
    if (not module or module == "LEAVE") and (
        can_approve_all or auth.has_permission(db, current_user, "hr:leave")
    ):
        leaves = db.query(models.LeaveRequest).join(
            models.Employee, models.Employee.employeeid == models.LeaveRequest.employee_id
        ).filter(
            models.LeaveRequest.status == "PENDING",
            models.Employee.branchid.in_(branch_ids) if branch_ids else models.Employee.branchid.is_(None),
        ).all()
        for lv in leaves:
            emp = db.get(models.Employee, lv.employee_id)
            result.append({
                "type": "LEAVE",
                "id": lv.leave_id,
                "description": f"{lv.leave_type} leave — {lv.start_date} to {lv.end_date}",
                "requester": emp.name if emp else "Unknown",
                "created_at": lv.created_at,
                "status": lv.status,
            })

    # Stock Adjustments
    if (not module or module == "ADJUSTMENT") and (
        can_approve_all or auth.has_permission(db, current_user, "inventory:approve_adjust")
    ):
        adjs = db.query(models.StockAdjustment).join(
            models.Warehouse, models.Warehouse.warehouse_id == models.StockAdjustment.warehouse_id
        ).filter(
            models.StockAdjustment.status == "PENDING",
            models.Warehouse.branch_id.in_(branch_ids) if branch_ids else models.Warehouse.branch_id.is_(None),
        ).all()
        for a in adjs:
            requester = db.get(models.Employee, a.requester_id)
            result.append({
                "type": "ADJUSTMENT",
                "id": a.adjustment_id,
                "description": f"Stock Adjustment — {a.product.itemname if a.product else 'Product'} ({a.variance_quantity})",
                "requester": requester.name if requester else "Unknown",
                "created_at": a.created_at,
                "status": a.status,
                "reason_code": a.reason_code,
            })

    return sorted(result, key=lambda x: x["created_at"] or "", reverse=True)


@api_router.post("/approvals/stock-adjustment", tags=["Approvals"])
def approve_stock_adjustment(
    payload: schemas.StockAdjustmentApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.has_permission(db, current_user, "inventory:approve_adjust"):
        raise HTTPException(status_code=403, detail="You do not have stock adjustment approval permission.")
    adjustment = db.get(models.StockAdjustment, payload.adjustment_id)
    if not adjustment:
        raise HTTPException(status_code=404, detail="Stock adjustment not found.")
    warehouse = db.get(models.Warehouse, adjustment.warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found.")
    erp_service.require_warehouse_access(db, current_user, adjustment.warehouse_id, warehouse.branch_id)
    result = erp_service.approve_or_reject_stock_adjustment(
        adjustment_id=payload.adjustment_id,
        action=payload.action,
        approver=current_user,
        notes=payload.notes,
        db=db,
        ip_address=request_ip(request),
    )
    return {"adjustment_id": result.adjustment_id, "status": result.status}


@api_router.post("/approvals/requisition", tags=["Approvals"])
def approve_requisition(
    payload: schemas.RequisitionApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "procurement:approve_req"):
        raise HTTPException(status_code=403, detail="You do not have requisition approval permission.")
    req = erp_service.approve_or_reject_requisition(
        requisition_id=payload.requisition_id,
        action=payload.action,
        approver=current_user,
        notes=payload.notes,
        db=db,
        ip_address=request_ip(request),
    )
    return {"requisition_id": req.requisition_id, "status": req.status}


@api_router.post("/approvals/purchase-order", tags=["Approvals"])
def approve_purchase_order(
    payload: schemas.POApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "procurement:po_approve"):
        raise HTTPException(status_code=403, detail="You do not have PO approval permission.")
    po = erp_service.approve_or_reject_po(
        po_id=payload.po_id,
        action=payload.action,
        approver=current_user,
        notes=payload.notes,
        db=db,
        ip_address=request_ip(request),
    )
    return {"po_id": po.po_id, "status": po.status.value}


@api_router.post("/approvals/leave", tags=["Approvals"])
def approve_leave(
    payload: schemas.LeaveApproval,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "hr:leave"):
        raise HTTPException(status_code=403, detail="You do not have leave approval permission.")
    lv = db.get(models.LeaveRequest, payload.leave_id)
    if not lv:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if lv.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Leave request is already {lv.status}.")
    if lv.employee_id == current_user.employeeid:
        raise HTTPException(status_code=403, detail="You cannot approve your own leave request.")
    lv.status = "APPROVED" if payload.action.upper() == "APPROVE" else "REJECTED"
    lv.approved_by = current_user.employeeid
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        action="LEAVE_APPROVED" if lv.status == "APPROVED" else "LEAVE_REJECTED",
        module="hr",
        entity_type="leave_request",
        entity_id=lv.leave_id,
        details=f"Leave request #{lv.leave_id} {lv.status}. Notes: {payload.notes or ''}",
        ip_address=request_ip(request),
    ))
    db.commit()
    return {"leave_id": lv.leave_id, "status": lv.status}


# =====================================================================
# /api/hr/attendance, /api/hr/leave
# =====================================================================

@api_router.get("/attendance", tags=["HR & Payroll"])
def get_attendance(
    employee_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "hr:attendance") and not auth.has_permission(db, current_user, "hr:view"):
        raise HTTPException(status_code=403, detail="HR authorization required.")
    q = db.query(models.AttendanceRecord)
    if employee_id:
        q = q.filter(models.AttendanceRecord.employee_id == employee_id)
    if date_from:
        q = q.filter(models.AttendanceRecord.date >= date_from)
    if date_to:
        q = q.filter(models.AttendanceRecord.date <= date_to)
    records = q.order_by(models.AttendanceRecord.date.desc()).limit(200).all()
    return [
        {
            "attendance_id": r.attendance_id,
            "employee_id": r.employee_id,
            "employee_name": r.employee.name if r.employee else "Unknown",
            "date": r.date,
            "status": r.status,
            "check_in": r.check_in,
            "check_out": r.check_out,
            "overtime_hours": float(r.overtime_hours or 0),
        }
        for r in records
    ]


@api_router.post("/attendance", tags=["HR & Payroll"])
def record_attendance(
    payload: schemas.AttendanceRecordCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "hr:attendance"):
        raise HTTPException(status_code=403, detail="HR attendance permission required.")
    rec = models.AttendanceRecord(
        employee_id=payload.employee_id,
        date=payload.date,
        status=payload.status,
        check_in=payload.check_in,
        check_out=payload.check_out,
        overtime_hours=payload.overtime_hours or Decimal("0"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"attendance_id": rec.attendance_id, "status": rec.status}


@api_router.get("/leave", tags=["HR & Payroll"])
def get_leave_requests(
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "hr:leave") and not auth.has_permission(db, current_user, "hr:view"):
        raise HTTPException(status_code=403, detail="HR authorization required.")
    q = db.query(models.LeaveRequest)
    if employee_id:
        q = q.filter(models.LeaveRequest.employee_id == employee_id)
    if status:
        q = q.filter(models.LeaveRequest.status == status)
    records = q.order_by(models.LeaveRequest.created_at.desc()).limit(100).all()
    return [
        {
            "leave_id": r.leave_id,
            "employee_id": r.employee_id,
            "employee_name": r.employee.name if r.employee else "Unknown",
            "leave_type": r.leave_type,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in records
    ]


@api_router.post("/leave", tags=["HR & Payroll"])
def create_leave_request(
    payload: schemas.LeaveRequestCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    can_manage_leave_for_others = auth.has_permission(db, current_user, "hr:manage")
    if payload.employee_id != current_user.employeeid and not can_manage_leave_for_others:
        raise HTTPException(status_code=403, detail="You may only submit leave for yourself.")
    lv = models.LeaveRequest(
        employee_id=payload.employee_id if can_manage_leave_for_others else current_user.employeeid,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    db.add(lv)
    db.commit()
    db.refresh(lv)
    return {"leave_id": lv.leave_id, "status": lv.status}


# =====================================================================
# /api/finance/cash-position, /api/finance/accounts
# =====================================================================

@api_router.get("/finance/cash-position", tags=["Finance"])
def get_cash_position(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "finance:view"):
        raise HTTPException(status_code=403, detail="Finance authorization required.")
    accts = db.query(models.FinancialAccount).all()
    total = sum([a.balance for a in accts], Decimal("0"))
    return {
        "total_cash_position": float(total),
        "accounts": [
            {
                "account_id": a.account_id,
                "account_name": a.account_name,
                "account_type": a.account_type,
                "balance": float(a.balance),
            }
            for a in accts
        ],
    }


@api_router.post("/finance/accounts", tags=["Finance"])
def create_financial_account(
    payload: schemas.FinancialAccountCreate,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_any_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT):
        raise HTTPException(status_code=403, detail="Finance authorization required.")
    acct = models.FinancialAccount(
        account_name=payload.account_name,
        account_type=payload.account_type,
        account_number=payload.account_number,
        balance=payload.opening_balance or Decimal("0"),
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return {"account_id": acct.account_id, "account_name": acct.account_name}


# =====================================================================
# /api/inventory/opening-stock
# =====================================================================

@api_router.post("/inventory/opening-stock", tags=["Inventory"])
def post_opening_stock(
    payload: schemas.OpeningStockCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "inventory:manage"):
        raise HTTPException(status_code=403, detail="Inventory management permission required.")
    result = erp_service.record_opening_stock(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request),
    )
    return result


# =====================================================================
# /api/transfers (Stock Transfer)
# =====================================================================

@api_router.post("/transfers", tags=["Inventory"])
def create_stock_transfer(
    payload: schemas.StockTransferCreate,
    request: Request,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "inventory:adjust"):
        raise HTTPException(status_code=403, detail="Inventory adjustment permission required.")
    return erp_service.execute_stock_transfer(
        payload=payload,
        current_user=current_user,
        db=db,
        ip_address=request_ip(request),
    )


# =====================================================================
# /api/returns (Sales Returns)
# =====================================================================

@api_router.post("/returns", tags=["Sales & POS"])
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


@api_router.get("/returns", tags=["Sales & POS"])
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

@api_router.get("/customers", tags=["Sales & POS"])
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


@api_router.post("/customers", tags=["Sales & POS"])
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


@api_router.post("/customers/credit-account", tags=["Sales & POS"])
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


@api_router.post("/customers/credit-payment", tags=["Sales & POS"])
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


# =====================================================================
# /api/users (User Management by Admin)
# =====================================================================

@api_router.get("/users", tags=["Administration"])
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


@api_router.post("/users/assign-role", tags=["Administration"])
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


@api_router.post("/users/toggle-active", tags=["Administration"])
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


@api_router.post("/users/unlock", tags=["Administration"])
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


@api_router.post("/users/reset-password", tags=["Administration"])
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


# =====================================================================
# /api/payroll/payslips (Payslip access with privacy enforcement)
# =====================================================================

@api_router.get("/payroll/payslips", tags=["HR & Payroll"])
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


# =====================================================================
# /api/reports (Department Report Endpoints)
# =====================================================================

@api_router.get("/reports/sales", tags=["Reports"])
def sales_report(
    branch_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "sales:view"):
        raise HTTPException(status_code=403, detail="Sales view permission required.")
    q = scope_sales_query(
        db,
        current_user,
        db.query(models.Sale).filter(models.Sale.status == "COMPLETED"),
        branch_id,
    )
    if date_from:
        q = q.filter(models.Sale.saledate >= date_from)
    if date_to:
        q = q.filter(models.Sale.saledate <= date_to)
    sales = q.all()
    total_rev = sum([s.totalamount or Decimal("0") for s in sales], Decimal("0"))
    total_cogs = Decimal("0")
    for s in sales:
        for i in s.sale_items:
            total_cogs += (i.unitcost or Decimal("0")) * i.quantity
    return {
        "total_revenue": float(total_rev),
        "total_cogs": float(total_cogs),
        "gross_profit": float(total_rev - total_cogs),
        "gross_margin_pct": float((total_rev - total_cogs) / total_rev * 100) if total_rev > 0 else 0.0,
        "transaction_count": len(sales),
        "average_basket": float(total_rev / len(sales)) if sales else 0.0,
    }


@api_router.get("/reports/inventory", tags=["Reports"])
def inventory_report(
    warehouse_id: Optional[int] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "inventory:view"):
        raise HTTPException(status_code=403, detail="Inventory view permission required.")
    q = db.query(models.InventoryBalance)
    if warehouse_id:
        q = q.filter(models.InventoryBalance.warehouse_id == warehouse_id)
    balances = q.all()
    total_val = Decimal("0")
    out_stock = 0
    low_stock = 0
    for b in balances:
        cost = b.product.costprice or Decimal("0")
        avail = b.available_stock or Decimal("0")
        total_val += avail * cost
        reorder = b.product.reorderlevel or 0
        if avail <= 0:
            out_stock += 1
        elif avail <= reorder:
            low_stock += 1
    return {
        "total_inventory_value": float(total_val),
        "out_of_stock_count": out_stock,
        "low_stock_count": low_stock,
        "product_count": len(balances),
    }


@api_router.get("/reports/payroll", tags=["Reports"])
def payroll_report(
    month: Optional[str] = None,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Rule 9: only HR/Finance/Admin
    if not auth.has_permission(db, current_user, "payroll:view"):
        raise HTTPException(status_code=403, detail="Payroll view permission required.")
    q = db.query(models.PayrollRun)
    if month:
        q = q.filter(models.PayrollRun.month == month)
    runs = q.order_by(models.PayrollRun.created_at.desc()).limit(12).all()
    return [
        {
            "run_id": r.run_id,
            "month": r.month,
            "status": r.status,
            "total_gross": float(r.total_gross),
            "total_deductions": float(r.total_deductions),
            "total_net": float(r.total_net),
            "created_at": r.created_at,
            "approved_at": r.approved_at,
        }
        for r in runs
    ]


# =====================================================================
# /api/audit-logs (Extended, role-protected)
# =====================================================================

@api_router.get("/audit-logs", tags=["Administration"])
def get_api_audit_logs(
    module: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not auth.has_permission(db, current_user, "admin:audit"):
        raise HTTPException(status_code=403, detail="Audit log access requires admin:audit permission.")
    q = db.query(models.AuditLog)
    if module:
        q = q.filter(models.AuditLog.module == module)
    if action:
        q = q.filter(models.AuditLog.action == action)
    if user_id:
        q = q.filter(models.AuditLog.user_id == user_id)
    total = q.count()
    items = q.order_by(desc(models.AuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "auditlogid": a.auditlogid,
                "user_id": a.user_id,
                "username_or_email": a.username_or_email,
                "action": a.action,
                "module": a.module,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "branch_id": a.branch_id,
                "details": a.details,
                "ip_address": a.ip_address,
                "timestamp": a.timestamp,
            }
            for a in items
        ],
    }
