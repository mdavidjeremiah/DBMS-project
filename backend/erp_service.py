from __future__ import annotations
"""Hardware World ERP Core Service Workflows.

Implements all transaction-linked business workflows:
- POS Sale transaction with stock deduction, payment, idempotency, and finance journals
- Cashier Session management with float and variance tracking
- Procure-to-pay workflow: Requisition -> Approval -> PO -> GRN -> 3-way matching -> Payment
- Customer Credit accounts and debt settlements
- HR Payroll generation, approval, finance posting, and payslip isolation
- Physical stocktakes, shrinkage, and stock adjustments
"""

from erp_service_support import require_branch_access, require_warehouse_access
from erp_pos_service import close_cashier_session, open_cashier_session, process_pos_sale
from erp_procurement_service import (
    create_goods_received_note,
    process_supplier_invoice,
    record_supplier_payment,
)
from erp_payroll_service import approve_and_post_payroll, execute_payroll_run
from erp_inventory_service import (
    approve_or_reject_po,
    approve_or_reject_requisition,
    approve_or_reject_stock_adjustment,
    record_opening_stock,
    submit_stock_adjustment,
)
from erp_credit_service import record_customer_credit_payment
from erp_returns_service import process_sales_return
from erp_transfer_service import execute_stock_transfer
