import os
from datetime import date

import auth
import models
from database import SessionLocal
from sqlalchemy.orm import Session


def ensure_configured_admin(db: Session) -> models.Employee:
    name = os.environ["ADMIN_NAME"].strip()
    email = os.environ["ADMIN_EMAIL"].strip()
    password = os.environ["ADMIN_PASSWORD"]
    if not name or not email:
        raise RuntimeError("ADMIN_NAME and ADMIN_EMAIL must be configured.")
    if len(password) < 12 or password.lower().startswith(("replace-with", "change-me")):
        raise RuntimeError("ADMIN_PASSWORD must be configured with at least 12 non-placeholder characters.")

    admin = db.query(models.Employee).filter(models.Employee.email == email).first()
    if admin is None:
        admin = models.Employee(
            name=name,
            nin=f"ADMIN-{name}"[:20],
            email=email,
            hashed_password=auth.get_password_hash(password),
            datehired=date.today(),
            roletype=models.RoleType.ADMIN,
        )
        db.add(admin)
    else:
        changed = False
        if admin.name != name:
            admin.name = name
            changed = True
        if not auth.verify_password(password, admin.hashed_password or ""):
            admin.hashed_password = auth.get_password_hash(password)
            changed = True
        if admin.roletype != models.RoleType.ADMIN:
            admin.roletype = models.RoleType.ADMIN
            changed = True
        if changed:
            admin.token_version = (admin.token_version or 0) + 1
    db.flush()
    return admin


def bootstrap_admin() -> None:
    db = SessionLocal()
    try:
        admin = ensure_configured_admin(db)
        db.commit()
        print(f"Administrator ready: {admin.name}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin()
