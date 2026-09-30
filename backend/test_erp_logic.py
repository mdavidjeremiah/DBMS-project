"""
Hardware World ERP — In-Memory Logic Tests (SQLite)
Validates all critical business logic without requiring a live MySQL instance.
Tests: security, POS pipeline, idempotency, separation of duties, payroll privacy
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Override DATABASE_URL to use SQLite in-memory
os.environ["DATABASE_URL"] = "sqlite:///./test_hw.db"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = {"pass": 0, "fail": 0, "errors": []}

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
        results["pass"] += 1
    else:
        msg = f"  {FAIL} {name}" + (f"  →  {detail}" if detail else "")
        print(msg)
        results["fail"] += 1
        results["errors"].append(f"{name}: {detail}")

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

# ── Bootstrap ──────────────────────────────────────────────────────
section("BOOTSTRAP: Create in-memory schema")

from database import Base, engine, SessionLocal
import models
import auth
import erp_service
import schemas

try:
    Base.metadata.create_all(bind=engine)
    check("SQLite schema creation", True)
except Exception as e:
    check("SQLite schema creation", False, str(e))
    sys.exit(1)

db = SessionLocal()

# ── Seed minimal data ─────────────────────────────────────────────
section("SEED MINIMAL DATA")

try:
    from seed import seed_baseline
    seed_baseline(db)
    check("seed_baseline() on SQLite", True)
except Exception as e:
    check("seed_baseline() on SQLite", False, str(e))
    import traceback; traceback.print_exc()

akena = db.query(models.Employee).filter(models.Employee.email == "akena@hardwareworld.com").first()
sarah = db.query(models.Employee).filter(models.Employee.email == "sarah.nakato@hardwareworld.com").first()
john  = db.query(models.Employee).filter(models.Employee.email == "john.kato@hardwareworld.com").first()
grace = db.query(models.Employee).filter(models.Employee.email == "grace.apio@hardwareworld.com").first()
brian = db.query(models.Employee).filter(models.Employee.email == "brian.mukasa@hardwareworld.com").first()

check("Admin Akena seeded",   akena is not None)
check("Cashier Sarah seeded", sarah is not None)
check("Procurement John seeded", john is not None)
check("Accountant Grace seeded", grace is not None)
check("Branch Manager Brian seeded", brian is not None)

# ── RBAC ──────────────────────────────────────────────────────────
section("RBAC PERMISSION CHECKS")

if sarah:
    perms = auth.get_user_permissions(db, sarah)
    check("Cashier has sales:pos",      "sales:pos"    in perms, str(perms[:8]))
    check("Cashier has sales:view",     "sales:view"   in perms)
    check("Cashier lacks payroll:view", "payroll:view" not in perms and "*" not in perms,
          f"perms={perms}")
    check("Cashier lacks finance:post", "finance:post" not in perms and "*" not in perms,
          f"perms={perms}")

if grace:
    perms_g = auth.get_user_permissions(db, grace)
    check("Accountant has finance:view",  "finance:view"  in perms_g or "*" in perms_g)
    check("Accountant has payroll:view",  "payroll:view"  in perms_g or "*" in perms_g)
    check("Accountant has finance:payment","finance:payment" in perms_g or "*" in perms_g)

if akena:
    perms_a = auth.get_user_permissions(db, akena)
    check("Admin has wildcard '*'", "*" in perms_a)

# ── Password Security ─────────────────────────────────────────────
section("PASSWORD & AUTH SECURITY")

if sarah:
    check("Correct password verifies",  auth.verify_password("Hardware@2026!", sarah.hashed_password))
    check("Wrong password rejected",    not auth.verify_password("wrongpassword", sarah.hashed_password))
    check("Empty password rejected",    not auth.verify_password("", sarah.hashed_password))
    check("SQL-injection string rejected", not auth.verify_password("' OR '1'='1", sarah.hashed_password))

if sarah:
    check("Sarah is_active=True", sarah.is_active == True)

# ── Pydantic Schema Validation ────────────────────────────────────
section("PYDANTIC INPUT VALIDATION (SQL INJECTION & BAD INPUT)")

# Negative quantity blocked at schema level
try:
    schemas.SaleItemCreate(itemid=1, quantity=Decimal("-2"))
    check("Negative quantity blocked by schema", False, "Should raise ValidationError")
except Exception as e:
    check("Negative quantity blocked by schema", True, type(e).__name__)

# Zero quantity blocked at schema level
try:
    schemas.SaleItemCreate(itemid=1, quantity=Decimal("0"))
    check("Zero quantity blocked by schema", False, "Should raise ValidationError")
except Exception as e:
    check("Zero quantity blocked by schema", True, type(e).__name__)

# SQL injection in string fields — Pydantic accepts strings (sanitization is at ORM layer)
try:
    item = schemas.SaleItemCreate(itemid=1, quantity=Decimal("1"))
    check("Valid item passes schema", item.itemid == 1)
except Exception as e:
    check("Valid item passes schema", False, str(e))

# ── POS Sale Pipeline ─────────────────────────────────────────────
section("POS SALE PIPELINE — ATOMIC TRANSACTION")

warehouse = db.query(models.Warehouse).first()
product = db.query(models.Product).filter(models.Product.is_active == True).first()

if product and warehouse and sarah:
    # Ensure stock balance
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
    audit_before = db.query(models.AuditLog).count()
    movements_before = db.query(models.InventoryMovement).count()

    print(f"\n  {INFO} Product: {product.itemname} (id={product.itemid})")
    print(f"  {INFO} Stock before: {stock_before}  UnitPrice: {product.unitprice}  Cost: {product.costprice}")

    ikey = "TESTKEY-001"
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
        print(f"  {INFO} Result: {result}")

        db.expire_all()
        bal_after = db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
        ).first()

        check("Sale record created (has saleid)",     result.get("saleid") is not None)
        check("Sale total > 0",                        result.get("totalamount", 0) > 0)
        sale_total = float(result.get("totalamount", 0))
        expected_total = float(product.unitprice) * 2
        check("Sale total = price × qty",              abs(sale_total - expected_total) < 0.01,
              f"got {sale_total}, expected {expected_total}")
        check("Stock decreased by 2",
              abs(float(bal_after.available_stock) - (stock_before - 2)) < 0.001,
              f"before={stock_before}, after={float(bal_after.available_stock)}")

        movement = db.query(models.InventoryMovement).filter(
            models.InventoryMovement.reference_id == result["saleid"],
            models.InventoryMovement.movement_type == "SALE_OUT",
        ).first()
        check("SALE_OUT movement created",    movement is not None)
        check("Movement quantity = -2",       movement is not None and abs(float(movement.quantity) + 2) < 0.001,
              f"qty={float(movement.quantity) if movement else 'N/A'}")

        payment = db.query(models.Payment).filter(models.Payment.sale_id == result["saleid"]).first()
        check("Payment record created",       payment is not None)
        check("Payment method = CASH",        payment is not None and payment.payment_method == "CASH")
        check("Payment amount matches total", payment is not None and abs(float(payment.amount) - sale_total) < 0.01,
              f"payment={float(payment.amount) if payment else 'N/A'}, total={sale_total}")

        new_journals = db.query(models.JournalEntry).count() - journals_before
        check("Journal entry created",        new_journals >= 1, f"new={new_journals}")

        jrn = db.query(models.JournalEntry).filter(
            models.JournalEntry.reference_type == "SALE",
            models.JournalEntry.reference_id == result["saleid"],
        ).first()
        check("Journal linked to sale",       jrn is not None)
        if jrn:
            debits  = {l.account_code for l in jrn.lines if float(l.debit)  > 0}
            credits = {l.account_code for l in jrn.lines if float(l.credit) > 0}
            check("Debit Cash on Hand (1010)",        "1010" in debits,   f"debits={debits}")
            check("Credit Sales Revenue (4010)",      "4010" in credits,  f"credits={credits}")
            if product.costprice and float(product.costprice) > 0:
                check("Debit COGS (5010)",            "5010" in debits,   f"debits={debits}")
                check("Credit Inventory Asset (1050)","1050" in credits,  f"credits={credits}")

            # Verify journals are balanced (debit = credit)
            total_debit  = sum(float(l.debit)  for l in jrn.lines)
            total_credit = sum(float(l.credit) for l in jrn.lines)
            check("Journal balanced (debit = credit)", abs(total_debit - total_credit) < 0.01,
                  f"debit={total_debit}, credit={total_credit}")

        new_audit = db.query(models.AuditLog).count() - audit_before
        check("Audit log entry created",      new_audit >= 1)
        audit = db.query(models.AuditLog).filter(
            models.AuditLog.action == "POS_SALE_COMPLETED",
            models.AuditLog.entity_id == result["saleid"],
        ).first()
        check("Audit action = POS_SALE_COMPLETED", audit is not None)

    except Exception as e:
        check("process_pos_sale() completed", False, str(e))
        import traceback; traceback.print_exc()
else:
    print(f"  {INFO} Skipping POS test — seeding may have failed")

# ── Security: Negative quantity goes through erp_service check ────
section("SECURITY: INVALID SALE INPUTS")

if product and sarah and warehouse:
    # Service-level negative quantity check
    try:
        bad = schemas.SaleCreate(
            employeeid=sarah.employeeid,
            branchid=sarah.branchid or 1,
            warehouseid=warehouse.warehouse_id,
            payment_method="CASH",
            items=[schemas.SaleItemCreate(itemid=product.itemid, quantity=Decimal("1"))],
        )
        bad.items[0] = type('Obj', (), {'itemid': product.itemid, 'quantity': Decimal("-2")})()
        erp_service.process_pos_sale(payload=bad, current_user=sarah, db=db, ip_address="127.0.0.1")
        check("Service blocks negative quantity", False, "Should have raised")
    except Exception as e:
        check("Service blocks negative quantity", "greater than zero" in str(e).lower() or "quantity" in str(e).lower(),
              f"Got: {str(e)[:80]}")

    # Oversell: request more than available
    bal_now = db.query(models.InventoryBalance).filter(
        models.InventoryBalance.item_id == product.itemid,
        models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
    ).first()
    oversell_qty = float(bal_now.available_stock) + 9999
    try:
        over_payload = schemas.SaleCreate(
            employeeid=sarah.employeeid,
            branchid=sarah.branchid or 1,
            warehouseid=warehouse.warehouse_id,
            payment_method="CASH",
            items=[schemas.SaleItemCreate(itemid=product.itemid, quantity=Decimal(str(oversell_qty)))],
        )
        erp_service.process_pos_sale(payload=over_payload, current_user=sarah, db=db, ip_address="127.0.0.1")
        check("Oversell blocked (insufficient stock)", False, "Should have raised")
    except Exception as e:
        check("Oversell blocked (insufficient stock)",
              "insufficient" in str(e).lower() or "stock" in str(e).lower(),
              f"Got: {str(e)[:80]}")

    # Inactive product
    inactive_prod = models.Product(
        itemname="Inactive Test Item",
        unitprice=Decimal("1000"),
        costprice=Decimal("500"),
        reorderlevel=5,
        is_active=False,
        categoryid=1,
    )
    db.add(inactive_prod)
    db.commit()
    db.refresh(inactive_prod)
    try:
        inact_payload = schemas.SaleCreate(
            employeeid=sarah.employeeid,
            branchid=sarah.branchid or 1,
            warehouseid=warehouse.warehouse_id,
            payment_method="CASH",
            items=[schemas.SaleItemCreate(itemid=inactive_prod.itemid, quantity=Decimal("1"))],
        )
        erp_service.process_pos_sale(payload=inact_payload, current_user=sarah, db=db, ip_address="127.0.0.1")
        check("Inactive product blocked", False, "Should have raised")
    except Exception as e:
        check("Inactive product blocked",
              "inactive" in str(e).lower(),
              f"Got: {str(e)[:80]}")

# ── Idempotency ────────────────────────────────────────────────────
section("IDEMPOTENCY: DUPLICATE SALE PREVENTION")

if product and sarah and warehouse:
    bal_now = db.query(models.InventoryBalance).filter(
        models.InventoryBalance.item_id == product.itemid,
        models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
    ).first()
    bal_before = float(bal_now.available_stock)
    ikey3 = "IDEM-TEST-KEY-999"

    try:
        p1 = schemas.SaleCreate(
            employeeid=sarah.employeeid,
            branchid=sarah.branchid or 1,
            warehouseid=warehouse.warehouse_id,
            payment_method="CASH",
            idempotency_key=ikey3,
            items=[schemas.SaleItemCreate(itemid=product.itemid, quantity=Decimal("1"))],
        )
        r1 = erp_service.process_pos_sale(payload=p1, current_user=sarah, db=db, ip_address="127.0.0.1")
        r2 = erp_service.process_pos_sale(payload=p1, current_user=sarah, db=db, ip_address="127.0.0.1")

        check("Same idempotency key returns same sale ID",
              r1["saleid"] == r2["saleid"],
              f"r1={r1['saleid']}, r2={r2['saleid']}")
        check("Second call flagged as replay",
              r2.get("idempotent_replay") == True,
              f"idempotent_replay={r2.get('idempotent_replay')}")

        db.expire_all()
        bal_after = float(db.query(models.InventoryBalance).filter(
            models.InventoryBalance.item_id == product.itemid,
            models.InventoryBalance.warehouse_id == warehouse.warehouse_id,
        ).first().available_stock)

        check("Stock deducted only once (not twice)",
              abs(bal_before - bal_after - 1) < 0.001,
              f"before={bal_before}, after={bal_after}, diff={bal_before - bal_after}")

    except Exception as e:
        check("Idempotency test", False, str(e))
        import traceback; traceback.print_exc()

# ── Separation of Duties ──────────────────────────────────────────
section("SEPARATION OF DUTIES")

if john and brian:
    # John creates requisition; John tries to approve it (should fail)
    req = models.PurchaseRequisition(
        requester_id=john.employeeid,
        branch_id=john.branchid or 1,
        status="PENDING",
        notes="Test SOD requisition",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    try:
        erp_service.approve_or_reject_requisition(
            requisition_id=req.requisition_id,
            action="APPROVE",
            approver=john,
            notes="Self-approval",
            db=db,
        )
        check("Requester cannot approve own requisition", False, "Should raise HTTPException")
    except Exception as e:
        check("Requester cannot approve own requisition",
              "separation" in str(e).lower() or "cannot approve" in str(e).lower(),
              f"Got: {str(e)[:100]}")

    # Brian can approve it
    try:
        erp_service.approve_or_reject_requisition(
            requisition_id=req.requisition_id,
            action="APPROVE",
            approver=brian,
            notes="Manager approval",
            db=db,
        )
        db.expire_all()
        req_refreshed = db.get(models.PurchaseRequisition, req.requisition_id)
        check("Branch manager approves requisition successfully",
              req_refreshed.status == "APPROVED",
              f"status={req_refreshed.status}")
    except Exception as e:
        check("Branch manager approves requisition", False, str(e))

# ── Payroll Privacy (Rule 9) ──────────────────────────────────────
section("PAYROLL PRIVACY (RULE 9)")

if sarah:
    has_payroll_view = auth.has_permission(db, sarah, "payroll:view")
    check("Cashier denied payroll:view", not has_payroll_view, f"has={has_payroll_view}")

if grace:
    has_payroll_view_g = auth.has_permission(db, grace, "payroll:view")
    check("Accountant granted payroll:view", has_payroll_view_g or "*" in auth.get_user_permissions(db, grace))

# ── Payroll Run ────────────────────────────────────────────────────
section("PAYROLL CALCULATION")

if grace:
    try:
        run = erp_service.execute_payroll_run(month="2026-09", prepared_by_user=grace, db=db)
        check("Payroll run created", run.run_id is not None)
        check("Payroll has gross > 0", float(run.total_gross) > 0, f"gross={run.total_gross}")
        check("Net <= Gross", float(run.total_net) <= float(run.total_gross),
              f"net={run.total_net}, gross={run.total_gross}")
        check("Status = DRAFT", run.status == "DRAFT")

        # Approve by Grace (accountant)
        approved = erp_service.approve_and_post_payroll(run_id=run.run_id, approver=grace, db=db)
        check("Payroll approved by accountant", approved.status == "APPROVED")

        # Check payroll journal created
        jrn = db.query(models.JournalEntry).filter(
            models.JournalEntry.reference_type == "PAYROLL",
            models.JournalEntry.reference_id == run.run_id,
        ).first()
        check("Payroll journal entry created", jrn is not None)
        if jrn:
            debits  = {l.account_code for l in jrn.lines if float(l.debit)  > 0}
            credits = {l.account_code for l in jrn.lines if float(l.credit) > 0}
            check("Salaries Expense debited (5020)", "5020" in debits, f"debits={debits}")
            check("Payroll Payable credited (2020)", "2020" in credits, f"credits={credits}")
    except Exception as e:
        check("Payroll run/approve", False, str(e))
        import traceback; traceback.print_exc()

# ── Balanced Books Final Check ─────────────────────────────────────
section("DOUBLE-ENTRY INTEGRITY: ALL JOURNALS BALANCED")

all_journals = db.query(models.JournalEntry).all()
unbalanced = []
for e in all_journals:
    total_dr = sum(float(l.debit) for l in e.lines)
    total_cr = sum(float(l.credit) for l in e.lines)
    if abs(total_dr - total_cr) > 0.01:
        unbalanced.append((e.entry_id, total_dr, total_cr))

check(f"All {len(all_journals)} journal entries are balanced",
      len(unbalanced) == 0,
      f"Unbalanced: {unbalanced[:3]}")

# ── Summary ────────────────────────────────────────────────────────
section("FINAL SUMMARY")
total = results["pass"] + results["fail"]
print(f"\n  Tests run:  {total}")
print(f"  {PASS} Passed: {results['pass']}")
print(f"  {FAIL if results['fail'] else PASS} Failed: {results['fail']}")
if results["errors"]:
    print(f"\n  FAILED TESTS:")
    for e in results["errors"]:
        print(f"    ✗ {e}")
else:
    print(f"\n  All tests passed! The ERP logic is validated.")

db.close()

# Clean up test SQLite file
import os as _os
try:
    _os.remove("test_hw.db")
except Exception:
    pass

sys.exit(0 if results["fail"] == 0 else 1)
