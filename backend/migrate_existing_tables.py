"""
Migrate existing MySQL tables to match the current SQLAlchemy models.
Adds missing columns to tables that already exist (non-destructive).
Run this once after the initial create_all when the DB was previously populated.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import pymysql

ROOT_PW = sys.argv[1] if len(sys.argv) > 1 else "backendiskey@28777"
DB = "hardware_world"

def connect_as_root():
    return pymysql.connect(host="127.0.0.1", port=3306, user="root",
                           password=ROOT_PW, database=DB, autocommit=True)

def get_existing_columns(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row[0].lower() for row in cursor.fetchall()}

def alter_add(cursor, table, col, definition):
    existing = get_existing_columns(cursor, table)
    if col.lower() not in existing:
        sql = f"ALTER TABLE `{table}` ADD COLUMN `{col}` {definition}"
        print(f"  ADD  {table}.{col}")
        cursor.execute(sql)
    else:
        print(f"  OK   {table}.{col}  (already exists)")

def table_exists(cursor, table):
    cursor.execute("SHOW TABLES LIKE %s", (table,))
    return cursor.fetchone() is not None

print("\n=== Hardware World — MySQL Schema Migration ===\n")

conn = connect_as_root()
cur = conn.cursor()

# ── employee ─────────────────────────────────────────────────────
if table_exists(cur, "employee"):
    print("[employee]")
    alter_add(cur, "employee", "is_active",     "TINYINT(1) NOT NULL DEFAULT 1")
    alter_add(cur, "employee", "hashed_password","VARCHAR(255) NULL")

# ── sale ─────────────────────────────────────────────────────────
if table_exists(cur, "sale"):
    print("[sale]")
    alter_add(cur, "sale", "status",          "VARCHAR(50) NOT NULL DEFAULT 'COMPLETED'")
    alter_add(cur, "sale", "paymentmethod",   "VARCHAR(50) DEFAULT 'CASH'")
    alter_add(cur, "sale", "subtotal",        "DECIMAL(12,2) DEFAULT 0")
    alter_add(cur, "sale", "discountamount",  "DECIMAL(12,2) DEFAULT 0")
    alter_add(cur, "sale", "taxamount",       "DECIMAL(12,2) DEFAULT 0")
    alter_add(cur, "sale", "idempotency_key", "VARCHAR(100) NULL")
    alter_add(cur, "sale", "warehouseid",     "INT NULL")
    alter_add(cur, "sale", "cashiersessionid","INT NULL")

# ── sale_item ─────────────────────────────────────────────────────
if table_exists(cur, "sale_item"):
    print("[sale_item]")
    alter_add(cur, "sale_item", "unitcost",  "DECIMAL(10,2) DEFAULT 0")
    alter_add(cur, "sale_item", "discount",  "DECIMAL(10,2) DEFAULT 0")
    alter_add(cur, "sale_item", "line_total","DECIMAL(12,2) NULL")

# ── product ──────────────────────────────────────────────────────
if table_exists(cur, "product"):
    print("[product]")
    alter_add(cur, "product", "costprice",  "DECIMAL(10,2) DEFAULT 0")
    alter_add(cur, "product", "base_unit",  "VARCHAR(20) DEFAULT 'Piece'")
    alter_add(cur, "product", "is_active",  "TINYINT(1) NOT NULL DEFAULT 1")

# ── purchase_order ────────────────────────────────────────────────
if table_exists(cur, "purchase_order"):
    print("[purchase_order]")
    alter_add(cur, "purchase_order", "total_amount", "DECIMAL(12,2) DEFAULT 0")
    alter_add(cur, "purchase_order", "approved_by",  "INT NULL")
    alter_add(cur, "purchase_order", "approved_at",  "DATETIME NULL")
    alter_add(cur, "purchase_order", "branchid",     "INT NULL")

# ── branch ────────────────────────────────────────────────────────
if table_exists(cur, "branch"):
    print("[branch]")
    alter_add(cur, "branch", "manageremployeeid", "INT NULL")

# ── supplier ─────────────────────────────────────────────────────
if table_exists(cur, "supplier"):
    print("[supplier]")
    # no new cols needed for supplier

# ── payroll ──────────────────────────────────────────────────────
if table_exists(cur, "payroll"):
    print("[payroll]")
    alter_add(cur, "payroll", "deductions", "DECIMAL(10,2) DEFAULT 0")

cur.close()
conn.close()

# ── Now run create_all for NEW tables ────────────────────────────
print("\n[Creating new tables via SQLAlchemy create_all...]")
from database import Base, engine
import models  # registers all models
Base.metadata.create_all(bind=engine)
print("  ✓ All new tables created\n")

# ── Unique index on sale.idempotency_key (if not exists) ─────────
conn2 = connect_as_root()
cur2 = conn2.cursor()
try:
    cur2.execute("SHOW INDEX FROM `sale` WHERE Key_name = 'ix_sale_idempotency_key'")
    if not cur2.fetchone():
        cur2.execute("ALTER TABLE `sale` ADD UNIQUE INDEX `ix_sale_idempotency_key` (`idempotency_key`)")
        print("  ADD  sale.idempotency_key unique index")
    else:
        print("  OK   sale.idempotency_key unique index")
except Exception as e:
    print(f"  NOTE sale idempotency index: {e}")
cur2.close()
conn2.close()

print("\n=== Migration complete. Running seed... ===\n")

from database import SessionLocal
from seed import seed_baseline
db = SessionLocal()
try:
    seed_baseline(db)
    print("✓ Seed complete")
except Exception as e:
    print(f"✗ Seed error: {e}")
    import traceback; traceback.print_exc()
finally:
    db.close()
