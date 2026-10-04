import unittest
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auth
import database
import main
import models
from database import Base


class InformationFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.db = self.session_factory()
        self.admin = models.Employee(
            name="okuja",
            nin="FLOW-ADMIN-001",
            email="okuja@hardwareworld.local",
            hashed_password=auth.get_password_hash("backendiskey@28777"),
            roletype=models.RoleType.ADMIN,
        )
        self.db.add(self.admin)
        self.db.commit()
        self.admin_environment = patch.dict(
            os.environ,
            {
                "ADMIN_NAME": "okuja",
                "ADMIN_EMAIL": "okuja@hardwareworld.local",
                "ADMIN_PASSWORD": "backendiskey@28777",
            },
        )
        self.admin_environment.start()

        def override_get_db():
            yield self.db

        main.app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.clear()
        self.db.query(models.JournalEntryLine).delete()
        self.db.query(models.JournalEntry).delete()
        self.db.query(models.InventoryMovement).delete()
        self.db.query(models.StockAdjustment).delete()
        self.db.query(models.InventoryBalance).delete()
        self.db.query(models.SaleItem).delete()
        self.db.query(models.Payment).delete()
        self.db.query(models.SalesReturn).delete()
        self.db.query(models.Sale).delete()
        self.db.query(models.UserBranchAssignment).delete()
        self.db.query(models.PasswordEvent).delete()
        self.db.query(models.AuditLog).delete()
        self.db.query(models.EmployeeERPRole).delete()
        self.db.query(models.UserRole).delete()
        self.db.query(models.Product).delete()
        self.db.query(models.Category).delete()
        self.db.query(models.PurchaseOrder).delete()
        self.db.query(models.Supplier).delete()
        self.db.query(models.Warehouse).delete()
        self.db.query(models.PurchaseRequisition).delete()
        self.db.query(models.ChartOfAccount).delete()
        self.db.query(models.Cashier).delete()
        self.db.query(models.ProcurementOfficer).delete()
        self.db.query(models.Accountant).delete()
        self.db.query(models.HRStaff).delete()
        self.db.query(models.BranchManager).delete()
        self.db.query(models.Employee).delete()
        self.db.query(models.Department).delete()
        self.db.query(models.Branch).delete()
        self.db.commit()
        self.db.close()
        self.admin_environment.stop()

    def test_system_admin_is_limited_to_administration_not_catalogue_operations(self):
        login_response = self.client.post(
            "/login",
            json={
                "username": "okuja",
                "password": "backendiskey@28777",
                "login_type": "admin",
            },
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = self.client.post(
            "/categories",
            json={"categoryname": "Flow Test Hardware"},
            headers=headers,
        )
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(self.client.get("/api/finance/accounts", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/payroll", headers=headers).status_code, 403)
        profile = self.client.get("/api/users/me", headers=headers).json()
        self.assertNotIn("*", profile["permissions"])
        self.assertNotIn("finance:view", profile["permissions"])
        self.assertNotIn("payroll:view", profile["permissions"])

    def test_database_backed_endpoint_rejects_missing_authentication(self):
        response = self.client.get("/categories")

        self.assertEqual(response.status_code, 401)

    def test_kiconco_default_profile_photo_is_available_in_employee_profiles(self):
        employee = models.Employee(
            name="Kiconco Flavia",
            nin="FLOW-EMPLOYEE-001",
            email="kiconco@hardwareworld.local",
            hashed_password=auth.get_password_hash("employee-password"),
            roletype=models.RoleType.HR_STAFF,
        )
        self.db.add(employee)
        self.db.commit()
        main.app.dependency_overrides[auth.get_current_user] = lambda: employee

        expected_url = f"/api/users/{employee.employeeid}/profile-photo"
        profile = self.client.get("/api/users/me")
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["profile_photo_url"], expected_url)

        directory = self.client.get("/employees")
        self.assertEqual(directory.status_code, 200, directory.text)
        employee_row = next(row for row in directory.json() if row["employeeid"] == employee.employeeid)
        self.assertEqual(employee_row["profile_photo_url"], expected_url)

        photo = self.client.get(expected_url)
        expected_photo = Path(__file__).resolve().parent / "default-profile-photos" / "kiconco-flavia.webp"
        self.assertEqual(photo.status_code, 200, photo.text)
        self.assertEqual(photo.headers["content-type"], "image/webp")
        self.assertEqual(photo.content, expected_photo.read_bytes())

    def test_employee_profile_photo_upload_is_validated_and_available_to_authenticated_users(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        main.app.dependency_overrides[auth.get_current_user] = lambda: self.admin
        with tempfile.TemporaryDirectory() as upload_dir:
            with patch("api_router.PROFILE_PHOTO_DIR", Path(upload_dir)):
                upload = self.client.put(
                    f"/api/users/{self.admin.employeeid}/profile-photo",
                    files={"file": ("portrait.png", png, "image/png")},
                )
                self.assertEqual(upload.status_code, 200, upload.text)
                self.assertEqual(
                    upload.json()["profile_photo_url"],
                    f"/api/users/{self.admin.employeeid}/profile-photo",
                )

                profile = self.client.get("/api/users/me")
                self.assertEqual(profile.status_code, 200, profile.text)
                self.assertEqual(profile.json()["profile_photo_url"], upload.json()["profile_photo_url"])
                directory = self.client.get("/employees")
                self.assertEqual(directory.status_code, 200, directory.text)
                admin_entry = next(
                    employee
                    for employee in directory.json()
                    if employee["employeeid"] == self.admin.employeeid
                )
                self.assertEqual(admin_entry["profile_photo_url"], upload.json()["profile_photo_url"])

                download = self.client.get(upload.json()["profile_photo_url"])
                self.assertEqual(download.status_code, 200, download.text)
                self.assertEqual(download.content, png)
                self.assertEqual(download.headers["content-type"], "image/png")
                self.assertEqual(download.headers["cache-control"], "private, no-store")

                jpeg = b"\xff\xd8\xff" + b"\x00" * 16
                jpeg_upload = self.client.put(
                    f"/api/users/{self.admin.employeeid}/profile-photo",
                    files={"file": ("portrait.jpg", jpeg, "image/jpeg")},
                )
                self.assertEqual(jpeg_upload.status_code, 200, jpeg_upload.text)
                jpeg_download = self.client.get(jpeg_upload.json()["profile_photo_url"])
                self.assertEqual(jpeg_download.status_code, 200, jpeg_download.text)
                self.assertEqual(jpeg_download.content, jpeg)
                self.assertEqual(jpeg_download.headers["content-type"], "image/jpeg")

                invalid = self.client.put(
                    f"/api/users/{self.admin.employeeid}/profile-photo",
                    files={"file": ("portrait.svg", b"<svg></svg>", "image/svg+xml")},
                )
                self.assertEqual(invalid.status_code, 415, invalid.text)

    def test_temporary_password_generation_requires_admin_permission_and_is_ephemeral(self):
        main.app.dependency_overrides[auth.get_current_user] = lambda: self.admin
        with patch("api_router.auth.generate_temporary_password", return_value="SecureServerGenerated_123"):
            generated = self.client.post("/api/users/generate-temporary-password")

        self.assertEqual(generated.status_code, 200, generated.text)
        self.assertEqual(generated.json(), {"temporary_password": "SecureServerGenerated_123"})
        self.assertEqual(self.db.query(models.PasswordEvent).count(), 0)

        branch = models.Branch(branchname="Password Generation Branch", location="Test")
        self.db.add(branch)
        self.db.flush()
        department = models.Department(
            departmentname="Finance",
            branchid=branch.branchid,
        )
        self.db.add(department)
        self.db.commit()
        created = self.client.post(
            "/employees",
            json={
                "name": "Generated Password Employee",
                "nin": "FLOW-PASSWORD-GENERATED",
                "email": "generated.password@example.com",
                "password": generated.json()["temporary_password"],
                "salary": 1000,
                "departmentid": department.departmentid,
                "branchid": branch.branchid,
                "roletype": "Accountant",
            },
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        created_employee = self.db.get(models.Employee, created.json()["employeeid"])
        self.assertIsNotNone(created_employee)
        self.assertNotEqual(created_employee.hashed_password, generated.json()["temporary_password"])
        self.assertTrue(auth.verify_password(
            generated.json()["temporary_password"],
            created_employee.hashed_password,
        ))
        self.assertTrue(created_employee.must_change_password)
        self.assertIsNotNone(created_employee.temporary_password_expires_at)
        self.assertNotIn(
            generated.json()["temporary_password"],
            " ".join(
                audit.details or ""
                for audit in self.db.query(models.AuditLog).all()
            ),
        )

        employee = models.Employee(
            name="Unauthorized Generator",
            nin="FLOW-PASSWORD-GENERATOR",
            email="unauthorized.generator@example.com",
            hashed_password=auth.get_password_hash("generator-password-2026"),
            roletype=models.RoleType.CASHIER,
        )
        self.db.add(employee)
        self.db.commit()
        main.app.dependency_overrides[auth.get_current_user] = lambda: employee
        with patch("api_router.auth.has_permission", return_value=False):
            denied = self.client.post("/api/users/generate-temporary-password")
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_sales_endpoints_enforce_assigned_branch_and_cashier_ownership(self):
        branch_a = models.Branch(branchname="Sales Branch A", location="Test")
        branch_b = models.Branch(branchname="Sales Branch B", location="Test")
        self.db.add_all([branch_a, branch_b])
        self.db.flush()
        cashier = models.Employee(
            name="Scoped Cashier",
            nin="FLOW-SALES-CASHIER",
            email="scoped.cashier@example.com",
            hashed_password=auth.get_password_hash("cashier-password-2026"),
            roletype=models.RoleType.CASHIER,
            branchid=branch_a.branchid,
        )
        other_cashier = models.Employee(
            name="Other Cashier",
            nin="FLOW-SALES-CASHIER-2",
            email="other.cashier@example.com",
            hashed_password=auth.get_password_hash("cashier-password-2026"),
            roletype=models.RoleType.CASHIER,
            branchid=branch_b.branchid,
        )
        self.db.add_all([cashier, other_cashier])
        self.db.flush()
        self.db.add_all([
            models.Sale(employeeid=cashier.employeeid, branchid=branch_a.branchid, totalamount=100, status="COMPLETED"),
            models.Sale(employeeid=other_cashier.employeeid, branchid=branch_b.branchid, totalamount=900, status="COMPLETED"),
        ])
        self.db.commit()
        main.app.dependency_overrides[auth.get_current_user] = lambda: cashier

        with patch("api_router.auth.has_permission", return_value=True):
            sales = self.client.get("/api/sales")
            report = self.client.get("/api/reports/sales")
            other_branch = self.client.get(f"/api/sales?branch_id={branch_b.branchid}")

        self.assertEqual(sales.status_code, 200, sales.text)
        self.assertEqual([sale["totalamount"] for sale in sales.json()], [100.0])
        self.assertEqual(report.status_code, 200, report.text)
        self.assertEqual(report.json()["total_revenue"], 100.0)
        self.assertEqual(other_branch.status_code, 403, other_branch.text)

    def test_procurement_lists_require_permission_and_stay_in_assigned_branch(self):
        branch_a = models.Branch(branchname="Procurement Branch A", location="Test")
        branch_b = models.Branch(branchname="Procurement Branch B", location="Test")
        self.db.add_all([branch_a, branch_b])
        self.db.flush()
        employee = models.Employee(
            name="Scoped Procurement",
            nin="FLOW-PROCUREMENT-USER",
            email="scoped.procurement@example.com",
            hashed_password=auth.get_password_hash("procurement-password-2026"),
            roletype=models.RoleType.PROCUREMENT_OFFICER,
            branchid=branch_a.branchid,
        )
        supplier = models.Supplier(suppliername="Scoped Test Supplier")
        self.db.add_all([employee, supplier])
        self.db.flush()
        self.db.add_all([
            models.PurchaseRequisition(reference="REQ-SCOPE-A", branch_id=branch_a.branchid, requested_by=employee.employeeid, status="PENDING"),
            models.PurchaseRequisition(reference="REQ-SCOPE-B", branch_id=branch_b.branchid, requested_by=employee.employeeid, status="PENDING"),
            models.PurchaseOrder(
                employeeid=employee.employeeid,
                branch_id=branch_a.branchid,
                status=models.POStatus.PENDING,
                total_amount=100,
            ),
            models.PurchaseOrder(
                employeeid=employee.employeeid,
                branch_id=branch_b.branchid,
                status=models.POStatus.PENDING,
                total_amount=900,
            ),
        ])
        self.db.commit()
        main.app.dependency_overrides[auth.get_current_user] = lambda: employee

        with patch("api_router.auth.has_permission", return_value=False):
            denied_reqs = self.client.get("/api/purchase-requisitions")
            denied_pos = self.client.get("/api/purchase-orders")
        self.assertEqual(denied_reqs.status_code, 403)
        self.assertEqual(denied_pos.status_code, 403)

        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "procurement:requisition",
        ):
            scoped_reqs = self.client.get("/api/purchase-requisitions")
        self.assertEqual(scoped_reqs.status_code, 200, scoped_reqs.text)
        self.assertEqual([req["requisition_id"] for req in scoped_reqs.json()], [
            self.db.query(models.PurchaseRequisition).filter_by(reference="REQ-SCOPE-A").one().requisition_id
        ])
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "procurement:po_create",
        ):
            scoped_orders = self.client.get("/api/purchase-orders")
        self.assertEqual(scoped_orders.status_code, 200, scoped_orders.text)
        self.assertEqual(len(scoped_orders.json()), 1)
        self.assertEqual(scoped_orders.json()[0]["total_amount"], 100.0)

        out_of_branch = self.client.post(
            "/api/purchase-orders",
            json={"supplierid": supplier.supplierid, "branchid": branch_b.branchid, "items": []},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        self.assertEqual(out_of_branch.status_code, 403, out_of_branch.text)
        own_branch = self.client.post(
            "/api/purchase-orders",
            json={"supplierid": supplier.supplierid, "branchid": branch_a.branchid, "items": []},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        self.assertEqual(own_branch.status_code, 200, own_branch.text)
        scoped_orders = self.client.get("/api/purchase-orders")
        self.assertEqual(len(scoped_orders.json()), 2)

    def test_stock_adjustment_is_pending_until_authorized_non_requester_approves(self):
        branch = models.Branch(branchname="Adjustment Branch", location="Test")
        self.db.add(branch)
        self.db.flush()
        warehouse = models.Warehouse(branch_id=branch.branchid, warehouse_name="Adjustment Warehouse")
        category = models.Category(categoryname="Adjustment Category")
        self.db.add_all([warehouse, category])
        self.db.flush()
        product = models.Product(
            itemname="Adjustment Test Product",
            unitprice=100,
            costprice=10,
            categoryid=category.categoryid,
        )
        requester = models.Employee(
            name="Adjustment Requester",
            nin="FLOW-ADJUST-REQUESTER",
            email="adjustment.requester@example.com",
            hashed_password=auth.get_password_hash("requester-password-2026"),
            roletype=models.RoleType.PROCUREMENT_OFFICER,
            branchid=branch.branchid,
        )
        approver = models.Employee(
            name="Adjustment Approver",
            nin="FLOW-ADJUST-APPROVER",
            email="adjustment.approver@example.com",
            hashed_password=auth.get_password_hash("approver-password-2026"),
            roletype=models.RoleType.BRANCH_MANAGER,
            branchid=branch.branchid,
        )
        self.db.add_all([product, requester, approver])
        self.db.flush()
        self.db.add(models.InventoryBalance(
            item_id=product.itemid,
            warehouse_id=warehouse.warehouse_id,
            available_stock=10,
            reserved_stock=0,
        ))
        self.db.add_all([
            models.UserBranchAssignment(user_id=requester.employeeid, branch_id=branch.branchid),
            models.UserBranchAssignment(user_id=approver.employeeid, branch_id=branch.branchid),
            models.ChartOfAccount(
                account_code="5030",
                account_name="Inventory Shrinkage Expense",
                account_type="EXPENSE",
            ),
            models.ChartOfAccount(
                account_code="1050",
                account_name="Inventory Asset",
                account_type="ASSET",
            ),
        ])
        self.db.commit()

        main.app.dependency_overrides[auth.get_current_user] = lambda: requester
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "inventory:adjust",
        ):
            submitted = self.client.post(
                "/api/stock-adjustments",
                json={
                    "warehouse_id": warehouse.warehouse_id,
                    "item_id": product.itemid,
                    "variance_quantity": -2,
                    "reason_code": "STOCKTAKE",
                },
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        adjustment_id = submitted.json()["adjustment_id"]
        self.assertEqual(submitted.json()["status"], "PENDING")
        balance = self.db.query(models.InventoryBalance).filter_by(item_id=product.itemid).one()
        self.assertEqual(float(balance.available_stock), 10.0)
        self.assertEqual(self.db.query(models.InventoryMovement).filter_by(reference_id=adjustment_id).count(), 0)

        main.app.dependency_overrides[auth.get_current_user] = lambda: requester
        with patch("api_router.auth.has_permission", return_value=True):
            self_approval = self.client.post(
                "/api/approvals/stock-adjustment",
                json={"adjustment_id": adjustment_id, "action": "APPROVE"},
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        self.assertEqual(self_approval.status_code, 403)

        main.app.dependency_overrides[auth.get_current_user] = lambda: approver
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "inventory:approve_adjust",
        ):
            approved = self.client.post(
                "/api/approvals/stock-adjustment",
                json={"adjustment_id": adjustment_id, "action": "APPROVE"},
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        balance = self.db.query(models.InventoryBalance).filter_by(item_id=product.itemid).one()
        self.assertEqual(float(balance.available_stock), 8.0)
        self.assertEqual(self.db.query(models.InventoryMovement).filter_by(reference_id=adjustment_id).count(), 1)
        journal = self.db.query(models.JournalEntry).filter_by(reference_id=adjustment_id).one()
        self.assertEqual(float(journal.total_amount), 20.0)
        self.assertEqual(
            self.db.query(models.JournalEntryLine).filter_by(entry_id=journal.entry_id).count(),
            2,
        )

        main.app.dependency_overrides[auth.get_current_user] = lambda: requester
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "inventory:adjust",
        ):
            rejected_submission = self.client.post(
                "/api/stock-adjustments",
                json={
                    "warehouse_id": warehouse.warehouse_id,
                    "item_id": product.itemid,
                    "variance_quantity": 1,
                    "reason_code": "STOCKTAKE",
                },
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        rejected_id = rejected_submission.json()["adjustment_id"]
        main.app.dependency_overrides[auth.get_current_user] = lambda: approver
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "inventory:approve_adjust",
        ):
            rejected = self.client.post(
                "/api/approvals/stock-adjustment",
                json={"adjustment_id": rejected_id, "action": "REJECT"},
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["status"], "REJECTED")
        self.assertEqual(float(balance.available_stock), 8.0)
        self.assertEqual(self.db.query(models.InventoryMovement).filter_by(reference_id=rejected_id).count(), 0)

        main.app.dependency_overrides[auth.get_current_user] = lambda: requester
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "inventory:adjust",
        ):
            excessive_submission = self.client.post(
                "/api/stock-adjustments",
                json={
                    "warehouse_id": warehouse.warehouse_id,
                    "item_id": product.itemid,
                    "variance_quantity": -20,
                    "reason_code": "STOCKTAKE",
                },
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        excessive_id = excessive_submission.json()["adjustment_id"]
        main.app.dependency_overrides[auth.get_current_user] = lambda: approver
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission == "inventory:approve_adjust",
        ):
            excessive_approval = self.client.post(
                "/api/approvals/stock-adjustment",
                json={"adjustment_id": excessive_id, "action": "APPROVE"},
                headers={"Origin": "http://127.0.0.1:8000"},
            )
        self.assertEqual(excessive_approval.status_code, 409, excessive_approval.text)
        balance = self.db.query(models.InventoryBalance).filter_by(item_id=product.itemid).one()
        self.assertEqual(float(balance.available_stock), 8.0)

    def test_approvals_are_visible_only_to_users_with_approval_permission(self):
        branch = models.Branch(branchname="Approvals Branch", location="Test")
        self.db.add(branch)
        self.db.flush()
        self.admin.branchid = branch.branchid
        requester = models.Employee(
            name="Approval Requester",
            nin="FLOW-REQUESTER-001",
            email="approval.requester@example.com",
            hashed_password=auth.get_password_hash("requester-password-2026"),
            roletype=models.RoleType.CASHIER,
        )
        self.db.add(requester)
        supplier = models.Supplier(suppliername="Approval Supplier")
        self.db.add(supplier)
        self.db.flush()
        self.db.add(models.PurchaseRequisition(
            reference="REQ-FLOW-001",
            branch_id=branch.branchid,
            requested_by=requester.employeeid,
            status="PENDING",
        ))
        self.db.add(models.PurchaseOrder(
            supplierid=supplier.supplierid,
            employeeid=requester.employeeid,
            branch_id=branch.branchid,
            status=models.POStatus.PENDING,
        ))
        self.db.commit()

        login_response = self.client.post(
            "/login",
            json={"username": "okuja", "password": "backendiskey@28777", "login_type": "admin"},
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        self.assertEqual(self.client.get("/api/approvals", headers=headers).json(), [])
        with patch(
            "api_router.auth.has_permission",
            side_effect=lambda _db, _user, permission: permission in {
                "procurement:approve_req",
                "procurement:po_approve",
            },
        ):
            approvals = self.client.get("/api/approvals", headers=headers)
            decision = self.client.post(
                "/api/approvals/requisition",
                headers=headers,
                json={"requisition_id": approvals.json()[0]["id"], "action": "APPROVE"},
            )

        self.assertEqual(approvals.status_code, 200, approvals.text)
        self.assertEqual(len(approvals.json()), 2)
        requisition_approval = next(item for item in approvals.json() if item["type"] == "REQUISITION")
        purchase_order_approval = next(item for item in approvals.json() if item["type"] == "PO")
        self.assertEqual(requisition_approval["description"], "Purchase Requisition — 0 item(s)")
        self.assertEqual(purchase_order_approval["requester"], requester.name)
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(decision.json()["status"], "APPROVED")

    def test_frontend_assets_require_cache_revalidation(self):
        response = self.client.get("/assets/js/api.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-cache, must-revalidate")

    def test_admin_organization_pages_and_create_routes(self):
        login_response = self.client.post(
            "/login",
            json={"username": "okuja", "password": "backendiskey@28777"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)

        for page in ("branches", "warehouses", "departments"):
            response = self.client.get(f"/{page}.html")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn(f'data-page="{page}"', response.text)

        approvals_page = self.client.get("/approvals.html")
        self.assertEqual(approvals_page.status_code, 200, approvals_page.text)
        self.assertIn('data-page="approvals"', approvals_page.text)

        branch_response = self.client.post(
            "/branches",
            json={"branchname": "Test Branch", "location": "Kampala"},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        self.assertEqual(branch_response.status_code, 200, branch_response.text)
        branch_id = branch_response.json()["branchid"]

        department_response = self.client.post(
            "/api/departments",
            json={"departmentname": "Test Department", "branchid": branch_id},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        self.assertEqual(department_response.status_code, 200, department_response.text)
        self.assertEqual(department_response.json()["branch_name"], "Test Branch")

        warehouse_response = self.client.post(
            "/api/warehouses",
            json={"warehouse_name": "Test Warehouse", "branch_id": branch_id},
            headers={"Origin": "http://127.0.0.1:8000"},
        )
        self.assertEqual(warehouse_response.status_code, 200, warehouse_response.text)
        self.assertEqual(warehouse_response.json()["branch_id"], branch_id)

        self.assertEqual(self.client.get("/api/branches").status_code, 200)
        self.assertEqual(self.client.get("/api/departments").status_code, 200)
        self.assertEqual(self.client.get("/api/warehouses").status_code, 200)

    def test_admin_dashboard_loads_from_empty_operational_tables(self):
        login_response = self.client.post(
            "/login",
            json={
                "username": "okuja",
                "password": "backendiskey@28777",
                "login_type": "admin",
            },
        )
        self.assertEqual(login_response.status_code, 200)
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        response = self.client.get("/api/dashboard", headers=headers)

        self.assertEqual(response.status_code, 200, response.text)
        self.db.add_all([
            models.AuditLog(
                username_or_email="cashier@example.com",
                action="LOGIN_FAILED",
                timestamp=datetime.utcnow(),
            ),
            models.AuditLog(
                username_or_email="cashier@example.com",
                action="LOGIN_FAILED",
                timestamp=datetime.utcnow(),
            ),
            models.AuditLog(
                username_or_email="clerk@example.com",
                action="LOGIN_FAILED",
                timestamp=datetime.utcnow(),
            ),
        ])
        self.db.commit()
        response = self.client.get("/api/dashboard", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        dashboard = response.json()
        self.assertIn("admin", dashboard)
        self.assertIn("procurement", dashboard)
        self.assertIsNone(dashboard["procurement"])
        self.assertIsNone(dashboard["finance"])
        self.assertEqual(dashboard["admin"]["active_accounts_count"], 1)
        self.assertEqual(dashboard["admin"]["pending_account_setup_count"], 0)
        self.assertEqual(dashboard["admin"]["failed_logins_today"], 3)
        self.assertEqual(dashboard["admin"]["accounts_affected_today"], 2)

    def test_configured_admin_can_login_without_preexisting_database_account(self):
        self.db.delete(self.admin)
        self.db.commit()
        configured_password = "configured-admin-password-2026"
        with patch.dict(
            os.environ,
            {
                "ADMIN_NAME": "okuja",
                "ADMIN_EMAIL": "okuja@hardwareworld.local",
                "ADMIN_PASSWORD": configured_password,
            },
        ):
            login_response = self.client.post(
                "/login",
                json={
                    "username": "okuja@hardwareworld.local",
                    "password": configured_password,
                },
            )

        self.assertEqual(login_response.status_code, 200, login_response.text)
        admin = self.db.query(models.Employee).filter_by(email="okuja@hardwareworld.local").one()
        self.assertEqual(admin.roletype, models.RoleType.ADMIN)
        self.assertTrue(auth.verify_password(configured_password, admin.hashed_password))
        self.assertEqual(self.client.get("/api/users/me").status_code, 200)

    def test_admin_portal_rejects_non_configured_credentials(self):
        with patch.dict(
            os.environ,
            {
                "ADMIN_NAME": "okuja",
                "ADMIN_EMAIL": "okuja@hardwareworld.local",
                "ADMIN_PASSWORD": "configured-admin-password-2026",
            },
        ):
            response = self.client.post(
                "/login",
                json={
                    "username": "okuja",
                    "password": "backendiskey@28777",
                    "login_type": "admin",
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_staff_login_requires_department_selection(self):
        staff = models.Employee(
            name="Test Cashier",
            nin="FLOW-STAFF-001",
            email="cashier@example.com",
            hashed_password=auth.get_password_hash("staff-password-2026"),
            roletype=models.RoleType.CASHIER,
        )
        self.db.add(staff)
        self.db.commit()

        response = self.client.post(
            "/login",
            json={"username": staff.email, "password": "staff-password-2026"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid sign-in details or department selection.")

    def test_admin_created_employee_must_change_temporary_password_before_access(self):
        branch = models.Branch(branchname="Flow Branch", location="Test")
        self.db.add(branch)
        self.db.flush()
        department = models.Department(departmentname="Sales", branchid=branch.branchid)
        self.db.add(department)
        self.db.commit()
        admin_login = self.client.post(
            "/login",
            json={"username": "okuja", "password": "backendiskey@28777", "login_type": "admin"},
        )
        admin_token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        created = self.client.post(
            "/employees",
            headers=headers,
            json={
                "name": "Temporary Cashier",
                "nin": "FLOW-TEMP-001",
                "email": "temporary.cashier@example.com",
                "salary": 0,
                "departmentid": department.departmentid,
                "branchid": branch.branchid,
                "roletype": "Cashier",
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        account = created.json()
        self.assertTrue(account["temporary_password"])
        self.assertTrue(account["must_change_password"])
        employee = self.db.get(models.Employee, account["employeeid"])
        self.assertNotEqual(employee.hashed_password, account["temporary_password"])
        self.assertTrue(auth.verify_password(account["temporary_password"], employee.hashed_password))
        self.assertTrue(employee.must_change_password)
        self.assertIsNotNone(employee.temporary_password_expires_at)

        mismatch = self.client.post(
            "/login",
            json={
                "username": "temporary.cashier@example.com",
                "password": account["temporary_password"],
                "department": "Finance",
            },
        )
        self.assertEqual(mismatch.status_code, 401)
        self.assertEqual(mismatch.json()["detail"], "Invalid sign-in details or department selection.")

        staff_login = self.client.post(
            "/login?cookie_only=true",
            json={
                "username": "temporary.cashier@example.com",
                "password": account["temporary_password"],
                "department": "Sales",
            },
        )
        self.assertEqual(staff_login.status_code, 200, staff_login.text)
        self.assertTrue(staff_login.json()["requires_password_change"])
        self.assertEqual(self.client.get("/api/users/me").status_code, 401)

        changed = self.client.post(
            "/api/auth/initial-password",
            headers={"Origin": "http://127.0.0.1:8000"},
            json={
                "current_password": account["temporary_password"],
                "new_password": "blue hammer market 2026",
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertFalse(employee.must_change_password)
        self.assertIsNone(employee.temporary_password_expires_at)
        self.assertEqual(self.client.get("/api/users/me").status_code, 200)


if __name__ == "__main__":
    unittest.main()
