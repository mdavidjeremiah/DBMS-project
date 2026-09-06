"use server"

import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"
import { cookies } from "next/headers"
import { createClient } from "@/utils/supabase/server"
import type { LedgerSourceType, POStatus, RoleType } from "@/lib/database.types"

const text = (form: FormData, key: string, required = true) => {
  const value = String(form.get(key) ?? "").trim()
  if (required && !value) throw new Error(`${key} is required`)
  return value
}
const number = (form: FormData, key: string, minimum = 0) => {
  const value = Number(text(form, key))
  if (!Number.isFinite(value) || value < minimum) throw new Error(`${key} must be a valid number`)
  return value
}
const optionalNumber = (form: FormData, key: string) => {
  const value = text(form, key, false)
  return value ? number(form, key) : null
}
const nullable = (form: FormData, key: string) => text(form, key, false) || null

async function db() { return createClient(await cookies()) }
function fail(error: { message: string } | null) { if (error) throw new Error(error.message) }
function done(path: string) { revalidatePath(path); redirect(path) }

export async function createCategory(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("category").insert({ categoryname: text(form, "categoryname") })).error)
  done("/categories")
}

export async function createSupplier(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("supplier").insert({ suppliername: text(form, "suppliername"), contactperson: nullable(form, "contactperson"), phone: nullable(form, "phone"), address: nullable(form, "address") })).error)
  done("/suppliers")
}

export async function createProduct(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("product").insert({ itemname: text(form, "itemname"), description: nullable(form, "description"), unitprice: number(form, "unitprice"), reorderlevel: number(form, "reorderlevel"), categoryid: number(form, "categoryid", 1) })).error)
  done("/products")
}

export async function createSupply(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("supply").insert({ supplierid: number(form, "supplierid", 1), itemid: number(form, "itemid", 1), costprice: number(form, "costprice"), leadtimedays: optionalNumber(form, "leadtimedays") })).error)
  done("/suppliers")
}

export async function createPurchaseOrder(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("purchase_order").insert({ supplierid: number(form, "supplierid", 1), employeeid: number(form, "employeeid", 1), status: "Pending" })).error)
  done("/purchase-orders")
}

export async function updatePurchaseOrderStatus(form: FormData) {
  const status = text(form, "status") as POStatus
  if (!(["Pending", "Approved", "Received", "Cancelled"] as string[]).includes(status)) throw new Error("Invalid status")
  const supabase = await db()
  fail((await supabase.from("purchase_order").update({ status }).eq("po_id", number(form, "po_id", 1))).error)
  done("/purchase-orders")
}

export async function createBranch(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("branch").insert({ branchname: text(form, "branchname"), location: text(form, "location"), contactnumber: nullable(form, "contactnumber") })).error)
  done("/settings")
}

export async function createDepartment(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("department").insert({ departmentname: text(form, "departmentname"), branchid: number(form, "branchid", 1) })).error)
  done("/settings")
}

export async function assignBranchManager(form: FormData) {
  const supabase = await db()
  fail((await supabase.from("branch").update({ manageremployeeid: number(form, "manageremployeeid", 1) }).eq("branchid", number(form, "branchid", 1))).error)
  done("/settings")
}

export async function createEmployee(form: FormData) {
  const role = text(form, "roletype") as RoleType
  if (!(["Cashier", "Procurement Officer", "Accountant", "HR Staff", "Branch Manager"] as string[]).includes(role)) throw new Error("Invalid employee role")
  const supabase = await db()
  const { data: employee, error } = await supabase.from("employee").insert({ name: text(form, "name"), nin: text(form, "nin"), phone: nullable(form, "phone"), datehired: text(form, "datehired", false) || undefined, salary: number(form, "salary"), departmentid: number(form, "departmentid", 1), branchid: number(form, "branchid", 1), supervisorid: optionalNumber(form, "supervisorid"), roletype: role }).select("employeeid").single()
  fail(error)
  if (!employee) throw new Error("Employee was not created")
  const employeeid = employee.employeeid
  if (role === "Cashier") fail((await supabase.from("cashier").insert({ employeeid, pos_terminalid: text(form, "pos_terminalid") })).error)
  if (role === "Procurement Officer") fail((await supabase.from("procurement_officer").insert({ employeeid, approvallimit: number(form, "approvallimit") })).error)
  if (role === "Accountant") fail((await supabase.from("accountant").insert({ employeeid, certificationnumber: nullable(form, "certificationnumber") })).error)
  if (role === "HR Staff") fail((await supabase.from("hr_staff").insert({ employeeid, hr_role: text(form, "hr_role") })).error)
  if (role === "Branch Manager") fail((await supabase.from("branch_manager").insert({ employeeid, managementlevel: nullable(form, "managementlevel") })).error)
  done("/employees")
}

export async function createPayroll(form: FormData) {
  const grosspay = number(form, "grosspay")
  const deductions = number(form, "deductions")
  if (deductions > grosspay) throw new Error("Deductions cannot exceed gross pay")
  const supabase = await db()
  fail((await supabase.from("payroll").insert({ employeeid: number(form, "employeeid", 1), month: text(form, "month"), grosspay, deductions, netpay: grosspay - deductions })).error)
  done("/payroll")
}

export async function createLedgerEntry(form: FormData) {
  const sourcetype = text(form, "sourcetype") as LedgerSourceType
  if (sourcetype !== "SALE" && sourcetype !== "PAYROLL") throw new Error("Invalid source type")
  const sourceId = number(form, sourcetype === "SALE" ? "saleid" : "payrollid", 1)
  const supabase = await db()
  fail((await supabase.from("ledger_entry").insert({ sourcetype, saleid: sourcetype === "SALE" ? sourceId : null, payrollid: sourcetype === "PAYROLL" ? sourceId : null, amount: number(form, "amount"), recordedby: number(form, "recordedby", 1) })).error)
  done("/ledger")
}

export async function createSale(form: FormData) {
  const itemIds = form.getAll("itemid").map(String).filter(Boolean).map(Number)
  const quantities = form.getAll("quantity").map(String).filter(Boolean).map(Number)
  if (!itemIds.length || itemIds.length !== quantities.length || quantities.some((q) => !Number.isInteger(q) || q < 1)) throw new Error("Add at least one product with a positive quantity")
  const unitPrices = form.getAll("unitprice").map(String).filter(Boolean).map(Number)
  if (unitPrices.length !== itemIds.length || unitPrices.some((price) => !Number.isFinite(price) || price < 0)) throw new Error("Invalid product price")
  const supabase = await db()
  let customerid: number | null = optionalNumber(form, "customerid")
  if (!customerid && (text(form, "customername", false) || text(form, "customerphone", false))) {
    const { data: customer, error } = await supabase.from("customer").insert({ name: nullable(form, "customername"), phone: nullable(form, "customerphone") }).select("customerid").single()
    fail(error); if (!customer) throw new Error("Customer was not created"); customerid = customer.customerid
  }
  const totalamount = unitPrices.reduce((sum, price, index) => sum + price * quantities[index], 0)
  const { data: sale, error } = await supabase.from("sale").insert({ customerid, employeeid: number(form, "employeeid", 1), branchid: number(form, "branchid", 1), totalamount }).select("saleid").single()
  fail(error)
  if (!sale) throw new Error("Sale was not created")
  const { error: itemError } = await supabase.from("sale_item").insert(itemIds.map((itemid, index) => ({ saleid: sale.saleid, itemid, quantity: quantities[index], unitpriceatsale: unitPrices[index] })))
  if (itemError) { await supabase.from("sale").delete().eq("saleid", sale.saleid); fail(itemError) }
  done("/sales")
}
