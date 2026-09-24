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
python -m bootstrap_admin
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The application is available at `http://127.0.0.1:8000/`.

The startup sequence creates or updates only the administrator configured by `ADMIN_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`. It does not insert sample branches, departments, employees, products, customers, sales, purchase orders, payroll records, or ledger entries. All business data must be entered through the application UI or API.

## Administrator

The local administrator is configured in `.env`. The current development credentials are:

- Username: `okuja`
- Password: `backendiskey@28777`
- Email: `okuja@hardwareworld.local`
- Role: `Admin`

The administrator can create other users through the protected registration endpoint. Change the local password before sharing or deploying the application.

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

## Security

Never commit `.env`, passwords, API keys, or production secrets. The local `.env` is ignored by Git. Replace the development `SECRET_KEY` and administrator password outside local development.
