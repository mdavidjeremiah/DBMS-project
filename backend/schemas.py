from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import date, datetime
from decimal import Decimal
from models import RoleType, POStatus, LedgerSourceType

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
    password: str
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
    email: Optional[EmailStr] = None
    roletype: RoleType
    departmentid: Optional[int] = None
    department_name: Optional[str] = None
    branchid: Optional[int] = None
    branch_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# Add more schemas as needed for other models
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

class CategoryCreate(BaseModel):
    categoryname: str

class ProductCreate(BaseModel):
    itemname: str
    description: Optional[str] = None
    unitprice: Decimal
    reorderlevel: int = 0
    categoryid: int

class SupplierCreate(BaseModel):
    suppliername: str
    contactperson: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class PurchaseOrderCreate(BaseModel):
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
    password: Optional[str] = None
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
