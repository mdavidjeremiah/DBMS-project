from pathlib import Path
import re
import main
from api_workflow_routes import context, review
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
import pytest


def test_operation_form_endpoints_exist():
    source=(Path(__file__).parents[2]/"frontend/assets/js/operations.js").read_text()
    paths=main.app.openapi()["paths"]
    for path in re.findall(r"'(/api/[^']+)'",source):
        assert path in paths, path
        assert ("get" if path in {"/api/operations/context", "/api/catalogue/pricing"} else "post") in paths[path], path
    assert "get" in paths["/api/operations/context"]
    assert "post" in paths["/api/cashier-sessions/{session_id}/review"]


def test_unknown_role_cannot_review_till():
    with patch("auth.has_permission",return_value=False):
        with pytest.raises(HTTPException) as failure:
            review(1,MagicMock(),MagicMock())
        assert failure.value.status_code==403


def test_empty_permission_context_does_not_expose_operational_records():
    with patch("auth.get_user_permissions",return_value=[]), patch("api_workflow_routes.employee_branch_ids",return_value=[]):
        result=context(MagicMock(),MagicMock())
        assert all(not value for value in result.values())
