import { Truck, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createSupplier } from "@/app/actions"
import { getSuppliers } from "@/lib/queries"

type Supplier = { supplierid: number; suppliername: string; contactperson: string | null; phone: string | null; address: string | null }
const columns: Column<Supplier>[] = [{ header: "Supplier ID", accessorKey: "supplierid", sortable: true }, { header: "Company", accessorKey: "suppliername", sortable: true }, { header: "Contact", accessorKey: "contactperson" }, { header: "Phone", accessorKey: "phone" }, { header: "Address", accessorKey: "address" }]

export default async function SuppliersPage() {
  const result = await getSuppliers()
  return <div className="flex flex-col gap-6"><header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between"><div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><Truck className="h-4 w-4" /> Vendor directory</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Suppliers & Manufacturers</h1><p className="text-sm text-slate-500">Live supplier records from Supabase.</p></div><FormDialog title="Register supplier" description="Add a supplier to the live vendor registry." trigger={<Button><Plus className="mr-2 h-4 w-4" /> Add Supplier</Button>} action={createSupplier} submitLabel="Save supplier"><Label htmlFor="suppliername">Company name</Label><Input id="suppliername" name="suppliername" required /><Label htmlFor="contactperson">Contact person</Label><Input id="contactperson" name="contactperson" /><Label htmlFor="phone">Phone</Label><Input id="phone" name="phone" /><Label htmlFor="address">Address</Label><Input id="address" name="address" /></FormDialog></header><DataNotice error={result.error} rlsBlocked={result.rlsBlocked} /><DataTable data={result.data} columns={columns} searchKey="suppliername" /></div>
}