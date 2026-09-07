# Hardware World

A full-stack management system for a hardware and construction-materials retail business — point-of-sale, procurement, HR/payroll, and accounting, built around a normalized (3NF) relational schema with role-based access control.

Built as a Database Management Systems group project at Makerere University, College of Computing and IT.

## What this is

Hardware World models a multi-branch hardware store chain with four departments — **HR**, **Procurement**, **Accounting**, and **Sales & Marketing** — each working from its own role-scoped dashboard. The system covers the full loop from a cashier ringing up a sale at the till, to a procurement officer restocking from a supplier, to an accountant seeing both sales and payroll land on a single ledger.

The relational schema (18 tables, fully normalized to 3NF) was derived from an Enhanced Entity Relationship Diagram (EERD) built for the business first — this repo implements that model, it doesn't design it from scratch. See `docs/schema.md` for how each table maps back to the logical model.

## Tech stack

- **Frontend:** Next.js (App Router, TypeScript), Tailwind CSS, shadcn/ui
- **Backend:** Supabase — Postgres, Auth, Row Level Security, auto-generated API
- **Database:** 18-relation 3NF schema with enforced specialization, weak/associative entities, and cross-department constraints
- **CI/CD:** Supabase GitHub integration (migrations auto-deploy to production on merge to `main`)

## Core features

- **Role-based dashboards** — Cashier, Procurement Officer, Accountant, HR Staff, and Branch Manager each see only what their role and branch permit, enforced at the database level via Postgres RLS, not just hidden UI
- **Point of sale** — line-item sales, live totals, optional customer lookup, atomic checkout
- **Procurement & inventory** — supplier catalogue, purchase orders with approval-limit enforcement, low-stock tracking
- **HR & payroll** — employee records per role (with role-specific fields), monthly payroll generation
- **Accounting ledger** — a single ledger fed by both sales (POS → Accounting) and payroll (HR → Accounting), giving accountants one place to see both
- **Multi-branch support** — every employee, sale, and department is scoped to a branch

## Database

18 relations, normalized to 3NF (verified via full UNF → 1NF → 2NF → 3NF walkthroughs — see the project's logical model document):

`BRANCH`, `DEPARTMENT`, `EMPLOYEE`, `CASHIER`, `PROCUREMENT_OFFICER`, `ACCOUNTANT`, `HR_STAFF`, `BRANCH_MANAGER`, `SUPPLIER`, `PURCHASE_ORDER`, `CATEGORY`, `PRODUCT`, `SUPPLY`, `CUSTOMER`, `SALE`, `SALE_ITEM`, `PAYROLL`, `LEDGER_ENTRY`

Notable modeling decisions:

- **EMPLOYEE specialization** (Cashier/Procurement Officer/Accountant/HR Staff/Branch Manager) is one-table-per-subtype, each sharing its primary key with `EMPLOYEE` as a foreign key.
- `SALE_ITEM` and `SUPPLY` are weak/associative entities with composite primary keys.
- `LEDGER_ENTRY` enforces, via a database `CHECK` constraint, that exactly one of `SaleID` / `PayrollID` is populated — matching its `SourceType`.

Full field-by-field data dictionary: `docs/schema.md`.

## Getting started

```bash
git clone https://github.com/mdavidjeremiah/DBMS-project.git
cd DBMS-project
npm install
```

Copy `.env.local.example` to `.env.local` and fill in your Supabase project's URL and anon key (Settings → API in the Supabase dashboard):

```bash
cp .env.local.example .env.local
npm run dev
```

Schema changes are managed as SQL migrations in `supabase/migrations/` and deploy automatically to the production database when merged to `main`, via the Supabase GitHub integration.

## Project roadmap

The build is sequenced as five GitHub issues, UI-first:

| # | Issue | Depends on |
|---|---|---|
| 1 | Project Scaffolding & Core UI Shell | — |
| 2 | Supabase Project & 3NF Database Schema | — (parallel with #1) |
| 3 | Authentication & Multi-User Role-Based Access Control | #1, #2 |
| 4 | Procurement & Inventory Management | #1, #2, #3 |
| 5 | Sales (POS), HR/Payroll, Accounting Ledger & Live Dashboard | #1, #2, #3, #4 |

## Team & contributions

| Member | Student No. | Reg. No. | Issue | Focus |
|---|---|---|---|---|
| Muwanguzi David Jeremiah | 2500728758 | 25/U/28758/PS | #1 | Project scaffolding, app shell, and reusable UI primitives (data table, modal, stat cards, badges) |
| Okuja Emmanuel Dila John | 2500728777 | 25/U/28777/PSA | #2 | Supabase project setup, 3NF database schema, seed data, TypeScript type generation<br>*(Project Manager)* |
| Akena Jonathan Ogaba | 2500728727 | 25/U/28727/PS | #3 | Authentication, role permission matrix, and Row Level Security policies |
| Mutebi Steven | 2500703479 | 25/U/03479/PSA | #4 | Procurement and inventory management: categories, products, suppliers, purchase orders |
| Ssemwogere Godwin | 2500703577 | 25/U/03577/PSA | #5 | Point of sale, HR/payroll, accounting ledger, and the live dashboard |

## Status

🚧 In progress — Issue #2 (database schema) is implemented and verified against the production Supabase project. See the Issues tab for current progress on the rest.