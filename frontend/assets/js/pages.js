import { apiRequest, API_URL, loadList } from './api.js';
import { field, money, openDialog, renderLoadingState, renderTable, selectField, showNotice } from './ui.js';
import { icons } from './icons.js';
import { buildGraphData, renderGraph } from './graph.js';
import { getCurrentUser, can } from './permissions.js';

// Legacy renderDashboard is now delegated to dashboard.js
// This stub satisfies any stale imports.
export async function renderDashboard(page) {
  const { renderDashboard: renderDept } = await import('./dashboard.js');
  await renderDept(page);
}

export async function renderLogin() {
  let departments = [];
  try {
    const res = await fetch(`${API_URL}/departments/public`, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) departments = data;
    }
  } catch {
    departments = [];
  }

  const staffDepts = departments.filter((d) => d.departmentname.trim().toLowerCase() !== 'administration');
  const root = document.getElementById('app');
  root.innerHTML = `
    <div class="auth-card">
      <div class="center">
        <div class="brand-mark" style="margin:0 auto 0.75rem">${icons.shield}</div>
        <h1>Hardware World</h1>
        <p class="kicker">Staff Member</p>
        <p class="muted">Sign in with your work account and assigned department.</p>
      </div>
      <div id="auth-error" class="notice error hidden"></div>
      <form id="login-form" class="form-grid">
        <label class="field">Name or email
          <input class="control" name="username" autocomplete="username" required placeholder="Enter your name or email">
        </label>
        <label class="field">Department
          <select class="control" name="department">
            <option value="" selected>Select your department</option>
            ${staffDepts.map((d) => `<option value="${d.departmentname}">${d.departmentname}</option>`).join('')}
          </select>
        </label>
        <label class="field">Password
          <input class="control" name="password" type="password" autocomplete="current-password" required placeholder="Enter your assigned password">
        </label>
        <button class="btn btn-primary" type="submit">Sign in</button>
      </form>
    </div>
  `;

  const form = root.querySelector('#login-form');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const errorEl = root.querySelector('#auth-error');
    errorEl.classList.add('hidden');
    try {
      const payload = {
        username: form.username.value.trim(),
        password: form.password.value,
        department: form.department.value || null,
        login_type: 'staff',
      };
      const loginResult = await fetch(`${API_URL}/login?cookie_only=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      }).then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail ?? 'Authentication failed.');
        return body;
      });
      window.location.replace(loginResult.requires_password_change ? 'change-password.html' : 'index.html');
    } catch (error) {
      errorEl.textContent = error instanceof Error ? error.message : 'Unable to sign in.';
      errorEl.classList.remove('hidden');
    }
  });
}

export function renderPasswordChange() {
  const root = document.getElementById('app');
  root.innerHTML = `
    <div class="auth-card">
      <div class="center">
        <div class="brand-mark" style="margin:0 auto 0.75rem">${icons.shield}</div>
        <h1>Set your personal password</h1>
        <p class="muted">Your administrator issued a temporary password. Change it before accessing your workspace.</p>
      </div>
      <div id="password-error" class="notice error hidden" role="alert"></div>
      <form id="password-change-form" class="form-grid">
        ${field('current_password', 'Temporary password', 'type="password" autocomplete="current-password" required')}
        ${field('new_password', 'New password', 'type="password" autocomplete="new-password" minlength="12" maxlength="72" required')}
        ${field('confirm_password', 'Confirm new password', 'type="password" autocomplete="new-password" minlength="12" maxlength="72" required')}
        <p class="muted">Use at least 12 characters. A memorable passphrase is fine.</p>
        <button class="btn btn-primary" type="submit">Save password and continue</button>
      </form>
    </div>
  `;

  root.querySelector('#password-change-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const error = root.querySelector('#password-error');
    error.classList.add('hidden');
    const currentPassword = form.elements.namedItem('current_password').value;
    const newPassword = form.elements.namedItem('new_password').value;
    const confirmation = form.elements.namedItem('confirm_password').value;
    if (newPassword !== confirmation) {
      error.textContent = 'The new passwords do not match.';
      error.classList.remove('hidden');
      return;
    }
    try {
      await apiRequest('/api/auth/initial-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      window.location.replace('index.html');
    } catch (reason) {
      error.textContent = reason instanceof Error ? reason.message : 'Unable to change your password.';
      error.classList.remove('hidden');
    }
  });
}

export async function renderCrud(page, config) {
  renderLoadingState(page, `Loading ${config.title.toLowerCase()}…`);
  const result = await loadList(config.endpoint);
  page.innerHTML = `
    <header class="page-head card">
      <div>
        <div class="kicker">${config.kicker}</div>
        <h1>${config.title}</h1>
        <p class="muted">${config.subtitle}</p>
      </div>
      ${config.create ? `<button class="btn btn-primary" id="add-btn">${icons.plus} ${config.create.trigger}</button>` : ''}
    </header>
    <div id="notice"></div>
    <div id="table"></div>
  `;
  showNotice(page.querySelector('#notice'), result.error, { onRetry: () => window.location.reload() });
  if (!result.error) {
    renderTable(page.querySelector('#table'), { columns: config.columns, data: result.data, searchKey: config.searchKey });
  }
  page.querySelector('#add-btn')?.addEventListener('click', () => {
    openDialog({
      title: config.create.title,
      description: config.create.description,
      submitLabel: config.create.submit,
      bodyHtml: config.create.fields,
      onSubmit: async (form) => {
        await config.create.submitFn(form);
        window.location.reload();
      },
    });
  });
}

export const CRUD_PAGES = {
  products: {
    endpoint: '/api/products',
    kicker: 'Hardware catalogue',
    title: 'Products & Stock Inventory',
    subtitle: 'Live product prices, stock levels, and reorder settings.',
    searchKey: 'itemname',
    columns: [
      { header: 'ID', key: 'itemid', sortable: true },
      { header: 'Item Name', key: 'itemname', sortable: true },
      { header: 'Category', key: 'category_name', sortable: true },
      { header: 'Unit', key: 'base_unit' },
      { header: 'Unit Price', key: 'unitprice', sortable: true, cell: (row) => money(row.unitprice) },
      { header: 'Available Stock', key: 'available_stock', sortable: true },
      { header: 'Reorder Level', key: 'reorderlevel', sortable: true },
      { header: 'Status', key: 'is_active', cell: (row) => row.is_active ? '<span style="color:var(--primary)">Active</span>' : '<span style="color:var(--destructive)">Inactive</span>' },
    ],
    create: {
      trigger: 'Add Product',
      title: 'Add product',
      description: 'Create a product in the live catalogue.',
      submit: 'Create product',
      fields: field('itemname', 'Item name', 'required') + field('description', 'Description') + field('unitprice', 'Selling Price (UGX)', 'type="number" min="0" step="0.01" required') + field('costprice', 'Cost Price (UGX)', 'type="number" min="0" step="0.01" required') + field('reorderlevel', 'Reorder level (qty)', 'type="number" min="0" required') + field('categoryid', 'Category ID', 'type="number" min="1" required'),
      submitFn: (form) => apiRequest('/api/products', { method: 'POST', body: JSON.stringify({ itemname: form.get('itemname'), description: form.get('description') || null, unitprice: Number(form.get('unitprice')), costprice: Number(form.get('costprice') || 0), reorderlevel: Number(form.get('reorderlevel')), categoryid: Number(form.get('categoryid')) }) }),
    },
  },
  categories: {
    endpoint: '/categories',
    kicker: 'Product taxonomy',
    title: 'Product Categories',
    subtitle: 'Categories currently stored in the live catalogue.',
    searchKey: 'categoryname',
    columns: [
      { header: 'Category ID', key: 'categoryid', sortable: true },
      { header: 'Category Name', key: 'categoryname', sortable: true },
    ],
    create: {
      trigger: 'Add Category',
      title: 'Add product category',
      description: 'Create a category in the live catalogue.',
      submit: 'Create category',
      fields: field('categoryname', 'Category name', 'required'),
      submitFn: (form) => apiRequest('/categories', { method: 'POST', body: JSON.stringify({ categoryname: form.get('categoryname') }) }),
    },
  },
  suppliers: {
    endpoint: '/api/suppliers',
    kicker: 'Vendor directory',
    title: 'Suppliers & Manufacturers',
    subtitle: 'Live supplier records from the database.',
    searchKey: 'suppliername',
    columns: [
      { header: 'Supplier ID', key: 'supplierid', sortable: true },
      { header: 'Company', key: 'suppliername', sortable: true },
      { header: 'Contact', key: 'contactperson' },
      { header: 'Phone', key: 'phone' },
      { header: 'Address', key: 'address' },
    ],
    create: {
      trigger: 'Add Supplier',
      title: 'Register supplier',
      description: 'Add a supplier to the live vendor registry.',
      submit: 'Save supplier',
      fields: field('suppliername', 'Company name', 'required') + field('contactperson', 'Contact person') + field('phone', 'Phone') + field('address', 'Address'),
      submitFn: (form) => apiRequest('/suppliers', { method: 'POST', body: JSON.stringify({ suppliername: form.get('suppliername'), contactperson: form.get('contactperson') || null, phone: form.get('phone') || null, address: form.get('address') || null }) }),
    },
  },
  'purchase-orders': {
    endpoint: '/api/purchase-orders',
    kicker: 'Procurement',
    title: 'Purchase Orders',
    subtitle: 'Purchase orders require an approved requisition and a separate approver.',
    searchKey: 'supplier_name',
    columns: [
      { header: 'PO #', key: 'po_id', sortable: true },
      { header: 'Date', key: 'orderdate', sortable: true },
      { header: 'Supplier', key: 'supplier_name', sortable: true },
      { header: 'Officer', key: 'officer_name' },
      { header: 'Total', key: 'total_amount', cell: (row) => money(row.total_amount) },
      { header: 'Status', key: 'status', sortable: true },
    ],
    create: {
      trigger: 'Create PO',
      title: 'Create purchase order',
      description: 'Issue an order from a requisition after a manager approves it.',
      submit: 'Issue order',
      fields: field('supplierid', 'Supplier ID', 'type="number" min="1" required') + field('requisition_id', 'Approved requisition ID', 'type="number" min="1" required'),
      submitFn: (form) => apiRequest('/purchase-orders', { method: 'POST', body: JSON.stringify({ supplierid: Number(form.get('supplierid')), requisition_id: Number(form.get('requisition_id')) }) }),
    },
  },
  payroll: {
    endpoint: '/api/payroll',
    kicker: 'HR compensation',
    title: 'Payroll & Salary Accounting',
    subtitle: 'Payroll records — restricted to HR, Finance, and Management.',
    searchKey: 'employee_name',
    columns: [
      { header: 'Payroll ID', key: 'payrollid', sortable: true },
      { header: 'Employee', key: 'employee_name', sortable: true },
      { header: 'Month', key: 'month', sortable: true },
      { header: 'Gross Pay', key: 'grosspay', cell: (row) => money(row.grosspay) },
      { header: 'Deductions', key: 'deductions', cell: (row) => money(row.deductions) },
      { header: 'Net Pay', key: 'netpay', cell: (row) => money(row.netpay) },
    ],
  },
  ledger: {
    endpoint: '/api/journals',
    kicker: 'Accounting',
    title: 'General Ledger Journals',
    subtitle: 'Double-entry journal entries from all ERP modules.',
    searchKey: 'description',
    columns: [
      { header: 'Entry #', key: 'entry_number', sortable: true },
      { header: 'Date', key: 'entry_date', sortable: true },
      { header: 'Description', key: 'description' },
      { header: 'Reference', key: 'reference_type' },
      { header: 'Total', key: 'total_amount', cell: (row) => money(row.total_amount) },
    ],
  },
};

export async function renderSales(page, user = window.__HW_USER__) {
  renderLoadingState(page, 'Loading sales and products…');
  const [sales, products] = await Promise.all([
    loadList('/sales'),
    loadList('/products'),
  ]);
  const cashiers = [user].filter(Boolean);
  const branches = { data: [{ branchid: user?.branchid, branchname: user?.branch_name }] };
  const canSell = ['Cashier', 'Admin'].includes(user?.roletype);
  const hasPOS = canSell;
  let cashierSession = null;
  let cashierSessionError = null;
  if (canSell) {
    try {
      cashierSession = await apiRequest('/cashier-sessions/current');
    } catch (error) {
      cashierSessionError = error instanceof Error ? error.message : 'Unable to check the cashier session.';
    }
  }
  page.innerHTML = `
    <header class="page-head card">
      <div>
        <div class="kicker">${icons.banknote} Point of sale</div>
        <h1>Sales & Retail Checkout</h1>
        <p class="muted">Completed sales with stock deduction, payment, and finance journals.</p>
      </div>
    </header>
    <div id="session-notice"></div>
    ${canSell && !cashierSession && !cashierSessionError ? `<form id="open-cashier-session" class="card form-grid"><h2>Open cashier session</h2><label class="field">Opening cash float (UGX)<input class="control" name="opening_float" type="number" min="0" step="0.01" value="0" required></label><button class="btn btn-primary" type="submit">Open session</button></form>` : ''}
    ${cashierSession ? `<div class="notice">Cashier session #${cashierSession.session_id} is open · Opening float ${money(cashierSession.opening_float)}</div>` : ''}
    <form id="pos" class="pos-grid ${!canSell || !cashierSession ? 'hidden' : ''}">
      <section class="card">
        <div style="display:flex;gap:.5rem;margin-bottom:.75rem">
          <select class="control" id="product-select" style="flex:1">
            <option value="">Select a product</option>
            ${products.data.filter((p) => p.is_active && Number(p.stock_qty) > 0).map((p) => `<option value="${p.itemid}">${p.itemname} · ${money(p.unitprice)} · ${p.stock_qty} in stock</option>`).join('')}
          </select>
          <button type="button" class="btn btn-primary" id="add-line">${icons.plus} Add</button>
        </div>
        <div id="lines"><p class="muted center">Add products to begin a sale.</p></div>
      </section>
      <aside class="card form-grid">
        <div><h2>Checkout</h2></div>
        <label class="field">Branch
          <select class="control" name="branchid" required>
            ${branches.data.map((b) => `<option value="${b.branchid}" ${b.branchid === user?.branchid ? 'selected' : ''}>${b.branchname}</option>`).join('')}
          </select>
        </label>
        <label class="field">Payment Method
          <select class="control" name="payment_method">
            <option value="CASH">Cash</option>
            <option value="MOBILE_MONEY">Mobile Money</option>
            <option value="CARD">Card / Bank</option>
            <option value="CREDIT">Customer Credit</option>
          </select>
        </label>
        <input class="control" name="customername" placeholder="Customer name">
        <input class="control" name="customerphone" placeholder="Phone number">
        <div class="page-head"><span>Total</span><strong id="pos-total">${money(0)}</strong></div>
        <button class="btn btn-primary" type="submit" id="complete-sale" disabled>Complete Sale</button>
      </aside>
    </form>
    <section id="receipt" class="notice hidden" aria-live="polite"></section>
    <div id="notice"></div>
    <div id="table"></div>
  `;
  showNotice(page.querySelector('#notice'), sales.error || products.error, { onRetry: () => window.location.reload() });
  showNotice(page.querySelector('#session-notice'), cashierSessionError, { onRetry: () => window.location.reload() });
  const savedReceipt = sessionStorage.getItem('hw_last_receipt');
  if (savedReceipt) {
    try {
      const receiptData = JSON.parse(savedReceipt);
      const receipt = page.querySelector('#receipt');
      receipt.classList.remove('hidden');
      receipt.textContent = `Sale #${receiptData.saleid} completed · Total ${money(receiptData.totalamount)} · COGS ${money(receiptData.cogs)} · Gross profit ${money(receiptData.gross_profit)}`;
      const printButton = document.createElement('button');
      printButton.className = 'btn btn-outline';
      printButton.textContent = 'Print receipt';
      printButton.addEventListener('click', () => window.print());
      receipt.appendChild(printButton);
      sessionStorage.removeItem('hw_last_receipt');
    } catch { sessionStorage.removeItem('hw_last_receipt'); }
  }
  page.querySelector('#open-cashier-session')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Opening session…';
    try {
      await apiRequest('/cashier-sessions/open', { method: 'POST', body: JSON.stringify({ opening_float: form.opening_float.value }) });
      window.location.reload();
    } catch (error) {
      showNotice(page.querySelector('#notice'), error instanceof Error ? error.message : 'Unable to open cashier session.');
      submitButton.disabled = false;
      submitButton.textContent = 'Open session';
    }
  });
  if (!sales.error) renderTable(page.querySelector('#table'), {
    columns: [
      { header: 'Receipt #', key: 'saleid', sortable: true },
      { header: 'Date', key: 'saledate', sortable: true },
      { header: 'Customer', key: 'customer_name' },
      { header: 'Cashier', key: 'cashier_name' },
      { header: 'Branch', key: 'branch_name' },
      { header: 'Payment', key: 'payment_method' },
      { header: 'Total', key: 'totalamount', sortable: true, cell: (row) => money(row.totalamount) },
    ],
    data: sales.data,
    searchKey: 'customer_name',
  });

  if (!hasPOS) return;

  const lines = [];
  const paintLines = () => {
    const box = page.querySelector('#lines');
    if (!lines.length) {
      box.innerHTML = '<p class="muted center">Add products to begin a sale.</p>';
    } else {
      box.innerHTML = lines.map((line) => {
        const product = products.data.find((p) => p.itemid === line.itemid);
        return `<div class="line" data-id="${line.itemid}"><div><strong>${product.itemname}</strong><div class="muted">${money(product.unitprice)} each · ${product.stock_qty} available</div></div><div class="qty"><button type="button" data-dec>-</button><input class="control" type="number" min="0.001" step="0.001" value="${line.quantity}"><button type="button" data-inc>+</button></div><button type="button" data-del>${icons.trash}</button></div>`;
      }).join('');
    }
    const total = lines.reduce((sum, line) => {
      return sum + (products.data.find((p) => p.itemid === line.itemid)?.unitprice ?? 0) * line.quantity;
    }, 0);
    page.querySelector('#pos-total').textContent = money(total);
    page.querySelector('#complete-sale').disabled = !lines.length;
  };

  page.querySelector('#add-line').addEventListener('click', () => {
    const sel = page.querySelector('#product-select');
    const itemid = Number(sel.value);
    if (!itemid) return;
    const existing = lines.find((l) => l.itemid === itemid);
    const selectedProduct = products.data.find((p) => p.itemid === itemid);
    if (existing) existing.quantity = Math.min(Number(selectedProduct.stock_qty), existing.quantity + 1);
    else lines.push({ itemid, quantity: 1 });
    sel.value = '';
    showNotice(page.querySelector('#notice'), null);
    paintLines();
  });

  page.querySelector('#lines').addEventListener('click', (event) => {
    const row = event.target.closest('.line');
    if (!row) return;
    const line = lines.find((l) => l.itemid === Number(row.dataset.id));
    if (event.target.closest('[data-inc]')) {
      const product = products.data.find((p) => p.itemid === line.itemid);
      line.quantity = Math.min(Number(product.stock_qty), line.quantity + 1);
    }
    if (event.target.closest('[data-dec]')) line.quantity -= 1;
    if (event.target.closest('[data-del]') || line.quantity < 1) {
      const idx = lines.findIndex((l) => l.itemid === line.itemid);
      lines.splice(idx, 1);
    }
    paintLines();
  });
  page.querySelector('#lines').addEventListener('change', (event) => {
    if (!event.target.matches('input[type="number"]')) return;
    const row = event.target.closest('.line');
    const line = lines.find((item) => item.itemid === Number(row.dataset.id));
    const product = products.data.find((item) => item.itemid === line.itemid);
    const quantity = Number(event.target.value);
    line.quantity = Number.isFinite(quantity) && quantity > 0
      ? Math.min(quantity, Number(product.stock_qty))
      : 0;
    if (!line.quantity) lines.splice(lines.indexOf(line), 1);
    paintLines();
  });
  page.querySelector('#pos').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    const noticeEl = page.querySelector('#notice');
    const btn = page.querySelector('#complete-sale');
    btn.disabled = true;
    btn.textContent = 'Processing…';
    try {
      const receipt = await apiRequest('/sales', {
        method: 'POST',
        headers: { 'Idempotency-Key': ikey },
        body: JSON.stringify({
          customername: form.customername.value || null,
          customerphone: form.customerphone.value || null,
          employeeid: user.employeeid,
          branchid: Number(form.branchid.value),
          payment_method: form.payment_method.value,
          items: lines.map((line) => ({ itemid: line.itemid, quantity: line.quantity })),
        }),
      });
      sessionStorage.setItem('hw_last_receipt', JSON.stringify(receipt));
      window.location.reload();
    } catch (error) {
      showNotice(noticeEl, error.message);
      btn.disabled = false;
      btn.textContent = 'Complete Sale';
    }
  });
}

function showTemporaryPasswordResult(dialog, account) {
  dialog.querySelector('p.muted').textContent = 'Copy this temporary password and share it securely. It will not be shown again.';
  const fields = dialog.querySelector('.form-grid');
  fields.replaceChildren();
  const message = document.createElement('p');
  message.textContent = `${account.name || 'The employee'} must change this password at first sign-in. It expires ${new Date(account.temporary_password_expires_at).toLocaleString()}.`;
  const passwordInput = document.createElement('input');
  passwordInput.className = 'control';
  passwordInput.readOnly = true;
  passwordInput.value = account.temporary_password;
  passwordInput.setAttribute('aria-label', 'One-time temporary password');
  const status = document.createElement('p');
  status.className = 'muted';
  const actions = dialog.querySelector('.dialog-actions');
  const submit = actions.querySelector('button[type="submit"]');
  submit.hidden = true;
  const done = actions.querySelector('[data-cancel]');
  done.textContent = 'Done';
  done.addEventListener('click', () => window.location.reload());
  const copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'btn btn-outline';
  copy.textContent = 'Copy password';
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(account.temporary_password);
      status.textContent = 'Temporary password copied.';
    } catch {
      passwordInput.focus();
      passwordInput.select();
      status.textContent = 'Clipboard access was unavailable. The password is selected; copy it now.';
    }
  });
  actions.prepend(copy);
  fields.append(message, passwordInput, status);
}

export async function renderEmployees(page) {
  renderLoadingState(page, 'Loading employee directory…');
  const [employees, branches, departments] = await Promise.all([
    loadList('/employees'),
    loadList('/branches'),
    loadList('/departments'),
  ]);
  page.innerHTML = `
    <header class="page-head card">
      <div>
        <div class="kicker">${icons.users} Human resources</div>
        <h1>Staff & Employee Directory</h1>
        <p class="muted">Live employees, departments, branches, and role assignments.</p>
      </div>
      <button class="btn btn-primary" id="add-btn">${icons.plus} Add Employee</button>
    </header>
    <div id="notice"></div>
    <div id="table"></div>
  `;
  const loadError = employees.error || branches.error || departments.error;
  showNotice(page.querySelector('#notice'), loadError, { onRetry: () => window.location.reload() });
  if (!loadError) renderTable(page.querySelector('#table'), {
    columns: [
      { header: 'Employee ID', key: 'employeeid', sortable: true },
      { header: 'Name', key: 'name', sortable: true },
      { header: 'Email', key: 'email' },
      { header: 'Role', key: 'roletype', sortable: true },
      { header: 'Department', key: 'department_name' },
      { header: 'Account Status', key: 'account_status' },
      { header: 'Branch', key: 'branch_name' },
      { header: 'Phone', key: 'phone' },
      { header: 'Date Hired', key: 'datehired', sortable: true },
      {
        header: 'Account Actions',
        key: 'employeeid',
        cell: (employee) => can('admin:users') && employee.employeeid !== getCurrentUser()?.employeeid
          ? `<div class="flex gap-2"><button class="btn btn-outline btn-sm" data-reset-password="${employee.employeeid}">Reset password</button>${employee.is_locked ? `<button class="btn btn-outline btn-sm" data-unlock-user="${employee.employeeid}">Unlock</button>` : ''}</div>`
          : '',
      },
    ],
    data: employees.data,
    searchKey: 'name',
  });
  page.querySelector('#table').addEventListener('click', async (event) => {
    const unlockButton = event.target.closest('[data-unlock-user]');
    if (unlockButton) {
      unlockButton.disabled = true;
      try {
        await apiRequest('/api/users/unlock', {
          method: 'POST',
          body: JSON.stringify({ user_id: Number(unlockButton.dataset.unlockUser) }),
        });
        window.location.reload();
      } catch (error) {
        showNotice(page.querySelector('#notice'), error instanceof Error ? error.message : 'Unable to unlock account.');
        unlockButton.disabled = false;
      }
      return;
    }
    const button = event.target.closest('[data-reset-password]');
    if (!button) return;
    const userId = Number(button.dataset.resetPassword);
    const employee = employees.data.find((item) => item.employeeid === userId);
    openDialog({
      title: 'Issue a temporary password',
      description: `Generate a one-time password for ${employee?.name || 'this employee'}. They must change it at next sign-in.`,
      bodyHtml: '<p class="muted">The new password will be shown once and expires after 24 hours.</p>',
      submitLabel: 'Generate password',
      onSubmit: async () => {
        const result = await apiRequest('/api/users/reset-password', {
          method: 'POST',
          body: JSON.stringify({ user_id: userId }),
        });
        showTemporaryPasswordResult(page.querySelector('.dialog-backdrop .dialog'), {
          ...result,
          name: employee?.name,
        });
        return false;
      },
    });
  });
  const addButton = page.querySelector('#add-btn');
  if (loadError) {
    addButton.disabled = true;
    addButton.title = 'Employee data could not be loaded. Retry before adding an employee.';
  }
  addButton.addEventListener('click', () => {
    const backdrop = openDialog({
      title: 'Provision New Employee & Assign Access',
      description: 'Create an employee sign-in account. A one-time temporary password will be generated and must be changed at first sign-in.',
      bodyHtml: `
        <div class="form-grid two">
          ${field('name', 'Full name', 'required placeholder="e.g. Samuel Okello"')}
          ${field('nin', 'National ID (NIN)', 'required')}
          ${field('email', 'Email Address', 'type="email" required')}
          ${field('phone', 'Phone Number', 'type="tel"')}
          ${field('datehired', 'Date hired', 'type="date"')}
          ${field('salary', 'Salary (UGX)', 'type="number" min="0" required')}
          <label class="field">Assigned Role (RBAC)
            <select class="control" name="roletype" id="roletype">
              <option value="Cashier">Cashier (Sales & POS)</option>
              <option value="Procurement Officer">Procurement Officer</option>
              <option value="Accountant">Accountant</option>
              <option value="HR Staff">HR Staff</option>
              <option value="Branch Manager">Branch Manager</option>
              <option value="Owner / Executive">Owner / Executive</option>
            </select>
          </label>
          ${selectField('branchid', 'Branch Assignment', `<option value="">Select branch</option>${branches.data.map((b) => `<option value="${b.branchid}">${b.branchname}</option>`).join('')}`, true)}
          ${selectField('departmentid', 'Department (ABAC Policy)', `<option value="">Select assigned department</option>${departments.data.map((d) => `<option value="${d.departmentid}">${d.departmentname}</option>`).join('')}`, true)}
          ${selectField('supervisorid', 'Supervisor (optional)', `<option value="">No supervisor</option>${employees.data.map((e) => `<option value="${e.employeeid}">${e.name}</option>`).join('')}`)}
        </div>
        <div id="role-fields">${field('pos_terminalid', 'Assigned POS Terminal ID', 'placeholder="e.g. POS-TERMINAL-02" required')}</div>
      `,
      submitLabel: 'Provision Account',
      onSubmit: async (form) => {
        const num = (key) => {
          const value = String(form.get(key) || '').trim();
          return value ? Number(value) : null;
        };
        const created = await apiRequest('/employees', {
          method: 'POST',
          body: JSON.stringify({
            name: form.get('name'),
            nin: form.get('nin'),
            email: form.get('email') || null,
            password: form.get('password') || null,
            phone: form.get('phone') || null,
            datehired: form.get('datehired') || null,
            salary: Number(form.get('salary')),
            departmentid: Number(form.get('departmentid')),
            branchid: Number(form.get('branchid')),
            supervisorid: num('supervisorid'),
            roletype: form.get('roletype') === 'Owner / Executive' ? 'Branch Manager' : form.get('roletype'),
            pos_terminalid: form.get('pos_terminalid') || null,
            approvallimit: num('approvallimit'),
            certificationnumber: form.get('certificationnumber') || null,
            hr_role: form.get('hr_role') || null,
            managementlevel: form.get('roletype') === 'Owner / Executive'
              ? 'Owner / Executive'
              : (form.get('managementlevel') || null),
          }),
        });
        if (!created.temporary_password) {
          window.location.reload();
          return;
        }
        showTemporaryPasswordResult(backdrop.querySelector('.dialog'), created);
        return false;
      },
    });
    const roleFields = {
      Cashier: field('pos_terminalid', 'Assigned POS Terminal ID', 'required'),
      'Procurement Officer': field('approvallimit', 'Approval Limit (UGX)', 'type="number" min="0" required'),
      Accountant: field('certificationnumber', 'CPA / Accounting Certification Number'),
      'HR Staff': field('hr_role', 'HR Designation', 'required'),
      'Branch Manager': field('managementlevel', 'Management Level'),
      'Owner / Executive': field('managementlevel', 'Management Level', 'value="Owner / Executive" readonly'),
    };
    backdrop.querySelector('#roletype')?.addEventListener('change', (event) => {
      backdrop.querySelector('#role-fields').innerHTML = roleFields[event.target.value] || '';
    });
  });
}

// Stub exports for page renderers called from main.js
// These delegate to CRUD_PAGES for now and can be replaced with richer pages

export async function renderPayroll(page) {
  const user = getCurrentUser() || window.__HW_USER__;
  // Rule 9: if cashier or sales-only role, show only their own payslip
  if (!can('payroll:view') && user) {
    try {
      const slips = await apiRequest(`/api/payroll/payslips?employee_id=${user.employeeid}`);
      page.innerHTML = `
        <header class="page-head card"><div><h1>My Payslip</h1></div></header>
        <div id="table"></div>`;
      renderTable(page.querySelector('#table'), {
        columns: [
          { header: 'Month', key: 'month' },
          { header: 'Gross Pay', key: 'gross_pay', cell: (r) => money(r.gross_pay) },
          { header: 'Deductions', key: 'deductions', cell: (r) => money(r.deductions) },
          { header: 'Net Pay', key: 'net_pay', cell: (r) => money(r.net_pay) },
          { header: 'Status', key: 'payment_status' },
        ],
        data: slips,
        searchKey: 'month',
      });
    } catch (e) {
      page.innerHTML = `<div class="card" style="padding:2rem;text-align:center"><p class="muted">🔒 ${e.message}</p></div>`;
    }
    return;
  }
  await renderCrud(page, CRUD_PAGES.payroll);
}

export async function renderLedger(page) {
  await renderCrud(page, CRUD_PAGES.ledger);
}

export async function renderPurchaseOrders(page) {
  await renderCrud(page, CRUD_PAGES['purchase-orders']);
}

export async function renderAuditLogs(page) {
  renderLoadingState(page, 'Loading audit logs…');
  const result = await loadList('/api/audit-logs');
  page.innerHTML = `
    <header class="page-head card">
      <div><div class="kicker">Security</div><h1>Audit Logs</h1></div>
    </header>
    <div id="notice"></div>
    <div id="table"></div>`;
  showNotice(page.querySelector('#notice'), result.error, { onRetry: () => window.location.reload() });
  const items = Array.isArray(result.data) ? result.data : (result.data?.items || []);
  if (!result.error) renderTable(page.querySelector('#table'), {
    columns: [
      { header: 'Time', key: 'timestamp', sortable: true },
      { header: 'User', key: 'username_or_email' },
      { header: 'Action', key: 'action', sortable: true },
      { header: 'Module', key: 'module' },
      { header: 'IP', key: 'ip_address' },
      { header: 'Details', key: 'details' },
    ],
    data: items,
    searchKey: 'action',
  });
}

const APPROVAL_ACTIONS = {
  REQUISITION: {
    permission: 'procurement:approve_req',
    endpoint: '/api/approvals/requisition',
    idField: 'requisition_id',
  },
  PO: {
    permission: 'procurement:po_approve',
    endpoint: '/api/approvals/purchase-order',
    idField: 'po_id',
  },
  LEAVE: {
    permission: 'hr:leave',
    endpoint: '/api/approvals/leave',
    idField: 'leave_id',
  },
};

export async function renderApprovals(page) {
  renderLoadingState(page, 'Loading pending approvals…');
  const result = await loadList('/api/approvals');
  page.innerHTML = `
    <header class="page-head card">
      <div><div class="kicker">${icons.shield} Workflow</div><h1>Pending Approvals</h1>
        <p class="muted">Review requests your account is authorized to approve or reject.</p>
      </div>
    </header>
    <div id="notice"></div>
    <div id="table"></div>`;
  showNotice(page.querySelector('#notice'), result.error, { onRetry: () => window.location.reload() });
  if (result.error) return;

  const approvals = Array.isArray(result.data) ? result.data : [];
  renderTable(page.querySelector('#table'), {
    columns: [
      { header: 'Type', key: 'type', sortable: true },
      { header: 'Request', key: 'description' },
      { header: 'Requested By', key: 'requester', sortable: true },
      { header: 'Submitted', key: 'created_at', sortable: true, cell: (item) => item.created_at ? new Date(item.created_at).toLocaleString() : '—' },
      {
        header: 'Decision',
        key: 'id',
        cell: (item) => {
          const action = APPROVAL_ACTIONS[item.type];
          if (!action || !can(action.permission)) return '<span class="muted">No action available</span>';
          return `<div class="flex gap-2">
            <button class="btn btn-primary btn-sm" type="button" data-approval-type="${item.type}" data-approval-id="${item.id}" data-approval-action="APPROVE">Approve</button>
            <button class="btn btn-outline btn-sm" type="button" data-approval-type="${item.type}" data-approval-id="${item.id}" data-approval-action="REJECT">Reject</button>
          </div>`;
        },
      },
    ],
    data: approvals,
    searchKey: 'description',
  });

  page.querySelector('#table').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-approval-action]');
    if (!button) return;
    const action = APPROVAL_ACTIONS[button.dataset.approvalType];
    if (!action || !can(action.permission)) return;
    if (button.dataset.approvalAction === 'REJECT' && !window.confirm('Reject this request?')) return;
    button.disabled = true;
    const buttons = button.parentElement.querySelectorAll('button');
    buttons.forEach((item) => { item.disabled = true; });
    try {
      await apiRequest(action.endpoint, {
        method: 'POST',
        body: JSON.stringify({
          [action.idField]: Number(button.dataset.approvalId),
          action: button.dataset.approvalAction,
        }),
      });
      await renderApprovals(page);
    } catch (error) {
      showNotice(page.querySelector('#notice'), error instanceof Error ? error.message : 'Unable to update this approval.');
      buttons.forEach((item) => { item.disabled = false; });
    }
  });
}

export async function renderSettings(page) {
  renderLoadingState(page, 'Loading system settings…');
  const employees = await loadList('/employees');
  const colors = {
    Cashier: 'background:#dbeafe;color:#1d4ed8',
    'Procurement Officer': 'background:#fef3c7;color:#b45309',
    Accountant: 'background:#ede9fe;color:#6d28d9',
    'HR Staff': 'background:#dcfce7;color:#15803d',
    'Branch Manager': 'background:#fee2e2;color:#b91c1c',
    Admin: 'background:#e2e8f0;color:#334155',
  };
  page.innerHTML = `
    <header class="card">
      <div class="kicker">${icons.settings} System Preferences</div>
      <h1>Branch & Store Settings</h1>
      <p class="muted">Configure branch operations, team members, and role-based access control.</p>
    </header>
    <div id="notice"></div>
    <div class="grid-2">
      <div class="card">
        <h2>Team Members</h2>
        <div class="form-grid">
          ${employees.error ? '<p class="muted">Team data is unavailable until the connection recovers.</p>' : employees.data.length ? employees.data.map((m) => `<div class="team-row"><div><strong>${m.name}</strong><div class="muted">ID: ${m.employeeid}</div></div><span class="badge" style="${colors[m.roletype] || ''}">${m.roletype}</span></div>`).join('') : '<p class="muted">No team members yet.</p>'}
        </div>
      </div>
      <div class="card">
        <h2>System Status</h2>
        <p class="page-head"><span>Auth Configured</span><span class="badge">JWT enabled</span></p>
        <p class="page-head"><span>Authorization</span><span class="badge">API role checks</span></p>
        <p class="muted">FastAPI validates the signed-in employee's role and permissions before allowing access to protected operations.</p>
      </div>
    </div>
    <div class="card">
      <h2>Business Profile</h2>
      <p class="muted">Business identity and tax settings are not currently editable in this interface. The system reports all monetary values in UGX.</p>
    </div>
  `;
  showNotice(page.querySelector('#notice'), employees.error, { onRetry: () => window.location.reload() });
}

const ORGANIZATION_PAGES = {
  branches: {
    title: 'Company Branches',
    endpoint: '/api/branches',
    createEndpoint: '/branches',
    columns: [
      { header: 'Branch ID', key: 'branchid', sortable: true },
      { header: 'Branch', key: 'branchname', sortable: true },
      { header: 'Location', key: 'location' },
      { header: 'Contact Number', key: 'contactnumber' },
    ],
    fields: () => field('branchname', 'Branch name', 'required')
      + field('location', 'Location', 'required')
      + field('contactnumber', 'Contact number', 'type="tel"'),
    payload: (form) => ({
      branchname: form.get('branchname'),
      location: form.get('location'),
      contactnumber: form.get('contactnumber') || null,
    }),
  },
  departments: {
    title: 'Departments',
    endpoint: '/api/departments',
    createEndpoint: '/api/departments',
    columns: [
      { header: 'Department ID', key: 'departmentid', sortable: true },
      { header: 'Department', key: 'departmentname', sortable: true },
      { header: 'Branch', key: 'branch_name' },
    ],
    fields: (branches) => field('departmentname', 'Department name', 'required')
      + selectField('branchid', 'Branch', `<option value="">Select branch</option>${branches.map((branch) => `<option value="${branch.branchid}">${branch.branchname}</option>`).join('')}`, true),
    payload: (form) => ({
      departmentname: form.get('departmentname'),
      branchid: Number(form.get('branchid')),
    }),
  },
  warehouses: {
    title: 'Warehouses',
    endpoint: '/api/warehouses',
    createEndpoint: '/api/warehouses',
    columns: [
      { header: 'Warehouse ID', key: 'warehouse_id', sortable: true },
      { header: 'Warehouse', key: 'warehouse_name', sortable: true },
      { header: 'Branch', key: 'branch_name' },
      { header: 'Location', key: 'location' },
      { header: 'Status', key: 'is_active', cell: (warehouse) => warehouse.is_active ? 'Active' : 'Inactive' },
    ],
    fields: (branches) => field('warehouse_name', 'Warehouse name', 'required')
      + selectField('branch_id', 'Branch', `<option value="">Select branch</option>${branches.map((branch) => `<option value="${branch.branchid}">${branch.branchname}</option>`).join('')}`, true)
      + field('location', 'Location'),
    payload: (form) => ({
      warehouse_name: form.get('warehouse_name'),
      branch_id: Number(form.get('branch_id')),
      location: form.get('location') || null,
      is_active: true,
    }),
  },
};

export async function renderOrganization(page, pageName) {
  const config = ORGANIZATION_PAGES[pageName];
  if (!config) {
    page.innerHTML = '<div class="card" role="alert">Organization page not found.</div>';
    return;
  }

  renderLoadingState(page, `Loading ${config.title.toLowerCase()}…`);
  const [records, branches] = await Promise.all([
    loadList(config.endpoint),
    pageName === 'branches' ? Promise.resolve({ data: [] }) : loadList('/api/branches'),
  ]);

  page.innerHTML = `
    <header class="page-head card">
      <div>
        <div class="kicker">${icons.settings} Organisation setup</div>
        <h1>${config.title}</h1>
        <p class="muted">Manage company structure and branch locations.</p>
      </div>
      ${can('admin:users') ? `<button class="btn btn-primary" id="add-btn">${icons.plus} Add ${pageName === 'branches' ? 'Branch' : pageName === 'departments' ? 'Department' : 'Warehouse'}</button>` : ''}
    </header>
    <div id="notice"></div>
    <div id="table"></div>
  `;

  const loadError = records.error || branches.error;
  showNotice(page.querySelector('#notice'), loadError, { onRetry: () => window.location.reload() });
  if (!loadError) {
    const branchNames = new Map(branches.data.map((branch) => [branch.branchid, branch.branchname]));
    const rows = records.data.map((record) => ({
      ...record,
      branch_name: record.branch_name || branchNames.get(record.branchid ?? record.branch_id) || 'Unknown branch',
    }));
    renderTable(page.querySelector('#table'), {
      columns: config.columns,
      data: rows,
      searchKey: pageName === 'branches' ? 'branchname' : pageName === 'departments' ? 'departmentname' : 'warehouse_name',
    });
  }

  const addButton = page.querySelector('#add-btn');
  if (!addButton) return;
  if (loadError) {
    addButton.disabled = true;
    addButton.title = 'Required organization data could not be loaded. Retry before adding a record.';
    return;
  }
  addButton.addEventListener('click', () => {
    openDialog({
      title: `Add ${pageName === 'branches' ? 'branch' : pageName === 'departments' ? 'department' : 'warehouse'}`,
      description: `Create a ${pageName === 'branches' ? 'company branch' : pageName === 'departments' ? 'department assigned to a branch' : 'warehouse assigned to a branch'}.`,
      bodyHtml: config.fields(branches.data),
      submitLabel: 'Save',
      onSubmit: async (form) => {
        await apiRequest(config.createEndpoint, {
          method: 'POST',
          body: JSON.stringify(config.payload(form)),
        });
        window.location.reload();
      },
    });
  });
}
