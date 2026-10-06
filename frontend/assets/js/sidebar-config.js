/**
 * Hardware World ERP — Sidebar Configuration
 *
 * Defines the sidebar navigation for each department / roletype.
 * The shell reads this file and renders only items the user has access to,
 * cross-checking against the permissions[] array from /users/me.
 *
 * Structure per item:
 *   { label, icon, href, perm? }
 *   perm  — optional permission code; item hidden if user lacks it
 */

export const SIDEBAR_CONFIG = {
  // ─────────────────────────────────────────────────────────────────
  // System administration (not operational finance or procurement)
  // ─────────────────────────────────────────────────────────────────
  Admin: [
    { section: 'Dashboard' },
    { label: 'Admin Overview', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Organisation Setup' },
    { label: 'Company Branches', icon: 'building-2', href: 'branches.html', perm: 'admin:users' },
    { label: 'Warehouses', icon: 'warehouse', href: 'warehouses.html', perm: 'admin:users' },
    { label: 'Departments', icon: 'layers', href: 'departments.html', perm: 'admin:users' },

    { section: 'Users & Access' },
    { label: 'User Accounts', icon: 'users', href: 'employees.html', perm: 'admin:users' },
    { label: 'System Settings', icon: 'settings', href: 'settings.html', perm: 'admin:users' },

    { section: 'Audit & Security' },
    { label: 'Audit Logs', icon: 'clipboard-list', href: 'audit-logs.html', perm: 'admin:audit' },

  ],

  // ─────────────────────────────────────────────────────────────────
  // Sales & POS (Cashier / Sarah Nakato)
  // ─────────────────────────────────────────────────────────────────
  Cashier: [
    { section: 'POS Operations' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },
    { label: 'New Sale', icon: 'shopping-cart', href: 'sales.html', perm: 'sales:pos' },
    { label: 'Sales History', icon: 'receipt', href: 'sales.html', perm: 'sales:view' },
    { label: 'Products & Stock', icon: 'package', href: 'products.html' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Procurement & Inventory (Procurement Officer / John Kato)
  // ─────────────────────────────────────────────────────────────────
  'Procurement Officer': [
    { section: 'Overview' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Inventory' },
    { label: 'Stock Levels', icon: 'package', href: 'products.html', perm: 'inventory:view' },

    { section: 'Procurement' },
    { label: 'Approvals', icon: 'check-circle', href: 'approvals.html', perm: ['procurement:approve_req', 'procurement:po_approve', 'inventory:approve_adjust'] },
    { label: 'Purchase Orders', icon: 'file-text', href: 'purchase-orders.html', perm: 'procurement:po_create' },

    { section: 'Suppliers' },
    { label: 'Supplier Directory', icon: 'building', href: 'suppliers.html', perm: 'procurement:supplier' },
    { label: 'Product Catalogue', icon: 'tags', href: 'products.html' },
    { label: 'Categories', icon: 'layers', href: 'categories.html' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Finance & Accounting (Accountant / Grace Apio)
  // ─────────────────────────────────────────────────────────────────
  Accountant: [
    { section: 'Overview' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Financial Records' },
    { label: 'Financial Ledger', icon: 'book-open', href: 'ledger.html', perm: 'finance:view' },

    { section: 'Payroll' },
    { label: 'Payroll Records', icon: 'wallet', href: 'payroll.html', perm: 'payroll:view' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Human Resources (HR Staff / Moses Opolot)
  // ─────────────────────────────────────────────────────────────────
  'HR Staff': [
    { section: 'Overview' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Workforce' },
    { label: 'Employee Directory', icon: 'users', href: 'employees.html', perm: 'hr:view' },
    { label: 'Leave Approvals', icon: 'calendar-check', href: 'approvals.html', perm: 'hr:leave' },

    { section: 'Payroll' },
    { label: 'Payroll Records', icon: 'wallet', href: 'payroll.html', perm: 'payroll:view' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Operations & Branch Management (Branch Manager / Brian Mukasa)
  // ─────────────────────────────────────────────────────────────────
  'Branch Manager': [
    { section: 'Overview' },
    { label: 'Operations Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Sales & Revenue' },
    { label: 'Sales Performance', icon: 'trending-up', href: 'sales.html', perm: 'sales:view' },
    { label: 'Pending Approvals', icon: 'check-circle', href: 'approvals.html', perm: ['procurement:approve_req', 'procurement:po_approve', 'inventory:approve_adjust', 'approvals:approve'] },

    { section: 'Inventory & Procurement' },
    { label: 'Stock Summary', icon: 'package', href: 'products.html', perm: 'inventory:view' },
    { label: 'Purchase Orders', icon: 'file-text', href: 'purchase-orders.html', perm: 'procurement:po_approve' },
    { section: 'People' },
    { label: 'Staff Overview', icon: 'users', href: 'employees.html', perm: 'hr:view' },

    { section: 'Finance' },
    { label: 'Financial Summary', icon: 'bar-chart-2', href: 'ledger.html', perm: 'finance:view' },
    { label: 'Payroll Overview', icon: 'wallet', href: 'payroll.html', perm: 'payroll:view' },

    { section: 'Audit & Security' },
    { label: 'Audit Logs', icon: 'clipboard-list', href: 'audit-logs.html', perm: 'admin:audit' },
  ],
};

/**
 * Get the sidebar items for a given roletype.
 * Filters out items the user lacks permission for.
 * @param {string} roletype
 * @param {string[]} permissions
 * @returns {Array<{section?: string, label?: string, icon?: string, href?: string, perm?: string|string[]}>}
 */
export function getSidebarItems(roletype, permissions = [], assignedRoles = []) {
  const config = assignedRoles.includes('Owner / Executive')
    ? SIDEBAR_CONFIG['Branch Manager']
    : (SIDEBAR_CONFIG[roletype] || SIDEBAR_CONFIG['Admin']);
  const hasWildcard = permissions.includes('*');

  const visible = config.filter((item) => {
    if (item.section || !item.perm || hasWildcard) return true;
    return Array.isArray(item.perm)
      ? item.perm.some((permission) => permissions.includes(permission))
      : permissions.includes(item.perm);
  });
  const result = [];
  let pendingSection = null;
  for (const item of visible) {
    if (item.section) {
      pendingSection = item;
      continue;
    }
    if (pendingSection) result.push(pendingSection);
    result.push(item);
    pendingSection = null;
  }
  return result;
}
