from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, ForeignKey, Enum, DateTime,
    Numeric, Text, Index, UniqueConstraint
)
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
    PARTIALLY_RECEIVED = "Partially Received"
    RECEIVED = "Received"
    PARTIALLY_RECEIVED = "Partially Received"
    CANCELLED = "Cancelled"

class LedgerSourceType(str, enum.Enum):
    SALE = "SALE"
    PAYROLL = "PAYROLL"
    PURCHASE = "PURCHASE"
    ADJUSTMENT = "ADJUSTMENT"
    PAYMENT = "PAYMENT"

# =====================================================================
# 1. Organization & Core Entities (Existing 18 + Extensions)
# =====================================================================

class Branch(Base):
    __tablename__ = "branch"
    branchid = Column(Integer, primary_key=True, index=True)
    branchname = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    contactnumber = Column(String(20))
    manageremployeeid = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    
    departments = relationship("Department", back_populates="branch")
    employees = relationship("Employee", foreign_keys="Employee.branchid", back_populates="branch")
    warehouses = relationship("Warehouse", back_populates="branch")

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
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    phone = Column(String(20))
    datehired = Column(Date)
    salary = Column(Numeric(10, 2))
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    departmentid = Column(Integer, ForeignKey("department.departmentid"))
    branchid = Column(Integer, ForeignKey("branch.branchid"))
    supervisorid = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    roletype = Column(Enum(RoleType), nullable=False)
    is_active = Column(Boolean, default=True)

    department = relationship("Department", back_populates="employees")
    branch = relationship("Branch", foreign_keys=[branchid], back_populates="employees")
    managed_branch = relationship("Branch", foreign_keys=[Branch.manageremployeeid])
    user_roles = relationship("UserRole", back_populates="employee")
    salary_structure = relationship("EmployeeSalaryStructure", back_populates="employee", uselist=False)

# Subtypes from existing schema
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

# =====================================================================
# 2. RBAC & Governance Tables (Section 3 & 5.2)
# =====================================================================

class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    role_permissions = relationship("RolePermission", back_populates="role")
    user_roles = relationship("UserRole", back_populates="role")

class Permission(Base):
    __tablename__ = "permissions"
    permission_id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)

    role_permissions = relationship("RolePermission", back_populates="permission")

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)

    employee = relationship("Employee", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.permission_id"), primary_key=True)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")

class UserBranchAssignment(Base):
    __tablename__ = "user_branch_assignments"
    user_id = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), primary_key=True)
    is_primary = Column(Boolean, default=False)

class UserWarehouseAssignment(Base):
    __tablename__ = "user_warehouse_assignments"
    user_id = Column(Integer, ForeignKey("employee.employeeid"), primary_key=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), primary_key=True)
    is_primary = Column(Boolean, default=False)

class ApprovalLimit(Base):
    __tablename__ = "approval_limits"
    limit_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    module = Column(String(50), nullable=False) # PO, DISCOUNT, REFUND, ADJUSTMENT, PAYROLL
    max_amount = Column(Numeric(12, 2), nullable=False)

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    request_id = Column(Integer, primary_key=True, index=True)
    module = Column(String(50), nullable=False) # PO, DISCOUNT, REFUND, ADJUSTMENT, PAYROLL
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    requester_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    approver_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    status = Column(String(20), default="PENDING") # PENDING, APPROVED, REJECTED
    requested_amount = Column(Numeric(12, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    actioned_at = Column(DateTime, nullable=True)

# =====================================================================
# 3. Warehousing & Products Catalogue (Section 5.2 & 6B)
# =====================================================================

class Warehouse(Base):
    __tablename__ = "warehouses"
    warehouse_id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False)
    warehouse_name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=True)

    branch = relationship("Branch", back_populates="warehouses")
    stock_locations = relationship("StockLocation", back_populates="warehouse")
    inventory_balances = relationship("InventoryBalance", back_populates="warehouse")

class StockLocation(Base):
    __tablename__ = "stock_locations"
    location_id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=False)
    location_code = Column(String(50), nullable=False)
    description = Column(String(150), nullable=True)

    warehouse = relationship("Warehouse", back_populates="stock_locations")

class Category(Base):
    __tablename__ = "category"
    categoryid = Column(Integer, primary_key=True, index=True)
    categoryname = Column(String(100), nullable=False)
    products = relationship("Product", back_populates="category")

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
    supplies = relationship("Supply", back_populates="product")
    inventory_balances = relationship("InventoryBalance", back_populates="product")

class Supplier(Base):
    __tablename__ = "supplier"
    supplierid = Column(Integer, primary_key=True, index=True)
    suppliername = Column(String(150), nullable=False)
    contactperson = Column(String(100))
    phone = Column(String(20))
    address = Column(String(255))
    supplies = relationship("Supply", back_populates="supplier")

class Supply(Base):
    __tablename__ = "supply"
    supplierid = Column(Integer, ForeignKey("supplier.supplierid"), primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), primary_key=True)
    costprice = Column(Numeric(10, 2), nullable=False)
    leadtimedays = Column(Integer)
    supplier = relationship("Supplier", back_populates="supplies")
    product = relationship("Product", back_populates="supplies")

# Inventory movements & balances
class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    balance_id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=False)
    available_stock = Column(Numeric(15, 3), default=0, nullable=False)
    reserved_stock = Column(Numeric(15, 3), default=0, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory_balances")
    warehouse = relationship("Warehouse", back_populates="inventory_balances")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    movement_id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=False)
    movement_type = Column(String(50), nullable=False) # OPENING_STOCK, SALE_OUT, PURCHASE_IN, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT, RETURN_IN, SHRINKAGE
    quantity = Column(Numeric(15, 3), nullable=False) # positive for inbound, negative for outbound
    unit_cost = Column(Numeric(10, 2), default=0)
    reference_type = Column(String(50), nullable=True) # SALE, PO, GRN, STOCKTAKE, TRANSFER, RETURN, ADJUSTMENT
    reference_id = Column(Integer, nullable=True)
    performed_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    warehouse = relationship("Warehouse")

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
    subtotal = Column(Numeric(12, 2), default=0)
    discountamount = Column(Numeric(12, 2), default=0)
    taxamount = Column(Numeric(12, 2), default=0)
    status = Column(String(50), default="COMPLETED") # COMPLETED, HELD, CANCELLED, REFUNDED
    paymentmethod = Column(String(50), default="CASH") # CASH, MOBILE_MONEY, CARD, CREDIT
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    customerid = Column(Integer, ForeignKey("customer.customerid"), nullable=True)
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    branchid = Column(Integer, ForeignKey("branch.branchid"))
    status = Column(String(20), nullable=False, default="COMPLETED", index=True)
    idempotency_key = Column(String(120), nullable=True, unique=True)
    customer = relationship("Customer", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale")
    payments = relationship("Payment", back_populates="sale")
    returns = relationship("SalesReturn", back_populates="sale")

class SaleItem(Base):
    __tablename__ = "sale_item"
    saleid = Column(Integer, ForeignKey("sale.saleid"), primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), primary_key=True)
    quantity = Column(Numeric(15, 3), nullable=False)
    unitpriceatsale = Column(Numeric(10, 2), nullable=False)
    unitcost = Column(Numeric(10, 2), default=0) # Unit cost snapshot at sale time
    discount = Column(Numeric(10, 2), default=0)
    line_total = Column(Numeric(12, 2), nullable=True)

    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale.saleid"), nullable=False)
    payment_method = Column(String(50), nullable=False) # CASH, MOBILE_MONEY, CARD, CREDIT
    amount = Column(Numeric(12, 2), nullable=False)
    reference_number = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sale = relationship("Sale", back_populates="payments")

class SalesReturn(Base):
    __tablename__ = "sales_returns"
    return_id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale.saleid"), nullable=False)
    reason = Column(String(255), nullable=False)
    status = Column(String(20), default="PENDING") # PENDING, APPROVED, REJECTED
    total_refund_amount = Column(Numeric(12, 2), default=0)
    requester_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    approver_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sale = relationship("Sale", back_populates="returns")

# =====================================================================
# 5. Procurement Workflows (Section 5.2 & 6E)
# =====================================================================

class PurchaseRequisition(Base):
    __tablename__ = "purchase_requisitions"
    requisition_id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branch.branchid"), nullable=False)
    status = Column(String(20), default="PENDING") # PENDING, APPROVED, REJECTED
    approved_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("PurchaseRequisitionItem", back_populates="requisition")

class PurchaseRequisitionItem(Base):
    __tablename__ = "purchase_requisition_items"
    item_req_id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.requisition_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)
    estimated_unit_price = Column(Numeric(10, 2), default=0)

    requisition = relationship("PurchaseRequisition", back_populates="items")
    product = relationship("Product")

class PurchaseOrder(Base):
    __tablename__ = "purchase_order"
    po_id = Column(Integer, primary_key=True, index=True)
    orderdate = Column(DateTime, default=datetime.utcnow)
    supplierid = Column(Integer, ForeignKey("supplier.supplierid"))
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    branchid = Column(Integer, ForeignKey("branch.branchid"), nullable=True)
    status = Column(Enum(POStatus), default=POStatus.PENDING)
    total_amount = Column(Numeric(12, 2), default=0)
    approved_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier")
    creator = relationship("Employee", foreign_keys=[employeeid])
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    grns = relationship("GoodsReceivedNote", back_populates="purchase_order")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    po_item_id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    quantity = Column(Numeric(15, 3), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    received_quantity = Column(Numeric(15, 3), default=0)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

class GoodsReceivedNote(Base):
    __tablename__ = "goods_received_notes"
    grn_id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.warehouse_id"), nullable=False)
    grn_number = Column(String(50), unique=True, nullable=False)
    received_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    received_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(255), nullable=True)
    status = Column(String(20), default="CONFIRMED")

    purchase_order = relationship("PurchaseOrder", back_populates="grns")
    warehouse = relationship("Warehouse")
    items = relationship("GoodsReceivedNoteItem", back_populates="grn")

class GoodsReceivedNoteItem(Base):
    __tablename__ = "goods_received_note_items"
    grn_item_id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.grn_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("product.itemid"), nullable=False)
    quantity_received = Column(Numeric(15, 3), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)

    grn = relationship("GoodsReceivedNote", back_populates="items")
    product = relationship("Product")

class SupplierInvoice(Base):
    __tablename__ = "supplier_invoices"
    __table_args__ = (UniqueConstraint("supplier_id", "invoice_number", name="uq_supplier_invoice_number"),)
    invoice_id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("supplier.supplierid"), nullable=False)
    po_id = Column(Integer, ForeignKey("purchase_order.po_id"), nullable=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.grn_id"), nullable=True)
    invoice_number = Column(String(50), nullable=False)
    invoice_amount = Column(Numeric(12, 2), nullable=False)
    matched_status = Column(String(20), default="MATCHED") # MATCHED, VARIANCE, UNMATCHED
    payment_status = Column(String(20), default="UNPAID") # UNPAID, PARTIAL, PAID
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    grn = relationship("GoodsReceivedNote")

class SupplierPayment(Base):
    __tablename__ = "supplier_payments"
    payment_id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.invoice_id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50), default="BANK") # BANK, CASH, CHEQUE
    paid_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("SupplierInvoice")

# =====================================================================
# 6. HR & Payroll Workflows (Section 5.2 & 6G)
# =====================================================================

class EmployeeSalaryStructure(Base):
    __tablename__ = "employee_salary_structures"
    structure_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.employeeid"), unique=True, nullable=False)
    basic_salary = Column(Numeric(10, 2), nullable=False)
    transport_allowance = Column(Numeric(10, 2), default=0)
    overtime_rate = Column(Numeric(10, 2), default=0)
    standard_deductions = Column(Numeric(10, 2), default=0)

    employee = relationship("Employee", back_populates="salary_structure")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    attendance_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(20), default="PRESENT") # PRESENT, ABSENT, ON_LEAVE
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    overtime_hours = Column(Numeric(4, 2), default=0)

    employee = relationship("Employee")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    leave_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    leave_type = Column(String(50), nullable=False) # Annual, Sick, Maternity, Paternity, Compassionate
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="PENDING") # PENDING, APPROVED, REJECTED
    approved_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", foreign_keys=[employee_id])

class Payroll(Base):
    __tablename__ = "payroll"
    payrollid = Column(Integer, primary_key=True, index=True)
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    month = Column(String(20), nullable=False)
    grosspay = Column(Numeric(10, 2), nullable=False)
    deductions = Column(Numeric(10, 2))
    netpay = Column(Numeric(10, 2), nullable=False)

    employee = relationship("Employee")

class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    run_id = Column(Integer, primary_key=True, index=True)
    month = Column(String(20), nullable=False) # e.g. "2026-09"
    total_gross = Column(Numeric(12, 2), default=0)
    total_deductions = Column(Numeric(12, 2), default=0)
    total_net = Column(Numeric(12, 2), default=0)
    status = Column(String(20), default="DRAFT") # DRAFT, REVIEWED, APPROVED, PAID
    prepared_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    approved_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    payslips = relationship("Payslip", back_populates="payroll_run")

class Payslip(Base):
    __tablename__ = "payslips"
    payslip_id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.run_id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employee.employeeid"), nullable=False)
    basic_salary = Column(Numeric(10, 2), nullable=False)
    allowances = Column(Numeric(10, 2), default=0)
    overtime = Column(Numeric(10, 2), default=0)
    deductions = Column(Numeric(10, 2), default=0)
    gross_pay = Column(Numeric(10, 2), nullable=False)
    net_pay = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(20), default="UNPAID") # UNPAID, PAID

    payroll_run = relationship("PayrollRun", back_populates="payslips")
    employee = relationship("Employee")

# =====================================================================
# 7. Financial Accounting & Ledger (Section 5.2 & 6C/E/G/H)
# =====================================================================

class LedgerEntry(Base):
    __tablename__ = "ledger_entry"
    entryid = Column(Integer, primary_key=True, index=True)
    entrydate = Column(DateTime, default=datetime.utcnow)
    sourcetype = Column(Enum(LedgerSourceType), nullable=False)
    saleid = Column(Integer, ForeignKey("sale.saleid"), nullable=True)
    payrollid = Column(Integer, ForeignKey("payroll.payrollid"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    recordedby = Column(Integer, ForeignKey("employee.employeeid"))

class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"
    account_id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(20), unique=True, nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    account_type = Column(String(50), nullable=False) # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    balance = Column(Numeric(15, 2), default=0)

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    entry_id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String(50), unique=True, nullable=False, index=True)
    entry_date = Column(DateTime, default=datetime.utcnow)
    description = Column(String(255), nullable=False)
    reference_type = Column(String(50), nullable=True) # SALE, PURCHASE, GRN, INVOICE, PAYROLL, STOCKTAKE, PAYMENT
    reference_id = Column(Integer, nullable=True)
    total_amount = Column(Numeric(15, 2), nullable=False)
    created_by = Column(Integer, ForeignKey("employee.employeeid"), nullable=True)

    lines = relationship("JournalEntryLine", back_populates="entry")

class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"
    line_id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("journal_entries.entry_id"), nullable=False)
    account_code = Column(String(20), ForeignKey("chart_of_accounts.account_code"), nullable=False)
    debit = Column(Numeric(15, 2), default=0)
    credit = Column(Numeric(15, 2), default=0)
    description = Column(String(255), nullable=True)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("ChartOfAccount")

class FinancialAccount(Base):
    __tablename__ = "financial_accounts"
    account_id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String(100), nullable=False)
    account_type = Column(String(50), nullable=False) # CASH, BANK, MOBILE_MONEY
    account_number = Column(String(50), nullable=True)
    balance = Column(Numeric(15, 2), default=0)

# =====================================================================
# 8. Audit Log (Section 5.3)
# =====================================================================

class AuditLog(Base):
    __tablename__ = "audit_log"

    auditlogid = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("employee.employeeid", ondelete="SET NULL"), nullable=True, index=True)
    username_or_email = Column(String(100), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    module = Column(String(50), nullable=True, index=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    reference_number = Column(String(100), nullable=True)
    branch_id = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("Employee", foreign_keys=[user_id])
