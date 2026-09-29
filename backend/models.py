from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, Enum, DateTime, Numeric, Text
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
    status = Column(Enum(POStatus), default=POStatus.PENDING)

class Sale(Base):
    __tablename__ = "sale"
    saleid = Column(Integer, primary_key=True, index=True)
    saledate = Column(DateTime, default=datetime.utcnow)
    totalamount = Column(Numeric(12, 2))
    customerid = Column(Integer, ForeignKey("customer.customerid"), nullable=True)
    employeeid = Column(Integer, ForeignKey("employee.employeeid"))
    branchid = Column(Integer, ForeignKey("branch.branchid"))
    customer = relationship("Customer", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale")

class SaleItem(Base):
    __tablename__ = "sale_item"
    saleid = Column(Integer, ForeignKey("sale.saleid"), primary_key=True)
    itemid = Column(Integer, ForeignKey("product.itemid"), primary_key=True)
    quantity = Column(Integer, nullable=False)
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


class AuditLog(Base):
    __tablename__ = "audit_log"

    auditlogid = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("employee.employeeid", ondelete="SET NULL"), nullable=True, index=True)
    username_or_email = Column(String(100), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("Employee", foreign_keys=[user_id])
