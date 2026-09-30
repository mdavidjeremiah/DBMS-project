import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import auth
import bootstrap_admin
import main
import models
from database import Base
from schemas import LoginRequest


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.db = self.session_factory()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_password_hash_round_trip(self):
        password = "backendiskey@28777"
        hashed_password = auth.get_password_hash(password)

        self.assertNotEqual(password, hashed_password)
        self.assertTrue(auth.verify_password(password, hashed_password))
        self.assertFalse(auth.verify_password("wrong-password", hashed_password))

    def test_login_request_requires_credentials(self):
        with self.assertRaises(Exception):
            LoginRequest(username="okuja")

    def test_login_request_accepts_admin_login(self):
        request = LoginRequest(
            username="okuja",
            password="backendiskey@28777",
            login_type="admin",
        )

        self.assertEqual(request.login_type, "admin")
        self.assertIsNone(request.department)

    def test_role_guard_allows_admin_only(self):
        admin = models.Employee(
            name="okuja",
            nin="ADMIN-TEST",
            roletype=models.RoleType.ADMIN,
        )
        cashier = models.Employee(
            name="Cashier",
            nin="CASHIER-TEST",
            roletype=models.RoleType.CASHIER,
        )

        self.assertIsNone(main.require_role(admin, models.RoleType.ADMIN))
        with self.assertRaises(Exception):
            main.require_role(cashier, models.RoleType.ADMIN)

    def test_bootstrap_creates_only_configured_admin(self):
        with patch.object(bootstrap_admin, "SessionLocal", self.session_factory), patch.dict(
            os.environ,
            {
                "ADMIN_NAME": "okuja",
                "ADMIN_EMAIL": "okuja@hardwareworld.local",
                "ADMIN_PASSWORD": "backendiskey@28777",
            },
            clear=False,
        ):
            bootstrap_admin.bootstrap_admin()

        employees = self.db.query(models.Employee).all()
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0].name, "okuja")
        self.assertEqual(employees[0].roletype, models.RoleType.ADMIN)
        self.assertTrue(auth.verify_password("backendiskey@28777", employees[0].hashed_password))
        self.assertEqual(self.db.query(models.Branch).count(), 0)
        self.assertEqual(self.db.query(models.Product).count(), 0)
        self.assertEqual(self.db.query(models.Sale).count(), 0)


if __name__ == "__main__":
    unittest.main()