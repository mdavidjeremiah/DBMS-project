/**
 * Hardware World ERP — App Shell
 *
 * Builds the full app layout (sidebar, topbar, page area, footer) using
 * the role-aware sidebar-config.js and the user's live permissions[].
 */

import { signOut } from './auth.js';
import { getSidebarItems } from './sidebar-config.js';
import { refreshAlerts, toggleNotificationCenter } from './notifications.js';
import { escapeHtml } from './ui.js';

const THEME_KEY = 'hw_theme';

function currentTheme() {
  return (
    localStorage.getItem(THEME_KEY) ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  );
}

function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  localStorage.setItem(THEME_KEY, theme);
}

function currentPageFile() {
  const p = window.location.pathname.split('/').pop() || 'index.html';
  return p || 'index.html';
}

/** Return a greeting based on current hour. */
function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function avatarMarkup(user) {
  const initial = escapeHtml((user.name || 'U').charAt(0));
  const photoUrl = user.profile_photo_url || (user.roletype === 'Admin' ? '/assets/images/admin-profile.jpg' : null);
  const image = photoUrl
    ? `<img src="${escapeHtml(photoUrl)}" alt="" loading="lazy">`
    : '';
  return `<div class="avatar">${initial}${image}</div>`;
}

/**
 * Mount the full app shell around the page content.
 * @param {HTMLElement} root  — document.getElementById('app') or document.body
 * @param {object} user       — resolved /users/me response
 * @param {string} pageHtml   — initial inner HTML for the page area
 */
export function initShell(user, pageHtml = '') {
  applyTheme(currentTheme());

  const role = user.roletype === 'Admin'
    ? 'System Administrator'
    : ((user.roles || []).includes('Owner / Executive') ? 'Owner / Executive' : (user.roletype || 'Admin'));
  const permissions = user.permissions || [];
  const currentFile = currentPageFile();
  const isDashboard = currentFile === 'index.html';

  // Build sidebar items for this role
  const items = getSidebarItems(user.roletype, permissions, user.roles || []);

  const navHtml = items
    .map((item) => {
      if (item.section) {
        return `<div class="nav-label"><span>${item.section}</span></div>`;
      }
      const page = item.href || '';
      const isActive = page === currentFile || (currentFile === '' && page === 'index.html');
      return `
        <a class="nav-link ${isActive ? 'active' : ''}" href="${item.href || '#'}" ${isActive ? 'aria-current="page"' : ''}>
          <i data-lucide="${item.icon}" class="w-5 h-5"></i>
          <span>${item.label}</span>
        </a>`;
    })
    .join('');

  // Determine role-aware quick action
  const quickActions = {
    Cashier: { label: 'New Sale', href: 'sales.html', icon: 'shopping-cart' },
    'Procurement Officer': { label: 'Create PO', href: 'purchase-orders.html', icon: 'file-plus' },
    Accountant: { label: 'Record Payment', href: 'ledger.html', icon: 'credit-card' },
    'HR Staff': { label: 'Add Employee', href: 'employees.html', icon: 'user-plus' },
    'Branch Manager': { label: 'Review Approvals', href: 'approvals.html', icon: 'check-circle' },
    'System Administrator': { label: 'Create User', href: 'employees.html', icon: 'user-plus' },
    'Owner / Executive': { label: 'Review Approvals', href: 'approvals.html', icon: 'check-circle' },
  };
  const qa = quickActions[role] || quickActions['Admin'];

  const root = document.getElementById('app') || document.body;
  const savedContent = root.innerHTML;

  root.innerHTML = `
    <div class="app-shell">
      <!-- Sidebar -->
      <aside class="sidebar" id="hw-sidebar">
        <div class="brand">
          <div class="brand-mark">HW</div>
          <div>
            <strong>HARDWARE WORLD</strong>
            <small>${escapeHtml(user.branch_name || 'Main Branch')}</small>
          </div>
          <button class="icon-btn md:hidden ml-auto" id="close-sidebar" aria-label="Close">✕</button>
        </div>
        <nav id="hw-nav">${navHtml}</nav>
        <div class="sidebar-user">
          ${avatarMarkup(user)}
          <div>
            <strong>${escapeHtml(user.name)}</strong>
            <div class="muted">${escapeHtml(role)} · ${escapeHtml(user.department_name || '')}</div>
          </div>
        </div>
      </aside>
      <button class="sidebar-backdrop" id="sidebar-backdrop" type="button" aria-label="Close navigation"></button>

      <!-- Main content column -->
      <div class="content-col">
        <!-- Topbar -->
        <header class="topbar" id="hw-topbar">
          <div class="flex items-center gap-3">
            <button class="icon-btn menu-btn" id="menu-btn" aria-label="Open navigation" aria-expanded="false" aria-controls="hw-sidebar">☰</button>
            <div class="search-wrap">
              <i data-lucide="search" class="w-4 h-4 search-icon"></i>
              <input class="search-input" placeholder="Jump to a workspace…" id="global-search" autocomplete="off" aria-controls="global-search-results" aria-expanded="false">
              <div class="search-results" id="global-search-results" role="listbox" hidden></div>
            </div>
          </div>
          <div class="topbar-right">
            <!-- Branch selector -->
            <span class="branch-chip" id="hw-branch-chip">${escapeHtml(user.branch_name || 'Main Branch')}</span>

            <!-- Date filter -->
            ${isDashboard ? `<select class="date-filter" id="hw-date-filter" aria-label="Date filter">
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="quarter">This Quarter</option>
            </select>` : ''}

            <!-- Notification bell -->
            <button class="icon-btn relative" id="hw-notif-btn" aria-label="Notifications" aria-expanded="false" aria-controls="hw-notification-center" type="button">
              <i data-lucide="bell" class="w-5 h-5"></i>
              <span id="hw-notif-badge" style="display:none;position:absolute;top:2px;right:2px;
                background:var(--destructive);color:#fff;border-radius:999px;
                font-size:.6rem;font-weight:700;padding:1px 4px;line-height:1.4;">0</span>
            </button>

            <!-- Theme toggle -->
            <button class="icon-btn" id="theme-btn" aria-label="Toggle theme">
              <i data-lucide="${currentTheme() === 'dark' ? 'sun' : 'moon'}" class="w-5 h-5"></i>
            </button>

            <!-- Quick action -->
            <a href="${qa.href}" class="btn btn-primary btn-sm quick-action-btn">
              <i data-lucide="${qa.icon}" class="w-4 h-4"></i>
              <span class="hidden md:inline">${qa.label}</span>
            </a>

            <!-- User chip -->
            <div class="user-chip">
              ${avatarMarkup(user)}
              <div class="hidden md:block">
                <p>${escapeHtml(user.name)}</p>
                <span>${escapeHtml(role)}</span>
              </div>
            </div>
            <button class="icon-btn" id="signout-btn" aria-label="Sign out">
              <i data-lucide="log-out" class="w-4 h-4"></i>
            </button>
          </div>
        </header>

        <!-- Page area -->
        <main class="main" id="hw-page">
          <div class="page" id="page">${pageHtml || savedContent}</div>
        </main>
      </div>
    </div>
  `;

  // ── Event wiring ──
  applyTheme(currentTheme());
  document.querySelectorAll('.avatar img').forEach((image) => {
    image.addEventListener('error', () => image.remove(), { once: true });
  });

  document.getElementById('theme-btn')?.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    const icon = document.querySelector('#theme-btn i[data-lucide]');
    if (icon) {
      icon.setAttribute('data-lucide', next === 'dark' ? 'sun' : 'moon');
      if (window.lucide) window.lucide.createIcons();
    }
  });

  document.getElementById('signout-btn')?.addEventListener('click', signOut);
  document.getElementById('hw-notif-btn')?.addEventListener('click', (event) => {
    toggleNotificationCenter(event.currentTarget).catch((error) => {
      console.error('Unable to open notification center:', error);
    });
  });

  const searchInput = document.getElementById('global-search');
  const searchResults = document.getElementById('global-search-results');
  const hideSearchResults = () => {
    searchResults.hidden = true;
    searchInput.setAttribute('aria-expanded', 'false');
  };
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.trim().toLowerCase();
    if (!query) {
      hideSearchResults();
      searchResults.replaceChildren();
      return;
    }
    const matches = items.filter((item) => item.href && item.label.toLowerCase().includes(query));
    searchResults.innerHTML = matches.length
      ? matches.map((item, index) => `<a role="option" aria-selected="${index === 0}" href="${item.href}">${item.label}</a>`).join('')
      : '<p class="muted">No matching workspace.</p>';
    searchResults.hidden = false;
    searchInput.setAttribute('aria-expanded', 'true');
  });
  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') hideSearchResults();
    if (event.key === 'Enter' && !searchResults.hidden) {
      const firstMatch = searchResults.querySelector('a');
      if (firstMatch) window.location.assign(firstMatch.href);
    }
  });
  searchResults.addEventListener('click', (event) => {
    if (event.target.closest('a')) hideSearchResults();
  });

  const sidebar = document.getElementById('hw-sidebar');
  const menuButton = document.getElementById('menu-btn');
  const sidebarBackdrop = document.getElementById('sidebar-backdrop');
  const setSidebarOpen = (open) => {
    sidebar?.classList.toggle('open', open);
    sidebarBackdrop?.classList.toggle('is-visible', open);
    menuButton?.setAttribute('aria-expanded', String(open));
  };
  menuButton?.addEventListener('click', () => setSidebarOpen(!sidebar?.classList.contains('open')));
  document.getElementById('close-sidebar')?.addEventListener('click', () => setSidebarOpen(false));
  sidebarBackdrop?.addEventListener('click', () => setSidebarOpen(false));
  sidebar?.querySelectorAll('.nav-link').forEach((link) => link.addEventListener('click', () => setSidebarOpen(false)));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setSidebarOpen(false);
      hideSearchResults();
      const notificationCenter = document.getElementById('hw-notification-center');
      notificationCenter?.remove();
      document.getElementById('hw-notif-btn')?.setAttribute('aria-expanded', 'false');
    }
  });

  // Date filter broadcasts to page via custom event
  document.getElementById('hw-date-filter')?.addEventListener('change', (e) => {
    document.dispatchEvent(new CustomEvent('hw:datefilter', { detail: { value: e.target.value } }));
  });

  // Initialize Lucide icons
  if (window.lucide) window.lucide.createIcons();

  // Refresh notification badge
  refreshAlerts().catch((error) => {
    console.error('Unable to refresh notification badge:', error);
  });
}

/**
 * Expose the page element so modules can render into it without
 * knowing the shell structure.
 */
export function getPageEl() {
  return document.getElementById('page');
}
