# Connection and action audit

## Scope and evidence

Reviewed the static HTML entry points, main page dispatcher, page renderers, shared dialogs, POS, shell controls, sidebar, API request helper, grouped API routes, legacy procurement routes and transaction services. Verification used isolated SQLite sessions; no business database was changed. Browser interaction and live MySQL behaviour remain unverified.

## Gaps repaired

| Area | Gap | Result |
| --- | --- | --- |
| Procurement | UI creation used a different route from the list and legacy invoice routes referenced missing journal models | PO UI posts to /api/purchase-orders; legacy PO and supplier writes delegate to shared implementations |
| PO creation | Approved requisition had no path into canonical PO lines | Canonical creation can load approved requisition lines, validates branch/products, rejects duplicate orders |
| Stock | Legacy product list read another inventory family | Product stock now reads InventoryBalance |
| Daily operations | No screens for services already implemented | Operations page offers opening stock, requisitions, receipts, supplier invoices/payments, payroll prepare/approve, till close/review, stock adjustment/transfer, returns, attendance, leave and customer payments |
| Till review | Pending variance could block further work with no review endpoint | Manager review validates branch, pending status and a different reviewer, then audits closure |
| POS access | UI used fixed role names instead of assigned permissions | Sell controls follow sales:pos |
| Unknown roles | Sidebar defaulted to administrator layout | Unknown roles use empty navigation; operational links require permissions |
| Transfers | Same source/destination and missing warehouse access checks | Both warehouses checked and same-warehouse transfers rejected |
| Attendance and leave | Foreign employee and invalid date ranges could be saved | Employee existence, branch and date order checked |
| Form feedback | Pydantic validation details could display as an unhelpful object | API helper formats field errors |
| Display safety | Some department/branch names and errors were interpolated unsafely | Those labels/errors are escaped |
| POS retry | Service mutated caller key and could prefix it again | Service copies the payload before scoping the key |
| Settings | Unverified security badges implied a completed audit | Text now describes session and assigned permissions |

Each Operations button opens a form, posts to a real route, displays an error on failure, refreshes its read model on success and reports the returned record. Dropdowns use scoped saved records for products, warehouses, orders, receipts, invoices, payroll and tills. Lookup lists are capped at 200; record search/pagination remains needed for larger deployments. Attendance, leave, returns and customer payments still require numeric employee/sale/customer references. Forms currently submit one product line at a time. No claim of fully polished multi-line operational UX is made.

## Checks run

- Python compilation: passed.
- pytest backend/test_information_flow.py backend/test_project.py backend/tests: 27 passed.
- node --test frontend/test_frontend.mjs: 27 passed.
- node --check frontend/assets/js/operations.js: passed.
- git diff --check: passed.

New checks verify Operations form URLs and methods against generated OpenAPI, deny unauthorised till review and ensure an account with no operational permission receives no workflow records. The procurement service integration test verifies stock receipt, invoice and payment. Existing tests cover account provisioning, organisation controls, approval actions, stock adjustments and frontend wiring. These are automated source/API checks, not a browser click-through of every new form.

## Outstanding gaps

The earlier CHANGES.md findings remain open unless explicitly repaired above. In particular: duplicate role and stock tables; legacy inventory-balance reads; broad branch scoping across all reports/lists; seeded permissions; full cumulative partial refunds; canonical accounting accounts; payroll payment and branch/month uniqueness; live MySQL concurrency; static-file exposure; reset-token authentication; frozen migration baseline; backup/restore verification; and broader security/performance tests. Operations forms expose existing permission requirements and do not grant missing permissions. The requested complete system-wide verification is not yet achieved.


## Latest completion evidence

The core purchasing-to-sale flow now passes an API integration test with SQLite foreign keys enabled: requisition, separate approval, PO, separate approval, receipt, POS sale, sale retry, till closure, invoice and payment. Stock decreases once and every journal balances. Payroll payment clears payslips and rejects repeated payment. Migration 0012 inserts missing account codes, preserving existing definitions; existing accounts still need review on a historical database.

32 selected backend tests and 27 frontend tests pass. Backend selection: backend/test_information_flow.py backend/test_project.py backend/tests. Not all historical script-style tests have been converted. Fresh isolated SQLite upgrade through 0012 passes. Catalogue preview rolls back, first apply adds 200 products in 20 categories, and second apply adds zero and skips 200. No stock balances are invented. Product pricing/activation is tested.

The owner requested importing later. No live database was changed; the CSV and importer are ready. MySQL integration, browser click-through and the broader security/consolidation findings above remain open or unverified. Core workflow completion does not establish completion of those separate findings.


## Browser and UI verification before branch push

Operations now uses branch-scoped employee, receipt and customer selectors; receiving filters products to the selected purchase order and fills remaining quantity and approved cost. Product pricing fills existing values. Empty prerequisites are explained beside disabled actions. Task layout adapts to narrow screens and successful saves show readable confirmation. Failed page loads offer retry. Employee directory access requires an explicit permission, and non-admin directory reads are branch-scoped.

32 backend tests and 27 frontend tests pass after these changes. An Edge browser check used the real app and an isolated in-memory database: requisition created through the form was returned by the API, prices filled from saved data, desktop/mobile screenshots were inspected, mobile content did not overflow and no page errors occurred. This browser check covers those actions, not every role/form combination.

Reproduce the browser check by starting `python backend/tests/browser_server.py` from the project root, then running `node tests/browser/workflow.cjs` with Playwright installed and Edge available. Set HW_PLAYWRIGHT_MODULE to an absolute Playwright module path if it is outside node_modules. This test app supplies synthetic identity and data and listens on localhost:8876; it must never be used as a production server. Screenshots are written to .codex-review, which is ignored by Git.

Live MySQL validation and the unresolved findings recorded earlier remain outside this verification. Catalogue import is intentionally left for the owner to run later.
