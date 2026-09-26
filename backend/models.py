from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, Enum, DateTime, Numeric, Text, UniqueConstraint, Table
from sqlalchemy.orm import relationship
import enum
from database import Base
from datetime import datetime

class RoleType(str, enum.Enum):
    CASHIER = "Cashier"
    PROCUREMENT_OFFICER = "Procurement Officer"
    ACCOUNTANT = "Accountant"
    HR_STAFF = "HR Staff"
    BRANCH_MANAGER = "Branch Manager"
    ADMIN = "Admin"

class POStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    RECEIVED = "Received"
    PARTIALLY_RECEIVED = "Partially Received"
    CANCELLED = "Cancelled"

class LedgerSourceType(str, enum.Enum):
    SALE = "SALE"
    PAYROLL = "PAYROLL"

class Category(Base):
    __tablename__ = "category"
    categoryid = Column(Integer, primary_key=True, index=True)
    categoryname = Column(String(100), nullable=False)
    products = relationship("Product", back_populates="category")

class Supplier(Base):
    __tablename__ = "supplier"
    supplierid = Column(Integer, primary_key=True, index=True)
    suppliername = Column(String(150), nullable=False)
    contactperson = Column(String(100))
    phone = Column(String(20))
    address = Column(String(255))
    supplies = relationship("Supply", back_populates="supplier")

class Customer(Base):
    __tablename__ = "customer"
    customerid = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    phone = Column(String(20))
    sales = relationship("Sale", back_populates="customer")

class Branch(Base):
    __tablename__ = "branch"
    branchid = Column(Integer, primary_key=True, index=True)
    branchname = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    contactnumber = Column(String(20))
    manageremployeeid = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    
    departments = relationship("Department", back_populates="branch")
    employees = relationship("Employee", foreign_keys="Employee.branchid", back_populates="branch")

class Department(Base):
    __tablename__ = "department"
    departmentid = Column(Integer, primary_key=True, index=True)
    departmentname = Column(String(50), nullable=False)
    branchid = Column(Integer, ForeignKey("branch.branchid"), nullable=False)
    branch = relationship("Branch", back_populates="departments")
    employees = relationship("Employee", back_populates="department")

class Employee(Base):
    __tablename__ = "employee"
    employeeid = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    nin = Column(String(20), nullable=False, unique=True)
    email = Column(String(100), unique=True, index=True) # Added for FastAPI Auth
    hashed_password = Column(String(255)) # Added for FastAPI Auth
    phone = Column(String(20))
    datehired = Column(Date)
    salary = Column(Numeric(10, 2))
    departmentid = Column(Integer, ForeignKey("department.departmentid"))
    branchid = Column(Integer, ForeignKey("branch.branchid"))
    supervisorid = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    roletype = Column(Enum(RoleType), nullable=False)

    department = relationship("Department", back_populates="employees")
    branch = relationship("Branch", foreign_keys=[branchid], back_populates="employees")
    managed_branch = relationship("Branch", foreign_keys=[Branch.manageremployeeid])

class Cashier(Base):
    __tablename__ = "cashier"
    employeeid = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    pos_terminalid = Column(String(50), nullable=False)

class ProcurementOfficer(Base):
    __tablename__ = "procurement_officer"
    employeeid = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    approvallimit = Column(Numeric(12, 2), nullable=False)

class Accountant(Base):
    __tablename__ = "accountant"
    employeeid = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    certificationnumber = Column(String(50))

class HRStaff(Base):
    __tablename__ = "hr_staff"
    employeeid = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    hr_role = Column(String(50), nullable=False)

class BranchManager(Base):
    __tablename__ = "branch_manager"
    employeeid = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    managementlevel = Column(String(50))

class Product(Base):
    __tablename__ = "product"
    itemid = Column(Integer, primary_key=True, index=True)
    itemname = Column(String(150), nullable=False)
    description = Column(String(255))
    unitprice = Column(Numeric(10, 2), nullable=False)
    reorderlevel = Column(Integer)
    is_active = Column(Boolean, nullable=False, default=True)
    categoryid = Column(Integer, ForeignKey("category.categoryid"))
    category = relationship("Category", back_populates="products")

class Supply(Base):
    __tablename__ = "supply"
    supplierid = Column(Integer, ForeignKey("supplier.supplierid"), primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), primary_key=True)
    costprice = Column(Numeric(10, 2), nullable=False)
    leadtimedays = Column(Integer)
    supplier = relationship("Supplier", back_populates="supplies")
    product = relationship("Product")

class PurchaseOrder(Base):
    __tablename__ = "purchase_order"
    po_id = Column(Integer, primary_key=True, index=True)
    orderdate = Column(DateTime, default=datetime.utcnow)
    supplierid = Column(Integer, ForeignKey("supplier.supplierid"))
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=True, index=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=True, unique=True)
    status = Column(Enum(POStatus), default=POStatus.PENDING)

class ERPPurchaseRequisition(Base):
    __tablename__ = "purchase_requisitions"
    id = Column(Integer, primary_key=True)
    reference = Column(String(32), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPPurchaseRequisitionItem(Base):
    __tablename__ = "purchase_requisition_items"
    id = Column(Integer, primary_key=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id", ondelete="CASCADE"), nullable=False, index=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)
    estimated_unit_cost = Column(Numeric(15, 2), nullable=False)

class ERPPurchaseRequisitionApproval(Base):
    __tablename__ = "purchase_requisition_approvals"
    id = Column(Integer, primary_key=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    approved_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    decision = Column(String(20), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPPurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id = Column(Integer, primary_key=True)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id", ondelete="CASCADE"), nullable=False, index=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)
    received_quantity = Column(Numeric(15, 3), nullable=False, default=0)
    unit_cost = Column(Numeric(15, 2), nullable=False)

class ERPPurchaseOrderApproval(Base):
    __tablename__ = "purchase_order_approvals"
    id = Column(Integer, primary_key=True)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    approved_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    decision = Column(String(20), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPGoodsReceivedNote(Base):
    __tablename__ = "goods_received_notes"
    id = Column(Integer, primary_key=True)
    reference = Column(String(32), nullable=False, unique=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    received_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    status = Column(String(20), nullable=False, default="CONFIRMED")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPGoodsReceivedNoteItem(Base):
    __tablename__ = "goods_received_note_items"
    id = Column(Integer, primary_key=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)

class ERPSupplierInvoice(Base):
    __tablename__ = "supplier_invoices"
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(80), nullable=False, index=True)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id"), nullable=False, index=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING_MATCH")
    created_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("invoice_number", "po_id", name="uq_supplier_invoice_po"),)

class ERPInvoiceMatchResult(Base):
    __tablename__ = "invoice_match_results"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    matched = Column(Boolean, nullable=False)
    ordered_quantity = Column(Numeric(15, 3), nullable=False)
    received_quantity = Column(Numeric(15, 3), nullable=False)
    invoiced_amount = Column(Numeric(15, 2), nullable=False)
    expected_amount = Column(Numeric(15, 2), nullable=False)
    variance_reason = Column(Text)
    checked_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPSupplierPayment(Base):
    __tablename__ = "supplier_payments"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_method = Column(String(32), nullable=False)
    paid_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Sale(Base):
    __tablename__ = "sale"
    saleid = Column(Integer, primary_key=True, index=True)
    saledate = Column(DateTime, default=datetime.utcnow)
    totalamount = Column(Numeric(12, 2))
    customerid = Column(Integer, ForeignKey("customer.customerid"), nullable=True)
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    branchid = Column(Integer, ForeignKey("branch.branchid"))
    status = Column(String(20), nullable=False, default="COMPLETED", index=True)
    idempotency_key = Column(String(120), nullable=True, unique=True)
    customer = relationship("Customer", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale")

class SaleItem(Base):
    __tablename__ = "sale_item"
    saleid = Column(Integer, ForeignKey("sale.saleid"), primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), primary_key=True)
    quantity = Column(Numeric(15, 3), nullable=False)
    unitpriceatsale = Column(Numeric(10, 2), nullable=False)
    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product")

class Payroll(Base):
    __tablename__ = "payroll"
    payrollid = Column(Integer, primary_key=True, index=True)
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    month = Column(String(20), nullable=False)
    grosspay = Column(Numeric(10, 2), nullable=False)
    deductions = Column(Numeric(10, 2))
    netpay = Column(Numeric(10, 2), nullable=False)

class LedgerEntry(Base):
    __tablename__ = "ledger_entry"
    entryid = Column(Integer, primary_key=True, index=True)
    entrydate = Column(DateTime, default=datetime.utcnow)
    sourcetype = Column(Enum(LedgerSourceType), nullable=False)
    saleid = Column(Integer, ForeignKey("sale.saleid"), nullable=True)
    payrollid = Column(Integer, ForeignKey("payroll.payrollid"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    recordedby = Column(Integer, ForeignKey("employee.employeeid"))

class ERPJournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True)
    reference_type = Column(String(40), nullable=False)
    reference_id = Column(Integer, nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="POSTED")
    created_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPJournalLine(Base):
    __tablename__ = "journal_entry_lines"
    id = Column(Integer, primary_key=True)
    journal_id = Column(Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_code = Column(String(32), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    debit = Column(Numeric(15, 2), nullable=False, default=0)
    credit = Column(Numeric(15, 2), nullable=False, default=0)


# Additive ERP foundation. The legacy six-value Employee.roletype remains the
# dashboard-routing role; these tables provide extensible, fine-grained RBAC.
user_roles = Table(
    "user_roles", Base.metadata,
    Column("employeeid", Integer, ForeignKey("employee.employeeid", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

class ERPOrganization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPWarehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("branch_id", "name", name="uq_warehouse_branch_name"),)

class ERPStockBalance(Base):
    __tablename__ = "inventory_balances"
    id = Column(Integer, primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True, index=True)
    quantity = Column(Numeric(15, 3), nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("itemid", "branch_id", "warehouse_id", name="uq_inventory_product_branch_warehouse"),)

class ERPInventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id = Column(Integer, primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    movement_type = Column(String(40), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)
    reference_type = Column(String(40), nullable=False)
    reference_id = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPPayment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    saleid = Column(Integer, ForeignKey("sale.saleid"), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    cashier_session_id = Column(Integer, ForeignKey("cashier_sessions.id"), nullable=True, index=True)
    method = Column(String(32), nullable=False, default="cash")
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), nullable=False, default="COMPLETED")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ERPAuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False, index=True)
    action = Column(String(80), nullable=False)
    module = Column(String(40), nullable=False)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(80), nullable=False)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=True, index=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class ERPRole(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True)
    description = Column(String(255))
    users = relationship("Employee", secondary=user_roles, backref="erp_roles")
    permissions = relationship("ERPPermission", secondary=role_permissions, back_populates="roles")

class ERPPermission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(120), nullable=False, unique=True, index=True)
    module = Column(String(50), nullable=False, index=True)
    action = Column(String(40), nullable=False)
    scope = Column(String(40), nullable=False, default="organization")
    roles = relationship("ERPRole", secondary=role_permissions, back_populates="permissions")

class ERPCashierSession(Base):
    __tablename__ = "cashier_sessions"
    id = Column(Integer, primary_key=True)
    employeeid = Column(Integer, ForeignKey("employee.employeeid"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False, index=True)
    opening_float = Column(Numeric(15, 2), nullable=False)
    closing_amount = Column(Numeric(15, 2))
    status = Column(String(20), nullable=False, default="OPEN")
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime)
