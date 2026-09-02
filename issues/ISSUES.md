# Hardware World — GitHub Issues (Sprint 1 Roadmap)

Five issues to open against the repo, sequenced UI-first as requested. They're written to be pasted almost verbatim into GitHub (title as the issue title, everything under it as the body). Each one assumes **Next.js (App Router, TypeScript)** on the frontend and **Supabase (Postgres + Auth + Row Level Security)** on the backend, and each one is scoped against the 18 relations in the *Hardware World Logical Data Model* doc.

**Suggested labels to create first:** `frontend`, `backend`, `database`, `auth`, `rbac`, `ui`, `epic`, `good-first-issue`

**Dependency chain:** #1 has no dependencies and can start immediately. #2 can run in parallel with #1. #3 needs both #1 and #2 merged. #4 and #5 both build on #3.

---

## Issue 1 — Project Scaffolding & Core UI Shell

**Labels:** `frontend`, `ui`, `epic`
**Depends on:** none — this is the starting point

### Context
Before any feature work starts, the team needs one shared shell and one shared set of UI primitives to build on — otherwise every feature reinvents its own table, modal, and card styling. The attached reference screenshots (a project-management tool) show the interaction patterns we want to borrow for Hardware World: a branch/workspace switcher in the sidebar header, a persistent left nav, a topbar with search + light/dark toggle, dashboard stat cards backed by an "overview" list and a "my items" side panel, filterable data tables, and a consistent modal pattern for create/edit forms (title → labeled fields → Cancel / primary-action buttons in the footer).

This issue produces that shell wired to **mock data only** — no Supabase calls yet. That's deliberate: it lets frontend work start immediately without waiting on the schema in Issue #2.

### Objectives
- Stand up the Next.js app with TypeScript, Tailwind, and a component library.
- Build the persistent app shell (sidebar + topbar) and wire up client-side routing between placeholder pages.
- Build the reusable primitives every later issue will consume: stat cards, a generic filterable/sortable data table, a modal/dialog wrapper, and status/role badges.
- Implement the light/dark theme toggle exactly as shown in the reference screenshots.

### Requirements
- [ ] `create-next-app` with App Router + TypeScript, ESLint + Prettier configured
- [ ] Tailwind CSS installed; component library added (shadcn/ui recommended — it gives you the dialog, dropdown, select, date-picker, and table primitives you'll need for every later issue with minimal extra work)
- [ ] `AppShell` layout component:
  - Collapsible left sidebar with nav sections: Dashboard, Products, Categories, Suppliers, Purchase Orders, Sales (POS), Employees, Payroll, Ledger, Settings
  - Branch/workspace switcher in the sidebar header (static list for now — becomes live in Issue #5)
  - Topbar: global search input, theme toggle, user avatar/menu placeholder
- [ ] Dashboard page skeleton: 4 stat cards in a row (placeholders: e.g. "Sales Today", "Low Stock Items", "Pending POs", "Overdue Payroll"), an "overview" panel with a couple of progress-style list rows, and a "My Tasks"-style side panel — all on mock data
- [ ] `DataTable` component: column sorting, a row of filter dropdowns above the table (mirrors "All Statuses / All Types / All Priorities / All Assignees"), pagination, empty/loading states
- [ ] `Modal` component matching the reference "Create New X" pattern: title, form body, Cancel + primary-action footer buttons
- [ ] `Badge` component with color variants for status (Pending/Approved/Received/Cancelled), and role (Cashier/Procurement Officer/Accountant/HR Staff/Branch Manager/Admin)
- [ ] Dark/light theme toggle, persisted across reloads
- [ ] Responsive behavior: sidebar collapses to icon-only or a drawer below tablet width; tables scroll horizontally instead of breaking layout

### Acceptance Criteria
- `npm run dev` renders every placeholder page inside the shared shell with working navigation
- Theme toggle switches instantly and survives a page reload
- `DataTable`, `Modal`, `StatCard`, and `Badge` are used on at least the Dashboard and one list page as proof they're genuinely reusable (not one-off styled per page)
- No network/Supabase calls exist anywhere in this issue's code — everything is mock/static data
- Keyboard users can open, tab through, and close a modal without a mouse

---

## Issue 2 — Supabase Project & 3NF Database Schema

**Labels:** `backend`, `database`
**Depends on:** none (can run in parallel with #1)

### Context
The *Hardware World Logical Data Model* document already specifies the full, normalized (3NF) schema — 18 relations, fully mapped with primary keys, foreign keys, types, and nullability. This issue is about implementing that schema exactly as specified, not redesigning it. Two things need special care because they don't map to plain tables 1:1: the `EMPLOYEE` specialization (one row in `EMPLOYEE` plus one row in the matching subtype table, sharing the same PK/FK) and the weak/associative entities (`SALE_ITEM`, `SUPPLY`) which use composite primary keys.

### Objectives
- Stand up a Supabase project and local dev workflow (Supabase CLI + Docker).
- Write migrations that create all 18 relations from the data dictionary, with correct keys, types, and constraints.
- Seed enough sample data to exercise every relationship in the model.
- Generate TypeScript types from the schema so the frontend gets compile-time safety.

### Requirements
- [ ] `supabase init`, local stack running via Docker; project linked to a hosted Supabase project for staging
- [ ] Migration(s) creating all 18 relations: `BRANCH`, `DEPARTMENT`, `EMPLOYEE`, `CASHIER`, `PROCUREMENT_OFFICER`, `ACCOUNTANT`, `HR_STAFF`, `BRANCH_MANAGER`, `SUPPLIER`, `PURCHASE_ORDER`, `CATEGORY`, `PRODUCT`, `SUPPLY`, `CUSTOMER`, `SALE`, `SALE_ITEM`, `PAYROLL`, `LEDGER_ENTRY`
- [ ] `EMPLOYEE` specialization implemented as one-table-per-subtype: each subtype table's PK is also a FK back to `EMPLOYEE(EmployeeID)`
- [ ] Composite primary keys correctly declared on `SUPPLY (SupplierID, ItemID)` and `SALE_ITEM (SaleID, ItemID)`
- [ ] Self-referencing FK `SupervisorID` on `EMPLOYEE`, and the 1:1 `BRANCH ↔ BRANCH_MANAGER` relationship via `ManagerEmployeeID` on `BRANCH`
- [ ] Enum/CHECK constraints where the data dictionary specifies a fixed set of values: `EMPLOYEE.RoleType`, `PURCHASE_ORDER.Status` (Pending/Approved/Received/Cancelled), `LEDGER_ENTRY.SourceType` (SALE/PAYROLL)
- [ ] `LEDGER_ENTRY` constraint enforcing that exactly one of `SaleID` / `PayrollID` is populated, matching its `SourceType`
- [ ] Indexes on all FK columns plus commonly-filtered columns (`Status`, `CategoryID`, `BranchID`)
- [ ] Seed script covering: a branch with an assigned manager, at least one employee of every subtype, a supplier supplying multiple products, a purchase order, a sale with multiple sale items, a payroll record, and the corresponding ledger entries
- [ ] `supabase gen types typescript` wired into a package script; generated types committed or generated in CI
- [ ] Schema/ERD reference added to `/docs` linking back to the source logical model document

### Acceptance Criteria
- Running migrations against a clean database produces all 18 tables matching the data dictionary field-for-field (names, types, nullability, keys)
- Seed script runs cleanly and populates data that touches every FK relationship in the model
- Generated TypeScript types compile and are importable from the Next.js app
- A second engineer can review the migration files against Section 2 of the logical model doc and sign off with no discrepancies

---

## Issue 3 — Authentication & Multi-User Role-Based Access Control

**Labels:** `auth`, `rbac`, `backend`, `frontend`
**Depends on:** #1 (modal/shell components), #2 (schema must exist)

### Context
This is the core "multi-user roles" requirement. `EMPLOYEE.RoleType` already gives us the roles (Cashier, Procurement Officer, Accountant, HR Staff, Branch Manager) — this issue wires Supabase Auth to that model, adds an Admin/Owner role for system-wide access, and enforces permissions at the database level (RLS), not just by hiding buttons in the UI. The reference screenshots' **"Invite Team Member"** modal (email + role dropdown) and **"Add Member to Project"** modal map directly onto inviting a new employee with a role and attaching an existing employee to a branch/department.

### Objectives
- Wire Supabase Auth (email/password) into Next.js with session-aware middleware.
- Link `auth.users` to `EMPLOYEE` records one-to-one.
- Define and enforce a role permission matrix via Postgres RLS — every table, every role.
- Build the invite flow and role-guarded navigation.

### Requirements
- [ ] Supabase Auth configured (email/password minimum; magic link optional)
- [ ] `@supabase/ssr` middleware for session handling across server components/route handlers
- [ ] Migration adding `AuthUserID (uuid)` to `EMPLOYEE`, referencing `auth.users(id)`
- [ ] Role enum finalized: `Cashier`, `Procurement Officer`, `Accountant`, `HR Staff`, `Branch Manager`, `Admin`
- [ ] Written permission matrix (role × table × read/write) reviewed before RLS is written — e.g. Cashier can insert `SALE`/`SALE_ITEM` only for their own `BranchID`; Procurement Officer can manage `PURCHASE_ORDER` but only approve up to their own `ApprovalLimit`; HR Staff manages `EMPLOYEE`/`PAYROLL`; Accountant manages `LEDGER_ENTRY`; Branch Manager has full read across their own branch; Admin is unrestricted
- [ ] RLS policies implementing that matrix on all 18 tables
- [ ] Sign in / sign up / forgot-password pages
- [ ] "Invite Team Member" modal (email + role select) — creates a pending invite, sends the Supabase invite email, and on acceptance creates the linked `EMPLOYEE` row (+ correct subtype row)
- [ ] "Add Member to Branch/Department" modal for attaching an existing employee
- [ ] Route guard (middleware or layout-level check) so a role can't reach a page it doesn't have access to via direct URL — not just a hidden nav item
- [ ] Topbar user menu shows current role badge and a sign-out action

### Acceptance Criteria
- Logging in as each of the six roles shows a nav/UI correctly scoped to that role's permissions
- RLS is verified by attempting a disallowed operation directly against the API (not just clicking around the UI) and confirming it's rejected
- The invite flow, end to end, produces a working login for the invited person with the correct role and subtype row already in place
- No page is reachable by pasting its URL directly while logged in as an unauthorized role

---

## Issue 4 — Procurement & Inventory Management

**Labels:** `frontend`, `backend`
**Depends on:** #1, #2, #3

### Context
This covers the buy-side of the business: what we stock, who we buy it from, and how restocking gets approved. It's the first issue where the `DataTable`/`Modal` primitives from Issue #1 get connected to real, RLS-protected Supabase data instead of mock data.

### Objectives
- CRUD for `CATEGORY`, `PRODUCT`, and `SUPPLIER`.
- A management screen for the `SUPPLY` associative entity (which suppliers provide which products, at what cost and lead time).
- A `PURCHASE_ORDER` workflow with status transitions and approval-limit enforcement.
- A live low-stock indicator feeding back into the Dashboard built in Issue #1.

### Requirements
- [ ] Category CRUD using the `DataTable` + `Modal` components
- [ ] Product CRUD: `ItemName`, `Description`, `UnitPrice`, `ReorderLevel`, `CategoryID` select; low-stock badge when on-hand quantity ≤ `ReorderLevel`
- [ ] Supplier CRUD
- [ ] Supply management UI: assign one or more products to a supplier with `CostPrice` and `LeadTimeDays`
- [ ] Purchase Order creation modal: supplier select, add-line-item flow for products + quantities, auto-calculated total
- [ ] PO status transitions (Pending → Approved → Received → Cancelled), with the "Approved" transition rejected server-side if it would exceed the acting Procurement Officer's `ApprovalLimit`
- [ ] PO list view with status filter row (mirrors the reference "All Statuses" filter pattern) and a detail view showing line items
- [ ] All data access goes through Supabase server-side (route handlers or server actions) using the authenticated session, so RLS from Issue #3 is actually enforced — no client-side-only permission checks
- [ ] Loading/empty/error states on every list

### Acceptance Criteria
- A Procurement Officer can create and manage purchase orders, but cannot approve one above their `ApprovalLimit` — enforced by the API/RLS, confirmed by trying it directly
- Low-stock products show a badge in the product list and feed a real count into the Dashboard's stat card
- Every CRUD action correctly respects the role/branch restrictions from Issue #3
- Table sorting/filtering works against live data with reasonable performance on a few hundred seeded rows

---

## Issue 5 — Sales (POS), HR/Payroll, Accounting Ledger & Live Dashboard

**Labels:** `frontend`, `backend`
**Depends on:** #1, #2, #3, #4

### Context
This is the sell-side and back-office half of the system, and it's the issue that finally replaces every mock/placeholder from Issue #1 with real, end-to-end data — closing the loop from "cashier rings up a sale" to "accountant sees it on the ledger."

### Objectives
- A point-of-sale screen for cashiers.
- Branch / Department / Employee management, including the subtype-specific fields per role.
- Payroll generation and history.
- A read-focused Ledger view.
- A Dashboard wired to real, branch-scoped aggregates.

### Requirements
- [ ] POS screen: search/add product lines, adjust quantity, live-calculated total, optional inline customer lookup/create, checkout creates the `SALE` + `SALE_ITEM` rows in one transaction
- [ ] Branch CRUD, including assigning `ManagerEmployeeID`
- [ ] Department CRUD, scoped to a branch
- [ ] Employee CRUD showing subtype-specific fields conditionally based on `RoleType`: `POS_TerminalID` (Cashier), `ApprovalLimit` (Procurement Officer), `CertificationNumber` (Accountant), `HR_Role` (HR Staff), `ManagementLevel` (Branch Manager); includes a `SupervisorID` picker
- [ ] Payroll generation form (per employee, per month: `GrossPay`, `Deductions`, auto-computed `NetPay`) plus a history table
- [ ] `LEDGER_ENTRY` table view, filterable by `SourceType`, with a drill-through link back to the originating Sale or Payroll record
- [ ] Dashboard stat cards and overview panel from Issue #1 wired to real queries: today's sales total, pending PO count, low-stock count, overdue payroll — all scoped to the logged-in user's branch (or all branches for Admin)
- [ ] An end-to-end smoke-test checklist committed to `/docs`: invite an employee → assign a role → cashier completes a sale → ledger entry appears → accountant can see it

### Acceptance Criteria
- A logged-in Cashier can complete a full sale and see it correctly reflected in `SALE`/`SALE_ITEM` (and `LEDGER_ENTRY`, if that's implemented via app logic in this issue rather than a DB trigger)
- HR Staff can create an employee of any subtype with the right conditional fields, and the record is correctly joinable back to `EMPLOYEE`
- Dashboard numbers are correct and properly branch-scoped per the logged-in user
- By the end of this issue, all 18 relations in the logical model have at least one real, UI-driven read or write path
