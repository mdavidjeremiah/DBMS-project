import { Truck, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getSuppliers, SupplierRow } from "@/lib/queries"

const columns: Column<SupplierRow>[] = [
  { header: "Supplier", accessorKey: "suppliername", sortable: true },
  { header: "Contact Person", accessorKey: "contactperson" },
  { header: "Phone", accessorKey: "phone" },
]

export default async function SuppliersPage() {
  const { data, rlsBlocked, error } = await getSuppliers()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Suppliers</h1>
          <p className="text-muted-foreground">
            External vendors Hardware World buys construction materials from.
          </p>
        </div>
        <Modal
          title="Add New Supplier"
          description="Register a new supplier."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add Supplier
            </Button>
          }
          confirmText="Add Supplier"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="suppliername">Supplier Name</Label>
              <Input id="suppliername" placeholder="e.g. Crown Cement Ltd" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="contactperson">Contact Person</Label>
              <Input id="contactperson" placeholder="e.g. Peter Okello" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" placeholder="+256..." />
            </div>
          </div>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Suppliers"
          value={data.length}
          icon={<Truck className="h-4 w-4" />}
        />
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="suppliername"
        emptyMessage={
          rlsBlocked
            ? "No suppliers visible yet -- RLS has no read policy configured."
            : "No suppliers yet. Add your first one above."
        }
      />
    </div>
  )
}