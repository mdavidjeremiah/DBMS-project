import { currentPageFile, signOut, visibleNav } from './auth.js';
import { icons, NAV_ICONS } from './icons.js';

const THEME_KEY = 'hw_theme';

export function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  localStorage.setItem(THEME_KEY, theme);
}

export function currentTheme() {
  return localStorage.getItem(THEME_KEY) || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

export function mountShell(root, user, pageHtml) {
  applyTheme(currentTheme());
  const role = user.roletype || 'Staff';
  const nav = visibleNav(role)
    .map((item) => {
      const active = item.href === currentPageFile();
      return `<a class="nav-link ${active ? 'active' : ''}" href="${item.href}">${NAV_ICONS[item.page] || ''}<span>${item.title}</span></a>`;
    })
    .join('');

  root.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar" id="sidebar">
        <div class="brand">
          <div class="brand-mark">HW</div>
          <div>
            <strong>HARDWARE WORLD</strong>
            <small>${user.branch_name ?? 'Main Branch'}</small>
          </div>
        </div>
        <div class="nav-label">
          <span>${role === 'Admin' ? 'Master Navigation' : `${role} Access`}</span>
          <span class="dept-chip">${user.department_name ?? 'general'}</span>
        </div>
        <nav>${nav}</nav>
        <div class="sidebar-user">
          <div class="icon-box">${role === 'Admin' ? icons.shield : icons.usercheck}</div>
          <div>
            <strong>${user.name ?? 'Authenticated Staff'}</strong>
            <div class="muted">${user.department_name ?? 'Administration'}</div>
          </div>
        </div>
      </aside>
      <div class="content-col">
        <header class="topbar">
          <button class="icon-btn menu-btn" id="menu-btn" aria-label="Open navigation">${icons.menu}</button>
          <div class="search">${icons.search}<input placeholder="Search live records, products, customers..."></div>
          <button class="icon-btn" id="theme-btn" aria-label="Toggle theme">${currentTheme() === 'dark' ? icons.sun : icons.moon}</button>
          <div class="user-chip">
            <div class="icon-box">${role === 'Admin' ? icons.shield : icons.usercheck}</div>
            <div>
              <p>${user.name ?? 'Hardware Staff'}</p>
              <span>${role} · ${user.department_name ?? 'General'}</span>
            </div>
          </div>
          <button class="icon-btn" id="signout-btn" aria-label="Sign out">${icons.logout}</button>
        </header>
        <main class="main">
          <div class="page" id="page">${pageHtml}</div>
          ${footerHtml()}
        </main>
      </div>
    </div>
  `;

  root.querySelector('#theme-btn').addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    root.querySelector('#theme-btn').innerHTML = next === 'dark' ? icons.sun : icons.moon;
  });
  root.querySelector('#signout-btn').addEventListener('click', signOut);
  root.querySelector('#menu-btn').addEventListener('click', () => {
    root.querySelector('#sidebar').classList.toggle('open');
  });
}

export function accessDeniedHtml(user) {
  return `
    <div class="access-denied card">
      <div class="icon-box" style="margin:0 auto 1rem;width:4rem;height:4rem;color:#f43f5e">${icons.shield}</div>
      <h1>Access Denied (ABAC / RBAC)</h1>
      <p class="kicker">Departmental Boundary Policy Violation</p>
      <p class="muted">Active role: <strong>${user.roletype}</strong> · Department: <strong>${user.department_name ?? 'General'}</strong></p>
      <p class="muted">Under ABAC, employees cannot access another department's records. Only the System Administrator has cross-departmental clearance.</p>
      <p><a class="btn btn-primary" href="index.html">Return to My Department Dashboard</a></p>
    </div>
  `;
}

function footerHtml() {
  return `
    <footer class="footer">
      <div class="trust">
        <div>Free Delivery<br><small>Orders over UGX 500k</small></div>
        <div>100% Genuine<br><small>Certified supplier stock</small></div>
        <div>Easy Returns<br><small>30-day money back guarantee</small></div>
        <div>Trade Support<br><small>24/7 dedicated assistance</small></div>
      </div>
      <div class="grid-4">
        <div>
          <strong>HARDWARE WORLD</strong>
          <p>Uganda's leading hardware, building materials, power tools, and DIY supplies retailer.</p>
        </div>
        <div>
          <strong>Quick Navigation</strong>
          <p><a href="products.html">Products Catalogue</a></p>
          <p><a href="categories.html">Building Categories</a></p>
          <p><a href="sales.html">POS & Retail Sales</a></p>
          <p><a href="purchase-orders.html">Purchase Orders</a></p>
        </div>
        <div>
          <strong>Main Branch</strong>
          <p>Plot 42 Jinja Road, Kampala</p>
          <p>+256 414 500 100</p>
          <p>sales@hardwareworld.co.ug</p>
        </div>
        <div>
          <strong>Newsletter & Offers</strong>
          <p>Subscribe for weekly trade discounts and restock alerts.</p>
        </div>
      </div>
      <p>© 2026 Hardware World Ltd. All rights reserved.</p>
    </footer>
  `;
}
