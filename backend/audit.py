"""Small, isolated helpers for writing audit events outside request transactions."""

import os
from typing import Optional

from sqlalchemy.orm import Session

from database import SessionLocal
import models


def request_ip(request) -> Optional[str]:
    """Prefer the original client IP when the app is running behind a trusted proxy."""
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    trusted = {x.strip() for x in os.getenv("TRUSTED_PROXIES", "").split(",") if x.strip()}
    if forwarded_for and request.client and request.client.host in trusted:
        return forwarded_for.split(",", 1)[0].strip()[:45]
    return request.client.host[:45] if request.client else None


def write_audit_log(
    *,
    user_id: Optional[int] = None,
    username_or_email: Optional[str] = None,
    action: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Persist an event using a short-lived session so application work is not affected."""
    db: Session = SessionLocal()
    try:
        if user_id is None and username_or_email:
            employee = db.query(models.Employee).filter(models.Employee.email == username_or_email).first()
            user_id = employee.employeeid if employee else None

        db.add(models.AuditLog(
            user_id=user_id,
            username_or_email=(username_or_email or "")[:100] or None,
            action=action[:64],
            details=(details or "")[:2000] or None,
            ip_address=(ip_address or "")[:45] or None,
        ))
        db.commit()
    except Exception:
        # Audit failures must never interrupt the main user workflow.
        db.rollback()
    finally:
        db.close()
