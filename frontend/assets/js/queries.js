import { apiRequest } from './api.js';

export async function getCategories() {
  return await apiRequest('/categories');
}

export async function getProducts() {
  return await apiRequest('/products');
}

export async function getSuppliers() {
  return await apiRequest('/suppliers');
}

export async function getSales() {
  return await apiRequest('/sales');
}

export async function getEmployees() {
  return await apiRequest('/employees');
}

export async function getPayroll() {
  return await apiRequest('/payroll');
}

export async function getLedger() {
  return await apiRequest('/ledger');
}

export async function getPurchaseOrders() {
  return await apiRequest('/purchase-orders');
}

export async function getOrganisation() {
  const [branches, departments] = await Promise.all([
    apiRequest('/branches'),
    apiRequest('/departments')
  ]);
  return { branches, departments };
}

export async function getDashboard() {
  const [sales, pos, staff] = await Promise.all([
    apiRequest('/sales/recent'),
    apiRequest('/purchase-orders/recent'),
    apiRequest('/employees')
  ]);
  return {
    sales: sales || [],
    recentPOs: pos || [],
    staffCount: staff?.length || 0,
    salesToday: (sales || []).reduce((sum, s) => sum + s.totalamount, 0),
    txCount: (sales || []).length
  };
}
