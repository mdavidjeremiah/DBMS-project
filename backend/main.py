import os
import uuid
from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import timedelta, datetime
from decimal import Decimal

import models
import schemas
import auth
from database import engine, get_db

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

@app.get("/", tags=["system"])
def read_root():
    frontend_index = os.path.join(frontend_dir, "index.html")
    return FileResponse(frontend_index)

@app.get("/departments/public", tags=["organisation"])
def get_public_departments(db: Session = Depends(get_db)):
    """Public endpoint for login page department dropdown."""
    departments = db.query(models.Department).order_by(models.Department.departmentname).all()
    return [{"departmentid": d.departmentid, "departmentname": d.departmentname, "branchid": d.branchid} for d in departments]

def require_role(current_user: models.Employee, *roles: models.RoleType):
    role_aliases = {
        models.RoleType.ADMIN: {"System Administrator"},
        models.RoleType.BRANCH_MANAGER: {"Branch Manager", "General Manager", "Owner / Executive"},
        models.RoleType.CASHIER: {"Cashier", "Sales Manager", "Sales Clerk"},
        models.RoleType.PROCUREMENT_OFFICER: {"Procurement Officer", "Procurement Manager", "Storekeeper", "Warehouse Supervisor", "Inventory Manager"},
        models.RoleType.ACCOUNTANT: {"Accountant", "Finance Clerk", "Finance Manager", "Owner / Executive"},
        models.RoleType.HR_STAFF: {"HR Officer", "HR Manager"},
    }
    permitted_names = set().union(*(role_aliases.get(role, set()) for role in roles))
    assigned_names = {role.name for role in current_user.erp_roles}
    if current_user.roletype not in roles and not (assigned_names & permitted_names):
        raise HTTPException(status_code=403, detail="Not authorized for this operation")

def employee_name(db: Session, employeeid: int | None):
    employee = db.query(models.Employee).filter(models.Employee.employeeid == employeeid).first() if employeeid else None
    return employee.name if employee else "Unknown employee"

def branch_name(db: Session, branchid: int | None):
    branch = db.query(models.Branch).filter(models.Branch.branchid == branchid).first() if branchid else None
    return branch.branchname if branch else "Unknown branch"

def user_profile(current_user: models.Employee):
    roles = [r.name for r in current_user.erp_roles] or [current_user.roletype.value]
    permissions = sorted({p.code for role in current_user.erp_roles for p in role.permissions})
    return {
        "employeeid": current_user.employeeid, "name": current_user.name,
        "email": current_user.email, "roletype": current_user.roletype.value,
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

@app.post("/register", response_model=schemas.UserResponse, tags=["authentication"])
def register_user(
    user: schemas.UserCreate, 
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
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token, tags=["authentication"])
async def login_for_access_token(request: Request, db: Session = Depends(get_db)):
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
            password = str(body.get("password", "")).strip()
            selected_dept = body.get("department")
            login_type = str(body.get("login_type", "staff")).strip().lower()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", "")).strip()
        selected_dept = form.get("department")
        login_type = str(form.get("login_type", "staff")).strip().lower()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username/Email and Password are required")

    # Lookup user by Email OR Full Name (case-insensitive)
    user = db.query(models.Employee).filter(
        or_(
            func.lower(models.Employee.email) == username.lower(),
            func.lower(models.Employee.name) == username.lower()
        )
    ).first()

    if not user or not user.hashed_password or not auth.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. RBAC (Role-Based Access Control) Policy Check:
    if login_type == "admin":
        if user.roletype != models.RoleType.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied (RBAC): Your account role is '{user.roletype.value}'. Only Administrators can log in through the Admin Portal."
            )

    # 2. ABAC (Attribute-Based Access Control) Policy Check:
    # If logging in as staff, check department match
    if login_type == "staff":
        if user.roletype != models.RoleType.ADMIN and selected_dept:
            user_dept = user.department.departmentname if user.department else ""
            # Match against department name or department ID
            is_name_match = user_dept.strip().lower() == str(selected_dept).strip().lower()
            is_id_match = str(user.departmentid) == str(selected_dept).strip()

            if not (is_name_match or is_id_match):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied (ABAC): Department mismatch. Your user profile is assigned to '{user_dept}', but you selected '{selected_dept}'. Staff members can only log into their assigned department dashboard."
                )

    dept_name = user.department.departmentname if user.department else "General"
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={
            "sub": user.email, 
            "name": user.name,
            "role": user.roletype.value,
            "departmentid": user.departmentid,
            "departmentname": dept_name,
            "branchid": user.branchid
        }, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user_profile(user)}

@app.get("/users/me", tags=["authentication"])
def read_users_me(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return user_profile(current_user)


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
        balance = db.query(func.coalesce(func.sum(models.ERPStockBalance.quantity), 0)).filter_by(itemid=p.itemid, branch_id=current_user.branchid).scalar() or 0
        result.append({"itemid": p.itemid, "itemname": p.itemname, "description": p.description, "unitprice": str(p.unitprice), "reorderlevel": p.reorderlevel or 0, "categoryid": p.categoryid, "category_name": p.category.categoryname if p.category else "Unknown category", "is_active": p.is_active, "stock_qty": str(balance)})
    return result

@app.get("/inventory/balances", tags=["catalogue"])
@app.get("/api/v1/inventory/balances", tags=["catalogue"])
def get_inventory_balances(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    query = db.query(models.ERPStockBalance).filter_by(branch_id=current_user.branchid)
    if current_user.roletype not in (models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER, models.RoleType.BRANCH_MANAGER):
        require_role(current_user, models.RoleType.CASHIER, models.RoleType.ACCOUNTANT, models.RoleType.HR_STAFF)
    return [{"itemid": b.itemid, "branch_id": b.branch_id, "warehouse_id": b.warehouse_id, "quantity": str(b.quantity), "updated_at": b.updated_at} for b in query.order_by(models.ERPStockBalance.itemid).all()]

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
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF, models.RoleType.ACCOUNTANT)
    employees = db.query(models.Employee).order_by(models.Employee.name).all()
    return [{"employeeid": e.employeeid, "name": e.name, "nin": e.nin, "phone": e.phone, "datehired": e.datehired, "salary": float(e.salary or 0), "roletype": e.roletype.value, "departmentid": e.departmentid, "department_name": e.department.departmentname if e.department else "Unknown department", "branchid": e.branchid, "branch_name": branch_name(db, e.branchid), "supervisorid": e.supervisorid, "supervisor_name": employee_name(db, e.supervisorid)} for e in employees]

@app.post("/employees", tags=["organisation"])
def create_employee(payload: schemas.EmployeeCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF)
    employee = models.Employee(name=payload.name, nin=payload.nin, email=payload.email, hashed_password=auth.get_password_hash(payload.password) if payload.password else None, phone=payload.phone, datehired=payload.datehired, salary=payload.salary, departmentid=payload.departmentid, branchid=payload.branchid, supervisorid=payload.supervisorid, roletype=payload.roletype)
    db.add(employee); db.flush()
    assign_primary_erp_role(db, employee)
    subtype = {models.RoleType.CASHIER: models.Cashier(employeeid=employee.employeeid, pos_terminalid=payload.pos_terminalid or "unassigned"), models.RoleType.PROCUREMENT_OFFICER: models.ProcurementOfficer(employeeid=employee.employeeid, approvallimit=payload.approvallimit or 0), models.RoleType.ACCOUNTANT: models.Accountant(employeeid=employee.employeeid, certificationnumber=payload.certificationnumber), models.RoleType.HR_STAFF: models.HRStaff(employeeid=employee.employeeid, hr_role=payload.hr_role or "HR"), models.RoleType.BRANCH_MANAGER: models.BranchManager(employeeid=employee.employeeid, managementlevel=payload.managementlevel)}.get(payload.roletype)
    if subtype: db.add(subtype)
    db.commit(); db.refresh(employee); return {"employeeid": employee.employeeid, "name": employee.name}

@app.get("/purchase-orders", tags=["operations"])
@app.get("/api/v1/procurement/purchase-orders", tags=["operations"])
def get_purchase_orders(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER, models.RoleType.ACCOUNTANT, models.RoleType.BRANCH_MANAGER)
    query = db.query(models.PurchaseOrder)
    if current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.PurchaseOrder.branch_id == current_user.branchid)
    orders = query.order_by(models.PurchaseOrder.orderdate.desc()).all()
    return [{"po_id": o.po_id, "orderdate": o.orderdate, "status": o.status.value, "branch_id": o.branch_id, "supplier_name": db.query(models.Supplier).filter(models.Supplier.supplierid == o.supplierid).first().suppliername if db.query(models.Supplier).filter(models.Supplier.supplierid == o.supplierid).first() else "Unknown supplier", "officer_name": employee_name(db, o.employeeid), "items": [{"id": line.id, "itemid": line.itemid, "item_name": db.query(models.Product).filter_by(itemid=line.itemid).first().itemname, "quantity": str(line.quantity), "received_quantity": str(line.received_quantity), "remaining_quantity": str(line.quantity - line.received_quantity), "unit_cost": str(line.unit_cost)} for line in db.query(models.ERPPurchaseOrderItem).filter_by(po_id=o.po_id).all()]} for o in orders]

@app.get("/purchase-requisitions", tags=["operations"])
@app.get("/api/v1/procurement/requisitions", tags=["operations"])
def get_purchase_requisitions(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER, models.RoleType.BRANCH_MANAGER)
    query = db.query(models.ERPPurchaseRequisition)
    if current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.ERPPurchaseRequisition.branch_id == current_user.branchid)
    return [{"id": r.id, "reference": r.reference, "branch_id": r.branch_id, "requested_by": employee_name(db, r.requested_by), "status": r.status, "notes": r.notes, "created_at": r.created_at, "items": [{"itemid": i.itemid, "item_name": db.query(models.Product).filter_by(itemid=i.itemid).first().itemname, "quantity": str(i.quantity), "estimated_unit_cost": str(i.estimated_unit_cost)} for i in db.query(models.ERPPurchaseRequisitionItem).filter_by(requisition_id=r.id).all()]} for r in query.order_by(models.ERPPurchaseRequisition.created_at.desc()).all()]

@app.post("/purchase-requisitions", tags=["operations"])
@app.post("/api/v1/procurement/requisitions", tags=["operations"])
def create_purchase_requisition(payload: schemas.PurchaseRequisitionCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    if not current_user.branchid or not payload.items:
        raise HTTPException(400, "A branch and at least one requisition line are required")
    requisition = models.ERPPurchaseRequisition(reference=f"PR-{uuid.uuid4().hex[:10].upper()}", branch_id=current_user.branchid, requested_by=current_user.employeeid, notes=payload.notes, status="PENDING")
    db.add(requisition); db.flush()
    for line in payload.items:
        if not db.query(models.Product).filter_by(itemid=line.itemid).first():
            raise HTTPException(404, f"Product {line.itemid} was not found")
        db.add(models.ERPPurchaseRequisitionItem(requisition_id=requisition.id, itemid=line.itemid, quantity=line.quantity, estimated_unit_cost=line.estimated_unit_cost))
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="REQUISITION_CREATED", module="procurement", entity_type="purchase_requisition", entity_id=str(requisition.id), branch_id=current_user.branchid))
    db.commit()
    return {"id": requisition.id, "reference": requisition.reference, "status": requisition.status}

@app.post("/purchase-requisitions/{requisition_id}/approve", tags=["operations"])
@app.post("/api/v1/procurement/requisitions/{requisition_id}/approve", tags=["operations"])
def approve_purchase_requisition(requisition_id: int, payload: schemas.ApprovalDecision, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.BRANCH_MANAGER)
    requisition = db.query(models.ERPPurchaseRequisition).filter_by(id=requisition_id).with_for_update().first()
    if not requisition:
        raise HTTPException(404, "Requisition not found")
    if requisition.status != "PENDING":
        raise HTTPException(409, "Only pending requisitions can be approved")
    if requisition.requested_by == current_user.employeeid:
        raise HTTPException(403, "A requester cannot approve their own requisition")
    if current_user.roletype != models.RoleType.ADMIN and requisition.branch_id != current_user.branchid:
        raise HTTPException(403, "Requisition is outside your branch scope")
    requisition.status = "APPROVED"
    db.add(models.ERPPurchaseRequisitionApproval(requisition_id=requisition.id, requested_by=requisition.requested_by, approved_by=current_user.employeeid, decision="APPROVED", reason=payload.reason))
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="REQUISITION_APPROVED", module="procurement", entity_type="purchase_requisition", entity_id=str(requisition.id), branch_id=requisition.branch_id, details_json=payload.reason))
    db.commit()
    return {"id": requisition.id, "status": requisition.status}

@app.post("/purchase-orders", tags=["operations"])
@app.post("/api/v1/procurement/purchase-orders", tags=["operations"])
def create_purchase_order(payload: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    if not payload.requisition_id:
        raise HTTPException(400, "An approved requisition is required to create a purchase order")
    requisition = db.query(models.ERPPurchaseRequisition).filter_by(id=payload.requisition_id).with_for_update().first()
    if not requisition or requisition.status != "APPROVED":
        raise HTTPException(409, "Purchase order requires an approved requisition")
    if current_user.roletype != models.RoleType.ADMIN and requisition.branch_id != current_user.branchid:
        raise HTTPException(403, "Requisition is outside your branch scope")
    if requisition.requested_by == current_user.employeeid:
        raise HTTPException(403, "A requisition requester cannot create its purchase order")
    supplier = db.query(models.Supplier).filter_by(supplierid=payload.supplierid).first()
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    order = models.PurchaseOrder(supplierid=payload.supplierid, employeeid=current_user.employeeid, branch_id=requisition.branch_id, requisition_id=requisition.id, status=models.POStatus.PENDING)
    db.add(order); db.flush()
    for line in db.query(models.ERPPurchaseRequisitionItem).filter_by(requisition_id=requisition.id).all():
        db.add(models.ERPPurchaseOrderItem(po_id=order.po_id, itemid=line.itemid, quantity=line.quantity, unit_cost=line.estimated_unit_cost))
    requisition.status = "CONVERTED"
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="PURCHASE_ORDER_CREATED", module="procurement", entity_type="purchase_order", entity_id=str(order.po_id), branch_id=requisition.branch_id))
    db.commit(); db.refresh(order)
    return {"po_id": order.po_id, "status": order.status.value, "branch_id": order.branch_id}

@app.post("/purchase-orders/{po_id}/approve", tags=["operations"])
@app.post("/api/v1/procurement/purchase-orders/{po_id}/approve", tags=["operations"])
def approve_purchase_order(po_id: int, payload: schemas.ApprovalDecision, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.BRANCH_MANAGER, models.RoleType.PROCUREMENT_OFFICER)
    order = db.query(models.PurchaseOrder).filter_by(po_id=po_id).with_for_update().first()
    if not order:
        raise HTTPException(404, "Purchase order not found")
    if current_user.roletype != models.RoleType.ADMIN and order.branch_id != current_user.branchid:
        raise HTTPException(403, "Purchase order is outside your branch scope")
    if order.status != models.POStatus.PENDING:
        raise HTTPException(409, "Only pending purchase orders can be approved")
    if order.employeeid == current_user.employeeid:
        raise HTTPException(403, "A purchase order creator cannot approve their own order")
    amount = sum((line.quantity * line.unit_cost for line in db.query(models.ERPPurchaseOrderItem).filter_by(po_id=po_id).all()), Decimal("0"))
    officer = db.query(models.ProcurementOfficer).filter_by(employeeid=current_user.employeeid).first()
    if officer and amount > officer.approvallimit:
        raise HTTPException(403, "Purchase order exceeds your approval limit")
    order.status = models.POStatus.APPROVED
    db.add(models.ERPPurchaseOrderApproval(po_id=po_id, requested_by=order.employeeid, approved_by=current_user.employeeid, decision="APPROVED", reason=payload.reason))
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="PURCHASE_ORDER_APPROVED", module="procurement", entity_type="purchase_order", entity_id=str(po_id), branch_id=order.branch_id, details_json=payload.reason))
    db.commit()
    return {"po_id": po_id, "status": order.status.value}

@app.post("/goods-received-notes", tags=["operations"])
@app.post("/api/v1/procurement/goods-received-notes", tags=["operations"])
def create_goods_received_note(payload: schemas.GRNCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    order = db.query(models.PurchaseOrder).filter_by(po_id=payload.po_id).with_for_update().first()
    if not order or order.status not in (models.POStatus.APPROVED, models.POStatus.PARTIALLY_RECEIVED):
        raise HTTPException(409, "Goods can only be received against an approved, open PO")
    if current_user.roletype != models.RoleType.ADMIN and order.branch_id != current_user.branchid:
        raise HTTPException(403, "Purchase order is outside your branch scope")
    approval = db.query(models.ERPPurchaseOrderApproval).filter_by(po_id=order.po_id, decision="APPROVED").order_by(models.ERPPurchaseOrderApproval.id.desc()).first()
    requisition = db.query(models.ERPPurchaseRequisition).filter_by(id=order.requisition_id).first() if order.requisition_id else None
    if not approval or current_user.employeeid in {order.employeeid, approval.approved_by} or (requisition and current_user.employeeid == requisition.requested_by):
        raise HTTPException(403, "Receiver must be different from the PO requester and approver")
    if not payload.items:
        raise HTTPException(400, "At least one received line is required")
    warehouse = db.query(models.ERPWarehouse).filter_by(branch_id=order.branch_id, is_active=True).first()
    if not warehouse:
        warehouse = models.ERPWarehouse(branch_id=order.branch_id, name="Main Warehouse"); db.add(warehouse); db.flush()
    grn = models.ERPGoodsReceivedNote(reference=f"GRN-{uuid.uuid4().hex[:10].upper()}", po_id=order.po_id, branch_id=order.branch_id, warehouse_id=warehouse.id, received_by=current_user.employeeid)
    db.add(grn); db.flush()
    lines = []
    for received in payload.items:
        po_line = db.query(models.ERPPurchaseOrderItem).filter_by(id=received.po_item_id, po_id=order.po_id).with_for_update().first()
        if not po_line or po_line.received_quantity + received.quantity > po_line.quantity:
            raise HTTPException(409, "Received quantity exceeds the remaining approved quantity")
        po_line.received_quantity += received.quantity
        db.add(models.ERPGoodsReceivedNoteItem(grn_id=grn.id, po_item_id=po_line.id, quantity=received.quantity))
        balance = db.query(models.ERPStockBalance).filter_by(itemid=po_line.itemid, branch_id=order.branch_id, warehouse_id=warehouse.id).with_for_update().first()
        if not balance:
            balance = models.ERPStockBalance(itemid=po_line.itemid, branch_id=order.branch_id, warehouse_id=warehouse.id, quantity=0); db.add(balance)
        balance.quantity += received.quantity
        db.add(models.ERPInventoryMovement(itemid=po_line.itemid, branch_id=order.branch_id, warehouse_id=warehouse.id, movement_type="GRN_IN", quantity=received.quantity, reference_type="GRN", reference_id=grn.id, created_by=current_user.employeeid))
        lines.append(po_line)
    complete = all(line.received_quantity >= line.quantity for line in db.query(models.ERPPurchaseOrderItem).filter_by(po_id=order.po_id).all())
    order.status = models.POStatus.RECEIVED if complete else models.POStatus.PARTIALLY_RECEIVED
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="GOODS_RECEIVED", module="procurement", entity_type="goods_received_note", entity_id=str(grn.id), branch_id=order.branch_id))
    db.commit()
    return {"id": grn.id, "reference": grn.reference, "status": grn.status, "po_status": order.status.value}

@app.post("/supplier-invoices", tags=["operations"])
@app.post("/api/v1/finance/supplier-invoices", tags=["operations"])
def create_supplier_invoice(payload: schemas.SupplierInvoiceCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
    order = db.query(models.PurchaseOrder).filter_by(po_id=payload.po_id).first()
    grn = db.query(models.ERPGoodsReceivedNote).filter_by(id=payload.grn_id, po_id=payload.po_id, status="CONFIRMED").first()
    if not order or not grn or order.status not in (models.POStatus.PARTIALLY_RECEIVED, models.POStatus.RECEIVED):
        raise HTTPException(409, "Invoice requires an approved PO and confirmed GRN")
    if current_user.roletype != models.RoleType.ADMIN and order.branch_id != current_user.branchid:
        raise HTTPException(403, "Purchase order is outside your branch scope")
    if grn.received_by == current_user.employeeid:
        raise HTTPException(403, "The goods receiver cannot record the supplier invoice")
    invoice = models.ERPSupplierInvoice(invoice_number=payload.invoice_number, po_id=order.po_id, grn_id=grn.id, branch_id=order.branch_id, amount=payload.amount, created_by=current_user.employeeid)
    db.add(invoice); db.flush()
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="SUPPLIER_INVOICE_RECORDED", module="finance", entity_type="supplier_invoice", entity_id=str(invoice.id), branch_id=order.branch_id))
    db.commit()
    return {"id": invoice.id, "status": invoice.status}

@app.post("/supplier-invoices/{invoice_id}/match", tags=["operations"])
@app.post("/api/v1/finance/supplier-invoices/{invoice_id}/match", tags=["operations"])
def match_supplier_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
    invoice = db.query(models.ERPSupplierInvoice).filter_by(id=invoice_id).with_for_update().first()
    if not invoice:
        raise HTTPException(404, "Supplier invoice not found")
    if current_user.roletype != models.RoleType.ADMIN and invoice.branch_id != current_user.branchid:
        raise HTTPException(403, "Invoice is outside your branch scope")
    received = db.query(models.ERPGoodsReceivedNoteItem, models.ERPPurchaseOrderItem).join(models.ERPPurchaseOrderItem, models.ERPGoodsReceivedNoteItem.po_item_id == models.ERPPurchaseOrderItem.id).filter(models.ERPGoodsReceivedNoteItem.grn_id == invoice.grn_id).all()
    expected = sum((grn_line.quantity * po_line.unit_cost for grn_line, po_line in received), Decimal("0")).quantize(Decimal("0.01"))
    received_qty = sum((grn_line.quantity for grn_line, _ in received), Decimal("0"))
    ordered_qty = sum((line.quantity for line in db.query(models.ERPPurchaseOrderItem).filter_by(po_id=invoice.po_id).all()), Decimal("0"))
    matched = expected == invoice.amount and bool(received)
    db.add(models.ERPInvoiceMatchResult(invoice_id=invoice.id, matched=matched, ordered_quantity=ordered_qty, received_quantity=received_qty, invoiced_amount=invoice.amount, expected_amount=expected, checked_by=current_user.employeeid))
    invoice.status = "MATCHED" if matched else "VARIANCE"
    if matched:
        journal = models.ERPJournalEntry(reference_type="SUPPLIER_INVOICE", reference_id=invoice.id, branch_id=invoice.branch_id, created_by=current_user.employeeid)
        db.add(journal); db.flush()
        db.add_all([models.ERPJournalLine(journal_id=journal.id, account_code="1200", account_name="Inventory Asset", debit=expected, credit=0), models.ERPJournalLine(journal_id=journal.id, account_code="2000", account_name="Accounts Payable", debit=0, credit=expected)])
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="SUPPLIER_INVOICE_MATCHED" if matched else "SUPPLIER_INVOICE_VARIANCE", module="finance", entity_type="supplier_invoice", entity_id=str(invoice.id), branch_id=invoice.branch_id))
    db.commit()
    if not matched:
        raise HTTPException(409, f"Three-way match variance: invoice UGX {invoice.amount} does not match GRN value UGX {expected}")
    return {"invoice_id": invoice.id, "matched": True, "expected_amount": str(expected), "received_quantity": str(received_qty)}

@app.post("/supplier-payments", tags=["operations"])
@app.post("/api/v1/finance/supplier-payments", tags=["operations"])
def pay_supplier_invoice(payload: schemas.SupplierPaymentCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
    if current_user.roletype != models.RoleType.ADMIN and not any(role.name in {"Finance Manager", "Owner / Executive"} for role in current_user.erp_roles):
        raise HTTPException(403, "Supplier payments require Finance Manager or Owner approval")
    invoice = db.query(models.ERPSupplierInvoice).filter_by(id=payload.invoice_id).with_for_update().first()
    if not invoice or invoice.status not in {"MATCHED", "PARTIALLY_PAID"}:
        raise HTTPException(409, "Only a three-way matched supplier invoice can be paid")
    if current_user.roletype != models.RoleType.ADMIN and invoice.branch_id != current_user.branchid:
        raise HTTPException(403, "Invoice is outside your branch scope")
    match = db.query(models.ERPInvoiceMatchResult).filter_by(invoice_id=invoice.id, matched=True).order_by(models.ERPInvoiceMatchResult.created_at.desc()).first()
    if not match:
        raise HTTPException(409, "A successful PO + GRN + invoice match is required")
    grn = db.query(models.ERPGoodsReceivedNote).filter_by(id=invoice.grn_id).first()
    order = db.query(models.PurchaseOrder).filter_by(po_id=invoice.po_id).first()
    requisition = db.query(models.ERPPurchaseRequisition).filter_by(id=order.requisition_id).first() if order and order.requisition_id else None
    po_approval = db.query(models.ERPPurchaseOrderApproval).filter_by(po_id=invoice.po_id, decision="APPROVED").order_by(models.ERPPurchaseOrderApproval.id.desc()).first()
    separation_ids = {invoice.created_by, match.checked_by}
    if grn: separation_ids.add(grn.received_by)
    if order: separation_ids.add(order.employeeid)
    if requisition: separation_ids.add(requisition.requested_by)
    if po_approval: separation_ids.add(po_approval.approved_by)
    if current_user.employeeid in separation_ids:
        raise HTTPException(403, "Payment approver must differ from requester, PO approver, receiver, invoice recorder, and matcher")
    paid = db.query(func.coalesce(func.sum(models.ERPSupplierPayment.amount), 0)).filter_by(invoice_id=invoice.id).scalar() or Decimal("0")
    if paid + payload.amount > invoice.amount:
        raise HTTPException(409, "Payment exceeds the unpaid invoice balance")
    payment = models.ERPSupplierPayment(invoice_id=invoice.id, branch_id=invoice.branch_id, amount=payload.amount, payment_method=payload.payment_method, paid_by=current_user.employeeid)
    db.add(payment); db.flush()
    journal = models.ERPJournalEntry(reference_type="SUPPLIER_PAYMENT", reference_id=payment.id, branch_id=invoice.branch_id, created_by=current_user.employeeid)
    db.add(journal); db.flush()
    cash_code, cash_name = {"cash": ("1000", "Cash on Hand"), "bank": ("1010", "Bank"), "mobile_money": ("1020", "Mobile Money")} [payload.payment_method]
    db.add_all([models.ERPJournalLine(journal_id=journal.id, account_code="2000", account_name="Accounts Payable", debit=payload.amount, credit=0), models.ERPJournalLine(journal_id=journal.id, account_code=cash_code, account_name=cash_name, debit=0, credit=payload.amount)])
    invoice.status = "PAID" if paid + payload.amount == invoice.amount else "PARTIALLY_PAID"
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="SUPPLIER_PAYMENT_POSTED", module="finance", entity_type="supplier_payment", entity_id=str(payment.id), branch_id=invoice.branch_id))
    db.commit()
    return {"payment_id": payment.id, "invoice_id": invoice.id, "amount": str(payment.amount), "invoice_status": invoice.status}

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
    query = db.query(models.Sale).filter(models.Sale.status == "COMPLETED")
    if current_user.roletype == models.RoleType.CASHIER:
        query = query.filter(models.Sale.employeeid == current_user.employeeid)
    elif current_user.roletype != models.RoleType.ADMIN:
        query = query.filter(models.Sale.branchid == current_user.branchid)
    sales = query.order_by(models.Sale.saledate.desc()).all()
    result = []
    for sale in sales:
        customer = db.query(models.Customer).filter(models.Customer.customerid == sale.customerid).first() if sale.customerid else None
        result.append({"saleid": sale.saleid, "saledate": sale.saledate, "totalamount": float(sale.totalamount or 0), "customer_name": customer.name if customer else "Walk-in", "cashier_name": employee_name(db, sale.employeeid), "branch_name": branch_name(db, sale.branchid), "items": [{"item_name": i.product.itemname if i.product else "Unknown product", "quantity": i.quantity, "unitpriceatsale": float(i.unitpriceatsale)} for i in sale.sale_items]})
    return result

@app.get("/cashier-sessions/current", tags=["operations"])
@app.get("/api/v1/sales/cashier-sessions/current", tags=["operations"])
def get_current_cashier_session(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    session = db.query(models.ERPCashierSession).filter_by(employeeid=current_user.employeeid, status="OPEN").order_by(models.ERPCashierSession.opened_at.desc()).first()
    return {"session_id": session.id, "branch_id": session.branch_id, "opening_float": str(session.opening_float), "status": session.status, "opened_at": session.opened_at} if session else None

@app.post("/cashier-sessions/open", tags=["operations"])
@app.post("/api/v1/sales/cashier-sessions/open", tags=["operations"])
def open_cashier_session(payload: schemas.CashierSessionOpen, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    if not current_user.branchid:
        raise HTTPException(403, "Your account is not assigned to a branch")
    active = db.query(models.ERPCashierSession).filter_by(employeeid=current_user.employeeid, status="OPEN").with_for_update().first()
    if active:
        return {"session_id": active.id, "status": active.status, "opening_float": str(active.opening_float)}
    session = models.ERPCashierSession(employeeid=current_user.employeeid, branch_id=current_user.branchid, opening_float=payload.opening_float)
    db.add(session); db.flush()
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="CASHIER_SESSION_OPENED", module="sales", entity_type="cashier_session", entity_id=str(session.id), branch_id=current_user.branchid))
    db.commit()
    return {"session_id": session.id, "status": session.status, "opening_float": str(session.opening_float)}

@app.post("/sales", tags=["operations"])
@app.post("/api/v1/sales", tags=["operations"])
def create_sale(payload: schemas.SaleCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user), idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    if not payload.items: raise HTTPException(400, "At least one sale item is required")
    if not current_user.branchid:
        raise HTTPException(403, "Your account is not assigned to a branch")
    existing = db.query(models.Sale).filter(models.Sale.idempotency_key == idempotency_key).first()
    if existing:
        return {"saleid": existing.saleid, "totalamount": str(existing.totalamount), "status": existing.status, "idempotent_replay": True}
    cashier_session = db.query(models.ERPCashierSession).filter_by(employeeid=current_user.employeeid, branch_id=current_user.branchid, status="OPEN").with_for_update().first()
    if not cashier_session:
        raise HTTPException(409, "Open a cashier session before completing a sale")
    quantities = {}
    for line in payload.items:
        quantities[line.itemid] = quantities.get(line.itemid, Decimal("0")) + line.quantity
    customerid = payload.customerid
    if not customerid and (payload.customername or payload.customerphone):
        customer = models.Customer(name=payload.customername, phone=payload.customerphone); db.add(customer); db.flush(); customerid = customer.customerid
    sale = models.Sale(customerid=customerid, employeeid=current_user.employeeid, branchid=current_user.branchid, totalamount=0, status="COMPLETED", idempotency_key=idempotency_key); db.add(sale); db.flush()
    total = Decimal("0")
    cogs = Decimal("0")
    for itemid, quantity in quantities.items():
        product = db.query(models.Product).filter(models.Product.itemid == itemid).with_for_update().first()
        if not product: raise HTTPException(400, f"Product {itemid} was not found")
        if not product.is_active:
            raise HTTPException(400, f"Product {product.itemname} is inactive")
        balances = db.query(models.ERPStockBalance).filter_by(itemid=product.itemid, branch_id=current_user.branchid).filter(models.ERPStockBalance.quantity > 0).order_by(models.ERPStockBalance.id).with_for_update().all()
        available = sum((balance.quantity for balance in balances), Decimal("0"))
        if available < quantity:
            raise HTTPException(409, f"Insufficient stock for {product.itemname}")
        remaining = quantity
        for balance in balances:
            moved = min(balance.quantity, remaining)
            if moved <= 0:
                break
            balance.quantity -= moved
            db.add(models.ERPInventoryMovement(itemid=product.itemid, branch_id=current_user.branchid, warehouse_id=balance.warehouse_id, movement_type="SALE_OUT", quantity=moved, reference_type="SALE", reference_id=sale.saleid, created_by=current_user.employeeid))
            remaining -= moved
        total += product.unitprice * quantity
        supply = db.query(models.Supply).filter_by(itemid=product.itemid).order_by(models.Supply.costprice).first()
        if supply:
            cogs += supply.costprice * quantity
        db.add(models.SaleItem(saleid=sale.saleid, itemid=product.itemid, quantity=quantity, unitpriceatsale=product.unitprice))
    total = total.quantize(Decimal("0.01"))
    cogs = cogs.quantize(Decimal("0.01"))
    sale.totalamount = total
    db.add(models.ERPPayment(saleid=sale.saleid, branch_id=current_user.branchid, cashier_session_id=cashier_session.id, method=payload.payment_method.lower(), amount=total))
    journal = models.ERPJournalEntry(reference_type="SALE", reference_id=sale.saleid, branch_id=current_user.branchid, created_by=current_user.employeeid)
    db.add(journal); db.flush()
    payment_account = {"cash": ("1000", "Cash on Hand"), "card": ("1010", "Card Clearing"), "mobile_money": ("1020", "Mobile Money")}[payload.payment_method]
    db.add_all([
        models.ERPJournalLine(journal_id=journal.id, account_code=payment_account[0], account_name=payment_account[1], debit=total, credit=0),
        models.ERPJournalLine(journal_id=journal.id, account_code="4000", account_name="Sales Revenue", debit=0, credit=total),
    ])
    if cogs:
        db.add_all([
            models.ERPJournalLine(journal_id=journal.id, account_code="5000", account_name="Cost of Goods Sold", debit=cogs, credit=0),
            models.ERPJournalLine(journal_id=journal.id, account_code="1200", account_name="Inventory Asset", debit=0, credit=cogs),
        ])
    db.add(models.LedgerEntry(sourcetype=models.LedgerSourceType.SALE, saleid=sale.saleid, amount=total, recordedby=current_user.employeeid))
    db.add(models.ERPAuditLog(user_id=current_user.employeeid, action="SALE_COMPLETED", module="sales", entity_type="sale", entity_id=str(sale.saleid), branch_id=current_user.branchid, details_json=f'{{"total":"{total}","cogs":"{cogs}"}}'))
    db.commit(); db.refresh(sale)
    return {"saleid": sale.saleid, "totalamount": str(total), "cogs": str(cogs), "gross_profit": str(total - cogs), "status": sale.status}

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
