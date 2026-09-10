import { serverApiRequest } from "@/lib/api-server"

export type QueryResult<T> = { data: T[]; error: string | null; rlsBlocked: boolean }
const load = async <T>(path: string): Promise<QueryResult<T>> => {
  try { return { data: await serverApiRequest<T[]>(path), error: null, rlsBlocked: false } }
  catch (error) { return { data: [], error: error instanceof Error ? error.message : "Unable to load data", rlsBlocked: false } }
}

export type CategoryRow = { categoryid: number; categoryname: string }
export const getCategories = () => load<CategoryRow>("/categories")
export type ProductRow = { itemid: number; itemname: string; description: string | null; unitprice: number; reorderlevel: number; categoryid: number; category_name: string }
export const getProducts = () => load<ProductRow>("/products")
export type SupplierRow = { supplierid: number; suppliername: string; contactperson: string | null; phone: string | null; address: string | null }
export const getSuppliers = () => load<SupplierRow>("/suppliers")
export type SupplyRow = { supplierid: number; itemid: number; supplier_name: string; item_name: string; costprice: number; leadtimedays: number | null }
export const getSupply = () => load<SupplyRow>("/supplies")
export type PurchaseOrderRow = { po_id: number; orderdate: string; status: string; supplier_name: string; officer_name: string }
export const getPurchaseOrders = () => load<PurchaseOrderRow>("/purchase-orders")
export type BranchRow = { branchid: number; branchname: string; location: string; contactnumber: string | null; manageremployeeid: number | null; manager_name: string | null }
export type DepartmentRow = { departmentid: number; departmentname: string; branchid: number; branch_name: string }
export async function getOrganisation() {
  const [branches, departments] = await Promise.all([load<BranchRow>("/branches"), load<DepartmentRow>("/departments")])
  return { branches, departments }
}
export type EmployeeRow = { employeeid: number; name: string; nin: string; phone: string | null; datehired: string; salary: number; roletype: string; departmentid: number; department_name: string; branchid: number; branch_name: string; supervisorid: number | null; supervisor_name: string | null }
export const getEmployees = () => load<EmployeeRow>("/employees")
export type PayrollRow = { payrollid: number; employeeid: number; employee_name: string; month: string; grosspay: number; deductions: number; netpay: number }
export const getPayroll = () => load<PayrollRow>("/payroll")
export type SaleRow = { saleid: number; saledate: string; totalamount: number; customer_name: string; cashier_name: string; branch_name: string; items: Array<{ item_name: string; quantity: number; unitpriceatsale: number }> }
export const getSales = () => load<SaleRow>("/sales")
export type LedgerRow = { entryid: number; entrydate: string; sourcetype: string; amount: number; source_label: string; accountant_name: string }
export const getLedger = () => load<LedgerRow>("/ledger")
export async function getDashboard() {
  const [sales, orders, employees, products] = await Promise.all([getSales(), getPurchaseOrders(), getEmployees(), getProducts()])
  const today = new Date().toDateString()
  return { sales, orders, stats: { salesToday: sales.data.filter((sale) => new Date(sale.saledate).toDateString() === today).reduce((sum, sale) => sum + sale.totalamount, 0), salesCount: sales.data.filter((sale) => new Date(sale.saledate).toDateString() === today).length, pendingOrders: orders.data.filter((order) => order.status === "Pending").length, employeeCount: employees.data.length, productCount: products.data.length } }
}
