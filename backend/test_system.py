"""
Hardware World ERP — Full System Test Suite
Tests: DB connection, seed, POS pipeline, security checks, idempotency
"""
import os
import sys
import json
import time
from decimal import Decimal
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, Base, engine
import models
import auth
import erp_service
import schemas

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
WARN = "\033[93m[WARN]\033[0m"

results = {"pass": 0, "fail": 0, "errors": []}

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
        results["pass"] += 1
    else:
        print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        results["fail"] += 1
        results["errors"].append(name)

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ─── 1. Database & Schema ──────────────────────────────────────────
section("1. DATABASE CONNECTION & SCHEMA CREATION")
try:
    Base.metadata.create_all(bind=engine)
    check("Create all tables from models", True)
except Exception as e:
    check("Create all tables from models", False, str(e))
    print(f"\n{FAIL} Cannot continue without database. Exiting.")
    sys.exit(1)

db = SessionLocal()

# ─── 2. Seed Data ─────────────────────────────────────────────────
section("2. SEED BASELINE DATA")
try:
    from seed import seed_baseline
    seed_baseline(db)
    check("seed_baseline() completed without error", True)
except Exception as e:
    check("seed_baseline() completed without error", False, str(e))

akena = db.query(models.Employee).filter(models.Employee.email == "akena@hardwareworld.com").first()
sarah = db.query(models.Employee).filter(models.Employee.email == "sarah.nakato@hardwareworld.com").first()
john  = db.query(models.Employee).filter(models.Employee.email == "john.kato@hardwareworld.com").first()
grace = db.query(models.Employee).filter(models.Employee.email == "grace.apio@hardwareworld.com").first()
moses = db.query(models.Employee).filter(models.Employee.email == "moses.opolot@hardwareworld.com").first()
brian = db.query(models.Employee).filter(models.Employee.email == "brian.mukasa@hardwareworld.com").first()

check("Admin Akena exists",  akena  is not None)
check("Cashier Sarah exists", sarah  is not None)
check("Procurement John exists", john is not None)
check("Accountant Grace exists", grace is not None)
check("HR Moses exists", moses is not None)
check("Branch Manager Brian exists", brian is not None)

branches = db.query(models.Branch).all()
check("2 branches seeded", len(branches) >= 2, f"found {len(branches)}")

warehouses = db.query(models.Warehouse).all()
check("Warehouses seeded", len(warehouses) >= 1, f"found {len(warehouses)}")

products = db.query(models.Product).all()
check("Products seeded (>=1)", len(products) >= 1, f"found {len(products)}")

categories = db.query(models.Category).all()
check("Categories seeded", len(categories) >= 1, f"found {len(categories)}")

roles = db.query(models.Role).all()
check("17 roles seeded", len(roles) >= 17, f"found {len(roles)}")

perms = db.query(models.Permission).all()
check("Permissions seeded", len(perms) >= 20, f"found {len(perms)}")

coa = db.query(models.ChartOfAccount).all()
check("Chart of Accounts seeded", len(coa) >= 5, f"found {len(coa)}")

fin_accts = db.query(models.FinancialAccount).all()
check("Financial accounts seeded", len(fin_accts) >= 1, f"found {len(fin_accts)}")

# ─── 3. RBAC & Permission System ─────────────────────────────────
section("3. RBAC & PERMISSION SYSTEM")

if sarah:
    sarah_perms = auth.get_user_permissions(db, sarah)
    check("Cashier has sales:pos", "sales:pos" in sarah_perms, f"perms: {sarah_perms[:5]}")
    check("Cashier has sales:view", "sales:view" in sarah_perms)
    check("Cashier does NOT have payroll:view", "payroll:view" not in sarah_perms or sarah_perms == ["*"])
    check("Cashier does NOT have finance:post", "finance:post" not in sarah_perms or sarah_perms == ["*"])

if grace:
    grace_perms = auth.get_user_permissions(db, grace)
    check("Accountant has finance:view", "finance:view" in grace_perms or grace_perms == ["*"])
    check("Accountant has payroll:view", "payroll:view" in grace_perms or grace_perms == ["*"])

if akena:
    akena_perms = auth.get_user_permissions(db, akena)
    check("Admin has wildcard '*'", "*" in akena_perms)

# ─── 4. Security: is_active check ────────────────────────────────
section("4. ACCOUNT SECURITY CHECKS")

if sarah:
    check("Sarah is_active=True", sarah.is_active == True)

# Password hashing
if sarah:
    check("Sarah password hashes correctly",
          auth.verify_password(os.environ.get("SEED_DEFAULT_PASSWORD", ""), sarah.hashed_password))
    check("Wrong password rejected",
          not auth.verify_password("wrongpassword", sarah.hashed_password))

# ─── 5. POS Sale Pipeline (Acceptance Test 1) ────────────────────
section("5. POS SALE PIPELINE — ACCEPTANCE TEST 1")

product = db.query(models.Product).filter(models.Product.is_active == True).first()
warehouse = db.query(models.Warehouse).first()

if product and warehouse and sarah:
    # Ensure stock balance exists
    bal = db.query(models.InventoryBalance).filter(
        models.InventoryBalance.item_id == product.itemid,
        models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
    ).first()
    if not bal:
        bal = models.InventoryBalance(
            item_id=product.itemid,
            warehouse_id=warehouse.warehouse_id,
            available_stock=Decimal("50"),
            reserved_stock=Decimal("0"),
        )
        db.add(bal)
        db.commit()
        db.refresh(bal)

    stock_before = float(bal.available_stock)
    journals_before = db.query(models.JournalEntry).count()
    movements_before = db.query(models.InventoryMovement).count()
    audit_before = db.query(models.AuditLog).count()

    print(f"\n  {INFO} Product: {product.itemname} (ID={product.itemid})")
    print(f"  {INFO} Stock before sale: {stock_before}")
    print(f"  {INFO} Unit price: {product.unitprice}, Cost: {product.costprice}")

    ikey = f"TEST-SALE-{int(time.time())}"
    payload = schemas.SaleCreate(
        employeeid=sarah.employeeid,
        branchid=sarah.branchid or 1,
        warehouseid=warehouse.warehouse_id,
        payment_method="CASH",
        idempotency_key=ikey,
        items=[schemas.SaleItemCreate(itemid=product.itemid, quantity=Decimal("2"))],
    )

    try:
        result = erp_service.process_pos_sale(payload=payload, current_user=sarah, db=db, ip_address="127.0.0.1")
        print(f"  {INFO} Sale result: {result}")

        db.expire_all()
        bal_after = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
        ).first()

        check("Sale created successfully", result.get("saleid") is not None)
        check("Sale total > 0", result.get("totalamount", 0) > 0)
        check("Stock decreased by 2",
              abs(float(bal_after.available_stock) - (stock_before - 2)) < 0.001,
              f"before={stock_before}, after={float(bal_after.available_stock)}")

        # Check SALE_OUT movement
        movement = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.reference_id == result["saleid"],
            models.InventoryMovement.movement_type == "SALE_OUT",
        ).first()
        check("SALE_OUT inventory movement created", movement is not None)
        check("Movement quantity = -2", movement is not None and abs(float(movement.quantity) - (-2)) < 0.001,
              f"qty={float(movement.quantity) if movement else 'N/A'}")

        # Check payment record
        payment = db.query(models.Payment).filter(models.Payment.sale_id == result["saleid"]).first()
        check("Payment record created", payment is not None)
        check("Payment method = CASH", payment is not None and payment.payment_method == "CASH")

        # Check double-entry journals
        new_journals = db.query(models.JournalEntry).count() - journals_before
        check("Journal entry created", new_journals >= 1, f"new journals: {new_journals}")

        jrn = db.query(models.JournalEntry).filter(
            models.JournalEntry.reference_type == "SALE",
            models.JournalEntry.reference_id == result["saleid"],
        ).first()
        check("Journal linked to sale", jrn is not None)
        if jrn:
            lines = jrn.lines
            debit_accounts = [l.account_code for l in lines if float(l.debit) > 0]
            credit_accounts = [l.account_code for l in lines if float(l.credit) > 0]
            check("Cash on Hand debited (1010)", "1010" in debit_accounts, f"debits: {debit_accounts}")
            check("Sales Revenue credited (4010)", "4010" in credit_accounts, f"credits: {credit_accounts}")
            check("COGS debited (5010)", "5010" in debit_accounts or product.costprice == 0, f"debits: {debit_accounts}")
            check("Inventory Asset credited (1050)", "1050" in credit_accounts or product.costprice == 0, f"credits: {credit_accounts}")

        # Check audit log
        new_audit = db.query(models.AuditLog).count() - audit_before
        check("Audit log entry created", new_audit >= 1)
        audit = db.query(models.AuditLog).filter(
            models.AuditLog.action == "POS_SALE_COMPLETED",
            models.AuditLog.entity_id == result["saleid"],
        ).first()
        check("Audit action = POS_SALE_COMPLETED", audit is not None)

    except Exception as e:
        check("process_pos_sale() completed", False, str(e))
        print(f"  {FAIL} Exception: {e}")
        import traceback; traceback.print_exc()
else:
    print(f"  {WARN} Skipping POS test — missing product/warehouse/sarah")

# ─── 6. Security Tests ────────────────────────────────────────────
section("6. SECURITY & VALIDATION TESTS")

# 6a. Negative quantity rejection
if product and sarah and warehouse:
    try:
        bad_payload = schemas.SaleCreate(
            employeeid=sarah.employeeid,
            branchid=sarah.branchid or 1,
            warehouseid=warehouse.warehouse_id,
            payment_method="CASH",
            items=[schemas.SaleItemCreate(itemid=product.itemid, quantity=Decimal("-2"))],
        )
        erp_service.process_pos_sale(payload=bad_payload, current_user=sarah, db=db, ip_address="127.0.0.1")
        check("Negative quantity rejected", False, "Should have raised HTTPException")
    except Exception as e:
        check("Negative quantity rejected (HTTPException)", "greater than zero" in str(e).lower() or "validation" in str(e).lower() or "quantity" in str(e).lower(),
              f"Got: {str(e)[:100]}")

# 6b. Pydantic schema validation rejects negative at schema level
try:
    bad = schemas.SaleItemCreate(itemid=1, quantity=Decimal("-1"))
    check("Pydantic schema blocks negative qty", False, "Should have raised ValidationError")
except Exception as e:
    check("Pydantic schema blocks negative qty", "greater than 0" in str(e).lower() or "gt" in str(e).lower() or "quantity" in str(e).lower(),
          f"Got: {type(e).__name__}")

# 6c. Payroll privacy — cashier has no payroll:view
if sarah:
    has_payroll = auth.has_permission(db, sarah, "payroll:view")
    check("Cashier blocked from payroll:view", not has_payroll, f"has_permission={has_payroll}")

# 6d. Finance access blocked for cashier
if sarah:
    has_finance = auth.has_permission(db, sarah, "finance:post")
    check("Cashier blocked from finance:post", not has_finance, f"has_permission={has_finance}")

# 6e. Separation of duties: cashier cannot approve own requests
# (Tested via erp_service logic — create a requisition by john, try to approve by john)
if john and brian:
    try:
        req = models.PurchaseRequisition(
            requester_id=john.employeeid,
            branch_id=john.branchid or 1,
            status="PENDING",
            notes="Test requisition",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        try:
            erp_service.approve_or_reject_requisition(
                requisition_id=req.requisition_id,
                action="APPROVE",
                approver=john,  # same person — should be rejected
                notes="Self-approval attempt",
                db=db,
            )
            check("Self-approval of requisition blocked", False, "Should have raised HTTPException")
        except Exception as e:
            check("Self-approval blocked (separation of duties)",
                  "separation" in str(e).lower() or "cannot approve" in str(e).lower() or "403" in str(e),
                  f"Got: {str(e)[:100]}")

        # Brian (branch manager) CAN approve
        erp_service.approve_or_reject_requisition(
            requisition_id=req.requisition_id,
            action="APPROVE",
            approver=brian,
            notes="Approved by manager",
            db=db,
        )
        db.expire_all()
        approved_req = db.get(models.PurchaseRequisition, req.requisition_id)
        check("Branch manager can approve requisition", approved_req.status == "APPROVED",
              f"status={approved_req.status}")
    except Exception as e:
        check("Requisition approval flow", False, str(e))

# 6f. Idempotency — duplicate sale with same key should return same result
section("7. IDEMPOTENCY TEST")
if product and sarah and warehouse:
    ikey2 = f"TEST-IDEMPOTENT-{int(time.time())}"
    payload2 = schemas.SaleCreate(
        employeeid=sarah.employeeid,
        branchid=sarah.branchid or 1,
        warehouseid=warehouse.warehouse_id,
        payment_method="CASH",
        idempotency_key=ikey2,
        items=[schemas.SaleItemCreate(itemid=product.itemid, quantity=Decimal("1"))],
    )

    bal_before = float(db.query(models.InventoryBalance).filter(
        models.InventoryBalance.item_id == product.itemid,
        models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
    ).first().available_stock)

    try:
        result1 = erp_service.process_pos_sale(payload=payload2, current_user=sarah, db=db, ip_address="127.0.0.1")
        result2 = erp_service.process_pos_sale(payload=payload2, current_user=sarah, db=db, ip_address="127.0.0.1")

        check("Idempotent retry returns same sale ID", result1["saleid"] == result2["saleid"],
              f"r1={result1['saleid']}, r2={result2['saleid']}")
        check("Idempotent replay flagged", result2.get("idempotent_replay") == True,
              f"idempotent_replay={result2.get('idempotent_replay')}")

        db.expire_all()
        bal_after2 = float(db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
        ).first().available_stock)

        check("Stock only deducted once (not twice)", abs(bal_before - bal_after2 - 1) < 0.001,
              f"before={bal_before}, after={bal_after2}")
    except Exception as e:
        check("Idempotency test", False, str(e))

# ─── 8. Data Flow Verification ────────────────────────────────────
section("8. DATA FLOW PIPELINE VERIFICATION")

sale_count = db.query(models.Sale).count()
movement_count = db.query(models.InventoryMovement).count()
journal_count = db.query(models.JournalEntry).count()
audit_count = db.query(models.AuditLog).count()
payment_count = db.query(models.Payment).count()

print(f"  {INFO} Sales:              {sale_count}")
print(f"  {INFO} Inventory Movements: {movement_count}")
print(f"  {INFO} Journal Entries:     {journal_count}")
print(f"  {INFO} Payments:            {payment_count}")
print(f"  {INFO} Audit Logs:          {audit_count}")

check("Sales exist in DB", sale_count >= 1)
check("Inventory movements exist", movement_count >= 1)
check("Journal entries exist", journal_count >= 1)
check("Payments exist", payment_count >= 1)
check("Audit logs exist", audit_count >= 1)

# Check every completed SALE_OUT has a matching sale
orphan_movements = db.query(models.InventoryMovement).filter(
    models.InventoryMovement.movement_type == "SALE_OUT",
    models.InventoryMovement.reference_id.isnot(None),
).all()

bad_movements = [m for m in orphan_movements if not db.get(models.Sale, m.reference_id)]
check("All SALE_OUT movements reference valid sales", len(bad_movements) == 0,
      f"orphans={len(bad_movements)}")

# Check journal debit == credit (balanced double-entry)
entries = db.query(models.JournalEntry).all()
unbalanced = []
for e in entries:
    total_debit = sum(float(l.debit) for l in e.lines)
    total_credit = sum(float(l.credit) for l in e.lines)
    if abs(total_debit - total_credit) > 0.01:
        unbalanced.append(e.entry_id)
check("All journal entries are balanced (debit = credit)", len(unbalanced) == 0,
      f"unbalanced IDs: {unbalanced[:5]}")

# ─── Summary ──────────────────────────────────────────────────────
section("TEST SUMMARY")
total = results["pass"] + results["fail"]
print(f"\n  Tests run:  {total}")
print(f"  {PASS} Passed: {results['pass']}")
print(f"  {FAIL if results['fail'] else PASS} Failed: {results['fail']}")
if results["errors"]:
    print(f"\n  Failed tests:")
    for e in results["errors"]:
        print(f"    - {e}")

db.close()
sys.exit(0 if results["fail"] == 0 else 1)
