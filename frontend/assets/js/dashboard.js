/**
 * Hardware World ERP — Departmental Dashboard Renderer
 *
 * Renders the role-appropriate bento-grid dashboard based on the user's
 * roletype and live data from /api/dashboard.
 *
 * Six dashboards:
 *   1. Sales & POS     (Cashier / Sales Manager)
 *   2. Procurement     (Procurement Officer / Inventory Manager)
 *   3. Human Resources (HR Staff / HR Manager)
 *   4. Finance         (Accountant / Finance Manager)
 *   5. Operations      (Branch Manager / Owner / Executive)
 *   6. Administration  (Admin / System Administrator)
 */

import { apiRequest } from './api.js';
import { can, hasRole, getCurrentUser } from './permissions.js';
import { renderAlertBanner, toast } from './notifications.js';

// ── Shared helpers ────────────────────────────────────────────────

const UGX = (n) =>
  `UGX ${Number(n || 0).toLocaleString('en-UG', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

const pct = (n) => `${(Number(n || 0)).toFixed(1)}%`;

const arrow = (n, favorableDir = 'up') => {
  const val = Number(n || 0);
  if (val === 0) return '<span style="color:var(--muted-foreground)">→ 0%</span>';
  const up = val > 0;
  const good = favorableDir === 'up' ? up : !up;
  const color = good ? 'var(--primary)' : 'var(--destructive)';
  return `<span style="color:${color}">${up ? '↑' : '↓'} ${Math.abs(val).toFixed(1)}%</span>`;
};

function heroCard(title, main, sub, action, actionHref, alertLevel = '') {
  const borderColor = { critical: 'var(--destructive)', warning: 'var(--accent)', '': 'var(--border)' }[alertLevel] || 'var(--border)';
  return `
    <div class="card bento-hero" style="border-left:4px solid ${borderColor}">
      <div class="muted kicker">${title}</div>
      <div class="hero-value">${main}</div>
      <div class="muted" style="margin:.25rem 0 .75rem">${sub}</div>
      ${action ? `<a href="${actionHref}" class="btn btn-primary btn-sm">${action}</a>` : ''}
    </div>`;
}

function kpiCard(title, value, sub, trend = '', trendDir = 'up', link = '') {
  return `
    <div class="card bento-kpi">
      <div class="muted" style="font-size:.75rem;text-transform:uppercase;letter-spacing:.04em">${title}</div>
      <div style="font-size:1.5rem;font-weight:700;margin:.25rem 0">${value}</div>
      <div class="muted" style="font-size:.8rem">${sub}</div>
      ${trend ? `<div style="font-size:.8rem;margin-top:.25rem">${arrow(trend, trendDir)} vs yesterday</div>` : ''}
      ${link ? `<a href="${link}" class="muted" style="font-size:.8rem;text-decoration:underline;margin-top:.25rem;display:block">View →</a>` : ''}
    </div>`;
}

function alertCard(message, level = 'warning', actionLabel = '', actionHref = '') {
  const colors = { critical: 'var(--destructive)', warning: 'var(--accent)', info: 'var(--steel)' };
  const bg = { critical: '#fef2f2', warning: '#fffbeb', info: '#eff6ff' };
  const icons = { critical: '⛔', warning: '⚠️', info: 'ℹ️' };
  return `
    <div class="card" style="border-left:4px solid ${colors[level]};background:${bg[level]}">
      <div style="display:flex;align-items:center;gap:.5rem;font-weight:600">
        ${icons[level]} ${message}
      </div>
      ${actionLabel ? `<a href="${actionHref}" class="btn btn-sm" style="margin-top:.5rem;background:${colors[level]};color:#fff;">${actionLabel}</a>` : ''}
    </div>`;
}

function statusBadge(status) {
  const map = {
    COMPLETED: 'background:var(--primary);color:#fff',
    APPROVED: 'background:var(--primary);color:#fff',
    OPEN: 'background:var(--steel);color:#fff',
    PENDING: 'background:var(--accent);color:#1e293b',
    PENDING_REVIEW: 'background:var(--accent);color:#1e293b',
    CLOSED: 'background:var(--muted-foreground);color:#fff',
    DRAFT: 'background:var(--muted-foreground);color:#fff',
    REJECTED: 'background:var(--destructive);color:#fff',
    CANCELLED: 'background:var(--destructive);color:#fff',
    LOW_STOCK: 'background:var(--accent);color:#1e293b',
    OUT_OF_STOCK: 'background:var(--destructive);color:#fff',
  };
  return `<span style="padding:.15rem .6rem;border-radius:999px;font-size:.75rem;font-weight:600;${map[status] || 'background:var(--muted);color:var(--muted-foreground)'}">${status}</span>`;
}

function tableHtml(cols, rows, emptyMsg = 'No records found.') {
  if (!rows || !rows.length) {
    return `<div class="empty-state card" style="text-align:center;padding:2rem;color:var(--muted-foreground)">${emptyMsg}</div>`;
  }
  return `
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:.875rem">
        <thead>
          <tr style="border-bottom:2px solid var(--border)">
            ${cols.map((c) => `<th style="text-align:left;padding:.5rem .75rem;color:var(--muted-foreground);font-weight:600;white-space:nowrap">${c}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => `<tr style="border-bottom:1px solid var(--border)">${r.map((cell) => `<td style="padding:.6rem .75rem">${cell}</td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function loadingCard(rows = 1) {
  return Array(rows).fill(0).map(() => `
    <div class="card" style="animation:pulse 1.5s infinite">
      <div style="height:1rem;background:var(--muted);border-radius:4px;margin-bottom:.5rem"></div>
      <div style="height:2rem;background:var(--muted);border-radius:4px;width:60%"></div>
    </div>`).join('');
}

// ── Main dashboard loader ─────────────────────────────────────────

export async function renderDashboard(container, dateFilter = 'today', branchId = null) {
  const user = getCurrentUser();
  if (!user) return;

  container.innerHTML = `
    <div class="context-bar">
      <div>
        <span class="kicker">${user.department_name || 'Dashboard'}</span>
        <h1 class="page-title" style="margin:0">${greeting(user.name)}, ${user.name.split(' ')[0]}</h1>
        <p class="muted" style="margin:.25rem 0 0">${user.branch_name || 'Main Industrial Branch'} · ${new Date().toLocaleDateString('en-UG', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>
    </div>
    <div id="dash-alerts"></div>
    <div id="dash-content" class="bento-grid">${loadingCard(6)}</div>
  `;

  let data;
  try {
    const params = new URLSearchParams({ date_filter: dateFilter });
    if (branchId) params.set('branch_id', branchId);
    data = await apiRequest(`/api/dashboard?${params}`);
  } catch (err) {
    container.querySelector('#dash-content').innerHTML = `
      <div class="card" style="grid-column:1/-1;text-align:center;padding:3rem;color:var(--muted-foreground)">
        <div style="font-size:2rem;margin-bottom:1rem">⚠️</div>
        <p>Unable to load dashboard data. ${err.message || 'Please try again.'}</p>
        <button class="btn btn-primary btn-sm" onclick="location.reload()">Retry</button>
      </div>`;
    return;
  }

  const alertsEl = container.querySelector('#dash-alerts');
  const contentEl = container.querySelector('#dash-content');
  const role = user.roletype;

  // Route to the appropriate department renderer
  if (role === 'Cashier') {
    renderSalesDashboard(contentEl, alertsEl, data, user);
  } else if (role === 'Procurement Officer') {
    renderProcurementDashboard(contentEl, alertsEl, data, user);
  } else if (role === 'HR Staff') {
    renderHRDashboard(contentEl, alertsEl, data, user);
  } else if (role === 'Accountant') {
    renderFinanceDashboard(contentEl, alertsEl, data, user);
  } else if (role === 'Branch Manager') {
    renderOperationsDashboard(contentEl, alertsEl, data, user);
  } else {
    renderAdminDashboard(contentEl, alertsEl, data, user);
  }
}

function greeting(name) {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

// ── 1. Sales & POS Dashboard ──────────────────────────────────────

function renderSalesDashboard(el, alertsEl, data, user) {
  const s = data.sales || {};
  const session = s.cashier_session || {};
  const sales = s.recent_sales || [];

  // Alerts
  if (!session.is_open) {
    renderAlertBanner(alertsEl, 'No open cashier session. Open your till before making sales.', 'warning', 'Open Session', 'sales.html#session');
  }

  el.innerHTML = `
    <!-- Hero: Cashier Session or New Sale -->
    ${session.is_open
      ? heroCard(
          'CASHIER SESSION — OPEN',
          UGX(s.today_revenue),
          `${s.transaction_count} completed transactions · Session opened ${session.opened_at ? new Date(session.opened_at).toLocaleTimeString() : '—'}`,
          'New Sale',
          'sales.html',
          ''
        )
      : heroCard(
          'OPEN YOUR TILL TO START SELLING',
          'Session Closed',
          `Opening float: ${UGX(session.opening_float || 0)}`,
          'Open Cashier Session',
          'sales.html#session',
          'warning'
        )
    }

    <!-- Today's Revenue -->
    ${kpiCard('TODAY\'S SALES', UGX(s.today_revenue), `Target progress: ${pct(s.target_progress)}`, '', '', 'sales.html')}

    <!-- Transactions -->
    ${kpiCard('TRANSACTIONS', s.transaction_count || 0, 'Completed today', '', '', 'sales.html')}

    <!-- Average Basket -->
    ${kpiCard('AVG BASKET VALUE', UGX(s.average_basket), 'Per completed transaction')}

    <!-- Expected Cash -->
    ${session.is_open ? kpiCard(
      'EXPECTED CASH IN TILL',
      UGX(session.expected_cash),
      `Float: ${UGX(session.opening_float)} + Cash Sales`,
      '', '', 'sales.html#session'
    ) : ''}

    <!-- Recent Sales Table -->
    <div class="card bento-wide" style="grid-column:1/-1">
      <div class="page-head" style="margin-bottom:.75rem">
        <h2>Recent Sales</h2>
        <a href="sales.html" class="muted">View all →</a>
      </div>
      ${tableHtml(
        ['Receipt #', 'Date/Time', 'Customer', 'Payment', 'Total', 'Status'],
        sales.map((s) => [
          `<strong>#${s.saleid}</strong>`,
          new Date(s.saledate).toLocaleString(),
          s.customer || 'Walk-in',
          s.payment_method || 'CASH',
          UGX(s.totalamount),
          statusBadge('COMPLETED'),
        ]),
        'No sales recorded today yet.'
      )}
    </div>
  `;
}

// ── 2. Procurement & Inventory Dashboard ─────────────────────────

function renderProcurementDashboard(el, alertsEl, data, user) {
  const p = data.procurement || {};
  const h = p.inventory_health || {};
  const criticalItems = p.critical_items || [];

  if (h.out_of_stock_count > 0) {
    renderAlertBanner(alertsEl, `${h.out_of_stock_count} product(s) are OUT OF STOCK. Sales may be lost.`, 'critical', 'Create Requisition', 'purchase-orders.html#requisitions');
  }
  if (h.pending_requisitions > 0) {
    renderAlertBanner(alertsEl, `${h.pending_requisitions} purchase requisition(s) awaiting approval.`, 'warning', 'View Approvals', 'purchase-orders.html#requisitions');
  }

  el.innerHTML = `
    <!-- Hero: Inventory Health -->
    ${heroCard(
      'INVENTORY HEALTH',
      `${h.out_of_stock_count || 0} Out of Stock · ${h.low_stock_count || 0} Low`,
      `Total inventory value: ${UGX(h.total_inventory_value)}`,
      'Review Replenishment',
      'purchase-orders.html#requisitions',
      h.out_of_stock_count > 0 ? 'critical' : h.low_stock_count > 0 ? 'warning' : ''
    )}

    ${kpiCard('TOTAL INVENTORY VALUE', UGX(h.total_inventory_value), 'Across all warehouses', '', '', 'products.html')}
    ${kpiCard('PENDING REQUISITIONS', h.pending_requisitions || 0, 'Awaiting approval', '', '', 'purchase-orders.html#requisitions')}
    ${kpiCard('PENDING PURCHASE ORDERS', h.pending_pos || 0, 'Awaiting dispatch', '', '', 'purchase-orders.html')}

    <!-- Critical Items -->
    <div class="card" style="grid-column:1/-1">
      <div class="page-head" style="margin-bottom:.75rem">
        <h2>⚠️ Low-Stock & Out-of-Stock Products</h2>
        <a href="products.html" class="muted">Full inventory →</a>
      </div>
      ${tableHtml(
        ['Product', 'Warehouse', 'Available Stock', 'Reorder Level', 'Status'],
        criticalItems.map((item) => {
          const avail = parseFloat(item.available_stock || 0);
          const reorder = parseInt(item.reorder_level || 0);
          const statusKey = avail <= 0 ? 'OUT_OF_STOCK' : 'LOW_STOCK';
          return [
            `<strong>${item.item_name}</strong>`,
            item.warehouse_name,
            `${avail} units`,
            `${reorder} units`,
            statusBadge(statusKey),
          ];
        }),
        'All stock levels are healthy. ✓'
      )}
    </div>
  `;
}

// ── 3. Human Resources Dashboard ─────────────────────────────────

function renderHRDashboard(el, alertsEl, data, user) {
  const h = data.hr || {};
  const wf = h.workforce_today || {};
  const pr = h.payroll_cycle || {};

  if (wf.pending_leave_requests > 0) {
    renderAlertBanner(alertsEl, `${wf.pending_leave_requests} leave request(s) need your attention.`, 'warning', 'Review Leaves', 'employees.html#leave');
  }

  const payrollAlert = pr.status === 'DRAFT' || pr.status === 'READY_FOR_RUN';

  el.innerHTML = `
    <!-- Hero: Workforce Today or Payroll Cycle -->
    ${payrollAlert
      ? heroCard('PAYROLL CYCLE', pr.status === 'DRAFT' ? `Draft Ready — ${UGX(pr.total_gross)}` : 'Not Yet Generated', `Month: ${pr.month || '—'} · Net: ${UGX(pr.total_net)}`, 'Review Payroll', 'payroll.html', 'warning')
      : heroCard('WORKFORCE TODAY', `${wf.active_headcount || 0} Active Staff`, `${wf.on_leave_count || 0} on leave · ${wf.pending_leave_requests || 0} pending requests`, 'View Employees', 'employees.html', '')
    }

    ${kpiCard('ACTIVE HEADCOUNT', wf.active_headcount || 0, 'All active employees', '', '', 'employees.html')}
    ${kpiCard('PENDING LEAVE REQUESTS', wf.pending_leave_requests || 0, 'Requires HR review', '', '', 'employees.html#leave')}
    ${kpiCard('PAYROLL STATUS', pr.status || '—', `Month: ${pr.month || '—'}`, '', '', 'payroll.html')}
    ${kpiCard('GROSS PAYROLL', UGX(pr.total_gross), `Net: ${UGX(pr.total_net)}`, '', '', 'payroll.html')}

    <!-- Quick Actions -->
    <div class="card" style="grid-column:1/-1">
      <h2 style="margin:0 0 1rem">HR Quick Actions</h2>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap">
        <a href="employees.html" class="btn btn-primary">Add Employee</a>
        <a href="employees.html#attendance" class="btn btn-secondary">Record Attendance</a>
        <a href="employees.html#leave" class="btn btn-secondary">Leave Management</a>
        <a href="payroll.html" class="btn btn-secondary">Run Payroll</a>
        <a href="payroll.html#payslips" class="btn btn-secondary">View Payslips</a>
      </div>
    </div>
  `;
}

// ── 4. Finance & Accounting Dashboard ────────────────────────────

function renderFinanceDashboard(el, alertsEl, data, user) {
  const f = data.finance || {};
  const cp = f.cash_position || {};
  const accounts = cp.accounts || [];

  if (f.payables_total > 0) {
    renderAlertBanner(alertsEl, `${UGX(f.payables_total)} in outstanding supplier payables.`, 'warning', 'View Payables', 'ledger.html#payables');
  }

  el.innerHTML = `
    <!-- Hero: Cash Position -->
    ${heroCard(
      'CASH POSITION',
      UGX(cp.total_cash),
      `Cash + Bank + Mobile Money across all accounts`,
      'View Cash Accounts',
      'ledger.html#cash',
      ''
    )}

    ${kpiCard('ACCOUNTS RECEIVABLE', UGX(f.receivables_total), 'Outstanding customer credit', '', '', 'sales.html#customers')}
    ${kpiCard('ACCOUNTS PAYABLE', UGX(f.payables_total), 'Unpaid supplier invoices', '', '', 'purchase-orders.html#invoices')}
    ${kpiCard("TODAY'S REVENUE", UGX(f.today_revenue), 'Completed sales only', '', '', 'sales.html')}
    ${kpiCard('GROSS PROFIT', UGX(f.gross_profit), `Margin: ${pct(f.gross_margin)}`, '', '', 'ledger.html')}

    <!-- Cash Accounts Breakdown -->
    <div class="card bento-wide" style="grid-column:span 6">
      <h2 style="margin:0 0 .75rem">Cash Accounts</h2>
      ${tableHtml(
        ['Account', 'Type', 'Balance'],
        accounts.map((a) => [
          `<strong>${a.account_name}</strong>`,
          `<span style="color:var(--steel)">${a.account_type}</span>`,
          UGX(a.balance),
        ]),
        'No financial accounts configured.'
      )}
    </div>

    <!-- Finance Quick Actions -->
    <div class="card" style="grid-column:span 6">
      <h2 style="margin:0 0 1rem">Finance Actions</h2>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap">
        <a href="ledger.html" class="btn btn-primary">Record Journal</a>
        <a href="purchase-orders.html#invoices" class="btn btn-secondary">Match Invoice</a>
        <a href="purchase-orders.html#payments" class="btn btn-secondary">Pay Supplier</a>
        <a href="payroll.html" class="btn btn-secondary">Post Payroll</a>
      </div>
    </div>
  `;
}

// ── 5. Operations & Branch Management Dashboard ───────────────────

function renderOperationsDashboard(el, alertsEl, data, user) {
  const o = data.operations || {};
  const bh = o.business_health || {};
  const risks = o.risks || {};
  const branches = o.branch_rankings || [];

  if (risks.out_of_stock_count > 0) {
    renderAlertBanner(alertsEl, `${risks.out_of_stock_count} product(s) are out of stock — potential lost sales.`, 'critical');
  }
  if (risks.pending_approvals > 0) {
    renderAlertBanner(alertsEl, `${risks.pending_approvals} approval(s) waiting for your decision.`, 'warning', 'Review', 'index.html#approvals');
  }

  el.innerHTML = `
    <!-- Hero: Business Health -->
    ${heroCard(
      'BUSINESS HEALTH',
      UGX(bh.total_revenue),
      `Gross Profit: ${UGX(bh.gross_profit)} · Margin: ${pct(bh.gross_margin)} · Cash: ${UGX(bh.cash_position)}`,
      'View Full Report',
      'ledger.html',
      ''
    )}

    ${kpiCard('TODAY\'S REVENUE', UGX(bh.total_revenue), 'Completed POS sales', '', '', 'sales.html')}
    ${kpiCard('GROSS PROFIT', UGX(bh.gross_profit), `Margin: ${pct(bh.gross_margin)}`)}
    ${kpiCard('PENDING APPROVALS', risks.pending_approvals || 0, 'Requires management decision', '', '', 'index.html#approvals')}
    ${kpiCard('OVERDUE DEBT', UGX(risks.overdue_debt), 'Outstanding customer receivables', '', '', 'sales.html#customers')}
    ${kpiCard('STOCK RISKS', risks.out_of_stock_count || 0, 'Out-of-stock products', '', '', 'products.html')}

    <!-- Branch Comparison -->
    <div class="card" style="grid-column:1/-1">
      <h2 style="margin:0 0 .75rem">Branch Performance</h2>
      ${tableHtml(
        ['Branch', 'Total Revenue', 'Status'],
        branches.map((b) => [
          `<strong>${b.branchname}</strong>`,
          UGX(b.total_revenue),
          statusBadge(b.total_revenue > 0 ? 'COMPLETED' : 'PENDING'),
        ]),
        'No branch data available.'
      )}
    </div>
  `;
}

// ── 6. Administration Dashboard ───────────────────────────────────

function renderAdminDashboard(el, alertsEl, data, user) {
  const a = data.admin || {};
  const events = a.recent_audit_events || [];

  if (a.failed_logins_today > 5) {
    renderAlertBanner(alertsEl, `${a.failed_logins_today} failed login attempts today. Review security.`, 'critical', 'View Audit Logs', 'audit-logs.html');
  }

  el.innerHTML = `
    <!-- Hero: System Status -->
    ${heroCard(
      'SYSTEM STATUS',
      a.system_status || 'OPERATIONAL',
      `${a.active_users_count || 0} active users · ${a.failed_logins_today || 0} failed logins today`,
      'View Audit Logs',
      'audit-logs.html',
      a.system_status !== 'OPERATIONAL' ? 'critical' : ''
    )}

    ${kpiCard('ACTIVE USERS', a.active_users_count || 0, 'Staff with active accounts', '', '', 'employees.html')}
    ${kpiCard('FAILED LOGINS TODAY', a.failed_logins_today || 0, 'Security monitoring', '', '', 'audit-logs.html')}

    <!-- Admin Quick Actions -->
    <div class="card" style="grid-column:span 4">
      <h2 style="margin:0 0 1rem">Quick Actions</h2>
      <div style="display:flex;flex-direction:column;gap:.5rem">
        <a href="employees.html" class="btn btn-primary">Create User</a>
        <a href="settings.html" class="btn btn-secondary">Manage Roles</a>
        <a href="audit-logs.html" class="btn btn-secondary">View Audit Logs</a>
        <a href="employees.html" class="btn btn-secondary">Reset Password</a>
      </div>
    </div>

    <!-- Recent Audit Events -->
    <div class="card" style="grid-column:1/-1">
      <div class="page-head" style="margin-bottom:.75rem">
        <h2>Recent Security & Audit Events</h2>
        <a href="audit-logs.html" class="muted">Full audit log →</a>
      </div>
      ${tableHtml(
        ['Time', 'User', 'Action', 'Details'],
        events.map((e) => [
          new Date(e.timestamp).toLocaleString(),
          e.user || 'System',
          `<strong>${e.action}</strong>`,
          (e.details || '').substring(0, 60) + ((e.details || '').length > 60 ? '…' : ''),
        ]),
        'No recent audit events.'
      )}
    </div>
  `;
}
