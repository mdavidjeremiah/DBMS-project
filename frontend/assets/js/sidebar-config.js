/**
 * Hardware World ERP — Sidebar Configuration
 *
 * Defines the sidebar navigation for each department / roletype.
 * The shell reads this file and renders only items the user has access to,
 * cross-checking against the permissions[] array from /users/me.
 *
 * Structure per item:
 *   { label, icon, href, perm?, badge? }
 *   perm  — optional permission code; item hidden if user lacks it
 *   badge — optional badge key; shell fetches count from dashboard data
 */

export const SIDEBAR_CONFIG = {
  // ─────────────────────────────────────────────────────────────────
  // Administration (Admin / Akena)
  // ─────────────────────────────────────────────────────────────────
  Admin: [
    { section: 'Dashboard' },
    { label: 'Admin Overview', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Organisation Setup' },
    { label: 'Company Branches', icon: 'building-2', href: 'branches.html', perm: 'admin:all' },
    { label: 'Warehouses', icon: 'warehouse', href: 'warehouses.html', perm: 'admin:all' },
    { label: 'Departments', icon: 'layers', href: 'departments.html', perm: 'admin:all' },

    { section: 'Users & Access' },
    { label: 'User Accounts', icon: 'users', href: 'employees.html', perm: 'admin:users' },
    { label: 'Roles & Permissions', icon: 'shield', href: 'settings.html', perm: 'admin:users' },

    { section: 'Audit & Security' },
    { label: 'Audit Logs', icon: 'clipboard-list', href: 'audit-logs.html', perm: 'admin:audit', badge: 'failed_logins' },

    { section: 'Reports' },
    { label: 'Business Overview', icon: 'bar-chart-2', href: 'index.html#reports' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Sales & POS (Cashier / Sarah Nakato)
  // ─────────────────────────────────────────────────────────────────
  Cashier: [
    { section: 'POS Operations' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },
    { label: 'New Sale', icon: 'shopping-cart', href: 'sales.html', perm: 'sales:pos', badge: 'held_sales' },
    { label: 'Sales History', icon: 'receipt', href: 'sales.html#history', perm: 'sales:view' },

    { section: 'Requests' },
    { label: 'Returns & Refunds', icon: 'rotate-ccw', href: 'sales.html#returns', perm: 'sales:refund' },
    { label: 'Discount Requests', icon: 'tag', href: 'sales.html#discounts', perm: 'sales:discount' },

    { section: 'Reference' },
    { label: 'Products & Stock', icon: 'package', href: 'products.html' },
    { label: 'Customers', icon: 'user-check', href: 'sales.html#customers' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Procurement & Inventory (Procurement Officer / John Kato)
  // ─────────────────────────────────────────────────────────────────
  'Procurement Officer': [
    { section: 'Overview' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Inventory' },
    { label: 'Stock Levels', icon: 'package', href: 'products.html', perm: 'inventory:view', badge: 'low_stock_count' },
    { label: 'Stock Movements', icon: 'arrow-up-down', href: 'products.html#movements', perm: 'inventory:view' },
    { label: 'Stock Adjustments', icon: 'sliders', href: 'products.html#adjustments', perm: 'inventory:adjust' },
    { label: 'Stocktake', icon: 'clipboard-check', href: 'products.html#stocktake', perm: 'inventory:stocktake' },

    { section: 'Procurement' },
    { label: 'Purchase Requisitions', icon: 'file-plus', href: 'purchase-orders.html#requisitions', perm: 'procurement:requisition', badge: 'pending_requisitions' },
    { label: 'Purchase Orders', icon: 'file-text', href: 'purchase-orders.html', perm: 'procurement:po_create', badge: 'pending_pos' },
    { label: 'Goods Received', icon: 'truck', href: 'purchase-orders.html#grn', perm: 'procurement:grn' },

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
    { label: 'Journal Entries', icon: 'book-open', href: 'ledger.html', perm: 'finance:view' },
    { label: 'Cash Position', icon: 'banknote', href: 'ledger.html#cash', perm: 'finance:view' },
    { label: 'Supplier Invoices', icon: 'file-invoice', href: 'purchase-orders.html#invoices', perm: 'finance:invoice' },
    { label: 'Supplier Payments', icon: 'credit-card', href: 'purchase-orders.html#payments', perm: 'finance:payment' },

    { section: 'Receivables & Payables' },
    { label: 'Customer Accounts', icon: 'user-check', href: 'sales.html#customers', perm: 'finance:view' },
    { label: 'Accounts Payable', icon: 'arrow-down-circle', href: 'ledger.html#payables', perm: 'finance:view' },

    { section: 'Payroll' },
    { label: 'Payroll Records', icon: 'wallet', href: 'payroll.html', perm: 'payroll:view' },
    { label: 'My Payslip', icon: 'receipt', href: 'payroll.html#payslip' },

    { section: 'Reports' },
    { label: 'Sales Report', icon: 'bar-chart-2', href: 'ledger.html#reports', perm: 'sales:view' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Human Resources (HR Staff / Moses Opolot)
  // ─────────────────────────────────────────────────────────────────
  'HR Staff': [
    { section: 'Overview' },
    { label: 'Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Workforce' },
    { label: 'Employee Directory', icon: 'users', href: 'employees.html', perm: 'hr:view' },
    { label: 'Attendance Records', icon: 'calendar-check', href: 'employees.html#attendance', perm: 'hr:attendance' },
    { label: 'Leave Requests', icon: 'calendar', href: 'employees.html#leave', perm: 'hr:leave', badge: 'pending_leaves' },

    { section: 'Payroll' },
    { label: 'Payroll Runs', icon: 'calculator', href: 'payroll.html', perm: 'payroll:prepare' },
    { label: 'Payslips', icon: 'receipt', href: 'payroll.html#payslips', perm: 'payroll:view' },
    { label: 'Salary Structures', icon: 'wallet', href: 'payroll.html#structures', perm: 'hr:manage' },

    { section: 'My Records' },
    { label: 'My Payslip', icon: 'file-text', href: 'payroll.html#my-payslip' },
  ],

  // ─────────────────────────────────────────────────────────────────
  // Operations & Branch Management (Branch Manager / Brian Mukasa)
  // ─────────────────────────────────────────────────────────────────
  'Branch Manager': [
    { section: 'Overview' },
    { label: 'Operations Dashboard', icon: 'layout-dashboard', href: 'index.html' },

    { section: 'Sales & Revenue' },
    { label: 'Sales Performance', icon: 'trending-up', href: 'sales.html', perm: 'sales:view' },
    { label: 'Pending Approvals', icon: 'check-circle', href: 'index.html#approvals', badge: 'pending_approvals' },

    { section: 'Inventory & Procurement' },
    { label: 'Stock Summary', icon: 'package', href: 'products.html', perm: 'inventory:view', badge: 'low_stock_count' },
    { label: 'Purchase Orders', icon: 'file-text', href: 'purchase-orders.html', perm: 'procurement:po_approve' },

    { section: 'People' },
    { label: 'Staff Overview', icon: 'users', href: 'employees.html', perm: 'hr:view' },
    { label: 'Leave Requests', icon: 'calendar', href: 'employees.html#leave', perm: 'hr:view' },

    { section: 'Finance' },
    { label: 'Financial Summary', icon: 'bar-chart-2', href: 'ledger.html', perm: 'finance:view' },
    { label: 'Payroll Overview', icon: 'wallet', href: 'payroll.html', perm: 'payroll:view' },

    { section: 'Reports' },
    { label: 'Branch Reports', icon: 'file-bar-chart', href: 'index.html#reports' },
    { label: 'Audit Logs', icon: 'clipboard-list', href: 'audit-logs.html', perm: 'admin:audit' },
  ],
};

/**
 * Get the sidebar items for a given roletype.
 * Filters out items the user lacks permission for.
 * @param {string} roletype
 * @param {string[]} permissions
 * @returns {Array<{section?: string, label?: string, icon?: string, href?: string, perm?: string}>}
 */
export function getSidebarItems(roletype, permissions = []) {
  const config = SIDEBAR_CONFIG[roletype] || SIDEBAR_CONFIG['Admin'];
  const hasWildcard = permissions.includes('*');

  return config.filter((item) => {
    if (item.section) return true; // Always include section headers (filtered visually)
    if (!item.perm) return true;   // No perm required → always visible
    if (hasWildcard) return true;
    return permissions.includes(item.perm);
  });
}
