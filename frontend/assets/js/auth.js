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
  'Branch Manager': ['/', '/categories.html', '/products.html', '/suppliers.html', '/purchase-orders.html', '/sales.html', '/employees.html', '/payroll.html', '/ledger.html'],
  'HR Staff': ['/', '/employees.html', '/payroll.html'],
  'Accountant': ['/', '/ledger.html', '/sales.html', '/payroll.html', '/purchase-orders.html'],
  'Procurement Officer': ['/', '/suppliers.html', '/categories.html', '/products.html', '/purchase-orders.html'],
  'Cashier': ['/', '/sales.html', '/products.html']
};

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
    // Not authenticated, redirect to login
    window.location.replace('/login.html');
    return null; // Return null so callers know execution should stop
  }

  // Check RBAC
  const currentPath = window.location.pathname;
  // If we are at root, it's index.html
  const pathToCheck = currentPath === '/' ? '/index.html' : currentPath;

  if (!hasAccess(user.role, pathToCheck) && pathToCheck !== '/index.html') {
    // We allow everyone to see the dashboard (index.html), but other pages are restricted.
    // If they don't have access to this page, render the Access Denied component
    document.body.innerHTML = '';
    
    // Dynamically import components to show access denied
    import('./components.js').then(({ createAccessDenied }) => {
      const container = document.createElement('div');
      container.className = 'app-shell';
      
      const main = document.createElement('main');
      main.style.padding = '2rem';
      main.appendChild(createAccessDenied(user.role, user.department?.departmentname || 'Unknown'));
      
      container.appendChild(main);
      document.body.appendChild(container);
    });
    
    return null; // Prevent further rendering
  }

  return user;
}

/** Sign out the user and redirect to login */
export function signOut() {
  clearAccessToken();
  window.location.replace('/login.html');
}
