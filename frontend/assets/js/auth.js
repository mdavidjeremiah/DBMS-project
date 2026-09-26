import { apiRequest, clearAccessToken } from './api.js';

/**
 * Access Control Matrix
 * Defines which roles can access which routes.
 * 
 * Rules:
 * - Admin: Access everything
 * - Branch Manager: Everything except settings (Admin only)
 * - HR Staff: Dashboard, Employees, Payroll, Departments
 * - Accountant: Dashboard, Ledger, Sales, Payroll, Purchase Orders
 * - Procurement Officer: Dashboard, Suppliers, Categories, Products, Purchase Orders
 * - Cashier: Dashboard, Sales, Products, Customers
 */
export const ROLE_ROUTES = {
  'Admin': ['*'],
  'Branch Manager': ['/', '/categories.html', '/products.html', '/suppliers.html', '/purchase-orders.html', '/sales.html', '/ledger.html'],
  'HR Staff': ['/', '/employees.html', '/payroll.html'],
  'Accountant': ['/', '/ledger.html', '/sales.html', '/payroll.html', '/purchase-orders.html'],
  'Procurement Officer': ['/', '/suppliers.html', '/categories.html', '/products.html', '/purchase-orders.html'],
  'Cashier': ['/', '/sales.html', '/products.html']
};

const NAV_ITEMS = [
  { title: 'Dashboard', page: 'dashboard', href: 'index.html', path: '/' },
  { title: 'Products', page: 'products', href: 'products.html', path: '/products.html', module: 'inventory' },
  { title: 'Categories', page: 'categories', href: 'categories.html', path: '/categories.html', module: 'inventory' },
  { title: 'Suppliers', page: 'suppliers', href: 'suppliers.html', path: '/suppliers.html', module: 'procurement' },
  { title: 'Purchase Orders', page: 'purchase-orders', href: 'purchase-orders.html', path: '/purchase-orders.html', module: 'procurement' },
  { title: 'Sales & POS', page: 'sales', href: 'sales.html', path: '/sales.html', module: 'sales' },
  { title: 'Employees', page: 'employees', href: 'employees.html', path: '/employees.html', module: 'hr' },
  { title: 'Payroll', page: 'payroll', href: 'payroll.html', path: '/payroll.html', module: 'payroll' },
  { title: 'Ledger', page: 'ledger', href: 'ledger.html', path: '/ledger.html', module: 'finance' },
  { title: 'Settings', page: 'settings', href: 'settings.html', path: '/settings.html' },
];

export function currentPageFile() {
  return window.location.pathname.split('/').pop() || 'index.html';
}

export function visibleNav(role, permissions = []) {
  return NAV_ITEMS.filter((item) => item.page === 'dashboard' || (
    hasAccess(role, item.path) && (!item.module || permissions.some((code) => code.startsWith(`${item.module}:`)))
  ));
}

/** Get the current user profile from the API */
export async function getCurrentUser() {
  try {
    return await apiRequest('/users/me');
  } catch (error) {
    console.error("Failed to fetch user profile:", error);
    return null;
  }
}

/** Check if a role has access to a specific path */
export function hasAccess(role, path) {
  if (role === 'Admin') return true;
  
  const allowedRoutes = ROLE_ROUTES[role] || [];
  if (allowedRoutes.includes('*')) return true;
  
  // Exact match or root
  if (allowedRoutes.includes(path)) return true;
  
  // Clean up path (e.g. /sales.html -> /sales)
  const cleanPath = path.replace('.html', '');
  if (allowedRoutes.includes(cleanPath)) return true;
  
  return false;
}

/**
 * Main authentication guard to be run on every protected page.
 * Returns the current user object if authenticated and authorized.
 * Redirects or shows access denied if not.
 */
export async function requireAuth() {
  const user = await getCurrentUser();
  if (!user) {
    window.location.replace('/login.html');
    return null;
  }
  const currentPath = window.location.pathname;
  const pathToCheck = currentPath === '/' ? '/index.html' : currentPath;
  if (!hasAccess(user.roletype, pathToCheck) && pathToCheck !== '/index.html') {
    document.body.innerHTML = '';
    import('./components.js').then(({ createAccessDenied }) => {
      const container = document.createElement('div');
      container.className = 'app-shell';
      const main = document.createElement('main');
      main.style.padding = '2rem';
      main.appendChild(createAccessDenied(user.roletype, user.department_name || 'Unknown'));
      container.appendChild(main);
      document.body.appendChild(container);
    });
    return null;
  }
  return user;
}

// Used by the app shell. Backend route guards remain authoritative.
export async function requireSession() {
  const user = await getCurrentUser();
  if (!user) {
    window.location.replace('/login.html');
    return null;
  }
  const page = document.body.dataset.page || 'dashboard';
  const paths = { dashboard: '/', sales: '/sales.html', employees: '/employees.html', settings: '/settings.html', products: '/products.html', categories: '/categories.html', suppliers: '/suppliers.html', 'purchase-orders': '/purchase-orders.html', payroll: '/payroll.html', ledger: '/ledger.html' };
  const accessPath = paths[page] || `/${page}.html`;
  const permissionModule = { sales: 'sales', employees: 'hr', ledger: 'finance', payroll: 'payroll', products: 'inventory', categories: 'inventory', suppliers: 'procurement', 'purchase-orders': 'procurement' }[page];
  const roleAllowed = hasAccess(user.roletype, accessPath);
  const permissionAllowed = !permissionModule || (user.permissions || []).some((code) => code.startsWith(`${permissionModule}:`));
  return { user, authorized: page === 'dashboard' || (roleAllowed && permissionAllowed) };
}
  
  /** Sign out the user and redirect to login */
  export function signOut() {
    clearAccessToken();
    window.location.replace('/login.html');
  }
