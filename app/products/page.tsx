import { Package, Plus, AlertTriangle } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Badge } from "@/components/ui/badge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getProducts, ProductRow } from "@/lib/queries"

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-UG", {
    style: "currency",
    currency: "UGX",
    maximumFractionDigits: 0,
  }).format(amount)
}

const columns: Column<ProductRow>[] = [
  { header: "Item", accessorKey: "itemname", sortable: true },
  { header: "Category", accessorKey: "category_name", sortable: true },
  {
    header: "Unit Price",
    accessorKey: "unitprice",
    sortable: true,
    cell: (item) => formatCurrency(item.unitprice),
  },
  {
    header: "Stock Status",
    accessorKey: "quantityonhand",
    sortable: true,
    cell: (item) => {
      const isLowStock = item.quantityonhand <= item.reorderlevel;
      return (
        <div className="flex items-center gap-2">
          {item.quantityonhand} / {item.reorderlevel}
          {isLowStock ? (
            <Badge variant="destructive" className="text-xs">
              <AlertTriangle className="mr-1 h-3 w-3" /> Low Stock
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs text-muted-foreground">
              threshold
            </Badge>
          )}
        </div>
      );
    },
  },
]

export default async function ProductsPage() {
  const { data, rlsBlocked, error } = await getProducts()
  
  const lowStockCount = data.filter(p => p.quantityonhand <= p.reorderlevel).length;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Products</h1>
          <p className="text-muted-foreground">
            Manage the item catalogue Hardware World stocks and sells.
          </p>
        </div>
        <Modal
          title="Add New Product"
          description="Add a product to the catalogue."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add Product
            </Button>
          }
          confirmText="Add Product"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="itemname">Item Name</Label>
              <Input id="itemname" placeholder="e.g. Portland Cement 50kg" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="unitprice">Unit Price (UGX)</Label>
              <Input id="unitprice" type="number" placeholder="0" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="quantityonhand">Initial Quantity</Label>
              <Input id="quantityonhand" type="number" placeholder="0" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="reorderlevel">Reorder Level</Label>
              <Input id="reorderlevel" type="number" placeholder="0" />
            </div>
          </div>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Products"
          value={data.length}
          icon={<Package className="h-4 w-4" />}
        />
        <StatCard
          title="Low Stock Items"
          value={lowStockCount}
          icon={<AlertTriangle className="h-4 w-4 text-destructive" />}
        />
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="itemname"
        emptyMessage={
          rlsBlocked
            ? "No products visible yet -- RLS has no read policy configured."
            : "No products yet. Add your first one above."
        }
      />
    </div>
  )
}