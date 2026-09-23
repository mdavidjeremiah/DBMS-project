# Hardware World

Hardware World is a hardware-retail management system built for a DBMS project. It combines a FastAPI backend, a vanilla HTML/CSS/JavaScript frontend, SQLAlchemy models, MySQL persistence, JWT authentication, role-based access control, and a seeded local development database.

## Current Status

The active application is the Dockerized FastAPI/MySQL implementation in this repository. The following milestones are complete:

- Relational SQLAlchemy model covering branches, departments, employees, roles, products, categories, suppliers, purchase orders, customers, sales, payroll, and ledger entries.
- Alembic baseline migration and repeatable container startup migrations.
- MySQL 8 Docker Compose environment with health checks and persistent local storage.
- Seed data for branches, departments, users, catalogue records, sales, purchase orders, and ledger entries.
- JWT login with name-or-email lookup and department-aware staff login.
- Six application roles: Cashier, Procurement Officer, Accountant, HR Staff, Branch Manager, and Admin.
- API-level RBAC checks for protected read and write operations.
- Static frontend pages for the dashboard, products, categories, suppliers, purchase orders, sales, employees, payroll, ledger, settings, login, and sign-up.
- OpenAPI documentation at `/docs`, with Swagger UI assets served locally so documentation works without external CDN access.

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
SQLAlchemy
  |
  v
MySQL 8 :3306 inside Docker (host port :3307)
```

| Location | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI application, API routes, and Swagger configuration |
| `backend/auth.py` | Password hashing, JWT creation, and current-user dependency |
| `backend/models.py` | SQLAlchemy entities and role/status enums |
| `backend/schemas.py` | Pydantic request and response models |
| `backend/database.py` | Database engine and session dependency |
| `backend/migrations/` | Alembic configuration and reviewed migrations |
| `backend/seed.py` | Local development seed data |
| `backend/swagger-ui/` | Local Swagger UI JavaScript and CSS assets |
| `frontend/` | Static application pages and browser modules |
| `docker-compose.yml` | MySQL and API services |
| `entrypoint.sh` | Database wait, migration, seed, and Uvicorn startup sequence |

## Requirements

For the recommended workflow, install:

- Docker Desktop with Docker Compose support
- Git

Verify Docker:

```bash
docker --version
docker compose version
```

No local Python, MySQL, or Node.js installation is required when using Docker Compose.

## Configuration

Copy the environment template into a local, uncommitted `.env` file at the repository root:

Linux/macOS:
```bash
cp .env.example .env
```
Windows PowerShell:

```powershell
Copy-Item .env.example .env
```
The default local settings use:
```env
MYSQL_DATABASE=hardware_world
MYSQL_USER=hw_user
MYSQL_PASSWORD=hw_password
MYSQL_ROOT_PASSWORD=hw_root_password
APP_HOST=0.0.0.0
APP_PORT=8000
```

Docker Compose converts these values into the API's internal connection string. The API connects to MySQL at `db:3306` inside the Compose network. Do not use `localhost` for the API's container-to-database connection.

Never commit `.env`, passwords, API keys, or production secrets.

## Run With Docker
Build and start the complete stack:
```bash
docker compose up -d --build
```

Watch API startup:

```bash
docker compose logs -f api
```

The API container:

1. Waits for the MySQL health check.
2. Runs `alembic upgrade head`.
3. Seeds the database when the admin account does not exist.
4. Starts Uvicorn with reload enabled.

Open the application:

| Resource | URL |
| --- | --- |
| Frontend dashboard | http://localhost:8000/ |
| Health check | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| ReDoc | http://localhost:8000/redoc |

Swagger UI is served from `backend/swagger-ui/`; it does not require access to jsDelivr or another external CDN.

## Demo Accounts

The seed script creates local development accounts:

| Account | Login | Password | Role |
| --- | --- | --- | --- |
| Akena | `akena@hardwareworld.com` or `Akena` | `adminpassword` | Admin |
| Sarah Nakato | `sarah@hardwareworld.com` or `Sarah Nakato` | `staff123` | Cashier |
| John Kato | `john@hardwareworld.com` or `John Kato` | `staff123` | Procurement Officer |
| Grace Apio | `grace@hardwareworld.com` or `Grace Apio` | `staff123` | Accountant |
| Moses Opolot | `moses@hardwareworld.com` or `Moses Opolot` | `staff123` | HR Staff |
| Brian Mukasa | `brian@hardwareworld.com` or `Brian Mukasa` | `staff123` | Branch Manager |

These credentials are for local testing only. Replace them and the default `SECRET_KEY` before using the application outside a private development environment.

## Authentication and Access Control

`POST /login` accepts JSON or form data with `username`, `password`, `department`, and `login_type`. Successful login returns a bearer token. The frontend stores the token in a same-origin cookie and sends it as an `Authorization: Bearer` header for protected API calls.

The API enforces role checks in route dependencies and handler logic:

| Role | Main responsibility |
| --- | --- |
| Cashier | Sales and point-of-sale operations |
| Procurement Officer | Products, categories, suppliers, and purchase orders |
| Accountant | Ledger, sales visibility, and payroll visibility |
| HR Staff | Employees, departments, and payroll |
| Branch Manager | Branch-level operational oversight |
| Admin | System-wide administration |

Staff login also verifies the selected department against the employee's assigned department. The complete role and table matrix is documented in [PERMISSION_MATRIX.md](PERMISSION_MATRIX.md).

## API Endpoints

All endpoints appear in Swagger UI and the generated OpenAPI document.

| Area | Endpoints |
| --- | --- |
| System | `GET /health`, `GET /` |
| Authentication | `POST /login`, `POST /register`, `GET /users/me` |
| Organisation | `GET /departments/public`, `GET/POST /branches`, `GET /departments`, `GET/POST /employees` |
| Catalogue | `GET /categories`, `POST /categories`, `GET /products`, `POST /products`, `GET /suppliers`, `POST /suppliers` |
| Operations | `GET/POST /purchase-orders`, `GET/POST /payroll`, `GET/POST /sales`, `GET/POST /ledger` |

`/departments/public`, `/health`, `/`, and `/login` are usable without a bearer token. Most business endpoints require authentication, and write operations apply additional role checks.

## Database Migrations

Apply the current migration manually when needed:

```bash
docker compose exec api alembic upgrade head
```

Inspect migration state:

```bash
docker compose exec api alembic current
docker compose exec api alembic history
```

After changing SQLAlchemy models, generate and review a migration:

```bash
docker compose exec api alembic revision --autogenerate -m "describe the change"
docker compose exec api alembic upgrade head
```

`0001_initial_schema.py` is the non-destructive baseline for the current model metadata. Review generated migrations for renames, data transformations, constraints, indexes, and destructive operations before committing them.

## MySQL Workbench

Connect from the host using:

- Host: `127.0.0.1`
- Port: `3307`
- User: the `MYSQL_USER` value from `.env`
- Password: the `MYSQL_PASSWORD` value from `.env`
- Schema: the `MYSQL_DATABASE` value from `.env`

Example:

```sql
USE hardware_world;
SELECT * FROM employee;
```

Use Alembic for schema changes instead of manually creating or altering tables.

## Common Commands

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f db
docker compose exec api alembic current
docker compose exec api alembic history
docker compose down
```

`docker compose down` removes containers but preserves the named MySQL volume. To intentionally delete all local database data:

```bash
docker compose down -v
docker compose up -d --build
```

Do not run `down -v` unless losing the local database is acceptable.

## Verification Checklist

1. Run `docker compose up -d --build`.
2. Confirm `docker compose ps` shows MySQL as healthy and the API as running.
3. Open `/health` and confirm it returns `{"status":"ok"}`.
4. Open `/docs` and confirm the grouped endpoints are visible.
5. Sign in with a seeded account.
6. Confirm `/users/me` returns the authenticated profile.
7. Verify role-appropriate frontend navigation and API access.
8. Confirm database tables and seed records in MySQL Workbench.

## Troubleshooting

- **Docker cannot connect:** Start Docker Desktop and retry `docker compose up -d --build`.
- **API cannot connect to MySQL:** Check `docker compose ps`, wait for the `db` health check, and ensure the API connection uses `@db:3306`.
- **API exits during startup:** Run `docker compose logs api`; migration and seed errors are intentionally surfaced.
- **Swagger is blank:** Rebuild the image with `docker compose up -d --build`. Swagger assets are expected at `/swagger-ui/swagger-ui-bundle.js` and `/swagger-ui/swagger-ui.css`.
- **Port 8000 is busy:** Change only the host side, for example `8001:8000`, then use `http://localhost:8001`.
- **Port 3307 is busy:** Change only the host side, for example `3308:3306`; keep the API's internal port at `3306`.
- **Login fails after changing credentials:** MySQL volumes retain their original initialization credentials. Reset the local volume intentionally with `docker compose down -v`, then rebuild.
- **Frontend shows authorization errors:** Sign in first and verify the browser has the `hw_access_token` cookie. Confirm the account role and department selection.

## Project Documentation

- [PERMISSION_MATRIX.md](PERMISSION_MATRIX.md): current role, table, and operation matrix.
- [ISSUE_3_IMPLEMENTATION.md](ISSUE_3_IMPLEMENTATION.md): historical authentication and access-control implementation notes.
- [ISSUE_3_QUICK_START.md](ISSUE_3_QUICK_START.md): historical Issue 3 testing notes.
- [docker-compose.yml](docker-compose.yml): local service topology and environment wiring.

The Issue 3 documents contain material from an earlier Supabase/Next.js direction and are retained as project history. They are not the startup instructions for the current FastAPI/MySQL application; use this README and the source files under `backend/` and `frontend/` as the active implementation reference.

## Security Notes

- Replace all example passwords and `SECRET_KEY` values before shared or production use.
- Do not expose MySQL's host port publicly.
- Do not commit `.env`, database files, generated Python caches, or credentials.
- Review every migration before applying it to a shared database.
- `docker compose down -v` permanently deletes the local MySQL volume.
