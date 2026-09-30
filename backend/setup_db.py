"""
Hardware World ERP — Database Setup Script
Creates the MySQL database and user, creates all tables, and runs the seed.

Usage: python setup_db.py [--root-password ROOT_PW]
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def banner(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def run_mysql_admin(root_password, sql_statements):
    """Execute SQL using PyMySQL with root credentials."""
    import pymysql
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password=root_password,
    )
    cursor = conn.cursor()
    for stmt in sql_statements:
        stmt = stmt.strip()
        if stmt:
            print(f"  SQL: {stmt[:80]}{'...' if len(stmt) > 80 else ''}")
            cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Setup Hardware World ERP database")
    parser.add_argument("--root-password", default="", help="MySQL root password (default: empty)")
    args = parser.parse_args()
    root_pw = args.root_password

    banner("STEP 1: Create database and user")
    try:
        run_mysql_admin(root_pw, [
            "CREATE DATABASE IF NOT EXISTS hardware_world CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
            "CREATE USER IF NOT EXISTS 'hw_user'@'%' IDENTIFIED BY 'hw_password'",
            "CREATE USER IF NOT EXISTS 'hw_user'@'localhost' IDENTIFIED BY 'hw_password'",
            "CREATE USER IF NOT EXISTS 'hw_user'@'127.0.0.1' IDENTIFIED BY 'hw_password'",
            "GRANT ALL PRIVILEGES ON hardware_world.* TO 'hw_user'@'%'",
            "GRANT ALL PRIVILEGES ON hardware_world.* TO 'hw_user'@'localhost'",
            "GRANT ALL PRIVILEGES ON hardware_world.* TO 'hw_user'@'127.0.0.1'",
            "FLUSH PRIVILEGES",
        ])
        print("  ✓ Database and user created/updated")
    except Exception as e:
        print(f"  ✗ MySQL admin step failed: {e}")
        print("\nTroubleshooting:")
        print("  Run: python setup_db.py --root-password YOUR_MYSQL_ROOT_PASSWORD")
        print("  Or manually create the DB and user, then run: python seed.py")
        sys.exit(1)

    banner("STEP 2: Create all tables")
    from dotenv import load_dotenv
    load_dotenv()
    from database import Base, engine
    import models  # noqa: ensures all models are registered
    try:
        Base.metadata.create_all(bind=engine)
        print("  ✓ All tables created successfully")
    except Exception as e:
        print(f"  ✗ Table creation failed: {e}")
        sys.exit(1)

    banner("STEP 3: Seed baseline data")
    from database import SessionLocal
    from seed import seed_baseline
    db = SessionLocal()
    try:
        seed_baseline(db)
        print("  ✓ Baseline data seeded successfully")
    except Exception as e:
        print(f"  ✗ Seed failed: {e}")
        import traceback; traceback.print_exc()
        db.close()
        sys.exit(1)
    finally:
        db.close()

    banner("SETUP COMPLETE")
    print("""
  The database is ready. Start the server with:

    .hardware_venv\\Scripts\\uvicorn.exe main:app --host 127.0.0.1 --port 8000

  Then visit: http://127.0.0.1:8000

  Default credentials (change after first login):
    Admin:         akena@hardwareworld.com  /  Hardware@2026!
    Cashier:       sarah.nakato@hardwareworld.com  /  Hardware@2026!
    Procurement:   john.kato@hardwareworld.com  /  Hardware@2026!
    Accountant:    grace.apio@hardwareworld.com  /  Hardware@2026!
    HR:            moses.opolot@hardwareworld.com  /  Hardware@2026!
    Branch Mgr:    brian.mukasa@hardwareworld.com  /  Hardware@2026!
""")

if __name__ == "__main__":
    main()
