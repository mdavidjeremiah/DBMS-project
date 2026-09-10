import { Receipt } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { POSCheckout } from "@/components/sales/POSCheckout"
import { getSales, getProducts, getEmployees, getOrganisation } from "@/lib/queries"

type Sale = { saleid: number; saledate: string; totalamount: number; customer_name: string; cashier_name: string; branch_name: string; items: Array<{ item_name: string; quantity: number; unitpriceatsale: number }> }
const columns: Column<Sale>[] = [
  { header: "Sale ID", accessorKey: "saleid", sortable: true },
  { header: "Date", accessorKey: "saledate", sortable: true },
  { header: "Customer", accessorKey: "customer_name" },
  { header: "Cashier", accessorKey: "cashier_name" },
  { header: "Branch", accessorKey: "branch_name" },
  { header: "Total", accessorKey: "totalamount", sortable: true, cell: (row) => `UGX ${row.totalamount.toLocaleString()}` },
]

export default async function SalesPage() {
  const [sales, products, employees, organisation] = await Promise.all([getSales(), getProducts(), getEmployees(), getOrganisation()])
  const cashiers = employees.data.filter((employee) => employee.roletype === "Cashier")
  return <div className="flex flex-col gap-6">
    <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><Receipt className="h-4 w-4" /> Point of sale</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Sales & Retail Checkout</h1><p className="text-sm text-slate-500">Live sales and line items from MySQL.</p></header>
    <POSCheckout products={products.data.map(({ itemid, itemname, unitprice }) => ({ itemid, itemname, unitprice }))} cashiers={cashiers.map(({ employeeid, name }) => ({ employeeid, name }))} branches={organisation.branches.data.map(({ branchid, branchname }) => ({ branchid, branchname }))} />
    <DataNotice error={sales.error || products.error || employees.error || organisation.branches.error} rlsBlocked={sales.rlsBlocked || products.rlsBlocked || employees.rlsBlocked || organisation.branches.rlsBlocked} />
    <DataTable data={sales.data} columns={columns} searchKey="customer_name" />
  </div>
}