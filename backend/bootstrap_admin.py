import os
from datetime import date

import auth
import models
from database import SessionLocal


def bootstrap_admin() -> None:
    name = os.environ["ADMIN_NAME"]
    email = os.environ["ADMIN_EMAIL"]
    password = os.environ["ADMIN_PASSWORD"]

    db = SessionLocal()
    try:
        admin = db.query(models.Employee).filter(models.Employee.email == email).first()
        if admin is None:
            admin = models.Employee(
                name=name,
                nin=f"ADMIN-{name}",
                email=email,
                hashed_password=auth.get_password_hash(password),
                datehired=date.today(),
                roletype=models.RoleType.ADMIN,
            )
            db.add(admin)
        else:
            admin.name = name
            admin.hashed_password = auth.get_password_hash(password)
            admin.roletype = models.RoleType.ADMIN

        db.commit()
        print(f"Administrator ready: {name}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin()
