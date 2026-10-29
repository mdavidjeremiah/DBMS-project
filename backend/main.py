import os
import secrets
import uuid
from typing import Optional
from datetime import timedelta, datetime
from fastapi import BackgroundTasks, FastAPI, Depends, HTTPException, status, Request, Query, Header, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from jose import JWTError, jwt
from starlette.background import BackgroundTasks as StarletteBackgroundTasks
from decimal import Decimal

import models
import schemas
import auth
import erp_service
from database import engine, get_db
from audit import request_ip, write_audit_log
from api_router import api_router, employee_profile_photo_url
from bootstrap_admin import ensure_configured_admin

app = FastAPI(
    title="Hardware World API",
    description="API for Hardware World inventory, sales, procurement, payroll, and accounting operations.",
    version="1.0.0",
    docs_url=None,
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "system", "description": "Health checks and public application endpoints."},
        {"name": "authentication", "description": "Login and user provisioning endpoints."},
        {"name": "organisation", "description": "Branches, departments, and employee endpoints."},
        {"name": "catalogue", "description": "Categories, products, and suppliers."},
        {"name": "operations", "description": "Purchase orders, payroll, sales, and ledger entries."},
    ],
)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))
swagger_ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swagger-ui")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/swagger-ui/favicon-32x32.png",
    )

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}

AUDIT_EXCLUDED_PATHS = {"/login", "/logout", "/audit/page-view", "/departments/public", "/openapi.json", "/docs", "/redoc"}


def add_audit_background_task(response, **event):
    """Attach audit persistence after the response so normal requests stay responsive."""
    background = StarletteBackgroundTasks()
    if response.background is not None:
        background.add_task(response.background)
    background.add_task(write_audit_log, **event)
    response.background = background


def audit_identity_from_request(request: Request):
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        token = request.cookies.get("hw_access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
        return {"username_or_email": email, "user_id": None} if email else None
    except JWTError:
        return None


@app.middleware("http")
async def audit_protected_api_access(request: Request, call_next):
    path = request.url.path
    if path.endswith((".mjs", ".json", ".txt")) and not path.startswith("/api/") and path != "/openapi.json":
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail":"Not found"},status_code=404)
    response = await call_next(request)
    if path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    identity = audit_identity_from_request(request)
    if (
        identity
        and request.method != "OPTIONS"
        and path not in AUDIT_EXCLUDED_PATHS
        and not path.startswith("/assets/")
        and not path.endswith(".html")
    ):
        if response.status_code in (401, 403):
            action = "ACCESS_DENIED"
        elif request.method == "GET":
            action = "DATABASE_QUERY"
        else:
            action = "DATABASE_MODIFICATION"
        add_audit_background_task(
            response,
            **identity,
            action=action,
            details=f"{request.method} {path} returned {response.status_code}",
            ip_address=request_ip(request),
        )
    return response

@app.get("/", tags=["system"])
def read_root():
    frontend_index = os.path.join(frontend_dir, "index.html")
    return FileResponse(frontend_index)

@app.get("/departments/public", tags=["organisation"])
def get_public_departments(db: Session = Depends(get_db)):
    """Public endpoint for login page department dropdown."""
    departments = db.query(models.Department).order_by(models.Department.departmentname).all()
    return [{"departmentid": d.departmentid, "departmentname": d.departmentname, "branchid": d.branchid} for d in departments]

def require_role(current_user: models.Employee, *roles: models.RoleType, allow_system_admin: bool = False):
    role_aliases = {
        models.RoleType.ADMIN: {"System Administrator"},
        models.RoleType.BRANCH_MANAGER: {"Branch Manager", "General Manager", "Owner / Executive"},
        models.RoleType.CASHIER: {"Cashier", "Sales Manager", "Sales Clerk"},
        models.RoleType.PROCUREMENT_OFFICER: {"Procurement Officer", "Procurement Manager", "Storekeeper", "Warehouse Supervisor", "Inventory Manager"},
        models.RoleType.ACCOUNTANT: {"Accountant", "Finance Clerk", "Finance Manager"},
        models.RoleType.HR_STAFF: {"HR Officer", "HR Manager"},
    }
    permission_roles = tuple(role for role in roles if role != models.RoleType.ADMIN)
    permitted_names = set().union(*(role_aliases.get(role, set()) for role in permission_roles))
    assigned_names = {role.name for role in current_user.erp_roles}
    assigned_names.update(
        assignment.role.role_name
        for assignment in current_user.user_roles
        if assignment.role is not None
    )
    if current_user.roletype == models.RoleType.ADMIN:
        if allow_system_admin or roles == (models.RoleType.ADMIN,):
            return
        if not (assigned_names & permitted_names):
            raise HTTPException(status_code=403, detail="Not authorized for this operation")
    elif current_user.roletype not in roles and not (assigned_names & permitted_names):
        raise HTTPException(status_code=403, detail="Not authorized for this operation")

def employee_name(db: Session, employeeid: int | None):
    employee = db.query(models.Employee).filter(models.Employee.employeeid == employeeid).first() if employeeid else None
    return employee.name if employee else "Unknown employee"

def branch_name(db: Session, branchid: int | None):
    branch = db.query(models.Branch).filter(models.Branch.branchid == branchid).first() if branchid else None
    return branch.branchname if branch else "Unknown branch"

def user_profile(current_user: models.Employee, db: Session):
    roles = [r.name for r in current_user.erp_roles] or [current_user.roletype.value]
    permissions = auth.get_user_permissions(db, current_user)
    return {
        "employeeid": current_user.employeeid, "name": current_user.name,
        "email": current_user.email,
        "profile_photo_url": employee_profile_photo_url(current_user),
        "roletype": current_user.roletype.value,
        "departmentid": current_user.departmentid,
        "department_name": current_user.department.departmentname if current_user.department else None,
        "branchid": current_user.branchid,
        "branch_name": current_user.branch.branchname if current_user.branch else None,
        "roles": roles, "permissions": permissions,
    }

def assign_primary_erp_role(db: Session, employee: models.Employee):
    role_name = {
        models.RoleType.ADMIN: "System Administrator",
        models.RoleType.CASHIER: "Cashier",
        models.RoleType.PROCUREMENT_OFFICER: "Procurement Officer",
        models.RoleType.ACCOUNTANT: "Accountant",
        models.RoleType.HR_STAFF: "HR Officer",
        models.RoleType.BRANCH_MANAGER: "Branch Manager",
    }[employee.roletype]
    role = db.query(models.ERPRole).filter_by(name=role_name).first()
    if not role:
        role = models.ERPRole(name=role_name)
        db.add(role)
        db.flush()
    if role not in employee.erp_roles:
        employee.erp_roles.append(role)


def record_login_failure(db: Session, user: Optional[models.Employee], username: str, request: Request, reason: str):
    now = datetime.utcnow()
    if user and user.is_active:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        user.last_failed_login_at = now
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            db.add(models.PasswordEvent(
                user_id=user.employeeid,
                event_type="ACCOUNT_LOCKED",
                timestamp=now,
                ip_address=request_ip(request),
                reason="Failed sign-in limit reached",
            ))
    db.add(models.AuditLog(
        user_id=user.employeeid if user else None,
        username_or_email=(user.email or user.name) if user else (username or None),
        action="LOGIN_FAILED",
        module="authentication",
        details=reason,
        ip_address=request_ip(request),
    ))
    db.commit()


@app.post("/register", response_model=schemas.UserResponse, tags=["authentication"])
def register_user(
    user: schemas.UserCreate, 
    request: Request,
    db: Session = Depends(get_db), 
    current_user: models.Employee = Depends(auth.get_current_user)
):
    # Only Administrator can provision new users into the system
    require_role(current_user, models.RoleType.ADMIN)
    
    db_user = db.query(models.Employee).filter(models.Employee.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.Employee(
        name=user.name,
        nin=user.nin,
        email=user.email,
        hashed_password=hashed_password,
        must_change_password=True,
        temporary_password_expires_at=auth.temporary_password_expiry(),
        phone=user.phone,
        datehired=user.datehired or datetime.utcnow().date(),
        salary=user.salary,
        departmentid=user.departmentid,
        branchid=user.branchid,
        supervisorid=user.supervisorid,
        roletype=user.roletype
    )
    db.add(new_user)
    db.flush()
    assign_primary_erp_role(db, new_user)
    db.add(models.PasswordEvent(
        user_id=new_user.employeeid,
        event_type="INITIAL_PASSWORD_CREATED",
        initiated_by_user_id=current_user.employeeid,
        ip_address=request_ip(request),
        reason="Temporary initial password issued by administrator",
    ))
    db.add(models.AuditLog(
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="USER_ACCOUNT_CREATED",
        module="admin",
        entity_type="employee",
        entity_id=new_user.employeeid,
        details=f"Created sign-in account for employee #{new_user.employeeid}; temporary password issued",
        ip_address=request_ip(request),
    ))
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=None, tags=["authentication"])
async def login_for_access_token(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    cookie_only: bool = Query(False, include_in_schema=False),
    db: Session = Depends(get_db),
):
    """
    Unified Authentication Endpoint with:
    - Support for JSON payload and Form Data
    - Name or Email lookup
    - Role-Based Access Control (RBAC) validation
    - Attribute-Based Access Control (ABAC) department matching
    """
    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""
    selected_dept = None
    login_type = "staff"

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = str(body.get("username", "")).strip()
            password = str(body.get("password", ""))
            selected_dept = body.get("department")
            login_type = str(body.get("login_type", "staff")).strip().lower()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        selected_dept = form.get("department")
        login_type = str(form.get("login_type", "staff")).strip().lower()

    if not username or not password:
        write_audit_log(action="FAILED_LOGIN", username_or_email=username or None, details="Login attempt missing username or password", ip_address=request_ip(request))
        raise HTTPException(status_code=400, detail="Username/Email and Password are required")

    if login_type not in {"admin", "staff"}:
        raise HTTPException(status_code=400, detail="Login type must be 'admin' or 'staff'.")

    admin_name = os.getenv("ADMIN_NAME", "").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    configured_usernames = {value.lower() for value in (admin_name, admin_email) if value}
    is_configured_admin_username = username.lower() in configured_usernames

    if login_type == "admin" or is_configured_admin_username:
        if (
            not is_configured_admin_username
            or not admin_password
            or not secrets.compare_digest(password.encode("utf-8"), admin_password.encode("utf-8"))
        ):
            write_audit_log(action="FAILED_LOGIN", username_or_email=username or None, details="Invalid configured administrator credentials", ip_address=request_ip(request))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect administrator username/email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        login_type = "admin"
        user = ensure_configured_admin(db)
        db.commit()
    else:
        # Lookup user by Email OR Full Name (case-insensitive)
        user = db.query(models.Employee).filter(
            or_(
                func.lower(models.Employee.email) == username.lower(),
                func.lower(models.Employee.name) == username.lower()
            )
        ).first()

    if not user or not user.hashed_password or (
        login_type == "staff" and not auth.verify_password(password, user.hashed_password)
    ):
        record_login_failure(db, user, username, request, "Invalid sign-in details")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sign-in details or department selection.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.utcnow()
    if not user.is_active or (user.locked_until and user.locked_until > now):
        record_login_failure(db, user, username, request, "Login blocked by account status or temporary lock")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sign-in details or department selection.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. RBAC (Role-Based Access Control) Policy Check:
    if login_type == "admin":
        if user.roletype != models.RoleType.ADMIN:
            write_audit_log(user_id=user.employeeid, username_or_email=user.email or user.name, action="ACCESS_DENIED", details="Non-admin account attempted to use the administrator portal", ip_address=request_ip(request))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied (RBAC): Your account role is '{user.roletype.value}'. Only Administrators can log in through the Admin Portal."
            )

    # 2. ABAC (Attribute-Based Access Control) Policy Check:
    # If logging in as staff, check department match
    if login_type == "staff":
        if user.roletype != models.RoleType.ADMIN:
            if not selected_dept:
                record_login_failure(db, user, username, request, "Staff login did not include a department selection")
                raise HTTPException(status_code=401, detail="Invalid sign-in details or department selection.")
            user_dept = user.department.departmentname if user.department else ""
            # Match against department name or department ID
            is_name_match = user_dept.strip().lower() == str(selected_dept).strip().lower()
            is_id_match = str(user.departmentid) == str(selected_dept).strip()

            if not (is_name_match or is_id_match):
                record_login_failure(db, user, username, request, "Staff login attempted with a different department")
                raise HTTPException(status_code=401, detail="Invalid sign-in details or department selection.")

    if user.must_change_password and user.temporary_password_expires_at and user.temporary_password_expires_at <= now:
        db.add(models.PasswordEvent(
            user_id=user.employeeid,
            event_type="TEMP_PASSWORD_EXPIRED",
            timestamp=now,
            ip_address=request_ip(request),
            reason="Temporary password expired before first use",
        ))
        db.add(models.AuditLog(
            user_id=user.employeeid,
            username_or_email=user.email or user.name,
            action="TEMP_PASSWORD_EXPIRED",
            module="authentication",
            details="Temporary sign-in password expired",
            ip_address=request_ip(request),
        ))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid sign-in details or department selection.")

    dept_name = user.department.departmentname if user.department else "General"
    user.failed_login_attempts = 0
    user.last_failed_login_at = None
    user.locked_until = None
    user.last_login_at = now
    if user.must_change_password:
        access_token = auth.create_access_token(
            data={
                "sub": user.email,
                "purpose": "initial-password-change",
                "tv": user.token_version or 0,
            },
            expires_delta=timedelta(minutes=15),
        )
        response.set_cookie(
            key="hw_access_token",
            value=access_token,
            max_age=15 * 60,
            path="/",
            secure=auth.COOKIE_SECURE,
            httponly=True,
            samesite="lax",
        )
        db.add(models.AuditLog(
            user_id=user.employeeid,
            username_or_email=user.email or user.name,
            action="LOGIN_SUCCESS",
            module="authentication",
            details="Temporary password accepted; password change required",
            ip_address=request_ip(request),
        ))
        db.commit()
        return {
            "requires_password_change": True,
            "next_route": "change-password.html",
        }

    db.commit()
    access_token = auth.create_access_token(
        data={
            "sub": user.email, 
            "name": user.name,
            "role": user.roletype.value,
            "departmentid": user.departmentid,
            "departmentname": dept_name,
            "branchid": user.branchid,
            "tv": user.token_version or 0,
        }, 
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    background_tasks.add_task(
        write_audit_log,
        user_id=user.employeeid,
        username_or_email=user.email or user.name,
        action="LOGIN_SUCCESS",
        details=f"Successful {login_type} portal login",
        ip_address=request_ip(request),
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
    if cookie_only:
        return {"detail": "Authenticated"}
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/logout")
def logout(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    current_user: models.Employee = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    response.delete_cookie(
        key="hw_access_token",
        path="/",
        secure=auth.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    background_tasks.add_task(
        write_audit_log,
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="LOGOUT",
        details="User signed out",
        ip_address=request_ip(request),
    )
    return {"detail": "Logged out"}


@app.post("/audit/page-view")
def record_page_view(
    payload: schemas.AuditPageView,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: models.Employee = Depends(auth.get_current_user),
):
    background_tasks.add_task(
        write_audit_log,
        user_id=current_user.employeeid,
        username_or_email=current_user.email or current_user.name,
        action="VIEW_PAGE",
        details=f"Viewed protected page: {payload.page[:255]}",
        ip_address=request_ip(request),
    )
    return {"detail": "Page view recorded"}

@app.get("/users/me", tags=["authentication"])
def read_users_me(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return user_profile(current_user, db)


@app.get("/audit-logs", response_model=schemas.AuditLogPage)
def get_audit_logs(
    user: Optional[str] = Query(None, max_length=100),
    action: Optional[str] = Query(None, max_length=64),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.Employee = Depends(auth.get_current_user),
):
    require_role(current_user, models.RoleType.ADMIN)
    query = db.query(models.AuditLog)
    if user:
        if user.isdigit():
            query = query.filter(or_(models.AuditLog.user_id == int(user), models.AuditLog.username_or_email.ilike(f"%{user}%")))
        else:
            query = query.filter(models.AuditLog.username_or_email.ilike(f"%{user}%"))
    if action:
        query = query.filter(models.AuditLog.action == action)
    if start_date:
        query = query.filter(models.AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.AuditLog.timestamp <= end_date)

    total = query.count()
    items = query.order_by(models.AuditLog.timestamp.desc(), models.AuditLog.auditlogid.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# Example of a protected endpoint
@app.get("/branches", response_model=list[schemas.BranchResponse], tags=["organisation"])
def get_branches(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    query = db.query(models.Branch)
    if current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.Branch.branchid == current_user.branchid)
    branches = query.all()
    return branches

@app.post("/branches", response_model=schemas.BranchResponse, tags=["organisation"])
def create_branch(branch: schemas.BranchCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN)
    new_branch = models.Branch(**branch.dict())
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch

@app.get("/departments", tags=["organisation"])
def get_departments(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    query = db.query(models.Department)
    if current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.Department.branchid == current_user.branchid)
    return [{"departmentid": d.departmentid, "departmentname": d.departmentname, "branchid": d.branchid, "branch_name": branch_name(db, d.branchid)} for d in query.order_by(models.Department.departmentname).all()]

@app.get("/categories", tags=["catalogue"])
def get_categories(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return [{"categoryid": c.categoryid, "categoryname": c.categoryname} for c in db.query(models.Category).order_by(models.Category.categoryname).all()]

@app.post("/categories", tags=["catalogue"])
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    category = models.Category(categoryname=payload.categoryname); db.add(category); db.commit(); db.refresh(category)
    return {"categoryid": category.categoryid, "categoryname": category.categoryname}

@app.get("/products", tags=["catalogue"])
@app.get("/api/v1/inventory/products", tags=["catalogue"])
def get_products(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    products = db.query(models.Product).order_by(models.Product.itemname).all()
    result = []
    for p in products:
        balance = db.query(func.coalesce(func.sum(models.InventoryBalance.available_stock), 0)).join(models.Warehouse, models.InventoryBalance.warehouse_id == models.Warehouse.warehouse_id).filter(models.InventoryBalance.item_id == p.itemid, models.Warehouse.branch_id == current_user.branchid).scalar() or 0
        result.append({"itemid": p.itemid, "itemname": p.itemname, "description": p.description, "unitprice": str(p.unitprice), "reorderlevel": p.reorderlevel or 0, "categoryid": p.categoryid, "category_name": p.category.categoryname if p.category else "Unknown category", "is_active": p.is_active, "stock_qty": str(balance)})
    return result

@app.get("/inventory/balances", tags=["catalogue"])
@app.get("/api/v1/inventory/balances", tags=["catalogue"])
def get_inventory_balances(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    from api_router import get_api_inventory
    return get_api_inventory(None,current_user,db)

@app.post("/products", tags=["catalogue"])
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    product = models.Product(**payload.model_dump()); db.add(product); db.commit(); db.refresh(product)
    return {"itemid": product.itemid, "itemname": product.itemname}

@app.get("/suppliers", tags=["catalogue"])
def get_suppliers(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return [{"supplierid": s.supplierid, "suppliername": s.suppliername, "contactperson": s.contactperson, "phone": s.phone, "address": s.address} for s in db.query(models.Supplier).order_by(models.Supplier.suppliername).all()]

@app.post("/suppliers", tags=["catalogue"])
def create_supplier(payload: schemas.SupplierCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    supplier = models.Supplier(**payload.model_dump()); db.add(supplier); db.commit(); db.refresh(supplier)
    return {"supplierid": supplier.supplierid, "suppliername": supplier.suppliername}

@app.get("/employees", tags=["organisation"])
def get_employees(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF, models.RoleType.ACCOUNTANT, allow_system_admin=True)
    employees = db.query(models.Employee).order_by(models.Employee.name).all()
    return [{
        "employeeid": e.employeeid,
        "name": e.name,
        "profile_photo_url": employee_profile_photo_url(e),
        "email": e.email,
        "nin": e.nin,
        "phone": e.phone,
        "datehired": e.datehired,
        "salary": float(e.salary or 0) if (
            auth.has_any_role(current_user, models.RoleType.HR_STAFF, models.RoleType.ACCOUNTANT)
            or auth.has_permission(db, current_user, "payroll:view")
        ) else None,
        "roletype": e.roletype.value,
        "departmentid": e.departmentid,
        "department_name": e.department.departmentname if e.department else "Unknown department",
        "branchid": e.branchid,
        "branch_name": branch_name(db, e.branchid),
        "supervisorid": e.supervisorid,
        "supervisor_name": employee_name(db, e.supervisorid),
        "account_status": (
            "INACTIVE" if not e.is_active
            else "LOCKED" if e.locked_until and e.locked_until > datetime.utcnow()
            else "PENDING_ACTIVATION" if not e.hashed_password
            else "PASSWORD_CHANGE_REQUIRED" if e.must_change_password
            else "ACTIVE"
        ),
        "is_locked": bool(e.is_active and e.locked_until and e.locked_until > datetime.utcnow()),
    } for e in employees]

@app.post("/employees", tags=["organisation"])
def create_employee(payload: schemas.EmployeeCreate, request: Request, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF, allow_system_admin=True)
    if payload.email and db.query(models.Employee).filter(func.lower(models.Employee.email) == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="An employee account already uses this email.")
    if current_user.roletype != models.RoleType.ADMIN and payload.password:
        raise HTTPException(status_code=403, detail="Only a System Administrator can issue employee passwords.")
    temporary_password = None
    expires_at = None
    if current_user.roletype == models.RoleType.ADMIN:
        if not payload.email:
            raise HTTPException(status_code=422, detail="An email address is required for a sign-in account.")
        temporary_password = payload.password or auth.generate_temporary_password()
        expires_at = auth.temporary_password_expiry()
    employee = models.Employee(
        name=payload.name,
        nin=payload.nin,
        email=payload.email,
        hashed_password=auth.get_password_hash(temporary_password) if temporary_password else None,
        must_change_password=temporary_password is not None,
        temporary_password_expires_at=expires_at,
        phone=payload.phone,
        datehired=payload.datehired,
        salary=payload.salary,
        departmentid=payload.departmentid,
        branchid=payload.branchid,
        supervisorid=payload.supervisorid,
        roletype=payload.roletype,
    )
    db.add(employee); db.flush()
    assign_primary_erp_role(db, employee)
    if payload.roletype == models.RoleType.BRANCH_MANAGER and payload.managementlevel == "Owner / Executive":
        executive_role = db.query(models.ERPRole).filter_by(name="Owner / Executive").first()
        if not executive_role:
            executive_role = models.ERPRole(name="Owner / Executive")
            db.add(executive_role)
            db.flush()
        if executive_role not in employee.erp_roles:
            employee.erp_roles.append(executive_role)
    subtype = {models.RoleType.CASHIER: models.Cashier(employeeid=employee.employeeid, pos_terminalid=payload.pos_terminalid or "unassigned"), models.RoleType.PROCUREMENT_OFFICER: models.ProcurementOfficer(employeeid=employee.employeeid, approvallimit=payload.approvallimit or 0), models.RoleType.ACCOUNTANT: models.Accountant(employeeid=employee.employeeid, certificationnumber=payload.certificationnumber), models.RoleType.HR_STAFF: models.HRStaff(employeeid=employee.employeeid, hr_role=payload.hr_role or "HR"), models.RoleType.BRANCH_MANAGER: models.BranchManager(employeeid=employee.employeeid, managementlevel=payload.managementlevel)}.get(payload.roletype)
    if subtype: db.add(subtype)
    if temporary_password:
        db.add(models.PasswordEvent(
            user_id=employee.employeeid,
            event_type="INITIAL_PASSWORD_CREATED",
            initiated_by_user_id=current_user.employeeid,
            ip_address=request_ip(request),
            reason="Temporary initial password issued by administrator",
        ))
        db.add(models.AuditLog(
            user_id=current_user.employeeid,
            username_or_email=current_user.email or current_user.name,
            action="USER_ACCOUNT_CREATED",
            module="admin",
            entity_type="employee",
            entity_id=employee.employeeid,
            details=f"Created sign-in account for employee #{employee.employeeid}; temporary password issued",
            ip_address=request_ip(request),
        ))
    db.commit(); db.refresh(employee)
    result = {"employeeid": employee.employeeid, "name": employee.name}
    if temporary_password:
        result.update({
            "temporary_password": temporary_password,
            "temporary_password_expires_at": expires_at.isoformat(),
            "must_change_password": True,
        })
    return result

@app.get("/purchase-orders", tags=["operations"])
@app.get("/api/v1/procurement/purchase-orders", tags=["operations"])
def get_purchase_orders(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER, models.RoleType.ACCOUNTANT, models.RoleType.BRANCH_MANAGER)
    query = db.query(models.PurchaseOrder)
    if current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.PurchaseOrder.branch_id == current_user.branchid)
    orders = query.order_by(models.PurchaseOrder.orderdate.desc()).all()
    return [{"po_id": o.po_id, "orderdate": o.orderdate, "status": o.status.value, "branch_id": o.branch_id, "supplier_name": db.query(models.Supplier).filter(models.Supplier.supplierid == o.supplierid).first().suppliername if db.query(models.Supplier).filter(models.Supplier.supplierid == o.supplierid).first() else "Unknown supplier", "officer_name": employee_name(db, o.employeeid), "items": [{"id": line.id, "itemid": line.itemid, "item_name": db.query(models.Product).filter_by(itemid=line.itemid).first().itemname, "quantity": str(line.quantity), "received_quantity": str(line.received_quantity), "remaining_quantity": str(line.quantity - line.received_quantity), "unit_cost": str(line.unit_cost)} for line in db.query(models.PurchaseOrderItem).filter_by(po_id=o.po_id).all()]} for o in orders]

@app.get("/purchase-requisitions", tags=["operations"])
@app.get("/api/v1/procurement/requisitions", tags=["operations"])
def get_purchase_requisitions(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER, models.RoleType.BRANCH_MANAGER)
    query = db.query(models.PurchaseRequisition)
    if current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.PurchaseRequisition.branch_id == current_user.branchid)
    return [{"id": r.id, "reference": r.reference, "branch_id": r.branch_id, "requested_by": employee_name(db, r.requested_by), "status": r.status, "notes": r.notes, "created_at": r.created_at, "items": [{"itemid": i.itemid, "item_name": db.query(models.Product).filter_by(itemid=i.itemid).first().itemname, "quantity": str(i.quantity), "estimated_unit_cost": str(i.estimated_unit_cost)} for i in db.query(models.PurchaseRequisitionItem).filter_by(requisition_id=r.id).all()]} for r in query.order_by(models.PurchaseRequisition.created_at.desc()).all()]

@app.post("/purchase-requisitions", tags=["operations"])
@app.post("/api/v1/procurement/requisitions", tags=["operations"])
def create_purchase_requisition(payload: schemas.PurchaseRequisitionCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    from api_router import create_requisition
    return create_requisition(payload, current_user, db)

@app.post("/purchase-requisitions/{requisition_id}/approve", tags=["operations"])
@app.post("/api/v1/procurement/requisitions/{requisition_id}/approve", tags=["operations"])
def approve_purchase_requisition(requisition_id: int, payload: schemas.ApprovalDecision, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    from api_router import approve_requisition
    return approve_requisition(requisition_id, current_user, db)

@app.post("/purchase-orders", tags=["operations"])
@app.post("/api/v1/procurement/purchase-orders", tags=["operations"])
def create_purchase_order(payload: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    from api_router import create_api_purchase_order
    return create_api_purchase_order(payload, current_user, db)

@app.post("/purchase-orders/{po_id}/approve", tags=["operations"])
@app.post("/api/v1/procurement/purchase-orders/{po_id}/approve", tags=["operations"])
def approve_purchase_order(po_id: int, payload: schemas.ApprovalDecision, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    if not auth.has_permission(db, current_user, "procurement:po_approve"):
        raise HTTPException(403, "Purchase approval permission required")
    order = erp_service.approve_or_reject_po(po_id, payload.action, current_user, payload.reason, db)
    return {"po_id": order.po_id, "status": order.status.value}

@app.post("/goods-received-notes", tags=["operations"])
@app.post("/api/v1/procurement/goods-received-notes", tags=["operations"])
def create_goods_received_note(payload: schemas.GRNCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    po = db.get(models.PurchaseOrder, payload.po_id)
    if not po:
        raise HTTPException(404, "Order not found")
    warehouse = db.query(models.Warehouse).filter_by(branch_id=po.branch_id,is_active=True).first()
    if not warehouse:
        raise HTTPException(409, "Create a warehouse before receiving goods")
    items=[]
    for item in payload.items:
        line=db.get(models.PurchaseOrderItem,item.po_item_id)
        if not line or line.po_id != po.po_id:
            raise HTTPException(422, "Receipt item is not on this order")
        items.append(schemas.GoodsReceivedNoteItemCreate(item_id=line.itemid,quantity_received=item.quantity,unit_cost=line.unit_cost))
    grn=erp_service.create_goods_received_note(schemas.GoodsReceivedNoteCreate(po_id=po.po_id,warehouse_id=warehouse.warehouse_id,items=items),current_user,db)
    return {"grn_id":grn.id,"reference":grn.reference,"status":grn.status}

@app.post("/supplier-invoices", tags=["operations"])
@app.post("/api/v1/finance/supplier-invoices", tags=["operations"])
def create_supplier_invoice(payload: schemas.SupplierInvoiceCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    from api_router import create_api_supplier_invoice
    return create_api_supplier_invoice(payload, None, current_user, db)

@app.post("/supplier-invoices/{invoice_id}/match", tags=["operations"])
@app.post("/api/v1/finance/supplier-invoices/{invoice_id}/match", tags=["operations"])
def match_supplier_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    if not auth.has_permission(db, current_user, "finance:invoice"):
        raise HTTPException(403, "Invoice permission required")
    invoice = db.get(models.SupplierInvoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    erp_service.require_branch_access(db, current_user, invoice.branch_id)
    return {"invoice_id": invoice.id, "matched": invoice.status in {"MATCHED", "PARTIAL", "PAID"}, "status": invoice.status}

@app.post("/supplier-payments", tags=["operations"])
@app.post("/api/v1/finance/supplier-payments", tags=["operations"])
def pay_supplier_invoice(payload: schemas.SupplierPaymentCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    from api_router import create_api_supplier_payment
    return create_api_supplier_payment(payload, None, current_user, db)

@app.get("/payroll", tags=["operations"])
@app.get("/api/v1/hr/payroll", tags=["operations"])
def get_payroll(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF, models.RoleType.ACCOUNTANT)
    query = db.query(models.Payroll)
    if current_user.roletype != models.RoleType.ADMIN:
        allowed_employees = db.query(models.Employee.employeeid).filter(models.Employee.branchid == current_user.branchid)
        query = query.filter(models.Payroll.employeeid.in_(allowed_employees))
    records = query.order_by(models.Payroll.month.desc()).all()
    return [{"payrollid": p.payrollid, "employeeid": p.employeeid, "employee_name": employee_name(db, p.employeeid), "month": p.month, "grosspay": float(p.grosspay), "deductions": float(p.deductions or 0), "netpay": float(p.netpay)} for p in records]

@app.post("/payroll", tags=["operations"])
@app.post("/api/v1/hr/payroll", tags=["operations"])
def create_payroll(payload: schemas.PayrollCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF)
    if payload.deductions > payload.grosspay: raise HTTPException(400, "Deductions cannot exceed gross pay")
    record = models.Payroll(**payload.model_dump(), netpay=payload.grosspay - payload.deductions); db.add(record); db.commit(); db.refresh(record); return record

@app.get("/sales", tags=["operations"])
@app.get("/api/v1/sales", tags=["operations"])
def get_sales(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    if not auth.has_permission(db, current_user, "sales:view"):
        raise HTTPException(status_code=403, detail="Sales view permission required.")
    query = db.query(models.Sale).filter(models.Sale.status == "COMPLETED")
    if current_user.roletype == models.RoleType.CASHIER:
        query = query.filter(models.Sale.employeeid == current_user.employeeid)
    elif current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.Sale.branchid == current_user.branchid)
    sales = query.order_by(models.Sale.saledate.desc()).all()
    result = []
    for sale in sales:
        customer = db.get(models.Customer, sale.customerid) if sale.customerid else None
        result.append({
            "saleid": sale.saleid,
            "saledate": sale.saledate,
            "totalamount": float(sale.totalamount or 0),
            "payment_method": sale.paymentmethod,
            "customer_name": customer.name if customer else "Walk-in",
            "cashier_name": employee_name(db, sale.employeeid),
            "branch_name": branch_name(db, sale.branchid),
            "items": [{
                "itemid": item.itemid,
                "item_name": item.product.itemname if item.product else "Unknown product",
                "quantity": float(item.quantity),
                "unitpriceatsale": float(item.unitpriceatsale),
                "line_total": float(item.line_total or (item.quantity * item.unitpriceatsale)),
            } for item in sale.sale_items],
        })
    return result

@app.get("/cashier-sessions/current", tags=["operations"])
@app.get("/api/v1/sales/cashier-sessions/current", tags=["operations"])
def get_current_cashier_session(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    session = db.query(models.CashierSession).filter_by(employee_id=current_user.employeeid, status="OPEN").order_by(models.CashierSession.opened_at.desc()).first()
    if not session:
        return None
    return {
        "session_id": session.session_id,
        "branch_id": session.branch_id,
        "warehouse_id": session.warehouse_id,
        "opening_float": str(session.opening_float),
        "status": session.status,
        "opened_at": session.opened_at,
    }

@app.post("/cashier-sessions/open", tags=["operations"])
@app.post("/api/v1/sales/cashier-sessions/open", tags=["operations"])
def open_cashier_session(payload: schemas.CashierSessionOpen, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    if not current_user.branchid:
        raise HTTPException(403, "Your account is not assigned to a branch")
    active = db.query(models.CashierSession).filter_by(employee_id=current_user.employeeid, status="OPEN").first()
    if active:
        return {"session_id": active.session_id, "status": active.status, "opening_float": str(active.opening_float)}
    warehouse = db.query(models.Warehouse).filter_by(branch_id=current_user.branchid, is_active=True).order_by(models.Warehouse.warehouse_id).first()
    if not warehouse:
        raise HTTPException(409, "Create an active warehouse for your branch before opening a cashier session")
    session = erp_service.open_cashier_session(
        employee_id=current_user.employeeid,
        branch_id=current_user.branchid,
        warehouse_id=warehouse.warehouse_id,
        opening_float=payload.opening_float,
        db=db,
    )
    return {"session_id": session.session_id, "status": session.status, "opening_float": str(session.opening_float)}

@app.post("/sales", tags=["operations"])
@app.post("/api/v1/sales", tags=["operations"])
def create_sale(payload: schemas.SaleCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user), idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    if not payload.items:
        raise HTTPException(400, "At least one sale item is required")
    if not current_user.branchid:
        raise HTTPException(403, "Your account is not assigned to a branch")
    cashier_session = db.query(models.CashierSession).filter_by(employee_id=current_user.employeeid, branch_id=current_user.branchid, status="OPEN").order_by(models.CashierSession.opened_at.desc()).first()
    if not cashier_session:
        raise HTTPException(409, "Open a cashier session before completing a sale")
    payload.branchid = current_user.branchid
    payload.warehouseid = cashier_session.warehouse_id
    payload.cashiersessionid = cashier_session.session_id
    payload.idempotency_key = payload.idempotency_key or idempotency_key
    return erp_service.process_pos_sale(payload=payload, current_user=current_user, db=db)

@app.get("/ledger", tags=["operations"])
@app.get("/api/v1/finance/ledger", tags=["operations"])
def get_ledger(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT, models.RoleType.BRANCH_MANAGER)
    entries = db.query(models.LedgerEntry).order_by(models.LedgerEntry.entrydate.desc()).all()
    return [{"entryid": e.entryid, "entrydate": e.entrydate, "sourcetype": e.sourcetype.value, "amount": float(e.amount), "source_label": f"Sale #{e.saleid}" if e.saleid else f"Payroll #{e.payrollid}", "accountant_name": employee_name(db, e.recordedby)} for e in entries]

@app.post("/ledger", tags=["operations"])
@app.post("/api/v1/finance/ledger", tags=["operations"])
def create_ledger(payload: schemas.LedgerCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
    entry = models.LedgerEntry(**payload.model_dump()); db.add(entry); db.commit(); db.refresh(entry); return entry


app.mount("/swagger-ui", StaticFiles(directory=swagger_ui_dir), name="swagger-ui")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
