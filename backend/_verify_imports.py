from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

# Hit endpoints WITHOUT auth. 401/403 = route exists (needs auth);
# 405 = wrong method but route exists; 422 = route exists (body needed);
# 404 = route genuinely missing.
checks = [
    ("GET", "/api/users/me"),
    ("GET", "/api/sales"),
    ("POST", "/api/sales"),
    ("POST", "/api/cashier-sessions/open"),
    ("GET", "/api/cashier-sessions/current"),
    ("GET", "/api/approvals"),
    ("POST", "/api/approvals/purchase-order"),
    ("GET", "/api/products"),
    ("GET", "/api/branches"),
    ("GET", "/api/employees"),
    ("GET", "/api/audit-logs"),
    ("GET", "/api/journals"),
    ("GET", "/api/payroll"),
    ("GET", "/api/departments"),
    ("GET", "/api/this-does-not-exist-xyz"),
]

for method, path in checks:
    r = client.request(method, path)
    status = r.status_code
    if status == 404:
        verdict = "MISSING"
    elif status in (401, 403, 405, 422, 400):
        verdict = "EXISTS"
    else:
        verdict = f"status={status}"
    print(f"  {verdict:12s} {method:4s} {path:45s} -> {status}")
