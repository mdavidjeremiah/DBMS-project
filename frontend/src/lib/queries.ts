import { cookies } from "next/headers"
import { createClient } from "@/utils/supabase/server"

export type QueryResult<T> = { data: T[]; error: string | null; rlsBlocked: boolean }
const empty = <T>(error: { code?: string; message: string } | null): QueryResult<T> => ({ data: [], error: error?.message ?? null, rlsBlocked: error?.code === "42501" || /row-level security|permission denied/i.test(error?.message ?? "") })
async function db() { return createClient(await cookies()) }
export type CategoryRow = { categoryid: number; categoryname: string }
export async function getCategories(): Promise<QueryResult<CategoryRow>> { const { data, error } = await (await db()).from("category").select("categoryid, categoryname").order("categoryname"); return error ? empty(error) : { data: data ?? [], error: null, rlsBlocked: false } }

export type ProductRow = { itemid: number; itemname: string; description: string | null; unitprice: number; reorderlevel: number; categoryid: number; category_name: string }
export async function getProducts(): Promise<QueryResult<ProductRow>> {
  const supabase = await db(); const [products, categories] = await Promise.all([supabase.from("product").select("itemid, itemname, description, unitprice, reorderlevel, categoryid").order("itemname"), supabase.from("category").select("categoryid, categoryname")])
  if (products.error) return empty(products.error); if (categories.error) return empty(categories.error)
  const names = new Map((categories.data ?? []).map((c) => [c.categoryid, c.categoryname]))
  return { data: (products.data ?? []).map((p) => ({ ...p, unitprice: Number(p.unitprice), category_name: names.get(p.categoryid) ?? "Unknown category" })), error: null, rlsBlocked: false }
}

export type SupplierRow = { supplierid: number; suppliername: string; contactperson: string | null; phone: string | null; address: string | null }
export async function getSuppliers(): Promise<QueryResult<SupplierRow>> { const { data, error } = await (await db()).from("supplier").select("supplierid, suppliername, contactperson, phone, address").order("suppliername"); return error ? empty(error) : { data: data ?? [], error: null, rlsBlocked: false } }

export type SupplyRow = { supplierid: number; itemid: number; supplier_name: string; item_name: string; costprice: number; leadtimedays: number | null }
export async function getSupply(): Promise<QueryResult<SupplyRow>> {
  const supabase = await db(); const [supply, suppliers, products] = await Promise.all([supabase.from("supply").select("supplierid, itemid, costprice, leadtimedays"), supabase.from("supplier").select("supplierid, suppliername"), supabase.from("product").select("itemid, itemname")])
  if (supply.error) return empty(supply.error); if (suppliers.error) return empty(suppliers.error); if (products.error) return empty(products.error)
  const supplierNames = new Map((suppliers.data ?? []).map((s) => [s.supplierid, s.suppliername])); const productNames = new Map((products.data ?? []).map((p) => [p.itemid, p.itemname]))
  return { data: (supply.data ?? []).map((s) => ({ ...s, costprice: Number(s.costprice), supplier_name: supplierNames.get(s.supplierid) ?? "Unknown supplier", item_name: productNames.get(s.itemid) ?? "Unknown product" })), error: null, rlsBlocked: false }
}

export type PurchaseOrderRow = { po_id: number; orderdate: string; status: string; supplier_name: string; officer_name: string }
export async function getPurchaseOrders(): Promise<QueryResult<PurchaseOrderRow>> {
  const supabase = await db(); const [orders, suppliers, employees] = await Promise.all([supabase.from("purchase_order").select("po_id, orderdate, supplierid, employeeid, status").order("orderdate", { ascending: false }), supabase.from("supplier").select("supplierid, suppliername"), supabase.from("employee").select("employeeid, name")])
  if (orders.error) return empty(orders.error); if (suppliers.error) return empty(suppliers.error); if (employees.error) return empty(employees.error)
  const supplierNames = new Map((suppliers.data ?? []).map((s) => [s.supplierid, s.suppliername])); const employeeNames = new Map((employees.data ?? []).map((e) => [e.employeeid, e.name]))
  return { data: (orders.data ?? []).map((o) => ({ po_id: o.po_id, orderdate: o.orderdate, status: o.status, supplier_name: supplierNames.get(o.supplierid) ?? "Unknown supplier", officer_name: employeeNames.get(o.employeeid) ?? "Unknown officer" })), error: null, rlsBlocked: false }
}

export type BranchRow = { branchid: number; branchname: string; location: string; contactnumber: string | null; manageremployeeid: number | null; manager_name: string | null }
export type DepartmentRow = { departmentid: number; departmentname: string; branchid: number; branch_name: string }
export async function getOrganisation(): Promise<{ branches: QueryResult<BranchRow>; departments: QueryResult<DepartmentRow> }> {
  const supabase = await db(); const [branches, departments, employees] = await Promise.all([supabase.from("branch").select("branchid, branchname, location, contactnumber, manageremployeeid").order("branchname"), supabase.from("department").select("departmentid, departmentname, branchid").order("departmentname"), supabase.from("employee").select("employeeid, name")])
  const employeeNames = new Map((employees.data ?? []).map((e) => [e.employeeid, e.name])); const branchNames = new Map((branches.data ?? []).map((b) => [b.branchid, b.branchname]))
  return { branches: branches.error ? empty(branches.error) : { data: (branches.data ?? []).map((b) => ({ ...b, manager_name: b.manageremployeeid ? employeeNames.get(b.manageremployeeid) ?? "Unknown employee" : null })), error: null, rlsBlocked: false }, departments: departments.error ? empty(departments.error) : { data: (departments.data ?? []).map((d) => ({ ...d, branch_name: branchNames.get(d.branchid) ?? "Unknown branch" })), error: null, rlsBlocked: false } }
}

export type EmployeeRow = { employeeid: number; name: string; nin: string; phone: string | null; datehired: string; salary: number; roletype: string; departmentid: number; department_name: string; branchid: number; branch_name: string; supervisorid: number | null; supervisor_name: string | null }
export async function getEmployees(): Promise<QueryResult<EmployeeRow>> {
  const supabase = await db(); const [employees, departments, branches] = await Promise.all([supabase.from("employee").select("employeeid, name, nin, phone, datehired, salary, roletype, departmentid, branchid, supervisorid").order("name"), supabase.from("department").select("departmentid, departmentname"), supabase.from("branch").select("branchid, branchname")])
  if (employees.error) return empty(employees.error); if (departments.error) return empty(departments.error); if (branches.error) return empty(branches.error)
  const departmentNames = new Map((departments.data ?? []).map((d) => [d.departmentid, d.departmentname])); const branchNames = new Map((branches.data ?? []).map((b) => [b.branchid, b.branchname])); const employeeNames = new Map((employees.data ?? []).map((e) => [e.employeeid, e.name]))
  return { data: (employees.data ?? []).map((e) => ({ ...e, salary: Number(e.salary), department_name: departmentNames.get(e.departmentid) ?? "Unknown department", branch_name: branchNames.get(e.branchid) ?? "Unknown branch", supervisor_name: e.supervisorid ? employeeNames.get(e.supervisorid) ?? "Unknown employee" : null })), error: null, rlsBlocked: false }
}

export type PayrollRow = { payrollid: number; employeeid: number; employee_name: string; month: string; grosspay: number; deductions: number; netpay: number }
export async function getPayroll(): Promise<QueryResult<PayrollRow>> { const supabase = await db(); const [payroll, employees] = await Promise.all([supabase.from("payroll").select("payrollid, employeeid, month, grosspay, deductions, netpay").order("month", { ascending: false }), supabase.from("employee").select("employeeid, name")]); if (payroll.error) return empty(payroll.error); if (employees.error) return empty(employees.error); const names = new Map((employees.data ?? []).map((e) => [e.employeeid, e.name])); return { data: (payroll.data ?? []).map((p) => ({ ...p, grosspay: Number(p.grosspay), deductions: Number(p.deductions), netpay: Number(p.netpay), employee_name: names.get(p.employeeid) ?? "Unknown employee" })), error: null, rlsBlocked: false } }

export type SaleRow = { saleid: number; saledate: string; totalamount: number; customer_name: string; cashier_name: string; branch_name: string; items: Array<{ item_name: string; quantity: number; unitpriceatsale: number }> }
export async function getSales(): Promise<QueryResult<SaleRow>> {
  const supabase = await db(); const [sales, customers, employees, branches, items, products] = await Promise.all([supabase.from("sale").select("saleid, saledate, totalamount, customerid, employeeid, branchid").order("saledate", { ascending: false }), supabase.from("customer").select("customerid, name"), supabase.from("employee").select("employeeid, name"), supabase.from("branch").select("branchid, branchname"), supabase.from("sale_item").select("saleid, itemid, quantity, unitpriceatsale"), supabase.from("product").select("itemid, itemname")])
  if (sales.error) return empty(sales.error); const failed = [customers, employees, branches, items, products].find((result) => result.error); if (failed?.error) return empty(failed.error)
  const customerNames = new Map((customers.data ?? []).map((c) => [c.customerid, c.name])); const employeeNames = new Map((employees.data ?? []).map((e) => [e.employeeid, e.name])); const branchNames = new Map((branches.data ?? []).map((b) => [b.branchid, b.branchname])); const productNames = new Map((products.data ?? []).map((p) => [p.itemid, p.itemname])); const lines = new Map<number, Array<{ item_name: string; quantity: number; unitpriceatsale: number }>>()
  for (const item of items.data ?? []) lines.set(item.saleid, [...(lines.get(item.saleid) ?? []), { item_name: productNames.get(item.itemid) ?? "Unknown product", quantity: item.quantity, unitpriceatsale: Number(item.unitpriceatsale) }])
  return { data: (sales.data ?? []).map((s) => ({ saleid: s.saleid, saledate: s.saledate, totalamount: Number(s.totalamount), customer_name: s.customerid ? customerNames.get(s.customerid) ?? "Unknown customer" : "Walk-in", cashier_name: employeeNames.get(s.employeeid) ?? "Unknown cashier", branch_name: branchNames.get(s.branchid) ?? "Unknown branch", items: lines.get(s.saleid) ?? [] })), error: null, rlsBlocked: false }
}

export type LedgerRow = { entryid: number; entrydate: string; sourcetype: string; amount: number; source_label: string; accountant_name: string }
export async function getLedger(): Promise<QueryResult<LedgerRow>> { const supabase = await db(); const [entries, sales, payroll, employees] = await Promise.all([supabase.from("ledger_entry").select("entryid, entrydate, sourcetype, saleid, payrollid, amount, recordedby").order("entrydate", { ascending: false }), supabase.from("sale").select("saleid"), supabase.from("payroll").select("payrollid, month"), supabase.from("employee").select("employeeid, name")]); if (entries.error) return empty(entries.error); const failed = [sales, payroll, employees].find((r) => r.error); if (failed?.error) return empty(failed.error); const payMonths = new Map((payroll.data ?? []).map((p) => [p.payrollid, p.month])); const employeeNames = new Map((employees.data ?? []).map((e) => [e.employeeid, e.name])); return { data: (entries.data ?? []).map((entry) => ({ entryid: entry.entryid, entrydate: entry.entrydate, sourcetype: entry.sourcetype, amount: Number(entry.amount), source_label: entry.saleid ? `Sale #${entry.saleid}` : `Payroll · ${payMonths.get(entry.payrollid ?? -1) ?? entry.payrollid}`, accountant_name: employeeNames.get(entry.recordedby) ?? "Unknown accountant" })), error: null, rlsBlocked: false } }

export async function getDashboard() { const [sales, orders, employees, products] = await Promise.all([getSales(), getPurchaseOrders(), getEmployees(), getProducts()]); const today = new Date().toDateString(); return { sales, orders, stats: { salesToday: sales.data.filter((sale) => new Date(sale.saledate).toDateString() === today).reduce((sum, sale) => sum + sale.totalamount, 0), salesCount: sales.data.filter((sale) => new Date(sale.saledate).toDateString() === today).length, pendingOrders: orders.data.filter((order) => order.status === "Pending").length, employeeCount: employees.data.length, productCount: products.data.length } } }
