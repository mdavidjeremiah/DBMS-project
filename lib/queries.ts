import { cookies } from "next/headers";
import { createClient } from "@/utils/supabase/server";

async function getServerClient() {
  const cookieStore = await cookies();
  return createClient(cookieStore);
}

/**
 * Every one of these queries runs against tables that have RLS switched on
 * with NO policies yet (Issue #2 deliberately leaves them locked until
 * Issue #3 adds the role permission matrix). That means right now, using
 * the anon/authenticated key, every query below will resolve successfully
 * with either an empty array or a permission-denied error -- NOT because
 * anything here is broken, but because there's no policy yet granting
 * read access. Each function surfaces that distinction via `rlsBlocked`
 * so pages can show an honest, specific empty state instead of a generic
 * "no data" message that looks like a bug.
 *
 * PostgREST embed note: `table(columns)` below follows a foreign key from
 * the base table to `table` -- the thing in front of the parens must be an
 * actual table name (or an alias:table pair), not the FK column name.
 */
export interface QueryResult<T> {
  data: T[];
  rlsBlocked: boolean;
  error: string | null;
}

function isRlsError(error: { code?: string; message?: string } | null): boolean {
  if (!error) return false;
  // 42501 = insufficient_privilege (Postgres), which is what a
  // RLS-enabled-no-policy table returns.
  return Boolean(
    error.code === "42501" ||
    error.message?.toLowerCase().includes("row-level security") ||
    error.message?.toLowerCase().includes("permission denied")
  );
}

function fail<T>(error: { code?: string; message?: string }): QueryResult<T> {
  return {
    data: [],
    rlsBlocked: isRlsError(error),
    error: isRlsError(error) ? null : error.message ?? "Unknown error",
  };
}

// ---------------------------------------------------------------------------
// Dashboard aggregates
// ---------------------------------------------------------------------------

export interface DashboardStats {
  totalSalesToday: number;
  salesCountToday: number;
  pendingPurchaseOrders: number;
  activeEmployees: number;
  totalProducts: number;
}

export async function getDashboardStats(): Promise<
  QueryResult<never> & { stats: DashboardStats }
> {
  const supabase = await getServerClient();
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const results = await Promise.all([
    supabase
      .from("sale")
      .select("totalamount", { count: "exact" })
      .gte("saledate", todayStart.toISOString()),
    supabase
      .from("purchase_order")
      .select("po_id", { count: "exact", head: true })
      .eq("status", "Pending"),
    supabase
      .from("employee")
      .select("employeeid", { count: "exact", head: true }),
    supabase.from("product").select("itemid", { count: "exact", head: true }),
  ]);
  const [salesToday, pendingPOs, employees, products] = results;

  const errors = results.map((r) => r.error);
  const anyRlsBlocked = errors.some((e) => isRlsError(e));
  const firstRealError = errors.find((e) => e && !isRlsError(e));

  const totalSalesToday = (salesToday.data ?? []).reduce(
    (sum: number, row: { totalamount: number | string | null }) =>
      sum + Number(row.totalamount ?? 0),
    0
  );

  return {
    data: [],
    rlsBlocked: anyRlsBlocked,
    error: firstRealError?.message ?? null,
    stats: {
      totalSalesToday,
      salesCountToday: salesToday.count ?? 0,
      pendingPurchaseOrders: pendingPOs.count ?? 0,
      activeEmployees: employees.count ?? 0,
      totalProducts: products.count ?? 0,
    },
  };
}

export interface RecentSale {
  saleid: number;
  saledate: string;
  totalamount: number;
  customer_name: string | null;
  cashier_name: string | null;
}

export async function getRecentSales(
  limit = 5
): Promise<QueryResult<RecentSale>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("sale")
    .select(
      "saleid, saledate, totalamount, customer(name), cashier(employee(name))"
    )
    .order("saledate", { ascending: false })
    .limit(limit);

  if (error) return fail(error);

  type RawRow = {
    saleid: number;
    saledate: string;
    totalamount: number;
    customer: { name: string | null } | null;
    cashier: { employee: { name: string } | null } | null;
  };

  const mapped: RecentSale[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    saleid: row.saleid,
    saledate: row.saledate,
    totalamount: Number(row.totalamount),
    customer_name: row.customer?.name ?? null,
    cashier_name: row.cashier?.employee?.name ?? null,
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

export interface PendingPO {
  po_id: number;
  orderdate: string;
  supplier_name: string;
}

export async function getPendingPurchaseOrders(
  limit = 5
): Promise<QueryResult<PendingPO>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("purchase_order")
    .select("po_id, orderdate, supplier(suppliername)")
    .eq("status", "Pending")
    .order("orderdate", { ascending: true })
    .limit(limit);

  if (error) return fail(error);

  type RawRow = {
    po_id: number;
    orderdate: string;
    supplier: { suppliername: string } | null;
  };

  const mapped: PendingPO[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    po_id: row.po_id,
    orderdate: row.orderdate,
    supplier_name: row.supplier?.suppliername ?? "Unknown supplier",
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Products
// ---------------------------------------------------------------------------

export interface ProductRow {
  itemid: number;
  itemname: string;
  unitprice: number;
  reorderlevel: number;
  quantityonhand: number;
  category_name: string;
}

export async function getProducts(): Promise<QueryResult<ProductRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("product")
    .select("itemid, itemname, unitprice, reorderlevel, quantityonhand, category(categoryname)")
    .order("itemname");

  if (error) return fail(error);

  type RawRow = {
    itemid: number;
    itemname: string;
    unitprice: number;
    reorderlevel: number;
    quantityonhand: number;
    category: { categoryname: string } | null;
  };

  const mapped: ProductRow[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    itemid: row.itemid,
    itemname: row.itemname,
    unitprice: Number(row.unitprice),
    reorderlevel: row.reorderlevel,
    quantityonhand: row.quantityonhand,
    category_name: row.category?.categoryname ?? "Uncategorized",
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export interface CategoryRow {
  categoryid: number;
  categoryname: string;
}

export async function getCategories(): Promise<QueryResult<CategoryRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("category")
    .select("categoryid, categoryname")
    .order("categoryname");

  if (error) return fail(error);
  return { data: data ?? [], rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Suppliers
// ---------------------------------------------------------------------------

export interface SupplierRow {
  supplierid: number;
  suppliername: string;
  contactperson: string | null;
  phone: string | null;
}

export async function getSuppliers(): Promise<QueryResult<SupplierRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("supplier")
    .select("supplierid, suppliername, contactperson, phone")
    .order("suppliername");

  if (error) return fail(error);
  return { data: data ?? [], rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Purchase Orders
// ---------------------------------------------------------------------------

export interface PurchaseOrderRow {
  po_id: number;
  orderdate: string;
  supplier_name: string;
  status: string;
}

export async function getPurchaseOrders(): Promise<
  QueryResult<PurchaseOrderRow>
> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("purchase_order")
    .select("po_id, orderdate, status, supplier(suppliername)")
    .order("orderdate", { ascending: false });

  if (error) return fail(error);

  type RawRow = {
    po_id: number;
    orderdate: string;
    status: string;
    supplier: { suppliername: string } | null;
  };

  const mapped: PurchaseOrderRow[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    po_id: row.po_id,
    orderdate: row.orderdate,
    status: row.status,
    supplier_name: row.supplier?.suppliername ?? "Unknown supplier",
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Sales
// ---------------------------------------------------------------------------

export interface SaleRow {
  saleid: number;
  saledate: string;
  totalamount: number;
  customer_name: string;
  cashier_name: string;
  branch_name: string;
}

export async function getSales(): Promise<QueryResult<SaleRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("sale")
    .select(
      "saleid, saledate, totalamount, customer(name), cashier(employee(name)), branch(branchname)"
    )
    .order("saledate", { ascending: false });

  if (error) return fail(error);

  type RawRow = {
    saleid: number;
    saledate: string;
    totalamount: number;
    customer: { name: string | null } | null;
    cashier: { employee: { name: string } | null } | null;
    branch: { branchname: string } | null;
  };

  const mapped: SaleRow[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    saleid: row.saleid,
    saledate: row.saledate,
    totalamount: Number(row.totalamount),
    customer_name: row.customer?.name ?? "Walk-in",
    cashier_name: row.cashier?.employee?.name ?? "Unknown",
    branch_name: row.branch?.branchname ?? "Unknown",
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Employees
// ---------------------------------------------------------------------------

export interface EmployeeRow {
  employeeid: number;
  name: string;
  roletype: string;
  department_name: string;
  branch_name: string;
}

export async function getEmployees(): Promise<QueryResult<EmployeeRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("employee")
    .select(
      "employeeid, name, roletype, department(departmentname), branch(branchname)"
    )
    .order("name");

  if (error) return fail(error);

  type RawRow = {
    employeeid: number;
    name: string;
    roletype: string;
    department: { departmentname: string } | null;
    branch: { branchname: string } | null;
  };

  const mapped: EmployeeRow[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    employeeid: row.employeeid,
    name: row.name,
    roletype: row.roletype,
    department_name: row.department?.departmentname ?? "Unassigned",
    branch_name: row.branch?.branchname ?? "Unassigned",
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Payroll
// ---------------------------------------------------------------------------

export interface PayrollRow {
  payrollid: number;
  employee_name: string;
  month: string;
  grosspay: number;
  deductions: number;
  netpay: number;
}

export async function getPayroll(): Promise<QueryResult<PayrollRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("payroll")
    .select("payrollid, month, grosspay, deductions, netpay, employee(name)")
    .order("month", { ascending: false });

  if (error) return fail(error);

  type RawRow = {
    payrollid: number;
    month: string;
    grosspay: number;
    deductions: number;
    netpay: number;
    employee: { name: string } | null;
  };

  const mapped: PayrollRow[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    payrollid: row.payrollid,
    employee_name: row.employee?.name ?? "Unknown",
    month: row.month,
    grosspay: Number(row.grosspay),
    deductions: Number(row.deductions),
    netpay: Number(row.netpay),
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}

// ---------------------------------------------------------------------------
// Ledger
// ---------------------------------------------------------------------------

export interface LedgerRow {
  entryid: number;
  entrydate: string;
  sourcetype: string;
  amount: number;
  recordedby_name: string;
}

export async function getLedgerEntries(): Promise<QueryResult<LedgerRow>> {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("ledger_entry")
    .select(
      "entryid, entrydate, sourcetype, amount, accountant(employee(name))"
    )
    .order("entrydate", { ascending: false });

  if (error) return fail(error);

  type RawRow = {
    entryid: number;
    entrydate: string;
    sourcetype: string;
    amount: number;
    accountant: { employee: { name: string } | null } | null;
  };

  const mapped: LedgerRow[] = ((data ?? []) as unknown as RawRow[]).map((row) => ({
    entryid: row.entryid,
    entrydate: row.entrydate,
    sourcetype: row.sourcetype,
    amount: Number(row.amount),
    recordedby_name: row.accountant?.employee?.name ?? "Unknown",
  }));

  return { data: mapped, rlsBlocked: false, error: null };
}