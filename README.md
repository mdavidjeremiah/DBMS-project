# Hardware World

Hardware World is a FastAPI, SQLAlchemy, MySQL, and vanilla JavaScript hardware-retail management system. It provides inventory, sales, procurement, payroll, ledger, JWT authentication, and role-based access control.

## Requirements

- Python 3.11 or newer
- MySQL 8 running locally on port `3306`
- Git

Install Python dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

Create a local `.env` file from `.env.example`, then set the MySQL credentials for your local server. The working `.env` file is ignored by Git.

## Run Locally

Create the database and application user in MySQL, or use an existing database with matching credentials. Then run:

```powershell
cd backend
alembic upgrade head
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The application is available at `http://127.0.0.1:8000/`.

On the first successful administrator login, the application creates or synchronizes the account configured by `ADMIN_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`. To provision it before logging in, you can optionally run `python -m bootstrap_admin` from the `backend` directory. Neither method inserts sample branches, departments, employees, products, customers, sales, purchase orders, payroll records, or ledger entries; business data must be entered through the application UI or API.

## Administrator

The administrator signs in using `ADMIN_NAME` or `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`; the application recognizes these credentials automatically, including when the login page is left on its default **Staff Member** option. No default login credentials are provided. From the dashboard, the administrator can provision employee accounts with a department and role using the employee management page; the application generates a temporary password for each account.

Employee sign-in accounts created by the System Administrator receive a randomly generated temporary password, shown once after account creation. Employees must change it on first sign-in; the default expiration is 24 hours and can be configured with `TEMP_PASSWORD_EXPIRY_HOURS` (1–168 hours). Passwords are stored only as bcrypt hashes. Staff sign-in verifies the selected department against the employee record, and repeated failed attempts temporarily lock the account. The System Administrator dashboard focuses on access management and audit/security signals; Owner / Executive accounts use the separate operational overview. System administrators receive system-management permissions only; operational permissions such as Finance or Payroll require an explicit role assignment.

Users with approval permissions can review and approve or reject pending purchase requisitions, purchase orders, and leave requests from the **Pending Approvals** page. The shared search field navigates only to workspaces available to the signed-in role; the date filter appears only on the dashboard.

## Architecture

```text
Browser
  |
  v
FastAPI + Uvicorn :8000
  |-- Static frontend files
  |-- JWT authentication and role checks
  |-- REST API and OpenAPI documentation
  |
  v
SQLAlchemy -> MySQL :3306
```

| Location | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI application and API routes |
| `backend/auth.py` | Password hashing, JWT creation, and authentication |
| `backend/models.py` | SQLAlchemy entities and role/status enums |
| `backend/schemas.py` | Pydantic request and response models |
| `backend/database.py` | Database engine and session dependency |
| `backend/bootstrap_admin.py` | Creates or updates the configured administrator |
| `backend/migrations/` | Alembic migrations |
| `frontend/` | Static application pages and browser modules |

## URLs

| Resource | URL |
| --- | --- |
| Frontend dashboard | http://127.0.0.1:8000/ |
| Health check | http://127.0.0.1:8000/health |
| Swagger UI | http://127.0.0.1:8000/docs |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json |
| ReDoc | http://127.0.0.1:8000/redoc |

## Database Changes

Apply existing migrations:

```powershell
cd backend
alembic upgrade head
```

After changing SQLAlchemy models, generate and review a migration:

```powershell
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Use Alembic for schema changes instead of manually altering tables.

Employee profile photos are stored in `backend/uploads/profile-photos`. JPG/JPEG, PNG, and WebP uploads are supported up to 5 MB; uploads are served through the authenticated profile-photo API. Apply migrations with `alembic upgrade head` before using employee photo uploads, and ensure the backend process can write to that directory. Kiconco Flavia's provided WebP image is bundled as a protected default profile photo under `backend/default-profile-photos`.

## Security

Never commit `.env`, passwords, API keys, or production secrets. The local `.env` is ignored by Git. Generate a signing key with `py -c "import secrets; print(secrets.token_urlsafe(48))"` and set it as `SECRET_KEY`; startup rejects missing, short, and placeholder keys. Set `COOKIE_SECURE=true` when served over HTTPS and configure `CORS_ALLOWED_ORIGINS` with only the exact trusted frontend origins. The optional `backend/seed.py` baseline also requires its own unique `SEED_DEFAULT_PASSWORD`; do not reuse the administrator password.

After upgrading, apply the token-revocation schema migration with `cd backend; alembic upgrade head`. Existing sessions are invalidated when a user logs out, has their password reset, or has their account status changed.
