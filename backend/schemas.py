from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from models import RoleType, POStatus, LedgerSourceType

class Token(BaseModel):
    access_token: str
    token_type: str

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
    employeeid: int
    status: POStatus = POStatus.PENDING

class PayrollCreate(BaseModel):
    employeeid: int
    month: str
    grosspay: Decimal
    deductions: Decimal = Decimal("0")

class SaleItemCreate(BaseModel):
    itemid: int
    quantity: int

class SaleCreate(BaseModel):
    customerid: Optional[int] = None
    customername: Optional[str] = None
    customerphone: Optional[str] = None
    employeeid: int
    branchid: int
    items: List[SaleItemCreate]

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
