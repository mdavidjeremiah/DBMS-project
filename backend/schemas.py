from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import date, datetime
from decimal import Decimal
from models import RoleType, POStatus, LedgerSourceType

# --- Authentication & User Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[dict] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
    department: Optional[str] = None
    login_type: Optional[str] = "staff" # "admin" or "staff"

class UserCreate(BaseModel):
    name: str
    nin: str
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    phone: Optional[str] = None
    datehired: Optional[date] = None
    salary: Decimal
    departmentid: int
    branchid: int
    supervisorid: Optional[int] = None
    roletype: RoleType

class UserResponse(BaseModel):
    employeeid: int
    name: str
    email: Optional[str] = None
    roletype: RoleType
    departmentid: Optional[int] = None
    department_name: Optional[str] = None
    branchid: Optional[int] = None
    branch_name: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    branch_ids: List[int] = []
    warehouse_ids: List[int] = []
    
    class Config:
        from_attributes = True

# --- Branch & Warehouse Schemas ---

class BranchBase(BaseModel):
    branchname: str
    location: str
    contactnumber: Optional[str] = None
    manageremployeeid: Optional[int] = None

class BranchCreate(BranchBase):
    pass

class BranchResponse(BranchBase):
    branchid: int
    class Config:
        from_attributes = True

class WarehouseBase(BaseModel):
    warehouse_name: str
    branch_id: int
    location: Optional[str] = None
    is_active: bool = True

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseResponse(WarehouseBase):
    warehouse_id: int
    class Config:
        from_attributes = True

class DepartmentCreate(BaseModel):
    departmentname: str
    branchid: int

# --- Catalogue & Inventory Schemas ---

class CategoryCreate(BaseModel):
    categoryname: str

class ProductCreate(BaseModel):
    itemname: str
    description: Optional[str] = None
    unitprice: Decimal
    costprice: Optional[Decimal] = Decimal("0")
    reorderlevel: int = 0
    base_unit: Optional[str] = "Piece"
    categoryid: int
    is_active: Optional[bool] = True

class ProductResponse(BaseModel):
    itemid: int
    itemname: str
    description: Optional[str] = None
    unitprice: Decimal
    costprice: Optional[Decimal] = Decimal("0")
    reorderlevel: int = 0
    base_unit: Optional[str] = "Piece"
    categoryid: int
    is_active: bool = True
    category_name: Optional[str] = None
    available_stock: Optional[Decimal] = Decimal("0")
    class Config:
        from_attributes = True

class SupplierCreate(BaseModel):
    suppliername: str
    contactperson: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class SupplyLinkCreate(BaseModel):
    supplierid: int
    employeeid: Optional[int] = None
    requisition_id: Optional[int] = None
    status: POStatus = POStatus.PENDING

class RequisitionItemCreate(BaseModel):
    itemid: int
    quantity: Decimal = Field(gt=0, max_digits=15, decimal_places=3)
    estimated_unit_cost: Decimal = Field(ge=0, max_digits=15, decimal_places=2)

class PurchaseRequisitionCreate(BaseModel):
    notes: Optional[str] = None
    items: List[RequisitionItemCreate]

class ApprovalDecision(BaseModel):
    reason: Optional[str] = None

class GRNItemCreate(BaseModel):
    po_item_id: int
    quantity: Decimal = Field(gt=0, max_digits=15, decimal_places=3)

class GRNCreate(BaseModel):
    po_id: int
    items: List[GRNItemCreate]

class SupplierInvoiceCreate(BaseModel):
    invoice_number: str
    po_id: int
    grn_id: int
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)

class SupplierPaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    payment_method: Literal["cash", "bank", "mobile_money"] = "bank"

class PayrollCreate(BaseModel):
    employeeid: int
    month: str
    grosspay: Decimal
    deductions: Decimal = Decimal("0")

class SaleItemCreate(BaseModel):
    itemid: int
    quantity: Decimal = Field(gt=0, max_digits=15, decimal_places=3)

class SaleCreate(BaseModel):
    customerid: Optional[int] = None
    customername: Optional[str] = None
    customerphone: Optional[str] = None
    # Retained as optional for compatibility. The API derives these from JWT.
    employeeid: Optional[int] = None
    branchid: Optional[int] = None
    payment_method: Literal["cash", "card", "mobile_money"] = "cash"
    items: List[SaleItemCreate]

class CashierSessionOpen(BaseModel):
    opening_float: Decimal = Field(ge=0, max_digits=15, decimal_places=2)

class LedgerCreate(BaseModel):
    sourcetype: LedgerSourceType
    saleid: Optional[int] = None
    payrollid: Optional[int] = None
    amount: Decimal
    recordedby: int

class EmployeeCreate(BaseModel):
    name: str
    nin: str
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=72)
    phone: Optional[str] = None
    datehired: Optional[date] = None
    salary: Decimal
    departmentid: int
    branchid: int
    supervisorid: Optional[int] = None
    roletype: RoleType
    pos_terminalid: Optional[str] = None
    approvallimit: Optional[Decimal] = None
    certificationnumber: Optional[str] = None
    hr_role: Optional[str] = None
    managementlevel: Optional[str] = None

# --- Financial Accounting Schemas ---

class LedgerCreate(BaseModel):
    sourcetype: LedgerSourceType
    saleid: Optional[int] = None
    payrollid: Optional[int] = None
    amount: Decimal
    recordedby: int

class ChartOfAccountCreate(BaseModel):
    account_code: str
    account_name: str
    account_type: str # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE

class JournalLineCreate(BaseModel):
    account_code: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    description: Optional[str] = None

class JournalEntryCreate(BaseModel):
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    lines: List[JournalLineCreate]

# --- Approvals Schemas ---

class ApprovalDecision(BaseModel):
    request_id: int
    action: str # "APPROVE" or "REJECT"
    notes: Optional[str] = None

# --- Roles & Permissions Schemas ---

class RoleCreate(BaseModel):
    role_name: str
    description: Optional[str] = None

class PermissionCreate(BaseModel):
    code: str
    module: str
    action: str
    description: Optional[str] = None

class RoleAssignCreate(BaseModel):
    user_id: int
    role_name: str

# --- Audit & Diagnostics Schemas ---

class AuditPageView(BaseModel):
    page: str

class AuditLogResponse(BaseModel):
    auditlogid: int
    user_id: Optional[int] = None
    username_or_email: Optional[str] = None
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogPage(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int

# =============================================================================
# ADDITIONAL SCHEMAS (Tasks 5 & 6 additions)
# =============================================================================

# --- Opening Stock ---

class OpeningStockItem(BaseModel):
    item_id: int
    warehouse_id: int
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)

class OpeningStockCreate(BaseModel):
    items: List[OpeningStockItem]
    notes: Optional[str] = None

# --- Customer Management ---

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class CustomerResponse(BaseModel):
    customerid: int
    name: Optional[str] = None
    phone: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    outstanding_balance: Optional[Decimal] = None
    class Config:
        from_attributes = True

# --- Approval Request Full ---

class ApprovalRequestCreate(BaseModel):
    module: str  # PO, DISCOUNT, REFUND, ADJUSTMENT, PAYROLL
    entity_type: str
    entity_id: int
    requested_amount: Optional[Decimal] = None
    notes: Optional[str] = None

class ApprovalRequestResponse(BaseModel):
    request_id: int
    module: str
    entity_type: str
    entity_id: int
    requester_id: int
    requester_name: Optional[str] = None
    approver_id: Optional[int] = None
    approver_name: Optional[str] = None
    status: str
    requested_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    actioned_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# --- Requisition Approval ---

class RequisitionApproval(BaseModel):
    requisition_id: int
    action: str  # "APPROVE" or "REJECT"
    notes: Optional[str] = None

# --- PO Approval ---

class POApproval(BaseModel):
    po_id: int
    action: str  # "APPROVE" or "REJECT"
    notes: Optional[str] = None

# --- Sales Return (enhanced) ---

class SalesReturnItemCreate(BaseModel):
    item_id: int
    quantity: Decimal = Field(gt=0)
    condition: Optional[str] = "GOOD"  # GOOD, DAMAGED

class SalesReturnFullCreate(BaseModel):
    sale_id: int
    reason: str
    items: List[SalesReturnItemCreate]
    refund_method: Optional[str] = "CASH"  # CASH, STORE_CREDIT, ORIGINAL_METHOD

# --- Stock Transfer ---

class StockTransferItemCreate(BaseModel):
    item_id: int
    quantity: Decimal = Field(gt=0)

class StockTransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    notes: Optional[str] = None
    items: List[StockTransferItemCreate]

# --- Stock Adjustment ---

class StockAdjustmentCreate(BaseModel):
    warehouse_id: int
    item_id: int
    variance_quantity: Decimal = Field(ne=0)  # positive = stock gain, negative = shrinkage
    reason_code: str = Field(min_length=1, max_length=50)
    notes: Optional[str] = None

class StockAdjustmentApproval(BaseModel):
    adjustment_id: int
    action: str
    notes: Optional[str] = None

# --- User Role Assignment ---

class UserRoleAssign(BaseModel):
    user_id: int
    role_name: str

class UserActivateToggle(BaseModel):
    user_id: int
    is_active: bool

class UserUnlock(BaseModel):
    user_id: int

class PasswordReset(BaseModel):
    user_id: int
    new_password: Optional[str] = Field(default=None, min_length=12, max_length=72)

class InitialPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=72)

# --- Dashboard query params ---

class DashboardParams(BaseModel):
    branch_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    date_filter: Optional[str] = "today"  # today, week, month, quarter

# --- Payslip access ---

class PayslipResponse(BaseModel):
    payslip_id: int
    employee_id: int
    employee_name: Optional[str] = None
    month: Optional[str] = None
    basic_salary: Decimal
    allowances: Decimal
    overtime: Decimal
    deductions: Decimal
    gross_pay: Decimal
    net_pay: Decimal
    payment_status: str
    class Config:
        from_attributes = True

# --- Leave Request approval ---

class LeaveApproval(BaseModel):
    leave_id: int
    action: str  # "APPROVE" or "REJECT"
    notes: Optional[str] = None

# --- Supplier link (extend) ---

class SupplierProductLink(BaseModel):
    supplier_id: int
    item_id: int
    cost_price: Decimal = Field(ge=0)
    lead_time_days: Optional[int] = 7

# --- Financial Account ---

class FinancialAccountCreate(BaseModel):
    account_name: str
    account_type: str  # CASH, BANK, MOBILE_MONEY
    account_number: Optional[str] = None
    opening_balance: Optional[Decimal] = Decimal("0")

# --- Customer credit payment ---

class CustomerCreditPayment(BaseModel):
    customer_id: int
    amount: Decimal = Field(gt=0)
    payment_method: Optional[str] = "CASH"
    reference: Optional[str] = None

# =============================================================================
# MISSING SCHEMAS (added to fix startup errors)
# =============================================================================

# --- Cashier Sessions ---

class CashierSessionCreate(BaseModel):
    branch_id: int
    warehouse_id: int
    opening_float: Decimal = Field(ge=0, max_digits=15, decimal_places=2)

class CashierSessionClose(BaseModel):
    actual_cash: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    notes: Optional[str] = None

# --- Purchase Order (direct API) ---

class PurchaseOrderItemCreate(BaseModel):
    item_id: int
    quantity: Decimal = Field(gt=0, max_digits=15, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

class PurchaseOrderCreate(BaseModel):
    supplierid: int
    branchid: Optional[int] = None
    items: Optional[List[PurchaseOrderItemCreate]] = []

# --- Goods Received Note (direct API) ---

class GoodsReceivedNoteItemCreate(BaseModel):
    item_id: int
    quantity_received: Decimal = Field(gt=0, max_digits=15, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

class GoodsReceivedNoteCreate(BaseModel):
    po_id: int
    warehouse_id: int
    grn_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[GoodsReceivedNoteItemCreate]

# --- Payroll Run ---

class PayrollRunCreate(BaseModel):
    month: str  # e.g. "2026-09"
    notes: Optional[str] = None

class PayrollRunApprove(BaseModel):
    run_id: int
    notes: Optional[str] = None

# --- Customer Credit Account ---

class CustomerCreditAccountCreate(BaseModel):
    customer_id: int
    credit_limit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

# --- Attendance Record ---

class AttendanceRecordCreate(BaseModel):
    employee_id: int
    date: date
    status: str  # PRESENT, ABSENT, HALF_DAY, LATE
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    overtime_hours: Optional[Decimal] = Decimal("0")

# --- Leave Request ---

class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: str  # ANNUAL, SICK, MATERNITY, PATERNITY, UNPAID
    start_date: date
    end_date: date
    notes: Optional[str] = None
