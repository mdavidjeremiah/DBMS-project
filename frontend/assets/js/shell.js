import { hasAccess, signOut } from './auth.js';

/**
 * AppShell initialization.
 * Injects the sidebar, topbar, and footer around the main content.
 */
export function initShell(user) {
  const currentPath = window.location.pathname;
  const path = currentPath === '/' ? '/index.html' : currentPath;

  // Wrap body content in a shell structure
  const originalBodyContent = document.body.innerHTML;
  document.body.innerHTML = '';
  
  const shell = document.createElement('div');
  shell.className = 'app-shell';

  // 1. Sidebar
  const sidebar = document.createElement('aside');
  sidebar.className = 'sidebar sidebar-mobile-hidden';
  sidebar.innerHTML = `
    <div class="flex items-center gap-2 mb-4 px-2">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <i data-lucide="hammer" class="w-5 h-5"></i>
      </div>
      <span class="text-xl font-black tracking-tight text-foreground">Hardware World</span>
      <button class="btn btn-icon btn-ghost md:hidden ml-auto" id="close-sidebar">
        <i data-lucide="x" class="w-5 h-5"></i>
      </button>
    </div>
    <div class="mb-4">
      <div class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Operations</div>
      <nav class="flex flex-col gap-1" id="nav-operations"></nav>
    </div>
    <div class="mb-4">
      <div class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">People & Ledger</div>
      <nav class="flex flex-col gap-1" id="nav-people"></nav>
    </div>
    <div class="mt-auto">
      <nav class="flex flex-col gap-1" id="nav-settings"></nav>
    </div>
  `;
  shell.appendChild(sidebar);

  // 2. Main Content Wrapper
  const main = document.createElement('div');
  main.className = 'main-content';

  // 3. Topbar
  const topbar = document.createElement('header');
  topbar.className = 'topbar';
  topbar.innerHTML = `
    <div class="flex items-center gap-4">
      <button class="btn btn-icon btn-ghost md:hidden" id="open-sidebar">
        <i data-lucide="menu" class="w-5 h-5"></i>
      </button>
      <div class="hidden md:flex items-center gap-2 text-sm text-muted-foreground bg-muted px-3 py-1.5 rounded-full">
        <i data-lucide="search" class="w-4 h-4"></i>
        <span>Search operations... (Ctrl+K)</span>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <button class="btn btn-icon btn-ghost" id="theme-toggle">
        <i data-lucide="moon" class="w-5 h-5 dark:hidden"></i>
        <i data-lucide="sun" class="w-5 h-5 hidden dark:block"></i>
      </button>
      <div class="flex items-center gap-2 border-l border-border pl-4">
        <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
          ${user.name.charAt(0)}
        </div>
        <div class="hidden md:block">
          <div class="text-sm font-medium leading-none">${user.name}</div>
          <div class="text-xs text-muted-foreground">${user.roletype}</div>
        </div>
        <button class="btn btn-icon btn-ghost text-muted-foreground ml-2" id="sign-out" title="Sign out">
          <i data-lucide="log-out" class="w-4 h-4"></i>
        </button>
      </div>
    </div>
  `;
  main.appendChild(topbar);

  // 4. Page Content
  const pageContent = document.createElement('main');
  pageContent.className = 'page-content';
  pageContent.innerHTML = originalBodyContent;
  main.appendChild(pageContent);

  // 5. Footer
  const footer = document.createElement('footer');
  footer.className = 'footer';
  footer.innerHTML = `
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2 text-primary font-bold">
        <i data-lucide="hammer" class="w-4 h-4"></i>
        <span>Hardware World</span>
      </div>
      <span>&copy; ${new Date().getFullYear()} Hardware World Ltd.</span>
    </div>
    <div class="flex gap-4">
      <a href="#" class="hover:text-foreground">Support</a>
      <a href="#" class="hover:text-foreground">Terms</a>
      <a href="#" class="hover:text-foreground">Privacy</a>
    </div>
  `;
  main.appendChild(footer);

  shell.appendChild(main);
  document.body.appendChild(shell);

  // --- Initialize Nav Links ---
  const navItems = [
    { label: 'Dashboard', icon: 'layout-dashboard', href: '/index.html', group: 'nav-operations' },
    { label: 'Sales & POS', icon: 'shopping-cart', href: '/sales.html', group: 'nav-operations' },
    { label: 'Purchase Orders', icon: 'file-text', href: '/purchase-orders.html', group: 'nav-operations' },
    { label: 'Suppliers', icon: 'truck', href: '/suppliers.html', group: 'nav-operations' },
    { label: 'Categories', icon: 'tags', href: '/categories.html', group: 'nav-operations' },
    { label: 'Products', icon: 'package', href: '/products.html', group: 'nav-operations' },
    { label: 'Employees', icon: 'users', href: '/employees.html', group: 'nav-people' },
    { label: 'Payroll', icon: 'banknote', href: '/payroll.html', group: 'nav-people' },
    { label: 'Ledger', icon: 'book-open', href: '/ledger.html', group: 'nav-people' },
    { label: 'Settings', icon: 'settings', href: '/settings.html', group: 'nav-settings' },
  ];

  navItems.forEach(item => {
    // Only render if user has access
    if (hasAccess(user.roletype, item.href)) {
      const container = document.getElementById(item.group);
      const a = document.createElement('a');
      a.href = item.href;
      a.className = `nav-link ${path === item.href ? 'active' : ''}`;
      a.innerHTML = `<i data-lucide="${item.icon}" class="w-5 h-5"></i><span>${item.label}</span>`;
      container.appendChild(a);
    }
  });

  // --- Initialize Event Listeners ---
  document.getElementById('theme-toggle').addEventListener('click', () => {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });

  // Set initial theme
  if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
  }

  document.getElementById('sign-out').addEventListener('click', signOut);

  const sidebarEl = document.querySelector('.sidebar');
  document.getElementById('open-sidebar').addEventListener('click', () => {
    sidebarEl.classList.remove('sidebar-mobile-hidden');
    sidebarEl.classList.add('sidebar-mobile-open');
  });
  
  document.getElementById('close-sidebar').addEventListener('click', () => {
    sidebarEl.classList.add('sidebar-mobile-hidden');
    sidebarEl.classList.remove('sidebar-mobile-open');
  });

  // Initialize Lucide icons if loaded
  if (window.lucide) {
    window.lucide.createIcons();
  }
}
