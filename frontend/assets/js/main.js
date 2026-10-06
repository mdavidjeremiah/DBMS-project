/**
 * Hardware World ERP — Main entry point
 *
 * Boots the application: resolves auth, mounts the shell, then
 * dispatches to the correct page renderer.
 */

import { apiRequest } from './api.js';
import { signOut } from './auth.js';
import { initShell, getPageEl } from './shell.js';
import { setCurrentUser } from './permissions.js';
import { renderDashboard } from './dashboard.js';
import { renderLogin, renderPasswordChange, renderCrud, CRUD_PAGES, renderSales, renderEmployees, renderSettings, renderOrganization, renderPayroll, renderLedger, renderPurchaseOrders, renderAuditLogs, renderApprovals } from './pages.js';
import { toast } from './notifications.js';

const pageName = document.body.dataset.page;

async function boot() {
  // ── Public pages: no auth required ──
  if (pageName === 'login') {
    await renderLogin();
    return;
  }

  if (pageName === 'change-password') {
    renderPasswordChange();
    return;
  }

  if (pageName === 'signup' || pageName === 'sign-up') {
    // Signup/inquiry page — no action needed here
    return;
  }

  // ── Resolve current user ──
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
      renderDashboard(page, e.detail.value).catch((error) => {
        console.error('Unable to refresh dashboard for the selected date range:', error);
      });
    }
  });

  if (pageName === 'dashboard' || pageName === 'index') await renderDashboard(page);
  else if (pageName === 'sales') await renderSales(page, user);
  else if (pageName === 'employees') await renderEmployees(page);
  else if (pageName === 'settings') await renderSettings(page);
  else if (['branches', 'warehouses', 'departments'].includes(pageName)) await renderOrganization(page, pageName);
  else if (pageName === 'payroll') await renderPayroll(page);
  else if (pageName === 'ledger') await renderLedger(page);
  else if (pageName === 'purchase-orders') await renderPurchaseOrders(page);
  else if (pageName === 'audit-logs') await renderAuditLogs(page);
  else if (pageName === 'approvals') await renderApprovals(page);
  else if (CRUD_PAGES[pageName]) await renderCrud(page, CRUD_PAGES[pageName]);
}

boot().catch((err) => {
  const el = document.getElementById('app') || document.body;
  el.innerHTML = `<div style="padding:2rem;color:red">Fatal error: ${err.message}</div>`;
});
