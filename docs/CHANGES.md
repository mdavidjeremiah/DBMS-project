# Stabilisation progress

Work is incomplete. This record distinguishes implemented changes from requirements still open.

## Implemented and checked

- Canonical procurement model names now map to the existing tables, with aliases declared on models instead of patched after class creation.
- Receipt, supplier invoice and supplier payment services use actual database columns. Receipt quantities feed InventoryBalance, shared with POS.
- Requisitions validate branch access; approval uses the service with state and separation checks. Empty direct purchase orders are rejected and direct auto-approval removed.
- POS requires an idempotency key, rejects duplicate product lines, uses a conditional stock decrement and handles duplicate-key races. Concurrent MySQL execution remains untested.
- Returns require manager permission, branch access and original-sale quantities. A sale can currently receive only one refund; further partial refunds require reconciliation. Full cumulative partial-return support remains open.
- Payroll rejects duplicate month runs, scopes staff to the preparer's branch and requires a separate approver. Month uniqueness is currently global and enforced in application code, not a database constraint.
- Audit IP forwarding is accepted only from TRUSTED_PROXIES.
- Failed request sessions explicitly roll back.
- Migration 0011 adds vw_inventory_position, vw_trial_balance, negative-stock triggers and stock_transaction_log. Trigger log records share the stock transaction and roll back with it.
- Migration 0005 no longer recreates a complete role-table set on fresh setup.
- Test credentials are generated; unsafe one-off database helpers now direct operators to migrations.

## Verification actually run

Python 3.13.13; application import and OpenAPI generation: passed (100 paths).
`python -m pytest backend/test_information_flow.py backend/test_project.py backend/tests -q --tb=short -W ignore`: 24 passed.
`node --test frontend/test_frontend.mjs`: 27 passed.
`alembic upgrade head` with APP_ENV=test and DATABASE_URL=sqlite://: passed from empty memory database through 0011.
`python -m compileall -q backend`: passed.
`git diff --check`: passed.

No live business database was migrated. MySQL trigger execution, InnoDB concurrency, schema drift, recovery/binary-log settings and deployment are not verified. The pre-existing application audit log exists. The new stock log is an application data-change log; it does not replace MySQL redo, undo or binary logs.

## Findings register

| IDs | Status | Remaining work |
| --- | --- | --- |
| C1 | Partly fixed | Import and procurement service tests pass; legacy routes still contain missing model references |
| C2, H7, M6, M12 | Not fixed | Consolidate duplicate stock/role/ledger systems and route surfaces; canonical account seed |
| C3 | Partly fixed | Generated test credentials and deprecated unsafe helpers; full secret scanner/history review and owner rotation outstanding |
| C4 | Partly fixed | Empty SQLite migration passes; frozen baseline and MySQL drift test outstanding |
| C5 | Partly fixed | Manager-only, scoped and quantity-limited single return; cumulative partial returns and accounting reversal outstanding |
| C6 | Partly fixed | Opening-stock branch checks added; seeded permissions and missing UI outstanding |
| H1, H2, H4, H5, H8, H9 | Not fixed | XSS, authentication, static exposure, permission and scope hardening remain |
| H3 | Fixed | Trusted proxy check implemented; full security test coverage remains |
| H6 | Partly fixed | Conditional decrement and key race handling added; MySQL concurrency test and session-scoped key required |
| H10 | Partly fixed | Duplicate month/state and separate approval checks; branch uniqueness migration and payment step required |
| H11 | Partly fixed | Pending review blocks reopening; manager review API and UI outstanding |
| H12 | Partly fixed | Empty orders rejected, auto-approval removed; route consolidation and universal approval limits outstanding |
| M1, M2, M3, M4, M5, M7, M8, M9, M10, M11, L1 | Partly fixed or open | Complete performance, security, dependency, test isolation, UI, scope and validation requirements from supplied documents |

## Open decisions

Returns are restricted to sales managers pending a configurable approval threshold. Payroll currently blocks a second run for a month across the system; branch-scoped uniqueness needs a data migration. Neither decision should be treated as the final business policy.

Rotate SECRET_KEY, the administrator password and database password identified in the supplied review. Old shared copies and Git history are outside the source cleanup performed here.
