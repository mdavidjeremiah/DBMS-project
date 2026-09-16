import { requireSession } from './auth.js';
import { accessDeniedHtml, mountShell } from './layout.js';
import { CRUD_PAGES, renderCrud, renderDashboard, renderEmployees, renderLogin, renderSales, renderSettings } from './pages.js';

const pageName = document.body.dataset.page;

async function boot() {
  if (pageName === 'login') {
    await renderLogin();
    return;
  }

  if (pageName === 'signup') return;

  const session = await requireSession();
  if (!session) return;

  const app = document.getElementById('app');
  if (!session.authorized) {
    mountShell(app, session.user, accessDeniedHtml(session.user));
    return;
  }

  window.__HW_USER__ = session.user;
  mountShell(app, session.user, '<p class="muted">Loading…</p>');
  const page = document.getElementById('page');

  if (pageName === 'dashboard') await renderDashboard(page);
  else if (pageName === 'sales') await renderSales(page);
  else if (pageName === 'employees') await renderEmployees(page);
  else if (pageName === 'settings') await renderSettings(page);
  else if (CRUD_PAGES[pageName]) await renderCrud(page, CRUD_PAGES[pageName]);
}

boot().catch((error) => {
  const page = document.getElementById('page') || document.getElementById('app');
  if (page) page.innerHTML = `<div class="notice error">${error.message}</div>`;
});
