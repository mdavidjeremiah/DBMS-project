import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Set
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

SECRET_KEY = os.getenv("SECRET_KEY", "")
if len(SECRET_KEY.encode("utf-8")) < 32 or SECRET_KEY.lower().startswith(("replace-with", "change-me")):
    raise RuntimeError("SECRET_KEY must be configured with at least 32 characters.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12 # 12 hours
ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
)
COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE",
    "false" if os.getenv("APP_ENV", "development").lower() in {"development", "test"} else "true",
).lower() == "true"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Fallback permission mapping for default roles if not yet in database
DEFAULT_ROLE_PERMS = {
    "Admin": ["admin:users", "admin:audit"],
    "System Administrator": ["admin:users", "admin:audit"],
    "Owner / Executive": [
        "reports:view", "sales:view", "inventory:view", "finance:view",
        "procurement:view", "hr:view", "approvals:approve",
    ],
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
        "procurement:po_approve", "procurement:supplier", "procurement:grn"
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
    if not hashed_password or not plain_password or len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Passwords must not exceed 72 UTF-8 bytes.")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(18)


def temporary_password_expiry(now: Optional[datetime] = None) -> datetime:
    try:
        hours = int(os.getenv("TEMP_PASSWORD_EXPIRY_HOURS", "24"))
    except ValueError as error:
        raise RuntimeError("TEMP_PASSWORD_EXPIRY_HOURS must be a whole number.") from error
    if not 1 <= hours <= 168:
        raise RuntimeError("TEMP_PASSWORD_EXPIRY_HOURS must be between 1 and 168.")
    return (now or datetime.utcnow()) + timedelta(hours=hours)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    cookie_token = request.cookies.get("hw_access_token")
    if not token and cookie_token:
        token = cookie_token
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin not in ALLOWED_ORIGINS:
            raise HTTPException(status_code=403, detail="Untrusted request origin.")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") == "initial-password-change":
            raise credentials_exception
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.Employee).filter(models.Employee.email == token_data.email).first()
    if (
        user is None
        or not user.is_active
        or user.must_change_password
        or payload.get("tv", 0) != (user.token_version or 0)
    ):
        raise credentials_exception
    return user


def get_initial_password_change_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """Resolve the short-lived token used only by the initial password-change endpoint."""
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Untrusted request origin.")
    token = request.cookies.get("hw_access_token")
    if not token:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as error:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from error
    if payload.get("purpose") != "initial-password-change" or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user = db.query(models.Employee).filter(models.Employee.email == payload["sub"]).first()
    if (
        user is None
        or not user.is_active
        or not user.must_change_password
        or payload.get("tv", 0) != (user.token_version or 0)
        or (
            user.temporary_password_expires_at is not None
            and user.temporary_password_expires_at <= datetime.utcnow()
        )
    ):
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return user

def get_user_roles(db: Session, employee: models.Employee) -> List[str]:
    """Retrieve full roles for user from user_roles and primary roletype."""
    assigned_roles = db.query(models.Role.role_name).join(
        models.UserRole, models.UserRole.role_id == models.Role.role_id
    ).filter(models.UserRole.user_id == employee.employeeid).all()
    roles = [r[0] for r in assigned_roles]
    roles.extend(role.name for role in employee.erp_roles if role.name not in roles)
    if employee.roletype.value not in roles:
        roles.append(employee.roletype.value)
    return roles


def has_any_role(employee: models.Employee, *roles: models.RoleType) -> bool:
    """Check a primary or explicitly assigned operational role without Admin bypass."""
    if employee.roletype != models.RoleType.ADMIN and employee.roletype in roles:
        return True
    if employee.roletype == models.RoleType.ADMIN and roles == (models.RoleType.ADMIN,):
        return True
    assigned_names = {role.name for role in employee.erp_roles}
    assigned_names.update(
        assignment.role.role_name
        for assignment in employee.user_roles
        if assignment.role is not None
    )
    role_aliases = {
        models.RoleType.ADMIN: {"System Administrator"},
        models.RoleType.CASHIER: {"Cashier", "Sales Manager", "Sales Clerk"},
        models.RoleType.PROCUREMENT_OFFICER: {"Procurement Officer", "Procurement Manager", "Storekeeper", "Warehouse Supervisor", "Inventory Manager"},
        models.RoleType.ACCOUNTANT: {"Accountant", "Finance Clerk", "Finance Manager"},
        models.RoleType.HR_STAFF: {"HR Staff", "HR Officer", "HR Manager"},
        models.RoleType.BRANCH_MANAGER: {"Branch Manager", "General Manager", "Owner / Executive"},
    }
    permitted_names = set().union(*(role_aliases.get(role, set()) for role in roles if role != models.RoleType.ADMIN))
    return bool(assigned_names & permitted_names)


def get_user_permissions(db: Session, employee: models.Employee) -> List[str]:
    """Retrieve permissions for an employee based on user roles and primary roletype."""
    perm_codes: Set[str] = (
        {"admin:users", "admin:audit"}
        if employee.roletype == models.RoleType.ADMIN
        else set()
    )
    permission_aliases = {
        "sales:read": "sales:view",
        "inventory:read": "inventory:view",
        "procurement:read": "procurement:view",
        "finance:read": "finance:view",
        "hr:read": "hr:view",
        "reports:read": "reports:view",
    }

    # 1. Fetch from database role_permissions
    db_perms = db.query(models.Permission.code).join(
        models.RolePermission, models.RolePermission.permission_id == models.Permission.permission_id
    ).join(
        models.UserRole, models.UserRole.role_id == models.RolePermission.role_id
    ).filter(models.UserRole.user_id == employee.employeeid)
    if employee.roletype == models.RoleType.ADMIN:
        db_perms = db_perms.join(models.Role, models.Role.role_id == models.UserRole.role_id).filter(
            models.Role.role_name.notin_(("Admin", "System Administrator"))
        )
    db_perms = db_perms.all()
    for p in db_perms:
        if employee.roletype != models.RoleType.ADMIN or p[0] != "*":
            perm_codes.add(permission_aliases.get(p[0], p[0]))

    for role in employee.erp_roles:
        if employee.roletype == models.RoleType.ADMIN and role.name == "System Administrator":
            continue
        for permission in role.permissions:
            if permission.code != "*":
                perm_codes.add(permission_aliases.get(permission.code, permission.code))

    # 2. Add fallback permissions based on roles
    for role_name in get_user_roles(db, employee):
        for perm in DEFAULT_ROLE_PERMS.get(role_name, []):
            perm_codes.add(perm)

    return list(perm_codes)

def has_permission(db: Session, employee: models.Employee, required_perm: str) -> bool:
    """Check if an employee possesses a required permission code."""
    perms = get_user_permissions(db, employee)
    return "*" in perms or required_perm in perms
