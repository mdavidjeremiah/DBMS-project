import { Package, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createProduct } from "@/app/actions"
import { getProducts, getCategories } from "@/lib/queries"

type Product = { itemid: number; itemname: string; description: string | null; unitprice: number; reorderlevel: number; categoryid: number; category_name: string }
const columns: Column<Product>[] = [
  { header: "Item ID", accessorKey: "itemid", sortable: true },
  { header: "Item Name", accessorKey: "itemname", sortable: true },
  { header: "Category", accessorKey: "category_name", sortable: true },
  { header: "Unit Price", accessorKey: "unitprice", sortable: true, cell: (row) => `UGX ${row.unitprice.toLocaleString()}` },
  { header: "Reorder Level", accessorKey: "reorderlevel", sortable: true },
]

export default async function ProductsPage() {
  const [products, categories] = await Promise.all([getProducts(), getCategories()])
  return <div className="flex flex-col gap-6">
    <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
      <div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><Package className="h-4 w-4" /> Hardware catalogue</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Products & Stock Inventory</h1><p className="text-sm text-slate-500">Live product prices and reorder settings.</p></div>
      <FormDialog title="Add product" description="Create a product in the live catalogue." trigger={<Button><Plus className="mr-2 h-4 w-4" /> Add Product</Button>} action={createProduct} submitLabel="Create product">
        <Label htmlFor="itemname">Item name</Label><Input id="itemname" name="itemname" required />
        <Label htmlFor="description">Description</Label><Input id="description" name="description" />
        <Label htmlFor="unitprice">Unit price (UGX)</Label><Input id="unitprice" name="unitprice" type="number" min="0" required />
        <Label htmlFor="reorderlevel">Reorder level</Label><Input id="reorderlevel" name="reorderlevel" type="number" min="0" required />
        <Label htmlFor="categoryid">Category ID</Label><Input id="categoryid" name="categoryid" type="number" min="1" required placeholder={categories.data[0] ? String(categories.data[0].categoryid) : undefined} />
      </FormDialog>
    </header>
    <DataNotice error={products.error || categories.error} rlsBlocked={products.rlsBlocked || categories.rlsBlocked} />
    <DataTable data={products.data} columns={columns} searchKey="itemname" />
  </div>
}