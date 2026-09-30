"""Quick smoke test: login all 6 seeded users against the running server."""
import urllib.request, json, urllib.error, sys, os

BASE = "http://127.0.0.1:8000"
SEED_PASSWORD = os.getenv("SEED_DEFAULT_PASSWORD")
if not SEED_PASSWORD:
    sys.exit("Set SEED_DEFAULT_PASSWORD to the password used by seed.py before running this smoke test.")

def post(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code
    except Exception as e:
        return {"error": str(e)}, 0

def get_auth(path, token):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("\n=== Hardware World ERP — Smoke Test ===\n")

# Health check
resp, code = post("/health", {}), 200
r2 = urllib.request.urlopen(f"{BASE}/health", timeout=5)
health = json.loads(r2.read())
print(f"  Health:   {health}  [{code}]")

# Login tests
users = [
    ("akena@hardwareworld.com",         "Administration",                 "admin"),
    ("sarah.nakato@hardwareworld.com",   "Sales & POS",                    "staff"),
    ("john.kato@hardwareworld.com",      "Procurement & Inventory",        "staff"),
    ("grace.apio@hardwareworld.com",     "Finance & Accounting",           "staff"),
    ("moses.opolot@hardwareworld.com",   "Human Resources",                "staff"),
    ("brian.mukasa@hardwareworld.com",   "Operations & Branch Management", "staff"),
]

tokens = {}
print("\n--- Login tests ---")
all_ok = True
for email, dept, ltype in users:
    body = {"username": email, "password": SEED_PASSWORD, "department": dept, "login_type": ltype}
    resp, code = post("/login", body)
    ok = "access_token" in resp
    label = "PASS" if ok else "FAIL"
    print(f"  {label} [{code}]  {email}")
    if ok:
        tokens[email] = resp["access_token"]
    else:
        print(f"        detail: {resp.get('detail', resp)}")
        all_ok = False

# /users/me test with Admin token
print("\n--- /users/me (Admin) ---")
admin_token = tokens.get("akena@hardwareworld.com")
if admin_token:
    me, code = get_auth("/users/me", admin_token)
    print(f"  {me.get('name')} | role={me.get('roletype')} | dept={me.get('department_name')} | perms={me.get('permissions', [])[:3]}...")

# Security: Cashier cannot access payroll
print("\n--- Security: Cashier blocked from /payroll ---")
sarah_token = tokens.get("sarah.nakato@hardwareworld.com")
if sarah_token:
    resp, code = get_auth("/payroll", sarah_token)
    if code == 403:
        print(f"  PASS [403]  Cashier correctly blocked from payroll")
    else:
        print(f"  FAIL [{code}]  Cashier got {code} on /payroll — should be 403")
        all_ok = False

# /api/dashboard test with Branch Manager token
print("\n--- /api/dashboard (Branch Manager) ---")
brian_token = tokens.get("brian.mukasa@hardwareworld.com")
if brian_token:
    resp, code = get_auth("/api/dashboard", brian_token)
    if code == 200:
        print(f"  PASS [200]  department={resp.get('department')}  roletype={resp.get('roletype')}")
    else:
        print(f"  FAIL [{code}]  {resp.get('detail', str(resp)[:80])}")

# /api/products (Cashier)
print("\n--- /api/products (Cashier) ---")
if sarah_token:
    resp, code = get_auth("/api/products", sarah_token)
    if code == 200 and isinstance(resp, list):
        print(f"  PASS [200]  {len(resp)} products returned")
        if resp:
            p = resp[0]
            print(f"         first: {p['itemname']} | stock={p.get('available_stock')} | active={p.get('is_active')}")
    else:
        print(f"  FAIL [{code}]  {str(resp)[:80]}")

print(f"\n=== {'ALL PASS' if all_ok else 'SOME FAILURES — see above'} ===\n")
sys.exit(0 if all_ok else 1)
