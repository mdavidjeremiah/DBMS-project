"use server"

import { revalidatePath } from "next/cache"
import { redirect } from "next/navigation"
import { serverApiRequest } from "@/lib/api-server"

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
const finish = (path: string) => { revalidatePath(path); redirect(path) }
const post = <T>(path: string, body: unknown) => serverApiRequest<T>(path, { method: "POST", body: JSON.stringify(body) })

export async function createCategory(form: FormData) { await post("/categories", { categoryname: text(form, "categoryname") }); finish("/categories") }
export async function createSupplier(form: FormData) { await post("/suppliers", { suppliername: text(form, "suppliername"), contactperson: text(form, "contactperson", false) || null, phone: text(form, "phone", false) || null, address: text(form, "address", false) || null }); finish("/suppliers") }
export async function createProduct(form: FormData) { await post("/products", { itemname: text(form, "itemname"), description: text(form, "description", false) || null, unitprice: number(form, "unitprice"), reorderlevel: number(form, "reorderlevel"), categoryid: number(form, "categoryid", 1) }); finish("/products") }
export async function createPurchaseOrder(form: FormData) { await post("/purchase-orders", { supplierid: number(form, "supplierid", 1), employeeid: number(form, "employeeid", 1), status: "Pending" }); finish("/purchase-orders") }
export async function createEmployee(form: FormData) { await post("/employees", { name: text(form, "name"), nin: text(form, "nin"), phone: text(form, "phone", false) || null, datehired: text(form, "datehired", false) || null, salary: number(form, "salary"), departmentid: number(form, "departmentid", 1), branchid: number(form, "branchid", 1), supervisorid: optionalNumber(form, "supervisorid"), roletype: text(form, "roletype"), pos_terminalid: text(form, "pos_terminalid", false) || null, approvallimit: optionalNumber(form, "approvallimit"), certificationnumber: text(form, "certificationnumber", false) || null, hr_role: text(form, "hr_role", false) || null, managementlevel: text(form, "managementlevel", false) || null }); finish("/employees") }
export async function createPayroll(form: FormData) { const grosspay = number(form, "grosspay"); const deductions = number(form, "deductions"); if (deductions > grosspay) throw new Error("Deductions cannot exceed gross pay"); await post("/payroll", { employeeid: number(form, "employeeid", 1), month: text(form, "month"), grosspay, deductions }); finish("/payroll") }
export async function createLedgerEntry(form: FormData) { const sourcetype = text(form, "sourcetype"); const sourceid = number(form, "sourceid", 1); await post("/ledger", { sourcetype, saleid: sourcetype === "SALE" ? sourceid : null, payrollid: sourcetype === "PAYROLL" ? sourceid : null, amount: number(form, "amount"), recordedby: number(form, "recordedby", 1) }); finish("/ledger") }
export async function createSale(form: FormData) {
  const itemIds = form.getAll("itemid").map(Number)
  const quantities = form.getAll("quantity").map(Number)
  if (!itemIds.length || itemIds.length !== quantities.length || quantities.some((quantity) => !Number.isInteger(quantity) || quantity < 1)) throw new Error("Add at least one product with a positive quantity")
  await post("/sales", { customerid: optionalNumber(form, "customerid"), customername: text(form, "customername", false) || null, customerphone: text(form, "customerphone", false) || null, employeeid: number(form, "employeeid", 1), branchid: number(form, "branchid", 1), items: itemIds.map((itemid, index) => ({ itemid, quantity: quantities[index] })) })
  finish("/sales")
}
