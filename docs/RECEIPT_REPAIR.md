# Receipt and item dropdown repair

The supplied trace reports MySQL error 1054 when inserting customer.email, followed by error 1091 when a downgrade tried to drop that already-missing column. The model includes email but the existing database does not. Downgrading is not the repair.

## Apply locally

Stop the application, activate its Python environment and run from backend:

```powershell
python -m alembic upgrade head
```

Restart the server and reload sales.html. Upgrade d2934db5301e now adds email only when missing; revision 0013 also repairs a missing column when an old revision was already stamped. Existing customer records and email data are preserved. Do not run downgrade or manually stamp past a failing migration. The application now returns an actionable schema-update message instead of an opaque database error.

## Receipt processing

Only active, priced products with positive stock in the selected till warehouse are selectable. Zero stock is not manufactured or pulled from another warehouse. Dark/light native controls use readable foreground/background colours. Cart quantities respect warehouse stock, including fractional remaining stock. Receipt preview hides the cart and commits no sale. Confirm uses a frozen cart snapshot; Edit is disabled while saving. The completed receipt uses committed server line prices/quantities/totals, and shows Print/New sale before reopening the cart.

The existing conditional inventory UPDATE is retained: it subtracts only when sufficient stock remains and verifies rowcount. Till selection and closing now use SELECT FOR UPDATE; till opening locks the employee to serialize session creation; credit checks lock the credit account. Stock row updates, movements, sale lines, payments, journals and business audit events remain within the sale transaction. Retry responses include the same authoritative receipt. The browser retains an uncertain checkout key and refuses to reuse it for a different payload.

## Database triggers

The existing stock_quality_insert/update triggers reject negative available/reserved balances. stock_log_insert/update write before/after quantities inside the same transaction. Repair revision 0013 checks for these triggers and installs missing ones without replacing existing triggers or erasing the change log. CREATE TRIGGER privileges are required on MySQL. These change logs do not replace MySQL recovery or binary logs.

## Evidence

- 41 backend tests passed, including the CSV backup tests pulled from the branch.
- 27 frontend tests passed.
- Two competing cashiers selling the final unit produce exactly one sale, zero remaining stock and one movement in the SQLite concurrency test.
- Tests cover email missing/already present, repeat upgrades and non-destructive downgrade, missing trigger repair, and negative-stock rejection.
- Fresh SQLite migration from empty database through 0013 passed.
- Real Edge browser check passed against the application and an isolated test database: open till, readable stock selector, preview with no write, confirmed receipt/customer/stock agreement, hidden cart during preview/completion, desktop/mobile fit, no page errors.
- Reproduce browser test from project root with Playwright and Edge installed: `node tests/browser/run_receipt.cjs`. Set HW_TEST_PYTHON to the virtual environment's Python executable if needed; set HW_PLAYWRIGHT_MODULE if Playwright is installed outside node_modules. This starts and stops a localhost test server with synthetic data and authentication, never the business database.

Physical MySQL execution was not available in this checkout because no connection configuration was supplied. MySQL trigger/locking statements are implemented, but the server-specific concurrency result remains to be confirmed locally after upgrading. Your live data was not modified.
