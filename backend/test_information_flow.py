import unittest
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

        def override_get_db():
            yield self.db

        main.app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.clear()
        self.db.query(models.Category).delete()
        self.db.query(models.Employee).delete()
        self.db.commit()
        self.db.close()

    def test_frontend_api_database_api_round_trip(self):
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

        frontend_payload = {"categoryname": "Flow Test Hardware"}
        create_response = self.client.post("/categories", json=frontend_payload, headers=headers)
        self.assertEqual(create_response.status_code, 200)
        created_category = create_response.json()

        stored_category = self.db.get(models.Category, created_category["categoryid"])
        self.assertIsNotNone(stored_category)
        self.assertEqual(stored_category.categoryname, frontend_payload["categoryname"])

        read_response = self.client.get("/categories", headers=headers)
        self.assertEqual(read_response.status_code, 200)
        self.assertIn(created_category, read_response.json())

    def test_database_backed_endpoint_rejects_missing_authentication(self):
        response = self.client.get("/categories")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
