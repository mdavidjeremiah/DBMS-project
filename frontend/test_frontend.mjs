import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { buildGraphData, renderGraph } from './assets/js/graph.js';
import { getSidebarItems, SIDEBAR_CONFIG } from './assets/js/sidebar-config.js';

const sourceRoot = new URL('.', import.meta.url);

function isoDate(daysAgo) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().split('T')[0];
}

test('buildGraphData returns seven database-backed daily points', () => {
  const sales = [
    { saledate: `${isoDate(0)}T10:00:00`, totalamount: '125000' },
    { saledate: `${isoDate(0)}T11:00:00`, totalamount: '75000' },
    { saledate: `${isoDate(1)}T09:00:00`, totalamount: '50000' },
  ];

  const graphData = buildGraphData(sales);
  const today = graphData.find((point) => point.date === isoDate(0));
  const yesterday = graphData.find((point) => point.date === isoDate(1));

  assert.equal(graphData.length, 7);
  assert.deepEqual(today, {
    date: isoDate(0),
    label: today.label,
    salesRevenue: 200000,
    transactions: 2,
  });
  assert.equal(yesterday.salesRevenue, 50000);
  assert.equal(yesterday.transactions, 1);
});

test('buildGraphData returns zero values when no sales exist', () => {
  const graphData = buildGraphData([]);

  assert.equal(graphData.length, 7);
  assert.ok(graphData.every((point) => point.salesRevenue === 0 && point.transactions === 0));
});

test('renderGraph shows an empty state instead of invented values', () => {
  const container = { innerHTML: '' };

  renderGraph(container, []);

  assert.match(container.innerHTML, /No sales data has been entered yet/);
  assert.doesNotMatch(container.innerHTML, /DEFAULT_DATA|2850000/);
});

test('dashboard alert actions render destination links instead of event handlers', async () => {
  const originalDocument = globalThis.document;
  const originalWindow = globalThis.window;
  const container = { prepend(element) { this.element = element; } };
  globalThis.window = { __HW_API_URL__: '' };
  globalThis.document = {
    createElement: () => ({
      style: {},
      innerHTML: '',
      querySelector: () => ({ addEventListener() {} }),
    }),
  };

  try {
    const { renderAlertBanner } = await import(`./assets/js/notifications.js?test=${Date.now()}`);
    renderAlertBanner(container, 'Review pending approvals.', 'warning', 'Review', 'approvals.html');
    assert.match(container.element.innerHTML, /<a id="alert-action" href="approvals\.html"/);
  } finally {
    if (originalDocument === undefined) delete globalThis.document;
    else globalThis.document = originalDocument;
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
  }
});

test('application pages reference the shared stylesheet', async () => {
  for (const page of ['index.html', 'login.html', 'sign-up.html']) {
    const html = await readFile(new URL(page, sourceRoot), 'utf8');
    assert.match(html, /assets\/css\/style\.css/);
  }
});

test('frontend source contains no demo login or fallback graph data', async () => {
  const [pages, graph] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/graph.js', sourceRoot), 'utf8'),
  ]);

  assert.doesNotMatch(pages, /data-fill|adminpassword|staff123|Akena/);
  assert.doesNotMatch(graph, /DEFAULT_DATA|2850000|7420000/);
});

test('login presents one staff form with department and assigned password fields', async () => {
  const [pages, html, styles] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('login.html', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
  ]);

  const loginSource = pages.slice(pages.indexOf('export async function renderLogin'), pages.indexOf('export async function renderCrud'));
  assert.match(loginSource, /<p class="kicker">Staff Member<\/p>/);
  assert.match(loginSource, /name="department"/);
  assert.match(loginSource, /placeholder="Enter your assigned password"/);
  assert.doesNotMatch(loginSource, /Administrator|data-type=|admin-note/);
  assert.match(html, /class="login-page" data-page="login"/);
  assert.match(styles, /\.login-page \.auth-card/);
  assert.match(styles, /\.login-page \.control/);
});

test('authenticated API requests use cookies and handle expired sessions', async () => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  let requestOptions;
  let redirect;

  globalThis.window = {
    __HW_API_URL__: '',
    location: {
      pathname: '/index.html',
      replace: (path) => { redirect = path; },
    },
  };
  globalThis.fetch = async (_url, options) => {
    requestOptions = options;
    return new Response(JSON.stringify({ detail: 'Could not validate credentials' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const { apiRequest } = await import(`./assets/js/api.js?test=${Date.now()}`);
    await assert.rejects(apiRequest('/users/me'), /Could not validate credentials/);
    assert.equal(requestOptions.credentials, 'include');
    assert.equal(redirect, '/login.html');
  } finally {
    globalThis.fetch = originalFetch;
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
  }
});

test('employee photo provisioning and shared avatar locations use profile photo data', async () => {
  const [pages, shell, router, styles] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/shell.js', sourceRoot), 'utf8'),
    readFile(new URL('../backend/api_router.py', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
  ]);

  assert.match(pages, /name="profile_photo"/);
  assert.match(pages, /accept="image\/jpeg,image\/png,image\/webp"/);
  assert.match(pages, /apiRequest\(`\/users\/\$\{created\.employeeid\}\/profile-photo`/);
  assert.match(pages, /Retry photo upload/);
  assert.match(shell, /user\.profile_photo_url/);
  assert.equal((shell.match(/\$\{avatarMarkup\(user\)\}/g) || []).length, 2);
  assert.match(router, /MAX_PROFILE_PHOTO_BYTES = 5 \* 1024 \* 1024/);
  assert.match(router, /Upload a valid JPEG, PNG, or WebP image/);
  assert.match(styles, /\.avatar img\s*\{[^}]*object-fit:\s*cover/s);
  assert.match(styles, /\.profile-photo-picker\s*\{/);
});

test('employee provisioning requires an explicit role and renders matching role-specific fields', async () => {
  const pages = await readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8');
  const roleFields = pages.slice(
    pages.indexOf('function employeeRoleFields'),
    pages.indexOf('export async function renderEmployees'),
  );
  const employeeForm = pages.slice(
    pages.indexOf('export async function renderEmployees'),
    pages.indexOf('// Stub exports for page renderers'),
  );

  assert.match(employeeForm, /name="roletype" id="roletype" required/);
  assert.match(employeeForm, /<option value="">Select an assigned role<\/option>/);
  assert.match(employeeForm, /<div id="role-fields" class="employee-role-fields" aria-live="polite">\$\{employeeRoleFields\(''\)\}<\/div>/);
  assert.match(roleFields, /Cashier: field\('pos_terminalid', 'Assigned POS Terminal ID'/);
  assert.match(roleFields, /'Procurement Officer': field\('approvallimit', 'Approval Limit \(UGX\)'/);
  assert.match(roleFields, /Accountant: field\('certificationnumber'/);
  assert.match(roleFields, /'HR Staff': field\('hr_role', 'HR Designation'/);
  assert.match(roleFields, /'Branch Manager': field\('managementlevel'/);
  assert.match(employeeForm, /roleSelect\.addEventListener\('change'/);
  assert.match(employeeForm, /roleFields\.replaceChildren\(\)/);
  assert.match(employeeForm, /employeeRoleFields\(roleSelect\.value\)/);
  assert.match(employeeForm, /role controls could not be initialized/);
  assert.doesNotMatch(employeeForm, /id="role-fields">\$\{field\('pos_terminalid'/);
});

test('admin requests a server-generated temporary password in the employee form', async () => {
  const [pages, router, styles] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('../backend/api_router.py', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
  ]);
  const employeeForm = pages.slice(
    pages.indexOf('export async function renderEmployees'),
    pages.indexOf('// Stub exports for page renderers'),
  );

  assert.match(employeeForm, /const isSystemAdmin = getCurrentUser\(\)\?\.roletype === 'Admin'/);
  assert.match(employeeForm, /\$\{isSystemAdmin \? `<div class="employee-password-field">/);
  assert.match(employeeForm, /name="password" type="text" autocomplete="new-password" readonly/);
  assert.match(employeeForm, /class="btn btn-primary btn-sm" id="generate-initial-password" type="button">Generate temporary password/);
  assert.match(employeeForm, /password: form\.get\('password'\) \|\| null/);
  assert.match(employeeForm, /apiRequest\('\/api\/users\/generate-temporary-password', \{ method: 'POST' \}\)/);
  assert.match(employeeForm, /passwordInput\.value = result\.temporary_password/);
  assert.match(router, /@api_router\.post\("\/users\/generate-temporary-password"/);
  assert.match(router, /auth\.generate_temporary_password\(\)/);
  assert.match(styles, /\.employee-password-field\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/);
  assert.match(styles, /\.dialog \.form-grid\.two > \.field\s*\{[^}]*align-self:\s*start/);
  assert.match(styles, /\.employee-role-fields\s*\{[^}]*grid-column:\s*1\s*\/\s*-1/);
});

test('System Administrator uses the linked GitHub avatar unless an employee photo is set', async () => {
  const shell = await readFile(new URL('./assets/js/shell.js', sourceRoot), 'utf8');
  const avatar = await readFile(new URL('./assets/images/admin-profile.jpg', sourceRoot));

  assert.match(shell, /user\.profile_photo_url \|\| \(user\.roletype === 'Admin' \? '\/assets\/images\/admin-profile\.jpg'/);
  assert.ok(avatar.length > 0);
  assert.deepEqual([...avatar.subarray(0, 3)], [255, 216, 255]);
});

test('apiRequest leaves the multipart boundary to the browser for profile photo uploads', async () => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  let requestOptions;
  globalThis.window = { __HW_API_URL__: '', location: { pathname: '/employees.html' } };
  globalThis.fetch = async (_url, options) => {
    requestOptions = options;
    return new Response(JSON.stringify({ profile_photo_url: '/api/users/1/profile-photo' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const { apiRequest } = await import(`./assets/js/api.js?multipart-test=${Date.now()}`);
    await apiRequest('/users/1/profile-photo', { method: 'PUT', body: new FormData() });
    assert.equal(requestOptions.headers.has('Content-Type'), false);
    assert.equal(requestOptions.credentials, 'include');
  } finally {
    globalThis.fetch = originalFetch;
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
  }
});

test('authenticated shell styles its rendered layout and supports responsive navigation', async () => {
  const [shell, styles, ui, pages] = await Promise.all([
    readFile(new URL('./assets/js/shell.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/ui.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
  ]);

  for (const selector of ['.content-col', '.topbar-right', '.search-wrap', '.sidebar-backdrop', '.main', '.page-head', '.table-wrap']) {
    assert.ok(styles.includes(selector), `missing shell style: ${selector}`);
  }
  assert.match(styles, /@media \(max-width: 1100px\)/);
  assert.match(shell, /aria-expanded="false"/);
  assert.match(shell, /aria-current="page"/);
  assert.match(ui, /renderLoadingState/);
  assert.match(ui, /No records yet\./);
  assert.match(ui, /onRetry/);
  assert.match(pages, /if \(!result\.error\) \{\s*renderTable/);
});

test('System Administrator dashboard displays access and security sections without invented metrics', async () => {
  const dashboard = await readFile(new URL('./assets/js/dashboard.js', sourceRoot), 'utf8');
  const styles = await readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8');

  for (const label of [
    'Access & Security Overview',
    'ACTIVE USER ACCOUNTS',
    'PENDING ACCOUNT SETUP',
    'PASSWORD ACTIONS',
    'LOCKED ACCOUNTS',
    'FAILED LOGIN ATTEMPTS',
    'RECENT PRIVILEGE CHANGES',
    'SUSPICIOUS ACCESS ALERTS',
    'Admin action queue',
    'Recent security &amp; audit events',
    'accounts_affected_today',
  ]) {
    assert.ok(dashboard.includes(label), `missing System Administrator dashboard content: ${label}`);
  }

  assert.match(dashboard, /Online now: Not tracked/);
  assert.match(dashboard, /Password reset requests: Not tracked/);
  assert.match(dashboard, /Role requests and conflicting-role reviews are not tracked/);
  assert.match(styles, /\.admin-metric-grid/);
  assert.match(styles, /\.admin-status-strip/);
});

test('add actions reuse one accessible modal instead of appending forms to the page', async () => {
  const originalDocument = globalThis.document;
  let appended = 0;
  let activeDialog;
  const listeners = new Map();
  const dialog = {
    focus() {},
    addEventListener() {},
  };
  const cancel = { addEventListener() {} };
  const form = { addEventListener() {} };
  const backdrop = {
    addEventListener() {},
    querySelector(selector) {
      return {
        '.dialog': dialog,
        '[data-cancel]': cancel,
        form,
        '[data-error]': {},
      }[selector];
    },
  };

  globalThis.document = {
    activeElement: { focus() {} },
    body: {
      append() {
        appended += 1;
        activeDialog = backdrop;
      },
    },
    createElement() {
      return {
        set innerHTML(_value) {},
        firstElementChild: backdrop,
      };
    },
    querySelector(selector) {
      return selector === '.dialog-backdrop.open' ? activeDialog : null;
    },
    addEventListener(type, callback) {
      listeners.set(type, callback);
    },
    removeEventListener(type) {
      listeners.delete(type);
    },
  };

  try {
    const { openDialog } = await import(`./assets/js/ui.js?modal-test=${Date.now()}`);
    const first = openDialog({
      title: 'Create employee',
      description: 'Add an employee.',
      bodyHtml: '<input name="name">',
      submitLabel: 'Create',
      onSubmit: async () => {},
    });
    const second = openDialog({
      title: 'Create employee',
      description: 'Add an employee.',
      bodyHtml: '<input name="name">',
      submitLabel: 'Create',
      onSubmit: async () => {},
    });

    assert.equal(first, second);
    assert.equal(appended, 1);
    assert.ok(listeners.has('keydown'));
  } finally {
    if (originalDocument === undefined) delete globalThis.document;
    else globalThis.document = originalDocument;
  }

  const [ui, styles] = await Promise.all([
    readFile(new URL('./assets/js/ui.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
  ]);
  assert.match(ui, /aria-modal="true"/);
  assert.match(ui, /document\.querySelector\('\.dialog-backdrop\.open'\)/);
  assert.match(styles, /\.dialog-backdrop\s*\{\s*position:\s*fixed/s);
});

test('settings page kicker icons use the same restrained size as page-header icons', async () => {
  const styles = await readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8');
  const pages = await readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8');

  assert.match(pages, /<div class="kicker">\$\{icons\.settings\} System Preferences<\/div>/);
  assert.match(styles, /\.page-head \.kicker svg,\s*\.page > \.card > \.kicker svg,\s*\.context-bar \.kicker svg\s*\{\s*width:\s*1\.1em;\s*height:\s*1\.1em/s);
});

test('organization sidebar destinations have authenticated pages and dashboard routing', async () => {
  const [main, pages, sidebar] = await Promise.all([
    readFile(new URL('./assets/js/main.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/sidebar-config.js', sourceRoot), 'utf8'),
  ]);

  for (const page of ['branches', 'warehouses', 'departments']) {
    const html = await readFile(new URL(`${page}.html`, sourceRoot), 'utf8');
    assert.match(html, new RegExp(`data-page="${page}"`));
    assert.match(sidebar, new RegExp(`href:\\s*['"]${page}\\.html['"]`));
    assert.match(main, /renderOrganization\(page, pageName\)/);
  }
  assert.match(pages, /const ORGANIZATION_PAGES = \{/);
  assert.match(pages, /createEndpoint: '\/api\/departments'/);
  assert.match(pages, /createEndpoint: '\/api\/warehouses'/);
});

test('dashboard navigation does not link to unimplemented page fragments', async () => {
  const [dashboard, sidebar] = await Promise.all([
    readFile(new URL('./assets/js/dashboard.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/sidebar-config.js', sourceRoot), 'utf8'),
  ]);

  assert.doesNotMatch(dashboard, /href=["'][^"']*#/);
  assert.doesNotMatch(sidebar, /href:\s*['"][^'"]*#/);
  for (const role of Object.keys(SIDEBAR_CONFIG)) {
    const links = getSidebarItems(role, ['*']).filter((item) => item.href);
    assert.ok(links.length, `${role} should have accessible workspace links`);
    assert.ok(links.every((item) => !item.href.includes('#')), `${role} has an unresolved page fragment`);
  }
  assert.doesNotMatch(dashboard, /onclick=/);
  assert.match(dashboard, /id="retry-dashboard"/);
  assert.doesNotMatch(sidebar, /badge:/);

  const destinations = new Set(
    Object.values(SIDEBAR_CONFIG).flatMap((items) => items.filter((item) => item.href).map((item) => item.href))
  );
  for (const destination of destinations) {
    await readFile(new URL(destination, sourceRoot), 'utf8');
  }
});

test('shared controls are wired and POS has a single payment method field', async () => {
  const [shell, pages, notifications] = await Promise.all([
    readFile(new URL('./assets/js/shell.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/notifications.js', sourceRoot), 'utf8'),
  ]);
  const salesRenderer = pages.slice(pages.indexOf('export async function renderSales'), pages.indexOf('function showTemporaryPasswordResult'));

  assert.match(shell, /searchInput\.addEventListener\('input'/);
  assert.match(shell, /hw-notif-btn.*addEventListener/s);
  assert.match(notifications, /export async function toggleNotificationCenter/);
  assert.match(notifications, /addEventListener\('click'/);
  assert.doesNotMatch(notifications, /onclick=/);
  assert.equal((salesRenderer.match(/name="payment_method"/g) || []).length, 1);
  assert.doesNotMatch(salesRenderer, /id="open-session-btn"/);
});

test('approval navigation uses a real page and supported approval endpoints', async () => {
  const [main, pages, sidebar] = await Promise.all([
    readFile(new URL('./assets/js/main.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/sidebar-config.js', sourceRoot), 'utf8'),
  ]);
  const html = await readFile(new URL('approvals.html', sourceRoot), 'utf8');

  assert.match(html, /data-page="approvals"/);
  assert.match(main, /pageName === 'approvals'.*renderApprovals/s);
  assert.match(sidebar, /href: 'approvals\.html'/);
  for (const endpoint of [
    '/api/approvals/requisition',
    '/api/approvals/purchase-order',
    '/api/approvals/leave',
    '/api/approvals/stock-adjustment',
  ]) {
    assert.ok(pages.includes(endpoint), `missing approval endpoint wiring: ${endpoint}`);
  }
  assert.match(pages, /ADJUSTMENT:\s*\{[\s\S]*permission: 'inventory:approve_adjust'/);
  assert.match(pages, /data-approval-action="APPROVE"/);
  assert.match(pages, /data-approval-action="REJECT"/);
  assert.match(sidebar, /inventory:approve_adjust/);
});

test('dynamic product and warehouse labels are escaped before HTML rendering', async () => {
  const [pages, dashboard] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/dashboard.js', sourceRoot), 'utf8'),
  ]);
  const { escapeHtml } = await import('./assets/js/ui.js');

  assert.equal(escapeHtml('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  assert.match(pages, /escapeHtml\(p\.itemname\)/);
  assert.match(pages, /escapeHtml\(product\.itemname\)/);
  assert.match(dashboard, /escapeHtml\(/);
});

test('employee directory preserves table readability on narrow screens and styles reset action as primary', async () => {
  const [pages, styles] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
  ]);
  const employees = pages.slice(pages.indexOf('export async function renderEmployees'), pages.indexOf('const APPROVAL_ACTIONS'));

  assert.match(employees, /id="table" class="employee-directory-table"/);
  assert.match(employees, /class="btn btn-primary btn-sm" data-reset-password/);
  assert.match(styles, /\.employee-directory-table \.table-wrap \.data\s*\{[^}]*min-width:\s*78rem/s);
  assert.match(styles, /\.table-wrap \.data td\s*\{[^}]*white-space:\s*nowrap/s);
  assert.match(styles, /\.employee-directory-table \.employee-account-actions\s*\{/);
});

test('shared tables and dashboard summary tables preserve content and scroll horizontally', async () => {
  const [ui, dashboard, styles] = await Promise.all([
    readFile(new URL('./assets/js/ui.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/dashboard.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/css/style.css', sourceRoot), 'utf8'),
  ]);

  assert.match(ui, /<div class="table-wrap">\s*<table class="data">/);
  assert.match(ui, /class="btn btn-primary" data-prev/);
  assert.match(ui, /class="btn btn-primary" data-next/);
  assert.match(styles, /\.table-wrap \.data\s*\{[^}]*width:\s*max-content;[^}]*min-width:\s*100%/s);
  assert.match(styles, /\.table-wrap \.data td\s*\{[^}]*white-space:\s*nowrap/s);
  assert.match(dashboard, /<div class="dashboard-table-wrap">\s*<table class="dashboard-table">/);
  assert.match(styles, /\.dashboard-table-wrap\s*\{[^}]*overflow-x:\s*auto/s);
  assert.match(styles, /\.dashboard-table\s*\{[^}]*width:\s*max-content;[^}]*min-width:\s*100%/s);
  assert.match(styles, /\.dashboard-table td\s*\{[^}]*white-space:\s*nowrap/s);
});