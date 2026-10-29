"""Repeatable bootstrap for additive ERP roles, permissions, and opening stock."""
from decimal import Decimal
import models

ROLE_NAMES = [
    "System Administrator", "Owner / Executive", "General Manager", "Branch Manager",
    "Sales Manager", "Cashier", "Sales Clerk", "Storekeeper", "Warehouse Supervisor",
    "Inventory Manager", "Procurement Officer", "Procurement Manager", "Finance Clerk",
    "Accountant", "Finance Manager", "HR Officer", "HR Manager",
]

LEGACY_ROLE = {
    models.RoleType.ADMIN: "System Administrator",
    models.RoleType.CASHIER: "Cashier",
    models.RoleType.PROCUREMENT_OFFICER: "Procurement Officer",
    models.RoleType.ACCOUNTANT: "Accountant",
    models.RoleType.HR_STAFF: "HR Officer",
    models.RoleType.BRANCH_MANAGER: "Branch Manager",
}

ROLE_ACCESS = {
    "System Administrator": {"admin:users", "admin:audit"},
    "Owner / Executive": {"reports:read", "sales:read", "inventory:read", "finance:read", "procurement:read", "hr:read", "approvals:approve"},
    "General Manager": {"reports:read", "sales:read", "inventory:read", "finance:read", "procurement:read", "hr:read", "approvals:approve"},
    "Branch Manager": {"reports:read", "sales:read", "inventory:read", "finance:read", "procurement:read", "approvals:approve"},
    "Sales Manager": {"sales:read", "sales:create", "sales:approve", "reports:read", "customers:read"},
    "Cashier": {"sales:read", "sales:create", "inventory:read", "customers:read"},
    "Sales Clerk": {"sales:read", "sales:create", "customers:read"},
    "Storekeeper": {"inventory:read", "inventory:create", "procurement:read"},
    "Warehouse Supervisor": {"inventory:read", "inventory:create", "inventory:approve", "procurement:read"},
    "Inventory Manager": {"inventory:read", "inventory:create", "inventory:approve", "reports:read"},
    "Procurement Officer": {"procurement:read", "procurement:create", "inventory:read"},
    "Procurement Manager": {"procurement:read", "procurement:create", "procurement:approve", "inventory:read"},
    "Finance Clerk": {"finance:read", "finance:create"},
    "Accountant": {"finance:read", "finance:create", "finance:post", "sales:read", "procurement:read", "payroll:read"},
    "Finance Manager": {"finance:read", "finance:create", "finance:post", "finance:approve", "reports:read"},
    "HR Officer": {"hr:read", "hr:create", "payroll:read", "payroll:create"},
    "HR Manager": {"hr:read", "hr:create", "hr:approve", "payroll:read", "payroll:create", "payroll:approve"},
}

def ensure_erp_seed(db):
    roles = {r.name: r for r in db.query(models.ERPRole).all()}
    for name in ROLE_NAMES:
        roles.setdefault(name, models.ERPRole(name=name, description=f"Hardware World {name} role"))
    db.add_all(roles.values())
    db.flush()

    permissions = {p.code: p for p in db.query(models.ERPPermission).all()}
    codes = set().union(*ROLE_ACCESS.values()) - {"*"}
    for code in codes:
        module, action = code.split(":", 1)
        permissions.setdefault(code, models.ERPPermission(code=code, module=module, action=action, scope="branch"))
    db.add_all(permissions.values())
    db.flush()
    for role_name, access in ROLE_ACCESS.items():
        role = roles[role_name]
        if "*" in access:
            role.permissions = list(permissions.values())
        elif role_name == "System Administrator":
            role.permissions = [permissions[code] for code in access]
        else:
            role.permissions = list({*role.permissions, *(permissions[code] for code in access)})

    for employee in db.query(models.Employee).all():
        role = roles[LEGACY_ROLE[employee.roletype]]
        if role not in employee.erp_roles:
            employee.erp_roles.append(role)
    for order in db.query(models.PurchaseOrder).filter(models.PurchaseOrder.branch_id.is_(None)).all():
        officer = db.query(models.Employee).filter_by(employeeid=order.employeeid).first()
        if officer:
            order.branch_id = officer.branchid

    # Stock is posted only through receipt/opening workflows. Never invent balances.
