/**
 * Hardware World ERP — Main entry point
 *
 * Boots the application: resolves auth, mounts the shell, then
 * dispatches to the correct page renderer.
 */

import { apiRequest, getToken } from './api.js';
import { signOut } from './auth.js';
import { initShell, getPageEl } from './shell.js';
import { setCurrentUser } from './permissions.js';
import { renderDashboard } from './dashboard.js';
import { renderLogin, renderCrud, CRUD_PAGES, renderSales, renderEmployees, renderSettings, renderPayroll, renderLedger, renderPurchaseOrders, renderAuditLogs } from './pages.js';
import { toast } from './notifications.js';

const pageName = document.body.dataset.page;

async function boot() {
  // ── Public pages: no auth required ──
  if (pageName === 'login') {
    await renderLogin();
    return;
  }

  if (pageName === 'signup' || pageName === 'sign-up') {
    // Signup/inquiry page — no action needed here
    return;
  }

  // ── Resolve current user ──
  const token = getToken();
  if (!token) {
    window.location.replace('login.html');
    return;
  }

  let user;
  try {
    user = await apiRequest('/users/me');
  } catch (err) {
    // Token invalid or expired
    window.location.replace('login.html');
    return;
  }

  // Store globally for permission helpers
  setCurrentUser(user);

  // Check account is active (belt-and-suspenders client-side check)
  if (user.is_active === false) {
    window.location.replace('login.html');
    return;
  }

  // Record page view for audit (non-blocking)
  void apiRequest('/audit/page-view', {
    method: 'POST',
    body: JSON.stringify({ page: window.location.pathname }),
  }).catch(() => {});

  // Mount shell
  initShell(user);

  const page = getPageEl();

  // Listen to date-filter changes and re-render
  document.addEventListener('hw:datefilter', (e) => {
    if (pageName === 'dashboard' || pageName === 'index') {
      renderDashboard(page, e.detail.value).catch(() => {});
    }
  });

  // ── Route to page renderer ──
  try {
    switch (pageName) {
      case 'dashboard':
      case 'index':
        await renderDashboard(page);
        break;

      case 'sales':
        if (typeof renderSales === 'function') await renderSales(page);
        else await renderCrud(page, CRUD_PAGES.sales || { endpoint: '/api/sales', title: 'Sales', columns: [] });
        break;

      case 'employees':
        if (typeof renderEmployees === 'function') await renderEmployees(page);
        else await renderCrud(page, CRUD_PAGES.employees || { endpoint: '/api/employees', title: 'Employees', columns: [] });
        break;

      case 'payroll':
        if (typeof renderPayroll === 'function') await renderPayroll(page);
        else await renderCrud(page, { endpoint: '/api/payroll', kicker: 'HR & Finance', title: 'Payroll Records', columns: [] });
        break;

      case 'ledger':
        if (typeof renderLedger === 'function') await renderLedger(page);
        else await renderCrud(page, { endpoint: '/api/journals', kicker: 'Finance', title: 'General Ledger', columns: [] });
        break;

      case 'purchase-orders':
        if (typeof renderPurchaseOrders === 'function') await renderPurchaseOrders(page);
        else await renderCrud(page, { endpoint: '/api/purchase-orders', kicker: 'Procurement', title: 'Purchase Orders', columns: [] });
        break;

      case 'audit-logs':
        if (typeof renderAuditLogs === 'function') await renderAuditLogs(page);
        else await renderCrud(page, { endpoint: '/api/audit-logs', kicker: 'Security', title: 'Audit Logs', columns: [] });
        break;

      case 'settings':
        if (typeof renderSettings === 'function') await renderSettings(page);
        break;

      default:
        // Attempt CRUD page
        if (CRUD_PAGES[pageName]) {
          await renderCrud(page, CRUD_PAGES[pageName]);
        } else {
          page.innerHTML = `
            <div class="card" style="text-align:center;padding:3rem">
              <h2>Page not found</h2>
              <p class="muted">The page "${pageName}" does not exist.</p>
              <a href="index.html" class="btn btn-primary">Go to Dashboard</a>
            </div>`;
        }
    }
  } catch (err) {
    if (err.message?.includes('401') || err.message?.includes('credentials')) {
      toast.error('Session expired. Please sign in again.');
      setTimeout(() => signOut(), 1500);
    } else if (err.message?.includes('403')) {
      page.innerHTML = `
        <div class="card" style="text-align:center;padding:3rem">
          <div style="font-size:2rem;margin-bottom:1rem">🔒</div>
          <h2>Access Denied</h2>
          <p class="muted">You do not have permission to access this page.</p>
          <a href="index.html" class="btn btn-primary">Return to Dashboard</a>
        </div>`;
    } else {
      page.innerHTML = `
        <div class="card notice error" style="padding:1.5rem">
          <strong>Error loading page</strong><br>${err.message}
          <br><br><button class="btn btn-sm" onclick="location.reload()">Retry</button>
        </div>`;
    }
  }
}

boot().catch((err) => {
  const el = document.getElementById('app') || document.body;
  el.innerHTML = `<div style="padding:2rem;color:red">Fatal error: ${err.message}</div>`;
});
