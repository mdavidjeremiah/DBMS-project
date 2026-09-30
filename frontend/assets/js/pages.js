import { apiRequest, API_URL, loadList } from './api.js';
import { field, money, openDialog, renderTable, selectField, showNotice } from './ui.js';
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

  const staffDepts = departments.filter((d) => d.departmentname !== 'Administration');
  const root = document.getElementById('app');
  root.innerHTML = `
    <div class="auth-card">
      <div class="center">
        <div class="brand-mark" style="margin:0 auto 0.75rem">${icons.shield}</div>
        <h1>Hardware World</h1>
        <p class="kicker">Enterprise DBMS Portal</p>
        <p class="muted">Role-Based & Attribute-Based Access Control (RBAC & ABAC)</p>
      </div>
      <div class="switcher">
        <button type="button" class="active" data-type="staff">${icons.usercheck} Staff Member</button>
        <button type="button" data-type="admin">${icons.shield} Administrator</button>
      </div>
      <div id="auth-error" class="notice error hidden"></div>
      <form id="login-form" class="form-grid">
        <label class="field">Full Name or Email
          <input class="control" name="username" required placeholder="Enter your name or email">
        </label>
        <div id="dept-field">
          <label class="field">Assigned Department (ABAC Verification)
            <select class="control" name="department" required>
              ${staffDepts.map((d) => `<option value="${d.departmentname}">${d.departmentname}</option>`).join('')}
            </select>
          </label>
        </div>
        <div id="admin-note" class="hidden card"><strong>System Administrator Scope</strong><p class="muted">Administrator credentials have unrestricted oversight across all store departments.</p></div>
        <label class="field">Password
          <input class="control" name="password" type="password" required placeholder="Enter account password">
        </label>
        <button class="btn btn-primary" type="submit">Sign in as Staff Member</button>
      </form>
      <p class="muted center">User accounts are created exclusively by the System Administrator.<br><a href="signup.html">Inquire about account provisioning →</a></p>
    </div>
  `;

  let loginType = 'staff';
  const form = root.querySelector('#login-form');
  const setType = (type) => {
    loginType = type;
    root.querySelectorAll('.switcher button').forEach((btn) => btn.classList.toggle('active', btn.dataset.type === type));
    root.querySelector('#dept-field').classList.toggle('hidden', type === 'admin');
    root.querySelector('#admin-note').classList.toggle('hidden', type !== 'admin');
    form.querySelector('button[type=submit]').textContent = `Sign in as ${type === 'admin' ? 'Administrator' : 'Staff Member'}`;
  };
  root.querySelectorAll('.switcher button').forEach((btn) => btn.addEventListener('click', () => setType(btn.dataset.type)));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const errorEl = root.querySelector('#auth-error');
    errorEl.classList.add('hidden');
    try {
      const payload = {
        username: form.username.value.trim(),
        password: form.password.value.trim(),
        department: loginType === 'staff' ? form.department.value : 'Administration',
        login_type: loginType,
      };
      await fetch(`${API_URL}/login?cookie_only=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      }).then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail ?? 'Authentication failed.');
        return body;
      });
      window.location.replace('index.html');
    } catch (error) {
      errorEl.textContent = error instanceof Error ? error.message : 'Unable to sign in.';
      errorEl.classList.remove('hidden');
    }
  });
}

export async function renderCrud(page, config) {
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
  showNotice(page.querySelector('#notice'), result.error);
  renderTable(page.querySelector('#table'), { columns: config.columns, data: result.data, searchKey: config.searchKey });
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
    subtitle: 'Live purchase orders and their assigned officers.',
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
      description: 'Issue an order using live supplier and employee records.',
      submit: 'Issue order',
      fields: field('supplierid', 'Supplier ID', 'type="number" min="1" required') + field('employeeid', 'Officer employee ID', 'type="number" min="1" required'),
      submitFn: (form) => apiRequest('/purchase-orders', { method: 'POST', body: JSON.stringify({ supplierid: Number(form.get('supplierid')), employeeid: Number(form.get('employeeid')), status: 'Pending' }) }),
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

export async function renderSales(page) {
  const user = getCurrentUser() || window.__HW_USER__;
  const [sales, products, branches] = await Promise.all([
    loadList('/api/sales'),
    loadList('/api/products'),
    loadList('/api/branches'),
  ]);

  // Check permission
  const hasPOS = can('sales:pos');

  page.innerHTML = `
    <header class="page-head card">
      <div>
        <div class="kicker">${icons.banknote} Point of sale</div>
        <h1>Sales & Retail Checkout</h1>
        <p class="muted">Completed sales with stock deduction, payment, and finance journals.</p>
      </div>
      ${hasPOS ? `<button class="btn btn-primary" id="open-session-btn">Open Session</button>` : ''}
    </header>
    ${hasPOS ? `
    <form id="pos" class="pos-grid">
      <section class="card">
        <div style="display:flex;gap:.5rem;margin-bottom:.75rem">
          <select class="control" id="product-select" style="flex:1">
            <option value="">Search / select a product</option>
            ${products.data.filter(p => p.is_active !== false).map((p) =>
              `<option value="${p.itemid}" data-price="${p.unitprice}" data-stock="${p.available_stock || 0}">
                ${p.itemname} · UGX ${Number(p.unitprice).toLocaleString()} · Stock: ${p.available_stock || 0}
              </option>`
            ).join('')}
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
        <input class="control" name="customername" placeholder="Customer name (optional)">
        <input class="control" name="customerphone" placeholder="Phone number (optional)">
        <div class="page-head"><span>Total</span><strong id="pos-total">${money(0)}</strong></div>
        <button class="btn btn-primary" type="submit" id="complete-sale" disabled>Complete Sale</button>
      </aside>
    </form>` : `<div class="card" style="padding:2rem;text-align:center"><p class="muted">🔒 You do not have POS sales permission.</p></div>`}
    <div id="notice"></div>
    <div id="table"></div>
  `;

  showNotice(page.querySelector('#notice'), sales.error || products.error);

  renderTable(page.querySelector('#table'), {
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
        return `<div class="line" data-id="${line.itemid}">
          <div><strong>${product.itemname}</strong><div class="muted">${money(product.unitprice)} each</div></div>
          <div class="qty">
            <button type="button" data-dec>−</button>
            <span>${line.quantity}</span>
            <button type="button" data-inc>+</button>
          </div>
          <strong>${money(product.unitprice * line.quantity)}</strong>
          <button type="button" data-del style="color:var(--destructive)">&times;</button>
        </div>`;
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
    const opt = sel.querySelector(`option[value="${itemid}"]`);
    const stock = parseFloat(opt?.dataset.stock || 0);
    const existing = lines.find((l) => l.itemid === itemid);
    const qty = existing ? existing.quantity + 1 : 1;
    if (qty > stock) {
      showNotice(page.querySelector('#notice'), `Insufficient stock. Available: ${stock}`);
      return;
    }
    if (existing) existing.quantity += 1;
    else lines.push({ itemid, quantity: 1 });
    sel.value = '';
    showNotice(page.querySelector('#notice'), null);
    paintLines();
  });

  page.querySelector('#lines').addEventListener('click', (event) => {
    const row = event.target.closest('.line');
    if (!row) return;
    const line = lines.find((l) => l.itemid === Number(row.dataset.id));
    if (!line) return;
    if (event.target.closest('[data-inc]')) line.quantity += 1;
    else if (event.target.closest('[data-dec]')) line.quantity -= 1;
    else if (event.target.closest('[data-del]')) line.quantity = 0;
    if (line.quantity < 1) {
      lines.splice(lines.findIndex((l) => l.itemid === line.itemid), 1);
    }
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
      // Generate a simple idempotency key
      const ikey = `POS-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      await apiRequest('/api/sales', {
        method: 'POST',
        headers: { 'Idempotency-Key': ikey },
        body: JSON.stringify({
          customername: form.customername.value || null,
          customerphone: form.customerphone.value || null,
          employeeid: user.employeeid,
          branchid: Number(form.branchid.value),
          payment_method: form.payment_method.value,
          idempotency_key: ikey,
          items: lines.map((line) => ({ itemid: line.itemid, quantity: line.quantity })),
        }),
      });
      showNotice(noticeEl, null);
      window.location.reload();
    } catch (error) {
      showNotice(noticeEl, error.message);
      btn.disabled = false;
      btn.textContent = 'Complete Sale';
    }
  });
}

export async function renderEmployees(page) {
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
  showNotice(page.querySelector('#notice'), employees.error || branches.error || departments.error);
  renderTable(page.querySelector('#table'), {
    columns: [
      { header: 'Employee ID', key: 'employeeid', sortable: true },
      { header: 'Name', key: 'name', sortable: true },
      { header: 'Role', key: 'roletype', sortable: true },
      { header: 'Department', key: 'department_name' },
      { header: 'Branch', key: 'branch_name' },
      { header: 'Phone', key: 'phone' },
      { header: 'Date Hired', key: 'datehired', sortable: true },
    ],
    data: employees.data,
    searchKey: 'name',
  });
  page.querySelector('#add-btn').addEventListener('click', () => {
    const backdrop = openDialog({
      title: 'Provision New Employee & Assign Access',
      description: 'Only Administrators can create new accounts and assign department credentials.',
      bodyHtml: `
        <div class="form-grid two">
          ${field('name', 'Full name', 'required placeholder="e.g. Samuel Okello"')}
          ${field('nin', 'National ID (NIN)', 'required')}
          ${field('email', 'Email Address', 'type="email" required')}
          ${field('password', 'Initial Password', 'type="password" required')}
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
        await apiRequest('/employees', {
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
            roletype: form.get('roletype'),
            pos_terminalid: form.get('pos_terminalid') || null,
            approvallimit: num('approvallimit'),
            certificationnumber: form.get('certificationnumber') || null,
            hr_role: form.get('hr_role') || null,
            managementlevel: form.get('managementlevel') || null,
          }),
        });
        window.location.reload();
      },
    });
    const roleFields = {
      Cashier: field('pos_terminalid', 'Assigned POS Terminal ID', 'required'),
      'Procurement Officer': field('approvallimit', 'Approval Limit (UGX)', 'type="number" min="0" required'),
      Accountant: field('certificationnumber', 'CPA / Accounting Certification Number'),
      'HR Staff': field('hr_role', 'HR Designation', 'required'),
      'Branch Manager': field('managementlevel', 'Management Level'),
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
  const result = await loadList('/api/audit-logs');
  page.innerHTML = `
    <header class="page-head card">
      <div><div class="kicker">Security</div><h1>Audit Logs</h1></div>
    </header>
    <div id="notice"></div>
    <div id="table"></div>`;
  showNotice(page.querySelector('#notice'), result.error);
  const items = Array.isArray(result.data) ? result.data : (result.data?.items || []);
  renderTable(page.querySelector('#table'), {
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
    <div class="grid-2">
      <div class="card">
        <h2>Team Members</h2>
        <div class="form-grid">
          ${employees.data.length ? employees.data.map((m) => `<div class="team-row"><div><strong>${m.name}</strong><div class="muted">ID: ${m.employeeid}</div></div><span class="badge" style="${colors[m.roletype] || ''}">${m.roletype}</span></div>`).join('') : '<p class="muted">No team members yet</p>'}
        </div>
      </div>
      <div class="card">
        <h2>System Status</h2>
        <p class="page-head"><span>Auth Configured</span><span class="badge">JWT enabled</span></p>
        <p class="page-head"><span>RLS Policies</span><span class="badge">Enabled</span></p>
        <p class="muted">FastAPI validates the signed-in employee role before allowing access to MySQL-backed operations.</p>
      </div>
    </div>
    <div class="card form-grid two">
      <h2 style="grid-column:1/-1">Store Identity & Tax Details</h2>
      ${field('store-name', 'Store Legal Name', 'placeholder="Configured in your business profile"')}
      ${field('tin', 'URA Tax Identification Number (TIN)', 'placeholder="Configured in your business profile"')}
      ${field('branch', 'Active Workspace Branch', 'placeholder="Select a live branch"')}
      ${field('currency', 'Operating Currency', 'value="UGX (Ugandan Shilling)" disabled')}
    </div>
  `;
}
