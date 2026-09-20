from database import SessionLocal
import models
import auth
from datetime import date
from decimal import Decimal

def seed_defaults():
    db = SessionLocal()
    try:
        b1 = db.query(models.Branch).first()
        depts = {d.departmentname: d for d in db.query(models.Department).all()}

        defaults = [
            {
                'name': 'default', 'email': 'default@hardwareworld.com', 'pass': 'default',
                'nin': 'DEF000000000001', 'role': models.RoleType.ADMIN, 'dept': 'Administration'
            },
            {
                'name': 'default_sales', 'email': 'default.sales@hardwareworld.com', 'pass': 'default_sales',
                'nin': 'DEF000000000002', 'role': models.RoleType.CASHIER, 'dept': 'Sales & POS',
                'subtype': ('cashier', {'pos_terminalid': 'POS-DEF-01'})
            },
            {
                'name': 'default_procurement', 'email': 'default.procurement@hardwareworld.com', 'pass': 'default_procurement',
                'nin': 'DEF000000000003', 'role': models.RoleType.PROCUREMENT_OFFICER, 'dept': 'Procurement & Inventory',
                'subtype': ('procurement', {'approvallimit': Decimal('50000000.00')})
            },
            {
                'name': 'default_finance', 'email': 'default.finance@hardwareworld.com', 'pass': 'default_finance',
                'nin': 'DEF000000000004', 'role': models.RoleType.ACCOUNTANT, 'dept': 'Finance & Accounting',
                'subtype': ('accountant', {'certificationnumber': 'CPA-DEF-01'})
            },
            {
                'name': 'default_hr', 'email': 'default.hr@hardwareworld.com', 'pass': 'default_hr',
                'nin': 'DEF000000000005', 'role': models.RoleType.HR_STAFF, 'dept': 'Human Resources',
                'subtype': ('hr', {'hr_role': 'HR Officer'})
            },
            {
                'name': 'default_operations', 'email': 'default.operations@hardwareworld.com', 'pass': 'default_operations',
                'nin': 'DEF000000000006', 'role': models.RoleType.BRANCH_MANAGER, 'dept': 'Operations & Branch Management',
                'subtype': ('ops', {'managementlevel': 'Operations Lead'})
            }
        ]

        for d in defaults:
            existing = db.query(models.Employee).filter(
                (models.Employee.email == d['email']) | (models.Employee.name == d['name'])
            ).first()
            if not existing:
                dept_obj = depts.get(d['dept'])
                dept_id = dept_obj.departmentid if dept_obj else None
                emp = models.Employee(
                    name=d['name'],
                    nin=d['nin'],
                    email=d['email'],
                    hashed_password=auth.get_password_hash(d['pass']),
                    phone='+256 700 000 000',
                    datehired=date(2024, 1, 1),
                    salary=Decimal('5000000.00'),
                    departmentid=dept_id,
                    branchid=b1.branchid if b1 else None,
                    roletype=d['role']
                )
                db.add(emp)
                db.flush()
                if 'subtype' in d:
                    st_type, st_args = d['subtype']
                    if st_type == 'cashier':
                        db.add(models.Cashier(employeeid=emp.employeeid, **st_args))
                    elif st_type == 'procurement':
                        db.add(models.ProcurementOfficer(employeeid=emp.employeeid, **st_args))
                    elif st_type == 'accountant':
                        db.add(models.Accountant(employeeid=emp.employeeid, **st_args))
                    elif st_type == 'hr':
                        db.add(models.HRStaff(employeeid=emp.employeeid, **st_args))
                    elif st_type == 'ops':
                        db.add(models.BranchManager(employeeid=emp.employeeid, **st_args))
                print(f"Seeded default account: {d['name']}")
            else:
                print(f"Account already exists: {d['name']}")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding defaults: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_defaults()
