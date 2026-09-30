"""Hardware World ERP Seed Baseline Script.

Seeds the 6 departments, 2 branches, 17 roles, permissions, baseline staff,
warehouses, chart of accounts, categories, suppliers, and initial inventory.
"""
import os
import sys
from datetime import date, datetime
from decimal import Decimal

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Base, engine
import models
import auth

ROLES = [
    ("System Administrator", "Full system access and security administration"),
    ("Owner / Executive", "Executive reporting and organization oversight"),
    ("General Manager", "Overall branch operations and high-level approvals"),
    ("Branch Manager", "Day-to-day branch management, inventory, and operations"),
    ("Sales Manager", "Sales oversight, credit customer and discount approvals"),
    ("Cashier", "Point of sale register operations and receipt issuance"),
    ("Sales Clerk", "Assisting customers and counter sales"),
    ("Storekeeper", "Warehouse receipt, transfers, and physical stocktakes"),
    ("Warehouse Supervisor", "Warehouse logistics and stock movement management"),
    ("Inventory Manager", "Inventory accuracy, stock adjustments, and reorder control"),
    ("Procurement Officer", "Purchase orders, supplier management, and pricing"),
    ("Procurement Manager", "Procurement approvals and supplier contract oversight"),
    ("Finance Clerk", "Invoice entry, receipt vouchers, and payment records"),
    ("Accountant", "Double-entry general ledger, bank reconciliations, and reporting"),
    ("Finance Manager", "Financial approvals, payroll authorization, and cash management"),
    ("HR Officer", "Employee records, attendance tracking, and leave management"),
    ("HR Manager", "HR oversight, compensation, and payroll run preparation"),
]

PERMISSIONS = [
    # Sales
    ("sales:pos", "sales", "pos", "Operate POS register and complete sales"),
    ("sales:view", "sales", "view", "View sales history and receipts"),
    ("sales:discount", "sales", "discount", "Request and apply sale discounts"),
    ("sales:refund", "sales", "refund", "Process sales refunds and returns"),
    ("sales:credit", "sales", "credit", "Create customer credit sales"),
    ("sales:approve", "sales", "approve", "Approve discounts, voids, and refunds"),
    # Inventory
    ("inventory:view", "inventory", "view", "View stock levels and movements"),
    ("inventory:adjust", "inventory", "adjust", "Submit stock adjustments"),
    ("inventory:approve_adjust", "inventory", "approve_adjust", "Approve stock adjustments"),
    ("inventory:stocktake", "inventory", "stocktake", "Conduct physical stocktakes"),
    ("inventory:manage", "inventory", "manage", "Create products, categories, units"),
    # Procurement
    ("procurement:requisition", "procurement", "requisition", "Create purchase requisitions"),
    ("procurement:approve_req", "procurement", "approve_req", "Approve purchase requisitions"),
    ("procurement:po_create", "procurement", "po_create", "Create purchase orders"),
    ("procurement:po_approve", "procurement", "po_approve", "Approve purchase orders"),
    ("procurement:grn", "procurement", "grn", "Receive goods and confirm GRN"),
    ("procurement:supplier", "procurement", "supplier", "Manage suppliers and catalogs"),
    # Finance
    ("finance:view", "finance", "view", "View financial reports, accounts, and ledger"),
    ("finance:post", "finance", "post", "Post general journal entries"),
    ("finance:invoice", "finance", "invoice", "Process supplier invoices and 3-way matching"),
    ("finance:payment", "finance", "payment", "Disburse supplier and operational payments"),
    ("finance:approve", "finance", "approve", "Approve payments and journals"),
    # HR & Payroll
    ("hr:view", "hr", "view", "View employee profiles and attendance"),
    ("hr:manage", "hr", "manage", "Manage employee records and contracts"),
    ("hr:attendance", "hr", "attendance", "Record attendance and overtime"),
    ("hr:leave", "hr", "leave", "Manage leave requests"),
    ("payroll:view", "payroll", "view", "View organization payroll and reports"),
    ("payroll:prepare", "payroll", "prepare", "Prepare and compute payroll runs"),
    ("payroll:approve", "payroll", "approve", "Approve payroll runs for payment"),
    # Admin
    ("admin:all", "admin", "all", "Unrestricted administrative operations"),
    ("admin:users", "admin", "users", "Manage user accounts, roles, and permissions"),
    ("admin:audit", "admin", "audit", "View security audit logs and telemetry"),
]

ROLE_PERMISSION_MAP = {
    "System Administrator": [p[0] for p in PERMISSIONS],
    "Owner / Executive": [p[0] for p in PERMISSIONS if not p[0].startswith("sales:pos")],
    "General Manager": [p[0] for p in PERMISSIONS if not p[0].startswith("admin:all")],
    "Branch Manager": [
        "sales:view", "sales:approve", "inventory:view", "inventory:approve_adjust",
        "procurement:requisition", "procurement:approve_req", "procurement:po_approve",
        "procurement:grn", "finance:view", "hr:view", "payroll:view"
    ],
    "Sales Manager": [
        "sales:pos", "sales:view", "sales:discount", "sales:refund", "sales:credit",
        "sales:approve", "inventory:view"
    ],
    "Cashier": [
        "sales:pos", "sales:view", "sales:discount", "sales:refund"
    ],
    "Sales Clerk": [
        "sales:pos", "sales:view"
    ],
    "Storekeeper": [
        "inventory:view", "inventory:stocktake", "inventory:adjust",
        "procurement:requisition", "procurement:grn"
    ],
    "Warehouse Supervisor": [
        "inventory:view", "inventory:stocktake", "inventory:adjust", "inventory:approve_adjust",
        "procurement:requisition", "procurement:grn"
    ],
    "Inventory Manager": [
        "inventory:view", "inventory:manage", "inventory:stocktake", "inventory:adjust",
        "inventory:approve_adjust", "procurement:requisition", "procurement:grn"
    ],
    "Procurement Officer": [
        "inventory:view", "procurement:requisition", "procurement:po_create",
        "procurement:po_approve", "procurement:supplier"
    ],
    "Procurement Manager": [
        "inventory:view", "procurement:requisition", "procurement:approve_req",
        "procurement:po_create", "procurement:po_approve", "procurement:supplier"
    ],
    "Finance Clerk": [
        "finance:view", "finance:invoice", "finance:post", "sales:view"
    ],
    "Accountant": [
        "finance:view", "finance:invoice", "finance:post", "finance:payment",
        "sales:view", "payroll:view"
    ],
    "Finance Manager": [
        "finance:view", "finance:invoice", "finance:post", "finance:payment",
        "finance:approve", "sales:view", "payroll:view", "payroll:approve"
    ],
    "HR Officer": [
        "hr:view", "hr:manage", "hr:attendance", "hr:leave", "payroll:view", "payroll:prepare"
    ],
    "HR Manager": [
        "hr:view", "hr:manage", "hr:attendance", "hr:leave", "payroll:view",
        "payroll:prepare", "payroll:approve"
    ],
}

CHART_OF_ACCOUNTS = [
    ("1010", "Cash on Hand", "ASSET"),
    ("1020", "Bank Account", "ASSET"),
    ("1030", "Mobile Money Clearing Account", "ASSET"),
    ("1040", "Accounts Receivable", "ASSET"),
    ("1050", "Inventory Asset", "ASSET"),
    ("2010", "Accounts Payable", "LIABILITY"),
    ("2020", "Payroll Payable", "LIABILITY"),
    ("2030", "Statutory Tax Payable", "LIABILITY"),
    ("3010", "Owner Equity", "EQUITY"),
    ("4010", "Sales Revenue", "REVENUE"),
    ("5010", "Cost of Goods Sold", "EXPENSE"),
    ("5020", "Salaries and Wages Expense", "EXPENSE"),
    ("5030", "Inventory Shrinkage Expense", "EXPENSE"),
]

def seed_baseline(db):
    """Seed or update all baseline data according to Master Prompt."""
    seed_password = os.getenv("SEED_DEFAULT_PASSWORD")
    if (
        not seed_password
        or len(seed_password) < 12
        or seed_password.lower().startswith(("replace-with", "change-me"))
    ):
        raise RuntimeError("SEED_DEFAULT_PASSWORD must be configured with at least 12 characters before seeding.")
    print("Seeding Hardware World ERP baseline...")

    # 1. Chart of Accounts
    for code, name, acct_type in CHART_OF_ACCOUNTS:
        existing = db.query(models.ChartOfAccount).filter(models.ChartOfAccount.account_code == code).first()
        if not existing:
            db.add(models.ChartOfAccount(account_code=code, account_name=name, account_type=acct_type))
    db.commit()

    # Financial Accounts
    fin_accts = [
        ("Main Cash Till", "CASH", "TILL-01", Decimal("500000")),
        ("Stanbic Bank Main", "BANK", "9030012345678", Decimal("25000000")),
        ("MTN Mobile Money Merchant", "MOBILE_MONEY", "0770001122", Decimal("3500000")),
    ]
    for name, acct_type, number, bal in fin_accts:
        if not db.query(models.FinancialAccount).filter(models.FinancialAccount.account_name == name).first():
            db.add(models.FinancialAccount(account_name=name, account_type=acct_type, account_number=number, balance=bal))
    db.commit()

    # 2. Roles & Permissions
    perm_lookup = {}
    for code, mod, act, desc in PERMISSIONS:
        perm = db.query(models.Permission).filter(models.Permission.code == code).first()
        if not perm:
            perm = models.Permission(code=code, module=mod, action=act, description=desc)
            db.add(perm)
            db.flush()
        perm_lookup[code] = perm

    role_lookup = {}
    for r_name, r_desc in ROLES:
        role = db.query(models.Role).filter(models.Role.role_name == r_name).first()
        if not role:
            role = models.Role(role_name=r_name, description=r_desc)
            db.add(role)
            db.flush()
        role_lookup[r_name] = role

        # Assign permissions
        assigned_perms = ROLE_PERMISSION_MAP.get(r_name, [])
        for p_code in assigned_perms:
            p_obj = perm_lookup.get(p_code)
            if p_obj:
                exists_rp = db.query(models.RolePermission).filter(
                    models.RolePermission.role_id == role.role_id,
                    models.RolePermission.permission_id == p_obj.permission_id
                ).first()
                if not exists_rp:
                    db.add(models.RolePermission(role_id=role.role_id, permission_id=p_obj.permission_id))
    db.commit()

    # 3. Branches
    branches_data = [
        ("Main Industrial Branch", "Plot 12-14 7th Street, Industrial Area, Kampala", "+256 414 123456"),
        ("Downtown Retail Store", "Plot 8 Market Street, City Centre, Kampala", "+256 414 654321"),
    ]
    branch_lookup = {}
    for b_name, loc, contact in branches_data:
        br = db.query(models.Branch).filter(models.Branch.branchname == b_name).first()
        if not br:
            br = models.Branch(branchname=b_name, location=loc, contactnumber=contact)
            db.add(br)
            db.flush()
        branch_lookup[b_name] = br
    db.commit()

    # 4. Warehouses
    wh_data = [
        ("Main Industrial Warehouse", branch_lookup["Main Industrial Branch"].branchid, "Building B, Industrial Area"),
        ("Downtown Retail Warehouse", branch_lookup["Downtown Retail Store"].branchid, "Basement Storage, Market Street"),
    ]
    warehouse_lookup = {}
    for w_name, b_id, loc in wh_data:
        wh = db.query(models.Warehouse).filter(models.Warehouse.warehouse_name == w_name).first()
        if not wh:
            wh = models.Warehouse(warehouse_name=w_name, branch_id=b_id, location=loc, is_active=True)
            db.add(wh)
            db.flush()
        warehouse_lookup[w_name] = wh
    db.commit()

    # 5. Departments
    dept_data = [
        ("Administration", branch_lookup["Main Industrial Branch"].branchid),
        ("Sales & POS", branch_lookup["Main Industrial Branch"].branchid),
        ("Procurement & Inventory", branch_lookup["Main Industrial Branch"].branchid),
        ("Finance & Accounting", branch_lookup["Main Industrial Branch"].branchid),
        ("Human Resources", branch_lookup["Main Industrial Branch"].branchid),
        ("Operations & Branch Management", branch_lookup["Main Industrial Branch"].branchid),
    ]
    dept_lookup = {}
    for d_name, b_id in dept_data:
        d = db.query(models.Department).filter(
            models.Department.departmentname == d_name,
            models.Department.branchid == b_id
        ).first()
        if not d:
            d = models.Department(departmentname=d_name, branchid=b_id)
            db.add(d)
            db.flush()
        dept_lookup[d_name] = d
    db.commit()

    # 6. Seed Staff (Master Prompt Section 0)
    default_password_hash = auth.get_password_hash(seed_password)

    staff_data = [
        {
            "name": "Akena",
            "nin": "CM85012345XYZ1",
            "email": "akena@hardwareworld.com",
            "roletype": models.RoleType.ADMIN,
            "dept": "Administration",
            "branch": "Main Industrial Branch",
            "salary": Decimal("3500000"),
            "role_name": "System Administrator",
        },
        {
            "name": "Sarah Nakato",
            "nin": "CF94023456ABC2",
            "email": "sarah.nakato@hardwareworld.com",
            "roletype": models.RoleType.CASHIER,
            "dept": "Sales & POS",
            "branch": "Main Industrial Branch",
            "salary": Decimal("950000"),
            "role_name": "Cashier",
            "pos_terminal": "POS-MAIN-01",
        },
        {
            "name": "John Kato",
            "nin": "CM90034567DEF3",
            "email": "john.kato@hardwareworld.com",
            "roletype": models.RoleType.PROCUREMENT_OFFICER,
            "dept": "Procurement & Inventory",
            "branch": "Main Industrial Branch",
            "salary": Decimal("1800000"),
            "role_name": "Procurement Officer",
            "approvallimit": Decimal("5000000"),
        },
        {
            "name": "Grace Apio",
            "nin": "CF91045678GHI4",
            "email": "grace.apio@hardwareworld.com",
            "roletype": models.RoleType.ACCOUNTANT,
            "dept": "Finance & Accounting",
            "branch": "Main Industrial Branch",
            "salary": Decimal("2200000"),
            "role_name": "Accountant",
            "cert": "CPA-UG-4891",
        },
        {
            "name": "Moses Opolot",
            "nin": "CM89056789JKL5",
            "email": "moses.opolot@hardwareworld.com",
            "roletype": models.RoleType.HR_STAFF,
            "dept": "Human Resources",
            "branch": "Main Industrial Branch",
            "salary": Decimal("1600000"),
            "role_name": "HR Officer",
            "hr_role": "HR Generalist",
        },
        {
            "name": "Brian Mukasa",
            "nin": "CM84067890MNO6",
            "email": "brian.mukasa@hardwareworld.com",
            "roletype": models.RoleType.BRANCH_MANAGER,
            "dept": "Operations & Branch Management",
            "branch": "Main Industrial Branch",
            "salary": Decimal("2800000"),
            "role_name": "Branch Manager",
            "mgmt_level": "Senior Branch Manager",
        },
    ]

    emp_lookup = {}
    for s in staff_data:
        emp = db.query(models.Employee).filter(models.Employee.email == s["email"]).first()
        if not emp:
            emp = models.Employee(
                name=s["name"],
                nin=s["nin"],
                email=s["email"],
                hashed_password=default_password_hash,
                phone="+256 772 000000",
                datehired=date(2023, 1, 15),
                salary=s["salary"],
                departmentid=dept_lookup[s["dept"]].departmentid,
                branchid=branch_lookup[s["branch"]].branchid,
                roletype=s["roletype"],
                is_active=True,
            )
            db.add(emp)
            db.flush()

            # Subtype record
            if s["roletype"] == models.RoleType.CASHIER:
                db.add(models.Cashier(employeeid=emp.employeeid, pos_terminalid=s.get("pos_terminal", "POS-01")))
            elif s["roletype"] == models.RoleType.PROCUREMENT_OFFICER:
                db.add(models.ProcurementOfficer(employeeid=emp.employeeid, approvallimit=s.get("approvallimit", Decimal("5000000"))))
            elif s["roletype"] == models.RoleType.ACCOUNTANT:
                db.add(models.Accountant(employeeid=emp.employeeid, certificationnumber=s.get("cert", "CPA-UG")))
            elif s["roletype"] == models.RoleType.HR_STAFF:
                db.add(models.HRStaff(employeeid=emp.employeeid, hr_role=s.get("hr_role", "HR Officer")))
            elif s["roletype"] == models.RoleType.BRANCH_MANAGER:
                db.add(models.BranchManager(employeeid=emp.employeeid, managementlevel=s.get("mgmt_level", "Branch Manager")))
        else:
            emp.hashed_password = default_password_hash
            emp.token_version = (emp.token_version or 0) + 1

            # Salary structure
            db.add(models.EmployeeSalaryStructure(
                employee_id=emp.employeeid,
                basic_salary=s["salary"],
                transport_allowance=Decimal("150000"),
                overtime_rate=Decimal("15000"),
                standard_deductions=Decimal("80000")
            ))

        # Assign Role
        r_obj = role_lookup.get(s["role_name"])
        if r_obj:
            user_role = db.query(models.UserRole).filter(
                models.UserRole.user_id == emp.employeeid,
                models.UserRole.role_id == r_obj.role_id
            ).first()
            if not user_role:
                db.add(models.UserRole(user_id=emp.employeeid, role_id=r_obj.role_id))

        # User Branch Assignment
        ub = db.query(models.UserBranchAssignment).filter(
            models.UserBranchAssignment.user_id == emp.employeeid,
            models.UserBranchAssignment.branch_id == branch_lookup[s["branch"]].branchid
        ).first()
        if not ub:
            db.add(models.UserBranchAssignment(
                user_id=emp.employeeid,
                branch_id=branch_lookup[s["branch"]].branchid,
                is_primary=True
            ))

        emp_lookup[s["name"]] = emp
    db.commit()

    # Link branch manager to Main Industrial Branch
    branch_lookup["Main Industrial Branch"].manageremployeeid = emp_lookup["Brian Mukasa"].employeeid
    db.commit()

    # 7. Categories
    cat_names = [
        "Hand Tools & Equipment",
        "Electrical Supplies",
        "Plumbing & Fixtures",
        "Building Materials",
        "Paints & Finishes"
    ]
    cat_lookup = {}
    for c_name in cat_names:
        cat = db.query(models.Category).filter(models.Category.categoryname == c_name).first()
        if not cat:
            cat = models.Category(categoryname=c_name)
            db.add(cat)
            db.flush()
        cat_lookup[c_name] = cat
    db.commit()

    # 8. Suppliers
    sup_data = [
        ("Tororo Cement Ltd", "Okello David", "+256 701 234567", "Plot 4 Industrial Area, Tororo"),
        ("Uganda Clays & Materials", "Namubiru Sarah", "+256 772 345678", "Entebbe Road, Kajjansi"),
        ("Kampala Hardware Importers", "Patel Rajesh", "+256 753 456789", "7th Street Industrial Area, Kampala"),
    ]
    sup_lookup = {}
    for s_name, cp, phone, addr in sup_data:
        sup = db.query(models.Supplier).filter(models.Supplier.suppliername == s_name).first()
        if not sup:
            sup = models.Supplier(suppliername=s_name, contactperson=cp, phone=phone, address=addr)
            db.add(sup)
            db.flush()
        sup_lookup[s_name] = sup
    db.commit()

    # 9. Baseline Products & Opening Stock
    main_wh = warehouse_lookup["Main Industrial Warehouse"]
    products_data = [
        {
            "name": "Claw Hammer 16oz Steel Shank",
            "desc": "Heavy duty forged steel claw hammer with shock reduction grip",
            "cat": "Hand Tools & Equipment",
            "unitprice": Decimal("15000"),
            "costprice": Decimal("10000"),
            "reorderlevel": 10,
            "unit": "Piece",
            "stock": Decimal("50.000"),
            "supplier": "Kampala Hardware Importers",
        },
        {
            "name": "Electrical Cable 2.5 mm Single Core",
            "desc": "Copper insulated wiring cable 450/750V (per metre)",
            "cat": "Electrical Supplies",
            "unitprice": Decimal("3500"),
            "costprice": Decimal("2200"),
            "reorderlevel": 50,
            "unit": "Metre",
            "stock": Decimal("250.000"),
            "supplier": "Kampala Hardware Importers",
        },
        {
            "name": "Portland Pozzolana Cement 50kg Bag",
            "desc": "CEM II / B-P 32.5N quality construction cement",
            "cat": "Building Materials",
            "unitprice": Decimal("38000"),
            "costprice": Decimal("32000"),
            "reorderlevel": 20,
            "unit": "Bag",
            "stock": Decimal("100.000"),
            "supplier": "Tororo Cement Ltd",
        },
        {
            "name": "Weatherguard Emulsion Paint Brilliant White 20L",
            "desc": "High opacity exterior & interior water-based emulsion paint",
            "cat": "Paints & Finishes",
            "unitprice": Decimal("85000"),
            "costprice": Decimal("65000"),
            "reorderlevel": 5,
            "unit": "Bucket",
            "stock": Decimal("30.000"),
            "supplier": "Kampala Hardware Importers",
        },
        {
            "name": "Steel Wood Screws 2-inch (Box of 100)",
            "desc": "Zinc plated countersunk wood screws",
            "cat": "Hand Tools & Equipment",
            "unitprice": Decimal("12000"),
            "costprice": Decimal("8000"),
            "reorderlevel": 15,
            "unit": "Box",
            "stock": Decimal("80.000"),
            "supplier": "Kampala Hardware Importers",
        },
    ]

    for p in products_data:
        prod = db.query(models.Product).filter(models.Product.itemname == p["name"]).first()
        if not prod:
            prod = models.Product(
                itemname=p["name"],
                description=p["desc"],
                unitprice=p["unitprice"],
                costprice=p["costprice"],
                reorderlevel=p["reorderlevel"],
                base_unit=p["unit"],
                categoryid=cat_lookup[p["cat"]].categoryid,
                is_active=True,
            )
            db.add(prod)
            db.flush()

            # Supplier link
            s_obj = sup_lookup.get(p["supplier"])
            if s_obj:
                db.add(models.Supply(
                    supplierid=s_obj.supplierid,
                    itemid=prod.itemid,
                    costprice=p["costprice"],
                    leadtimedays=5
                ))

            # Opening Inventory Balance
            db.add(models.InventoryBalance(
                item_id=prod.itemid,
                warehouse_id=main_wh.warehouse_id,
                available_stock=p["stock"],
                reserved_stock=Decimal("0")
            ))

            # Inventory Movement: OPENING_STOCK
            db.add(models.InventoryMovement(
                item_id=prod.itemid,
                warehouse_id=main_wh.warehouse_id,
                movement_type="OPENING_STOCK",
                quantity=p["stock"],
                unit_cost=p["costprice"],
                reference_type="OPENING_STOCK",
                performed_by=emp_lookup["Akena"].employeeid,
                notes="Initial opening stock baseline"
            ))

            # Reorder Rule
            db.add(models.ReorderRule(
                item_id=prod.itemid,
                warehouse_id=main_wh.warehouse_id,
                reorder_level=Decimal(str(p["reorderlevel"])),
                critical_level=Decimal(str(max(1, p["reorderlevel"] // 2))),
                target_stock_level=Decimal(str(p["stock"]))
            ))
    db.commit()

    # 10. Sample Verified Customer with Credit Account
    cust = db.query(models.Customer).filter(models.Customer.name == "Ssekandi Contractors Ltd").first()
    if not cust:
        cust = models.Customer(name="Ssekandi Contractors Ltd", phone="+256 782 112233")
        db.add(cust)
        db.flush()
        db.add(models.CustomerCreditAccount(
            customer_id=cust.customerid,
            credit_limit=Decimal("5000000"),
            current_balance=Decimal("0"),
            is_blocked=False
        ))
        db.commit()

    print("Baseline seed successfully applied!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        # Create all tables first
        Base.metadata.create_all(bind=engine)
        seed_baseline(db)
    finally:
        db.close()
