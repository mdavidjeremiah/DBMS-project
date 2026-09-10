import { ShoppingCart, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createPurchaseOrder } from "@/app/actions"
import { getPurchaseOrders, getSuppliers, getEmployees } from "@/lib/queries"

type Order = { po_id: number; orderdate: string; status: string; supplier_name: string; officer_name: string }
const columns: Column<Order>[] = [{ header: "Order ID", accessorKey: "po_id", sortable: true }, { header: "Date", accessorKey: "orderdate", sortable: true }, { header: "Supplier", accessorKey: "supplier_name", sortable: true }, { header: "Officer", accessorKey: "officer_name" }, { header: "Status", accessorKey: "status", sortable: true }]

export default async function PurchaseOrdersPage() {
  const [orders, suppliers, employees] = await Promise.all([getPurchaseOrders(), getSuppliers(), getEmployees()])
  return <div className="flex flex-col gap-6"><header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between"><div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><ShoppingCart className="h-4 w-4" /> Procurement</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Purchase Orders</h1><p className="text-sm text-slate-500">Live purchase orders and their assigned officers.</p></div><FormDialog title="Create purchase order" description="Issue an order using live supplier and employee records." trigger={<Button><Plus className="mr-2 h-4 w-4" /> Create Order</Button>} action={createPurchaseOrder} submitLabel="Issue order"><Label htmlFor="supplierid">Supplier ID</Label><Input id="supplierid" name="supplierid" type="number" min="1" required placeholder={suppliers.data[0] ? String(suppliers.data[0].supplierid) : undefined} /><Label htmlFor="employeeid">Officer employee ID</Label><Input id="employeeid" name="employeeid" type="number" min="1" required placeholder={employees.data[0] ? String(employees.data[0].employeeid) : undefined} /></FormDialog></header><DataNotice error={orders.error || suppliers.error || employees.error} rlsBlocked={orders.rlsBlocked || suppliers.rlsBlocked || employees.rlsBlocked} /><DataTable data={orders.data} columns={columns} searchKey="supplier_name" /></div>
}