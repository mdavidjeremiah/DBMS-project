import { apiRequest, API_URL, loadList } from './api.js';
import { field, money, openDialog, renderTable, selectField, showNotice } from './ui.js';
import { icons } from './icons.js';
import { buildGraphData, renderGraph } from './graph.js';

export async function renderDashboard(page) {
  const [sales, orders, employees, products] = await Promise.all([
    loadList('/sales'),
    loadList('/purchase-orders'),
    loadList('/employees'),
    loadList('/products'),
  ]);
  const today = new Date().toDateString();
  const salesToday = sales.data.filter((sale) => new Date(sale.saledate).toDateString() === today);
  const stats = {
    salesToday: salesToday.reduce((sum, sale) => sum + Number(sale.totalamount || 0), 0),
    salesCount: salesToday.length,
    pendingOrders: orders.data.filter((order) => order.status === 'Pending').length,
    employeeCount: employees.data.length,
    productCount: products.data.length,
  };
  const user = window.__HW_USER__;
  const isAdmin = user.roletype === 'Admin';
  const userDept = user.department_name ?? (isAdmin ? 'Administration' : 'General Staff');
  const latestSales = sales.data.slice(0, 5);
  const latestOrders = orders.data.slice(0, 5);
  const error = [sales.error, orders.error].filter(Boolean).join('; ') || null;

  page.innerHTML = `
    <header class="hero">
      <div class="hero-row">
        <div>
          <div class="pills">
            <span class="pill orange">${isAdmin ? icons.shield : icons.usercheck} ${isAdmin ? 'Admin Oversight Authority' : `${user.roletype} Scope`}</span>
            <span class="pill slate">${userDept}</span>
          </div>
          <h1>Welcome back, ${user.name}</h1>
          <p>${isAdmin ? 'Full cross-departmental RBAC & ABAC administrative oversight.' : `Assigned departmental workspace: ${userDept}.`}</p>
        </div>
        <div>
          ${isAdmin ? `<a class="btn btn-primary" href="employees.html">${icons.plus} Provision New User</a>` : ''}
          ${userDept === 'Sales & POS' ? `<a class="btn btn-primary" href="sales.html">Open POS Register</a>` : ''}
          ${userDept === 'Procurement & Inventory' ? `<a class="btn btn-primary" href="purchase-orders.html">Create Purchase Order</a>` : ''}
        </div>
      </div>
    </header>
    <div id="notice"></div>
    <div id="graph"></div>
    <section class="grid-4">
      ${metric('Sales Today', money(stats.salesToday), 'Processed in active branch')}
      ${metric('Transactions Today', String(stats.salesCount), 'Customer checkout entries')}
      ${metric('Pending Purchase Orders', String(stats.pendingOrders), 'Awaiting officer sign-off')}
      ${metric('Total Staff in System', String(stats.employeeCount), 'Across all 6 departments')}
    </section>
    <section class="grid-2">
      ${liveList('Recent Point-of-Sale Transactions', 'sales.html', latestSales.length ? latestSales.map((sale) => listRow(`Sale #${sale.saleid}`, `${sale.customer_name} · Cashier: ${sale.cashier_name}`, money(sale.totalamount))).join('') : empty('No recent sales found.'))}
      ${liveList('Recent Procurement Purchase Orders', 'purchase-orders.html', latestOrders.length ? latestOrders.map((order) => listRow(`PO #${order.po_id}`, `${order.supplier_name} · Officer: ${order.officer_name}`, `<span class="badge">${order.status}</span>`)).join('') : empty('No recent purchase orders found.'))}
    </section>
    <p class="muted">${stats.productCount} active products in live database inventory.</p>
  `;
  showNotice(page.querySelector('#notice'), error);
  renderGraph(page.querySelector('#graph'), buildGraphData(sales.data));
}

function metric(label, value, subtext) {
  return `<div class="card"><div class="metric"><span class="muted">${label}</span><div class="metric-icon">${icons.activity}</div></div><strong>${value}</strong><p class="muted">${subtext}</p></div>`;
}

function liveList(title, href, body) {
  return `<div class="card"><div class="page-head"><h2>${title}</h2><a href="${href}">View all →</a></div>${body}</div>`;
}

function listRow(title, sub, right) {
  return `<div class="list-item"><span><strong>${title}</strong><div class="muted">${sub}</div></span><strong>${right}</strong></div>`;
}

function empty(text) {
  return `<p class="muted center">${text}</p>`;
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
      const { setAccessToken } = await import('./api.js');
      const data = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail ?? 'Authentication failed.');
        return body;
      });
      setAccessToken(data.access_token);
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
    endpoint: '/products',
    kicker: 'Hardware catalogue',
    title: 'Products & Stock Inventory',
    subtitle: 'Live product prices and reorder settings.',
    searchKey: 'itemname',
    columns: [
      { header: 'Item ID', key: 'itemid', sortable: true },
      { header: 'Item Name', key: 'itemname', sortable: true },
      { header: 'Category', key: 'category_name', sortable: true },
      { header: 'Unit Price', key: 'unitprice', sortable: true, cell: (row) => money(row.unitprice) },
      { header: 'Reorder Level', key: 'reorderlevel', sortable: true },
    ],
    create: {
      trigger: 'Add Product',
      title: 'Add product',
      description: 'Create a product in the live catalogue.',
      submit: 'Create product',
      fields: field('itemname', 'Item name', 'required') + field('description', 'Description') + field('unitprice', 'Unit price (UGX)', 'type="number" min="0" required') + field('reorderlevel', 'Reorder level', 'type="number" min="0" required') + field('categoryid', 'Category ID', 'type="number" min="1" required'),
      submitFn: (form) => apiRequest('/products', { method: 'POST', body: JSON.stringify({ itemname: form.get('itemname'), description: form.get('description') || null, unitprice: Number(form.get('unitprice')), reorderlevel: Number(form.get('reorderlevel')), categoryid: Number(form.get('categoryid')) }) }),
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
    endpoint: '/suppliers',
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
    endpoint: '/purchase-orders',
    kicker: 'Procurement',
    title: 'Purchase Orders',
    subtitle: 'Live purchase orders and their assigned officers.',
    searchKey: 'supplier_name',
    columns: [
      { header: 'Order ID', key: 'po_id', sortable: true },
      { header: 'Date', key: 'orderdate', sortable: true },
      { header: 'Supplier', key: 'supplier_name', sortable: true },
      { header: 'Officer', key: 'officer_name' },
      { header: 'Status', key: 'status', sortable: true },
    ],
    create: {
      trigger: 'Create Order',
      title: 'Create purchase order',
      description: 'Issue an order using live supplier and employee records.',
      submit: 'Issue order',
      fields: field('supplierid', 'Supplier ID', 'type="number" min="1" required') + field('employeeid', 'Officer employee ID', 'type="number" min="1" required'),
      submitFn: (form) => apiRequest('/purchase-orders', { method: 'POST', body: JSON.stringify({ supplierid: Number(form.get('supplierid')), employeeid: Number(form.get('employeeid')), status: 'Pending' }) }),
    },
  },
  payroll: {
    endpoint: '/payroll',
    kicker: 'HR compensation',
    title: 'Payroll & Salary Accounting',
    subtitle: 'Live payroll records linked to employees.',
    searchKey: 'employee_name',
    columns: [
      { header: 'Payroll ID', key: 'payrollid', sortable: true },
      { header: 'Employee', key: 'employee_name', sortable: true },
      { header: 'Month', key: 'month', sortable: true },
      { header: 'Gross Pay', key: 'grosspay', cell: (row) => money(row.grosspay) },
      { header: 'Deductions', key: 'deductions', cell: (row) => money(row.deductions) },
      { header: 'Net Pay', key: 'netpay', cell: (row) => money(row.netpay) },
    ],
    create: {
      trigger: 'Add Payroll',
      title: 'Create payroll record',
      description: 'Record payroll for one live employee.',
      submit: 'Save payroll',
      fields: field('employeeid', 'Employee ID', 'type="number" min="1" required') + field('month', 'Month', 'placeholder="2026-09" required') + field('grosspay', 'Gross pay', 'type="number" min="0" required') + field('deductions', 'Deductions', 'type="number" min="0" required'),
      submitFn: (form) => {
        const grosspay = Number(form.get('grosspay'));
        const deductions = Number(form.get('deductions'));
        if (deductions > grosspay) throw new Error('Deductions cannot exceed gross pay');
        return apiRequest('/payroll', { method: 'POST', body: JSON.stringify({ employeeid: Number(form.get('employeeid')), month: form.get('month'), grosspay, deductions }) });
      },
    },
  },
  ledger: {
    endpoint: '/ledger',
    kicker: 'Accounting',
    title: 'Master Accounting Ledger',
    subtitle: 'Live entries sourced from sales and payroll.',
    searchKey: 'source_label',
    columns: [
      { header: 'Entry ID', key: 'entryid', sortable: true },
      { header: 'Date', key: 'entrydate', sortable: true },
      { header: 'Source', key: 'sourcetype' },
      { header: 'Reference', key: 'source_label' },
      { header: 'Recorded By', key: 'accountant_name' },
      { header: 'Amount', key: 'amount', sortable: true, cell: (row) => money(row.amount) },
    ],
    create: {
      trigger: 'Add Entry',
      title: 'Post ledger entry',
      description: 'Link a ledger entry to an existing sale or payroll record.',
      submit: 'Post entry',
      fields: selectField('sourcetype', 'Source type', '<option value="SALE">Sale</option><option value="PAYROLL">Payroll</option>', true) + field('sourceid', 'Sale or payroll ID', 'type="number" min="1" required') + field('amount', 'Amount', 'type="number" min="0" required') + field('recordedby', 'Recorded by employee ID', 'type="number" min="1" required'),
      submitFn: (form) => {
        const sourcetype = form.get('sourcetype');
        const sourceid = Number(form.get('sourceid'));
        return apiRequest('/ledger', { method: 'POST', body: JSON.stringify({ sourcetype, saleid: sourcetype === 'SALE' ? sourceid : null, payrollid: sourcetype === 'PAYROLL' ? sourceid : null, amount: Number(form.get('amount')), recordedby: Number(form.get('recordedby')) }) });
      },
    },
  },
};

export async function renderSales(page) {
  const [sales, products, employees, branches] = await Promise.all([
    loadList('/sales'),
    loadList('/products'),
    loadList('/employees'),
    loadList('/branches'),
  ]);
  const cashiers = employees.data.filter((e) => e.roletype === 'Cashier');
  page.innerHTML = `
    <header class="card">
      <div class="kicker">${icons.banknote} Point of sale</div>
      <h1>Sales & Retail Checkout</h1>
      <p class="muted">Live sales and line items from MySQL.</p>
    </header>
    <form id="pos" class="pos-grid">
      <section class="card">
        <div style="display:flex;gap:.5rem">
          <select class="control" id="product-select" style="flex:1">
            <option value="">Select a product</option>
            ${products.data.map((p) => `<option value="${p.itemid}">${p.itemname} · ${money(p.unitprice)}</option>`).join('')}
          </select>
          <button type="button" class="btn btn-primary" id="add-line">${icons.plus} Add</button>
        </div>
        <div id="lines"><p class="muted center">Add products to begin a sale.</p></div>
      </section>
      <aside class="card form-grid">
        <div><h2>Checkout</h2><p class="muted">Sale and sale-item records are saved together.</p></div>
        <label class="field">Cashier
          <select class="control" name="employeeid" required>
            <option value="">Select cashier</option>
            ${cashiers.map((c) => `<option value="${c.employeeid}">${c.name}</option>`).join('')}
          </select>
        </label>
        <label class="field">Branch
          <select class="control" name="branchid" required>
            <option value="">Select branch</option>
            ${branches.data.map((b) => `<option value="${b.branchid}">${b.branchname}</option>`).join('')}
          </select>
        </label>
        <input class="control" name="customername" placeholder="Customer name">
        <input class="control" name="customerphone" placeholder="Phone number">
        <div class="page-head"><span>Total</span><strong id="pos-total">${money(0)}</strong></div>
        <button class="btn btn-primary" type="submit" id="complete-sale" disabled>Complete sale</button>
      </aside>
    </form>
    <div id="notice"></div>
    <div id="table"></div>
  `;
  showNotice(page.querySelector('#notice'), sales.error || products.error || employees.error || branches.error);
  renderTable(page.querySelector('#table'), {
    columns: [
      { header: 'Sale ID', key: 'saleid', sortable: true },
      { header: 'Date', key: 'saledate', sortable: true },
      { header: 'Customer', key: 'customer_name' },
      { header: 'Cashier', key: 'cashier_name' },
      { header: 'Branch', key: 'branch_name' },
      { header: 'Total', key: 'totalamount', sortable: true, cell: (row) => money(row.totalamount) },
    ],
    data: sales.data,
    searchKey: 'customer_name',
  });

  const lines = [];
  const paintLines = () => {
    const box = page.querySelector('#lines');
    if (!lines.length) {
      box.innerHTML = '<p class="muted center">Add products to begin a sale.</p>';
    } else {
      box.innerHTML = lines.map((line) => {
        const product = products.data.find((p) => p.itemid === line.itemid);
        return `<div class="line" data-id="${line.itemid}"><div><strong>${product.itemname}</strong><div class="muted">${money(product.unitprice)} each</div></div><div class="qty"><button type="button" data-dec>-</button><input class="control" type="number" min="1" value="${line.quantity}"><button type="button" data-inc>+</button></div><button type="button" data-del>${icons.trash}</button></div>`;
      }).join('');
    }
    const total = lines.reduce((sum, line) => sum + (products.data.find((p) => p.itemid === line.itemid)?.unitprice ?? 0) * line.quantity, 0);
    page.querySelector('#pos-total').textContent = money(total);
    page.querySelector('#complete-sale').disabled = !lines.length || !cashiers.length || !branches.data.length;
  };

  page.querySelector('#add-line').addEventListener('click', () => {
    const itemid = Number(page.querySelector('#product-select').value);
    if (!itemid) return;
    const existing = lines.find((l) => l.itemid === itemid);
    if (existing) existing.quantity += 1;
    else lines.push({ itemid, quantity: 1 });
    page.querySelector('#product-select').value = '';
    paintLines();
  });
  page.querySelector('#lines').addEventListener('click', (event) => {
    const row = event.target.closest('.line');
    if (!row) return;
    const line = lines.find((l) => l.itemid === Number(row.dataset.id));
    if (event.target.closest('[data-inc]')) line.quantity += 1;
    if (event.target.closest('[data-dec]')) line.quantity -= 1;
    if (event.target.closest('[data-del]') || line.quantity < 1) {
      const idx = lines.findIndex((l) => l.itemid === line.itemid);
      lines.splice(idx, 1);
    }
    paintLines();
  });
  page.querySelector('#pos').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    try {
      await apiRequest('/sales', {
        method: 'POST',
        body: JSON.stringify({
          customername: form.customername.value || null,
          customerphone: form.customerphone.value || null,
          employeeid: Number(form.employeeid.value),
          branchid: Number(form.branchid.value),
          items: lines.map((line) => ({ itemid: line.itemid, quantity: line.quantity })),
        }),
      });
      window.location.reload();
    } catch (error) {
      showNotice(page.querySelector('#notice'), error.message);
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

export async function renderSettings(page) {
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
