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
  const isSystemAdmin = user.roletype === 'Admin';

  container.innerHTML = `
    <div class="context-bar">
      <div>
        <span class="kicker">${isSystemAdmin ? 'System administration' : (user.department_name || 'Dashboard')}</span>
        <h1 class="page-title" style="margin:0">${isSystemAdmin ? 'Access & Security Overview' : `${greeting(user.name)}, ${user.name.split(' ')[0]}`}</h1>
        <p class="muted" style="margin:.25rem 0 0">${isSystemAdmin ? 'Manage employee accounts, credentials, roles, and access activity.' : `${user.branch_name || 'Main Industrial Branch'} · ${new Date().toLocaleDateString('en-UG', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`}</p>
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
        <button class="btn btn-primary btn-sm" id="retry-dashboard" type="button">Retry</button>
      </div>`;
    container.querySelector('#retry-dashboard').addEventListener('click', () => {
      renderDashboard(container, dateFilter, branchId).catch((retryError) => {
        console.error('Dashboard retry failed:', retryError);
      });
    });
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
    renderAlertBanner(alertsEl, 'No open cashier session. Open your till before making sales.', 'warning', 'Open Session', 'sales.html');
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
          'sales.html',
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
      '', '', 'sales.html'
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
    renderAlertBanner(alertsEl, `${h.out_of_stock_count} product(s) are OUT OF STOCK. Sales may be lost.`, 'critical');
  }
  if (h.pending_requisitions > 0) {
    const canReviewRequisitions = can('procurement:approve_req') || can('approvals:approve');
    renderAlertBanner(
      alertsEl,
      `${h.pending_requisitions} purchase requisition(s) awaiting approval.`,
      'warning',
      canReviewRequisitions ? 'Review Approvals' : null,
      canReviewRequisitions ? 'approvals.html' : null
    );
  }

  el.innerHTML = `
    <!-- Hero: Inventory Health -->
    ${heroCard(
      'INVENTORY HEALTH',
      `${h.out_of_stock_count || 0} Out of Stock · ${h.low_stock_count || 0} Low`,
      `Total inventory value: ${UGX(h.total_inventory_value)}`,
      'Review Stock Levels',
      'products.html',
      h.out_of_stock_count > 0 ? 'critical' : h.low_stock_count > 0 ? 'warning' : ''
    )}

    ${kpiCard('TOTAL INVENTORY VALUE', UGX(h.total_inventory_value), 'Across all warehouses', '', '', 'products.html')}
    ${kpiCard('PENDING REQUISITIONS', h.pending_requisitions || 0, 'Awaiting approval')}
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
    renderAlertBanner(
      alertsEl,
      `${wf.pending_leave_requests} leave request(s) need your attention.`,
      'warning',
      can('hr:leave') || can('approvals:approve') ? 'Review Approvals' : null,
      can('hr:leave') || can('approvals:approve') ? 'approvals.html' : null
    );
  }

  const payrollAlert = pr.status === 'DRAFT' || pr.status === 'READY_FOR_RUN';

  el.innerHTML = `
    <!-- Hero: Workforce Today or Payroll Cycle -->
    ${payrollAlert
      ? heroCard('PAYROLL CYCLE', pr.status === 'DRAFT' ? `Draft Ready — ${UGX(pr.total_gross)}` : 'Not Yet Generated', `Month: ${pr.month || '—'} · Net: ${UGX(pr.total_net)}`, 'Review Payroll', 'payroll.html', 'warning')
      : heroCard('WORKFORCE TODAY', `${wf.active_headcount || 0} Active Staff`, `${wf.on_leave_count || 0} on leave · ${wf.pending_leave_requests || 0} pending requests`, 'View Employees', 'employees.html', '')
    }

    ${kpiCard('ACTIVE HEADCOUNT', wf.active_headcount || 0, 'All active employees', '', '', 'employees.html')}
    ${kpiCard('PENDING LEAVE REQUESTS', wf.pending_leave_requests || 0, 'Requires HR review')}
    ${kpiCard('PAYROLL STATUS', pr.status || '—', `Month: ${pr.month || '—'}`, '', '', 'payroll.html')}
    ${kpiCard('GROSS PAYROLL', UGX(pr.total_gross), `Net: ${UGX(pr.total_net)}`, '', '', 'payroll.html')}

    <!-- Quick Actions -->
    <div class="card" style="grid-column:1/-1">
      <h2 style="margin:0 0 1rem">HR Quick Actions</h2>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap">
        <a href="employees.html" class="btn btn-primary">Add Employee</a>
        <a href="payroll.html" class="btn btn-secondary">View Payroll Records</a>
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
    renderAlertBanner(alertsEl, `${UGX(f.payables_total)} in outstanding supplier payables.`, 'warning');
  }

  el.innerHTML = `
    <!-- Hero: Cash Position -->
    ${heroCard(
      'CASH POSITION',
      UGX(cp.total_cash),
      `Cash + Bank + Mobile Money across all accounts`,
      'View Financial Ledger',
      'ledger.html',
      ''
    )}

    ${kpiCard('ACCOUNTS RECEIVABLE', UGX(f.receivables_total), 'Outstanding customer credit')}
    ${kpiCard('ACCOUNTS PAYABLE', UGX(f.payables_total), 'Unpaid supplier invoices')}
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
        <a href="ledger.html" class="btn btn-primary">View Financial Ledger</a>
        <a href="payroll.html" class="btn btn-secondary">View Payroll Records</a>
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
  const isExecutive = (user.roles || []).includes('Owner / Executive');

  if (risks.out_of_stock_count > 0) {
    renderAlertBanner(alertsEl, `${risks.out_of_stock_count} product(s) are out of stock — potential lost sales.`, 'critical');
  }
  if (risks.pending_approvals > 0) {
    renderAlertBanner(alertsEl, `${risks.pending_approvals} approval(s) waiting for your decision.`, 'warning', 'Review Approvals', 'approvals.html');
  }

  el.innerHTML = `
    <!-- Hero: Business Health -->
    ${heroCard(
      isExecutive ? 'EXECUTIVE BUSINESS OVERVIEW' : 'BUSINESS HEALTH',
      UGX(bh.total_revenue),
      `Gross Profit: ${UGX(bh.gross_profit)} · Margin: ${pct(bh.gross_margin)} · Cash: ${UGX(bh.cash_position)}`,
      'View Financial Ledger',
      'ledger.html',
      ''
    )}

    ${kpiCard('TODAY\'S REVENUE', UGX(bh.total_revenue), 'Completed POS sales', '', '', 'sales.html')}
    ${kpiCard('GROSS PROFIT', UGX(bh.gross_profit), `Margin: ${pct(bh.gross_margin)}`)}
    ${kpiCard('PENDING APPROVALS', risks.pending_approvals || 0, 'Requires management decision', '', '', 'approvals.html')}
    ${kpiCard('OVERDUE DEBT', UGX(risks.overdue_debt), 'Outstanding customer receivables')}
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
  const accountCount = a.active_accounts_count ?? a.active_users_count ?? 0;
  const securityAlerts = Number(a.failed_logins_today || 0) + Number(a.locked_accounts_count || 0) + Number(a.suspicious_access_count || 0);

  if (a.failed_logins_today > 5) {
    renderAlertBanner(alertsEl, `${a.failed_logins_today} failed login attempts today. Review security.`, 'critical', 'View Audit Logs', 'audit-logs.html');
  }

  el.innerHTML = `
    <section class="admin-status-strip" aria-label="System status">
      <div class="admin-status-indicator ${a.system_status === 'OPERATIONAL' ? 'is-healthy' : 'is-warning'}" aria-hidden="true"></div>
      <div>
        <div class="admin-status-title">System status: ${a.system_status || 'UNKNOWN'}</div>
        <div class="muted">${accountCount} active sign-in accounts · ${securityAlerts} current security signals</div>
      </div>
      <a href="audit-logs.html" class="btn btn-outline btn-sm">Review audit log</a>
    </section>

    <section class="admin-dashboard-section" aria-labelledby="admin-access-heading">
      <div class="admin-section-heading">
        <div>
          <span class="kicker">Account lifecycle</span>
          <h2 id="admin-access-heading">Users &amp; access</h2>
        </div>
      </div>
      <div class="admin-metric-grid admin-access-grid">
        ${adminMetricCard('ACTIVE USER ACCOUNTS', accountCount, 'Employee accounts that can sign in', 'Online now: Not tracked', 'View users', 'employees.html', 'users')}
        ${adminMetricCard('PENDING ACCOUNT SETUP', a.pending_account_setup_count || 0, 'Active employees without sign-in credentials', 'Create accounts for eligible employees.', 'Create accounts', 'employees.html', 'user-plus')}
        ${adminMetricCard('PASSWORD ACTIONS', a.password_actions_count || 0, 'Temporary passwords expired or expiring within 24 hours', 'Password reset requests: Not tracked', 'Review accounts', 'employees.html', 'key-round')}
      </div>
    </section>

    <section class="admin-dashboard-section" aria-labelledby="admin-security-heading">
      <div class="admin-section-heading">
        <div>
          <span class="kicker">Monitoring</span>
          <h2 id="admin-security-heading">Security activity</h2>
        </div>
      </div>
      <div class="admin-metric-grid admin-security-grid">
        ${adminMetricCard('LOCKED ACCOUNTS', a.locked_accounts_count || 0, 'Accounts temporarily locked after repeated failed sign-ins', '', 'Review locks', 'employees.html', 'lock-keyhole')}
        ${adminMetricCard('FAILED LOGIN ATTEMPTS', a.failed_logins_today || 0, `${a.accounts_affected_today || 0} account(s) affected today`, 'Attempts recorded today.', 'Review alerts', 'audit-logs.html', 'shield-alert')}
        ${adminMetricCard('RECENT PRIVILEGE CHANGES', a.privilege_changes_week || 0, 'Roles or access scopes changed this week', '', 'View audit log', 'audit-logs.html', 'shield-check')}
        ${adminMetricCard('SUSPICIOUS ACCESS ALERTS', a.suspicious_access_count || 0, 'Source addresses with repeated failed sign-ins', '', 'Review alerts', 'audit-logs.html', 'triangle-alert')}
      </div>
    </section>

    <section class="card admin-dashboard-section admin-quick-actions" aria-labelledby="admin-actions-heading">
      <div class="admin-section-heading">
        <div>
          <span class="kicker">Administration</span>
          <h2 id="admin-actions-heading">Quick actions</h2>
        </div>
      </div>
      <div class="admin-action-links">
        <a href="employees.html" class="btn btn-primary">Create employee account</a>
        <a href="settings.html" class="btn btn-outline">View system settings</a>
        <a href="audit-logs.html" class="btn btn-outline">View audit logs</a>
      </div>
    </section>

    <section class="card admin-dashboard-section" aria-labelledby="admin-queue-heading">
      <div class="admin-section-heading">
        <div>
          <span class="kicker">Needs attention</span>
          <h2 id="admin-queue-heading">Admin action queue</h2>
        </div>
        <span class="badge badge-outline">${(a.action_queue || []).length} actions</span>
      </div>
      ${tableHtml(
        ['Action', 'Employee', 'Department / Details', 'Next step'],
        (a.action_queue || []).map((item) => [
          `<strong>${item.action}</strong>`,
          item.employee,
          item.details,
          `<a href="${item.href}">Review →</a>`,
        ]),
        'No account or access actions need attention.'
      )}
      <p class="admin-data-note">Role requests and conflicting-role reviews are not tracked by the current system.</p>
    </section>

    <section class="card admin-dashboard-section" aria-labelledby="admin-audit-heading">
      <div class="admin-section-heading">
        <div>
          <span class="kicker">Accountability</span>
          <h2 id="admin-audit-heading">Recent security &amp; audit events</h2>
        </div>
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
    </section>
  `;
  if (window.lucide) window.lucide.createIcons();
}

function adminMetricCard(title, value, description, note, action, href, icon) {
  const card = `
    <article class="card admin-metric-card">
      <div class="admin-metric-icon" aria-hidden="true"><i data-lucide="${icon}"></i></div>
      <div class="admin-metric-label">${title}</div>
      <div class="admin-metric-value">${value}</div>
      <p class="admin-metric-description">${description}</p>
      ${note ? `<p class="admin-data-note">${note}</p>` : ''}
      <a href="${href}" class="admin-metric-action">${action} <span aria-hidden="true">→</span></a>
    </article>`;
  return card;
}
