from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from decimal import Decimal

import models
import schemas
import auth
from database import engine, get_db

# Create the database tables automatically
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hardware World API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Hardware World API"}

def require_role(current_user: models.Employee, *roles: models.RoleType):
    if current_user.roletype not in roles:
        raise HTTPException(status_code=403, detail="Not authorized for this operation")

def employee_name(db: Session, employeeid: int | None):
    employee = db.query(models.Employee).filter(models.Employee.employeeid == employeeid).first() if employeeid else None
    return employee.name if employee else "Unknown employee"

def branch_name(db: Session, branchid: int | None):
    branch = db.query(models.Branch).filter(models.Branch.branchid == branchid).first() if branchid else None
    return branch.branchname if branch else "Unknown branch"

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
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
        datehired=user.datehired,
        salary=user.salary,
        departmentid=user.departmentid,
        branchid=user.branchid,
        supervisorid=user.supervisorid,
        roletype=user.roletype
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    if new_user.roletype == models.RoleType.HR_STAFF:
        db.add(models.HRStaff(employeeid=new_user.employeeid, hr_role="HR"))
        db.commit()
    return new_user

@app.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Employee).filter(models.Employee.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.roletype}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.Employee = Depends(auth.get_current_user)):
    return current_user

# Example of a protected endpoint
@app.get("/branches", response_model=list[schemas.BranchResponse])
def get_branches(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    branches = db.query(models.Branch).all()
    return branches

@app.post("/branches", response_model=schemas.BranchResponse)
def create_branch(branch: schemas.BranchCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN)
    new_branch = models.Branch(**branch.dict())
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch

@app.get("/departments")
def get_departments(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return [{"departmentid": d.departmentid, "departmentname": d.departmentname, "branchid": d.branchid, "branch_name": branch_name(db, d.branchid)} for d in db.query(models.Department).order_by(models.Department.departmentname).all()]

@app.get("/categories")
def get_categories(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return [{"categoryid": c.categoryid, "categoryname": c.categoryname} for c in db.query(models.Category).order_by(models.Category.categoryname).all()]

@app.post("/categories")
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    category = models.Category(categoryname=payload.categoryname); db.add(category); db.commit(); db.refresh(category)
    return {"categoryid": category.categoryid, "categoryname": category.categoryname}

@app.get("/products")
def get_products(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return [{"itemid": p.itemid, "itemname": p.itemname, "description": p.description, "unitprice": float(p.unitprice), "reorderlevel": p.reorderlevel or 0, "categoryid": p.categoryid, "category_name": p.category.categoryname if p.category else "Unknown category"} for p in db.query(models.Product).order_by(models.Product.itemname).all()]

@app.post("/products")
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    product = models.Product(**payload.model_dump()); db.add(product); db.commit(); db.refresh(product)
    return {"itemid": product.itemid, "itemname": product.itemname}

@app.get("/suppliers")
def get_suppliers(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    return [{"supplierid": s.supplierid, "suppliername": s.suppliername, "contactperson": s.contactperson, "phone": s.phone, "address": s.address} for s in db.query(models.Supplier).order_by(models.Supplier.suppliername).all()]

@app.post("/suppliers")
def create_supplier(payload: schemas.SupplierCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    supplier = models.Supplier(**payload.model_dump()); db.add(supplier); db.commit(); db.refresh(supplier)
    return {"supplierid": supplier.supplierid, "suppliername": supplier.suppliername}

@app.get("/employees")
def get_employees(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    employees = db.query(models.Employee).order_by(models.Employee.name).all()
    return [{"employeeid": e.employeeid, "name": e.name, "nin": e.nin, "phone": e.phone, "datehired": e.datehired, "salary": float(e.salary or 0), "roletype": e.roletype.value, "departmentid": e.departmentid, "department_name": e.department.departmentname if e.department else "Unknown department", "branchid": e.branchid, "branch_name": branch_name(db, e.branchid), "supervisorid": e.supervisorid, "supervisor_name": employee_name(db, e.supervisorid)} for e in employees]

@app.post("/employees")
def create_employee(payload: schemas.EmployeeCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF)
    employee = models.Employee(name=payload.name, nin=payload.nin, email=payload.email, hashed_password=auth.get_password_hash(payload.password) if payload.password else None, phone=payload.phone, datehired=payload.datehired, salary=payload.salary, departmentid=payload.departmentid, branchid=payload.branchid, supervisorid=payload.supervisorid, roletype=payload.roletype)
    db.add(employee); db.flush()
    subtype = {models.RoleType.CASHIER: models.Cashier(employeeid=employee.employeeid, pos_terminalid=payload.pos_terminalid or "unassigned"), models.RoleType.PROCUREMENT_OFFICER: models.ProcurementOfficer(employeeid=employee.employeeid, approvallimit=payload.approvallimit or 0), models.RoleType.ACCOUNTANT: models.Accountant(employeeid=employee.employeeid, certificationnumber=payload.certificationnumber), models.RoleType.HR_STAFF: models.HRStaff(employeeid=employee.employeeid, hr_role=payload.hr_role or "HR"), models.RoleType.BRANCH_MANAGER: models.BranchManager(employeeid=employee.employeeid, managementlevel=payload.managementlevel)}.get(payload.roletype)
    if subtype: db.add(subtype)
    db.commit(); db.refresh(employee); return {"employeeid": employee.employeeid, "name": employee.name}

@app.get("/purchase-orders")
def get_purchase_orders(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    orders = db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.orderdate.desc()).all()
    return [{"po_id": o.po_id, "orderdate": o.orderdate, "status": o.status.value, "supplier_name": db.query(models.Supplier).filter(models.Supplier.supplierid == o.supplierid).first().suppliername if db.query(models.Supplier).filter(models.Supplier.supplierid == o.supplierid).first() else "Unknown supplier", "officer_name": employee_name(db, o.employeeid)} for o in orders]

@app.post("/purchase-orders")
def create_purchase_order(payload: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.PROCUREMENT_OFFICER)
    order = models.PurchaseOrder(**payload.model_dump()); db.add(order); db.commit(); db.refresh(order); return order

@app.get("/payroll")
def get_payroll(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    records = db.query(models.Payroll).order_by(models.Payroll.month.desc()).all()
    return [{"payrollid": p.payrollid, "employeeid": p.employeeid, "employee_name": employee_name(db, p.employeeid), "month": p.month, "grosspay": float(p.grosspay), "deductions": float(p.deductions or 0), "netpay": float(p.netpay)} for p in records]

@app.post("/payroll")
def create_payroll(payload: schemas.PayrollCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.HR_STAFF)
    if payload.deductions > payload.grosspay: raise HTTPException(400, "Deductions cannot exceed gross pay")
    record = models.Payroll(**payload.model_dump(), netpay=payload.grosspay - payload.deductions); db.add(record); db.commit(); db.refresh(record); return record

@app.get("/sales")
def get_sales(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    sales = db.query(models.Sale).order_by(models.Sale.saledate.desc()).all()
    result = []
    for sale in sales:
        customer = db.query(models.Customer).filter(models.Customer.customerid == sale.customerid).first() if sale.customerid else None
        result.append({"saleid": sale.saleid, "saledate": sale.saledate, "totalamount": float(sale.totalamount or 0), "customer_name": customer.name if customer else "Walk-in", "cashier_name": employee_name(db, sale.employeeid), "branch_name": branch_name(db, sale.branchid), "items": [{"item_name": i.product.itemname if i.product else "Unknown product", "quantity": i.quantity, "unitpriceatsale": float(i.unitpriceatsale)} for i in sale.sale_items]})
    return result

@app.post("/sales")
def create_sale(payload: schemas.SaleCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.CASHIER)
    if not payload.items: raise HTTPException(400, "At least one sale item is required")
    customerid = payload.customerid
    if not customerid and (payload.customername or payload.customerphone):
        customer = models.Customer(name=payload.customername, phone=payload.customerphone); db.add(customer); db.flush(); customerid = customer.customerid
    sale = models.Sale(customerid=customerid, employeeid=payload.employeeid, branchid=payload.branchid, totalamount=0); db.add(sale); db.flush()
    total = Decimal("0")
    for item in payload.items:
        product = db.query(models.Product).filter(models.Product.itemid == item.itemid).first()
        if not product: raise HTTPException(400, f"Product {item.itemid} was not found")
        total += product.unitprice * item.quantity; db.add(models.SaleItem(saleid=sale.saleid, itemid=product.itemid, quantity=item.quantity, unitpriceatsale=product.unitprice))
    sale.totalamount = total; db.commit(); db.refresh(sale); return {"saleid": sale.saleid, "totalamount": float(total)}

@app.get("/ledger")
def get_ledger(db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    entries = db.query(models.LedgerEntry).order_by(models.LedgerEntry.entrydate.desc()).all()
    return [{"entryid": e.entryid, "entrydate": e.entrydate, "sourcetype": e.sourcetype.value, "amount": float(e.amount), "source_label": f"Sale #{e.saleid}" if e.saleid else f"Payroll #{e.payrollid}", "accountant_name": employee_name(db, e.recordedby)} for e in entries]

@app.post("/ledger")
def create_ledger(payload: schemas.LedgerCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(auth.get_current_user)):
    require_role(current_user, models.RoleType.ADMIN, models.RoleType.ACCOUNTANT)
    entry = models.LedgerEntry(**payload.model_dump()); db.add(entry); db.commit(); db.refresh(entry); return entry
