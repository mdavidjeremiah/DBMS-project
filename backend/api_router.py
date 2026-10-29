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
from api_helpers import can_view_procurement, employee_branch_ids, employee_name, scope_sales_query

api_router = APIRouter(prefix="/api")
PROFILE_PHOTO_DIR = Path(__file__).resolve().parent / "uploads" / "profile-photos"
DEFAULT_PROFILE_PHOTO_DIR = Path(__file__).resolve().parent / "default-profile-photos"
MAX_PROFILE_PHOTO_BYTES = 5 * 1024 * 1024
DEFAULT_PROFILE_PHOTO_BY_NAME = {
    "kiconco flavia": "kiconco-flavia.webp",
}
PROFILE_PHOTO_FORMATS = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}


def employee_profile_photo_filename(employee: models.Employee) -> Optional[str]:
    if employee.profile_photo_filename:
        return Path(employee.profile_photo_filename).name
    normalized_name = " ".join((employee.name or "").casefold().split())
    return DEFAULT_PROFILE_PHOTO_BY_NAME.get(normalized_name)


def employee_profile_photo_url(employee: models.Employee) -> Optional[str]:
    if not employee_profile_photo_filename(employee):
        return None
    return f"/api/users/{employee.employeeid}/profile-photo"



def backup_admin(current_user: models.Employee = Depends(auth.get_current_user)):
    if current_user.roletype != models.RoleType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    return current_user


@api_router.get("/backups/status", tags=["Backups"])
def csv_backup_status(current_user=Depends(backup_admin)):
    import json
    from csv_backup import backup_directory, backup_lock
    root = backup_directory()
    with backup_lock(root):
        error = root / "last-error.txt"
        result = {"available": False, "last_error": error.read_text(encoding="utf-8") if error.exists() else None}
        if (root / "CURRENT").exists():
            folder = root / (root / "CURRENT").read_text(encoding="utf-8")
            result.update(available=True, manifest=json.loads((folder / "manifest.json").read_text(encoding="utf-8")))
        return result


@api_router.post("/backups/export", tags=["Backups"])
def download_csv_backup(current_user=Depends(backup_admin)):
    import io
    import zipfile
    from fastapi.responses import Response
    from database import engine
    from csv_backup import backup_directory, backup_lock, create_snapshot
    root = backup_directory()
    create_snapshot(engine)
    # Hold the lock while packaging so another commit cannot remove the snapshot.
    with backup_lock(root):
        folder = root / (root / "CURRENT").read_text(encoding="utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in folder.iterdir():
                archive.write(source, source.name)
    return Response(buffer.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": 'attachment; filename="hardware-world-csv-backup.zip"'
    })

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
        "profile_photo_url": employee_profile_photo_url(current_user),
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


@api_router.post("/users/generate-temporary-password", tags=["Administration"])
def generate_employee_temporary_password(
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.has_permission(db, current_user, "admin:users"):
        raise HTTPException(status_code=403, detail="Admin authorization required.")
    return {"temporary_password": auth.generate_temporary_password()}


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
    if not employee:
        raise HTTPException(status_code=404, detail="Profile photo not found.")

    filename = employee_profile_photo_filename(employee)
    if not filename:
        raise HTTPException(status_code=404, detail="Profile photo not found.")
    photo_directory = PROFILE_PHOTO_DIR if employee.profile_photo_filename else DEFAULT_PROFILE_PHOTO_DIR
    photo_path = photo_directory / filename
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

    if not any(auth.has_permission(db,current_user,p) for p in ("hr:view","hr:manage","payroll:view","admin:users")):
        raise HTTPException(403,"Employee directory permission required")
    query=db.query(models.Employee)
    if not auth.has_permission(db,current_user,"admin:users"):
        query=query.filter(models.Employee.branchid.in_(employee_branch_ids(db,current_user)))
    employees=query.order_by(models.Employee.name).all()
    result = []
    for e in employees:
        is_self = e.employeeid == current_user.employeeid
        salary_val = float(e.salary or 0) if (can_view_salary or is_self) else None

        result.append({
            "employeeid": e.employeeid,
            "name": e.name,
            "profile_photo_url": employee_profile_photo_url(e),
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
        ).join(models.Warehouse,models.Warehouse.warehouse_id == models.InventoryBalance.warehouse_id).filter(models.Warehouse.branch_id.in_(employee_branch_ids(db,current_user)))
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
    q = db.query(models.InventoryBalance).join(models.Warehouse).filter(models.Warehouse.branch_id.in_(employee_branch_ids(db,current_user)))
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
    q = db.query(models.InventoryMovement).join(models.Warehouse).filter(models.Warehouse.branch_id.in_(employee_branch_ids(db,current_user)))
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
    if not auth.has_permission(db, current_user, "procurement:requisition"):
        raise HTTPException(403, "Requisition permission required")
    erp_service.require_branch_access(db, current_user, payload.branch_id or current_user.branchid)
    req = models.PurchaseRequisition(
        requester_id=current_user.employeeid,
        branch_id=payload.branch_id or current_user.branchid,
        reference="REQ-" + secrets.token_hex(10),
        notes=payload.notes,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()

    for item in payload.items:
        db.add(models.PurchaseRequisitionItem(
            requisition_id=req.requisition_id,
            item_id=item.itemid,
            quantity=item.quantity,
            estimated_unit_price=item.estimated_unit_cost or Decimal("0"),
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
    req = erp_service.approve_or_reject_requisition(req_id, "APPROVE", current_user, None, db)
    return {"requisition_id": req.id, "status": req.status}

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

    if payload.requisition_id:
        req = db.query(models.PurchaseRequisition).filter_by(id=payload.requisition_id).with_for_update().first()
        if not req or req.status != "APPROVED" or req.branch_id != branch_id:
            raise HTTPException(409, "An approved requisition in this branch is required")
        if db.query(models.PurchaseOrder).filter_by(requisition_id=req.id).first():
            raise HTTPException(409, "This requisition already has an order")
        if not payload.items:
            payload.items = [schemas.PurchaseOrderItemCreate(item_id=i.itemid,quantity=i.quantity,unit_price=i.estimated_unit_cost) for i in req.items]
    total = Decimal("0")
    if payload.items:
        for itm in payload.items:
            if not db.get(models.Product, itm.item_id):
                raise HTTPException(404, "Product not found")
            total += itm.unit_price * itm.quantity

    if not payload.items:
        raise HTTPException(422, "At least one purchase order item is required")
    if not db.get(models.Supplier, payload.supplierid):
        raise HTTPException(404, "Supplier not found")
    po = models.PurchaseOrder(
        supplierid=payload.supplierid,
        requisition_id=payload.requisition_id,
        employeeid=current_user.employeeid,
        branch_id=branch_id,
        status=models.POStatus.PENDING,
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
    return {"grn_id": grn.id, "grn_number": grn.reference, "status": grn.status}

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
    return {"invoice_id": invoice.id, "invoice_number": invoice.invoice_number, "matched_status": invoice.status}

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
    return {"payment_id": payment.id, "amount": float(payment.amount)}

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
    if not auth.has_permission(db, current_user, "payroll:prepare"):
        raise HTTPException(status_code=403, detail="Payroll preparation permission required.")

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
    if not auth.has_permission(db, current_user, "payroll:approve"):
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
    employee = db.get(models.Employee, payload.employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    erp_service.require_branch_access(db,current_user,employee.branchid)
    if payload.status not in {"PRESENT", "ABSENT", "HALF_DAY", "LATE", "ON_LEAVE"}:
        raise HTTPException(422, "Invalid attendance status")
    if payload.check_in and payload.check_out and payload.check_out < payload.check_in:
        raise HTTPException(422, "Check-out cannot precede check-in")
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
    employee = db.get(models.Employee, payload.employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    erp_service.require_branch_access(db,current_user,employee.branchid)
    if payload.end_date < payload.start_date:
        raise HTTPException(422, "Leave end date cannot precede start date")
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

# Keep the API facade small while mounting domain route modules on the same /api prefix.
from api_dashboard_routes import router as dashboard_router
from api_approval_routes import router as approval_router
from api_sales_routes import router as sales_router
from api_admin_routes import router as admin_router
from api_payroll_routes import router as payroll_router
from api_report_routes import router as report_router

for domain_router in (dashboard_router, approval_router, sales_router, admin_router, payroll_router, report_router):
    api_router.include_router(domain_router)

from api_workflow_routes import router as workflow_router
api_router.include_router(workflow_router)
