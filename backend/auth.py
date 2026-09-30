import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Set
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_for_hardware_world_123!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12 # 12 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Fallback permission mapping for default roles if not yet in database
DEFAULT_ROLE_PERMS = {
    "Admin": ["*"],
    "System Administrator": ["*"],
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
    "HR Staff": [
        "hr:view", "hr:manage", "hr:attendance", "hr:leave", "payroll:view", "payroll:prepare"
    ],
    "HR Officer": [
        "hr:view", "hr:manage", "hr:attendance", "hr:leave", "payroll:view", "payroll:prepare"
    ],
    "HR Manager": [
        "hr:view", "hr:manage", "hr:attendance", "hr:leave", "payroll:view",
        "payroll:prepare", "payroll:approve"
    ],
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not plain_password:
        return False
    try:
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.Employee).filter(models.Employee.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

def get_user_roles(db: Session, employee: models.Employee) -> List[str]:
    """Retrieve full roles for user from user_roles and primary roletype."""
    assigned_roles = db.query(models.Role.role_name).join(
        models.UserRole, models.UserRole.role_id == models.Role.role_id
    ).filter(models.UserRole.user_id == employee.employeeid).all()
    roles = [r[0] for r in assigned_roles]
    if employee.roletype.value not in roles:
        roles.append(employee.roletype.value)
    return roles

def get_user_permissions(db: Session, employee: models.Employee) -> List[str]:
    """Retrieve permissions for an employee based on user roles and primary roletype."""
    if employee.roletype == models.RoleType.ADMIN:
        return ["*"]

    perm_codes: Set[str] = set()

    # 1. Fetch from database role_permissions
    db_perms = db.query(models.Permission.code).join(
        models.RolePermission, models.RolePermission.permission_id == models.Permission.permission_id
    ).join(
        models.UserRole, models.UserRole.role_id == models.RolePermission.role_id
    ).filter(models.UserRole.user_id == employee.employeeid).all()
    for p in db_perms:
        perm_codes.add(p[0])

    # 2. Add fallback permissions based on roles
    for role_name in get_user_roles(db, employee):
        for perm in DEFAULT_ROLE_PERMS.get(role_name, []):
            perm_codes.add(perm)

    return list(perm_codes)

def has_permission(db: Session, employee: models.Employee, required_perm: str) -> bool:
    """Check if an employee possesses a required permission code."""
    if employee.roletype == models.RoleType.ADMIN:
        return True
    perms = get_user_permissions(db, employee)
    return "*" in perms or required_perm in perms
