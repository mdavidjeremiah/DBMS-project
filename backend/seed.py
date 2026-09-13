from datetime import datetime, date, timedelta
from decimal import Decimal
import models
import auth
from database import engine, SessionLocal

def seed_database():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if already seeded
        admin_exists = db.query(models.Employee).filter(models.Employee.email == "akena@hardwareworld.com").first()
        if admin_exists:
            print("Database already contains Admin account 'Akena'. Checking departments and records...")
            return

        print("Seeding Hardware World initial database records...")

        # 1. Branches
        b1 = models.Branch(
            branchname="Main Industrial Branch",
            location="Plot 42 Jinja Road, Kampala",
            contactnumber="+256 414 500 100"
        )
        b2 = models.Branch(
            branchname="Downtown Retail Store",
            location="Shop 14 Luwum Street, Kampala",
            contactnumber="+256 414 500 200"
        )
        db.add_all([b1, b2])
        db.flush()

        # 2. Departments
        dept_sales = models.Department(departmentname="Sales & POS", branchid=b1.branchid)
        dept_proc = models.Department(departmentname="Procurement & Inventory", branchid=b1.branchid)
        dept_fin = models.Department(departmentname="Finance & Accounting", branchid=b1.branchid)
        dept_hr = models.Department(departmentname="Human Resources", branchid=b1.branchid)
        dept_ops = models.Department(departmentname="Operations & Branch Management", branchid=b1.branchid)
        dept_admin = models.Department(departmentname="Administration", branchid=b1.branchid)
        
        db.add_all([dept_sales, dept_proc, dept_fin, dept_hr, dept_ops, dept_admin])
        db.flush()

        # 3. Admin Account: Akena
        admin = models.Employee(
            name="Akena",
            nin="CM900241009AKN",
            email="akena@hardwareworld.com",
            hashed_password=auth.get_password_hash("adminpassword"),
            phone="+256 700 000 001",
            datehired=date(2024, 1, 1),
            salary=Decimal("15000000.00"),
            departmentid=dept_admin.departmentid,
            branchid=b1.branchid,
            roletype=models.RoleType.ADMIN
        )
        db.add(admin)
        db.flush()

        # 4. Department Staff Members
        # Cashier -> Sales & POS
        cashier = models.Employee(
            name="Sarah Nakato",
            nin="CF950123456SNK",
            email="sarah@hardwareworld.com",
            hashed_password=auth.get_password_hash("staff123"),
            phone="+256 772 111 222",
            datehired=date(2024, 3, 15),
            salary=Decimal("1800000.00"),
            departmentid=dept_sales.departmentid,
            branchid=b1.branchid,
            supervisorid=admin.employeeid,
            roletype=models.RoleType.CASHIER
        )
        db.add(cashier)
        db.flush()
        db.add(models.Cashier(employeeid=cashier.employeeid, pos_terminalid="POS-TERMINAL-01"))

        # Procurement Officer -> Procurement & Inventory
        proc_officer = models.Employee(
            name="John Kato",
            nin="CM920654321JKT",
            email="john@hardwareworld.com",
            hashed_password=auth.get_password_hash("staff123"),
            phone="+256 772 333 444",
            datehired=date(2024, 2, 1),
            salary=Decimal("3500000.00"),
            departmentid=dept_proc.departmentid,
            branchid=b1.branchid,
            supervisorid=admin.employeeid,
            roletype=models.RoleType.PROCUREMENT_OFFICER
        )
        db.add(proc_officer)
        db.flush()
        db.add(models.ProcurementOfficer(employeeid=proc_officer.employeeid, approvallimit=Decimal("50000000.00")))

        # Accountant -> Finance & Accounting
        accountant = models.Employee(
            name="Grace Apio",
            nin="CF940987654GAP",
            email="grace@hardwareworld.com",
            hashed_password=auth.get_password_hash("staff123"),
            phone="+256 772 555 666",
            datehired=date(2024, 1, 15),
            salary=Decimal("4200000.00"),
            departmentid=dept_fin.departmentid,
            branchid=b1.branchid,
            supervisorid=admin.employeeid,
            roletype=models.RoleType.ACCOUNTANT
        )
        db.add(accountant)
        db.flush()
        db.add(models.Accountant(employeeid=accountant.employeeid, certificationnumber="CPA-UG-4821"))

        # HR Staff -> Human Resources
        hr_staff = models.Employee(
            name="Moses Opolot",
            nin="CM910112233MOP",
            email="moses@hardwareworld.com",
            hashed_password=auth.get_password_hash("staff123"),
            phone="+256 772 777 888",
            datehired=date(2024, 4, 1),
            salary=Decimal("3000000.00"),
            departmentid=dept_hr.departmentid,
            branchid=b1.branchid,
            supervisorid=admin.employeeid,
            roletype=models.RoleType.HR_STAFF
        )
        db.add(hr_staff)
        db.flush()
        db.add(models.HRStaff(employeeid=hr_staff.employeeid, hr_role="Senior Human Resource Officer"))

        # Branch Manager -> Operations & Branch Management
        branch_mgr = models.Employee(
            name="Brian Mukasa",
            nin="CM890334455BMK",
            email="brian@hardwareworld.com",
            hashed_password=auth.get_password_hash("staff123"),
            phone="+256 772 999 000",
            datehired=date(2023, 11, 1),
            salary=Decimal("6000000.00"),
            departmentid=dept_ops.departmentid,
            branchid=b1.branchid,
            supervisorid=admin.employeeid,
            roletype=models.RoleType.BRANCH_MANAGER
        )
        db.add(branch_mgr)
        db.flush()
        db.add(models.BranchManager(employeeid=branch_mgr.employeeid, managementlevel="Branch Operations Lead"))
        b1.manageremployeeid = branch_mgr.employeeid

        # 5. Categories
        cat_tools = models.Category(categoryname="Power Tools")
        cat_building = models.Category(categoryname="Building Materials")
        cat_plumbing = models.Category(categoryname="Plumbing & Piping")
        cat_elec = models.Category(categoryname="Electrical Supplies")
        cat_paint = models.Category(categoryname="Paints & Hardware")
        db.add_all([cat_tools, cat_building, cat_plumbing, cat_elec, cat_paint])
        db.flush()

        # 6. Products
        p1 = models.Product(
            itemname="Bosch Rotary Hammer Drill 800W",
            description="Heavy-duty SDS plus rotary hammer for concrete and masonry drilling.",
            unitprice=Decimal("850000.00"),
            reorderlevel=5,
            categoryid=cat_tools.categoryid
        )
        p2 = models.Product(
            itemname="Tororo Portland Cement 50kg (Grade 32.5R)",
            description="High-grade setting cement for general structural construction.",
            unitprice=Decimal("38000.00"),
            reorderlevel=100,
            categoryid=cat_building.categoryid
        )
        p3 = models.Product(
            itemname="PPR Water Pipe 20mm x 4m (Hot/Cold)",
            description="Polypropylene random copolymer pipe for high-pressure water reticulation.",
            unitprice=Decimal("18500.00"),
            reorderlevel=50,
            categoryid=cat_plumbing.categoryid
        )
        p4 = models.Product(
            itemname="Chint 3-Phase Circuit Breaker 32A",
            description="DIN-rail miniature circuit breaker with short-circuit protection.",
            unitprice=Decimal("45000.00"),
            reorderlevel=20,
            categoryid=cat_elec.categoryid
        )
        p5 = models.Product(
            itemname="Sadolin Supercoat Silk Emulsion 20L",
            description="Premium washable acrylic interior paint in Brilliant White.",
            unitprice=Decimal("165000.00"),
            reorderlevel=15,
            categoryid=cat_paint.categoryid
        )
        p6 = models.Product(
            itemname="DeWalt 115mm Angle Grinder 850W",
            description="Compact disc grinder with paddle switch for metal cutting and beveling.",
            unitprice=Decimal("340000.00"),
            reorderlevel=8,
            categoryid=cat_tools.categoryid
        )
        p7 = models.Product(
            itemname="High-Tensile TMT Steel Rebars 12mm x 12m",
            description="Ribbed reinforcement steel bars for reinforced concrete slabs and columns.",
            unitprice=Decimal("42000.00"),
            reorderlevel=80,
            categoryid=cat_building.categoryid
        )
        db.add_all([p1, p2, p3, p4, p5, p6, p7])
        db.flush()

        # 7. Suppliers
        s1 = models.Supplier(
            suppliername="Tororo Cement Industries Ltd",
            contactperson="Rajesh Patel",
            phone="+256 454 448 000",
            address="Tororo Industrial Area, Uganda"
        )
        s2 = models.Supplier(
            suppliername="Bosch Power Tools East Africa",
            contactperson="Alice Namutebi",
            phone="+256 414 234 567",
            address="6th Street Industrial Area, Kampala"
        )
        s3 = models.Supplier(
            suppliername="Davis & Shirtliff Uganda",
            contactperson="Patrick Ouma",
            phone="+256 414 346 337",
            address="Plot 84 Jinja Road, Kampala"
        )
        db.add_all([s1, s2, s3])
        db.flush()

        # 8. Customers
        c1 = models.Customer(name="Kampala Construction Ltd", phone="+256 701 234 567")
        c2 = models.Customer(name="Eng. David Kasumba", phone="+256 782 987 654")
        c3 = models.Customer(name="Victoria Lake Developments", phone="+256 752 444 333")
        db.add_all([c1, c2, c3])
        db.flush()

        # 9. Recent Sales with dates across the past 10 days for statistical plotting
        now = datetime.utcnow()
        sales_data = [
            (9, Decimal("1850000.00"), c1.customerid, [(p2, 25), (p7, 20)]),
            (8, Decimal("2450000.00"), c2.customerid, [(p1, 2), (p6, 2)]),
            (7, Decimal("3200000.00"), c3.customerid, [(p2, 50), (p7, 30)]),
            (6, Decimal("1420000.00"), None, [(p5, 6), (p3, 20)]),
            (5, Decimal("2950000.00"), c1.customerid, [(p1, 1), (p2, 40), (p4, 10)]),
            (4, Decimal("3800000.00"), c3.customerid, [(p7, 50), (p2, 45)]),
            (3, Decimal("2100000.00"), c2.customerid, [(p6, 3), (p5, 5)]),
            (2, Decimal("4350000.00"), c1.customerid, [(p2, 80), (p7, 30)]),
            (1, Decimal("3600000.00"), None, [(p1, 2), (p5, 8), (p4, 15)]),
            (0, Decimal("2850000.00"), c2.customerid, [(p2, 50), (p3, 25)]),
        ]

        for days_ago, total, cust_id, items in sales_data:
            s_date = now - timedelta(days=days_ago, hours=days_ago * 2)
            sale = models.Sale(
                saledate=s_date,
                totalamount=total,
                customerid=cust_id,
                employeeid=cashier.employeeid,
                branchid=b1.branchid
            )
            db.add(sale)
            db.flush()
            for prod, qty in items:
                db.add(models.SaleItem(
                    saleid=sale.saleid,
                    itemid=prod.itemid,
                    quantity=qty,
                    unitpriceatsale=prod.unitprice
                ))

        # 10. Purchase Orders
        po1 = models.PurchaseOrder(
            orderdate=now - timedelta(days=5),
            supplierid=s1.supplierid,
            employeeid=proc_officer.employeeid,
            status=models.POStatus.APPROVED
        )
        po2 = models.PurchaseOrder(
            orderdate=now - timedelta(days=2),
            supplierid=s2.supplierid,
            employeeid=proc_officer.employeeid,
            status=models.POStatus.PENDING
        )
        po3 = models.PurchaseOrder(
            orderdate=now - timedelta(days=1),
            supplierid=s3.supplierid,
            employeeid=proc_officer.employeeid,
            status=models.POStatus.PENDING
        )
        db.add_all([po1, po2, po3])

        # 11. Ledger Entries
        db.add(models.LedgerEntry(
            entrydate=now - timedelta(days=3),
            sourcetype=models.LedgerSourceType.SALE,
            amount=Decimal("4350000.00"),
            recordedby=accountant.employeeid
        ))
        db.add(models.LedgerEntry(
            entrydate=now - timedelta(days=1),
            sourcetype=models.LedgerSourceType.PAYROLL,
            amount=Decimal("12500000.00"),
            recordedby=accountant.employeeid
        ))

        db.commit()
        print("Hardware World database seeded successfully!")
        print("Admin user: Akena (email: akena@hardwareworld.com, password: adminpassword)")
        print("Staff users seeded for Sales, Procurement, Finance, HR, Operations with password: staff123")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
