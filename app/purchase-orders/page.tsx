import { ShoppingCart, Plus } from "lucide-react"
import { StatCard } from "@/components/shared/StatCard"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getPurchaseOrders, PurchaseOrderRow } from "@/lib/queries"

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

const columns: Column<PurchaseOrderRow>[] = [
  {
    header: "Order ID",
    accessorKey: "po_id",
    sortable: true,
    cell: (item) => `PO-${item.po_id}`,
  },
  { header: "Supplier", accessorKey: "supplier_name", sortable: true },
  {
    header: "Order Date",
    accessorKey: "orderdate",
    sortable: true,
    cell: (item) => formatDate(item.orderdate),
  },
  {
    header: "Status",
    accessorKey: "status",
    sortable: true,
    cell: (item) => (
      <StatusBadge
        status={item.status as "Pending" | "Approved" | "Received" | "Cancelled"}
      />
    ),
  },
]

export default async function PurchaseOrdersPage() {
  const { data, rlsBlocked, error } = await getPurchaseOrders()
  const pendingCount = data.filter((o) => o.status === "Pending").length
  const receivedCount = data.filter((o) => o.status === "Received").length
  const cancelledCount = data.filter((o) => o.status === "Cancelled").length

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Purchase Orders
          </h1>
          <p className="text-muted-foreground">
            Manage and track your supplier orders.
          </p>
        </div>

        <Modal
          title="Create New Order"
          description="Create a new purchase order manually."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Create New Order
            </Button>
          }
          confirmText="Create Order"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="supplier">Supplier</Label>
              <Input id="supplier" placeholder="e.g. Crown Cement Ltd" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="total">Estimated Total</Label>
              <Input id="total" type="number" placeholder="0" />
            </div>
          </div>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Orders"
          value={data.length}
          icon={<ShoppingCart className="h-4 w-4" />}
        />
        <StatCard
          title="Pending Approval"
          value={pendingCount}
          icon={<ShoppingCart className="h-4 w-4 text-yellow-500" />}
        />
        <StatCard
          title="Received"
          value={receivedCount}
          icon={<ShoppingCart className="h-4 w-4 text-green-500" />}
        />
        <StatCard
          title="Cancelled"
          value={cancelledCount}
          icon={<ShoppingCart className="h-4 w-4 text-red-500" />}
        />
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="supplier_name"
        showMockFilters
        emptyMessage={
          rlsBlocked
            ? "No purchase orders visible yet -- RLS has no read policy configured."
            : "No purchase orders yet. Create your first one above."
        }
      />
    </div>
  )
}