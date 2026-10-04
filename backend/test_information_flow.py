import unittest
import os
from datetime import datetime
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
        self.db.query(models.PasswordEvent).delete()
        self.db.query(models.AuditLog).delete()
        self.db.query(models.EmployeeERPRole).delete()
        self.db.query(models.UserRole).delete()
        self.db.query(models.Category).delete()
        self.db.query(models.Warehouse).delete()
        self.db.query(models.PurchaseRequisition).delete()
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

    def test_approvals_are_visible_only_to_users_with_approval_permission(self):
        branch = models.Branch(branchname="Approvals Branch", location="Test")
        self.db.add(branch)
        self.db.flush()
        requester = models.Employee(
            name="Approval Requester",
            nin="FLOW-REQUESTER-001",
            email="approval.requester@example.com",
            hashed_password=auth.get_password_hash("requester-password-2026"),
            roletype=models.RoleType.CASHIER,
        )
        self.db.add(requester)
        self.db.flush()
        self.db.add(models.PurchaseRequisition(
            reference="REQ-FLOW-001",
            branch_id=branch.branchid,
            requested_by=requester.employeeid,
            status="PENDING",
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
            side_effect=lambda _db, _user, permission: permission == "procurement:approve_req",
        ):
            approvals = self.client.get("/api/approvals", headers=headers)
            decision = self.client.post(
                "/api/approvals/requisition",
                headers=headers,
                json={"requisition_id": approvals.json()[0]["id"], "action": "APPROVE"},
            )

        self.assertEqual(approvals.status_code, 200, approvals.text)
        self.assertEqual(len(approvals.json()), 1)
        self.assertEqual(approvals.json()[0]["type"], "REQUISITION")
        self.assertEqual(approvals.json()[0]["description"], "Purchase Requisition — 0 item(s)")
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
