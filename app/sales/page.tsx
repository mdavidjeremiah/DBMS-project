import { Banknote, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getSales, SaleRow } from "@/lib/queries"

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-UG", {
    style: "currency",
    currency: "UGX",
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

const columns: Column<SaleRow>[] = [
  {
    header: "Sale ID",
    accessorKey: "saleid",
    sortable: true,
    cell: (item) => `#${item.saleid}`,
  },
  { header: "Customer", accessorKey: "customer_name", sortable: true },
  { header: "Cashier", accessorKey: "cashier_name" },
  { header: "Branch", accessorKey: "branch_name" },
  {
    header: "Date",
    accessorKey: "saledate",
    sortable: true,
    cell: (item) => formatDate(item.saledate),
  },
  {
    header: "Total",
    accessorKey: "totalamount",
    sortable: true,
    cell: (item) => formatCurrency(item.totalamount),
  },
]

export default async function SalesPage() {
  const { data, rlsBlocked, error } = await getSales()
  const totalRevenue = data.reduce((sum, s) => sum + s.totalamount, 0)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Sales (POS)
          </h1>
          <p className="text-muted-foreground">
            Transaction history across all branches.
          </p>
        </div>
        <Modal
          title="New Sale"
          description="Point-of-sale checkout arrives with Issue #5. This is a placeholder for the form shape."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> New Sale
            </Button>
          }
          confirmText="Checkout"
        >
          <p className="text-sm text-muted-foreground">
            Line-item entry, quantity, and live totals will be built out as
            part of Issue #5 (Sales, HR/Payroll, Accounting Ledger).
          </p>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Sales"
          value={data.length}
          icon={<Banknote className="h-4 w-4" />}
        />
        <StatCard
          title="Total Revenue"
          value={formatCurrency(totalRevenue)}
          icon={<Banknote className="h-4 w-4 text-green-500" />}
        />
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="customer_name"
        emptyMessage={
          rlsBlocked
            ? "No sales visible yet -- RLS has no read policy configured."
            : "No sales recorded yet."
        }
      />
    </div>
  )
}