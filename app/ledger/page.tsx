import { BookText } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Badge } from "@/components/ui/badge"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getLedgerEntries, LedgerRow } from "@/lib/queries"

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

const columns: Column<LedgerRow>[] = [
  {
    header: "Entry",
    accessorKey: "entryid",
    sortable: true,
    cell: (item) => `#${item.entryid}`,
  },
  {
    header: "Source",
    accessorKey: "sourcetype",
    sortable: true,
    cell: (item) => (
      <Badge
        variant="outline"
        className={
          item.sourcetype === "SALE"
            ? "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-500"
            : "border-transparent bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
        }
      >
        {item.sourcetype}
      </Badge>
    ),
  },
  {
    header: "Date",
    accessorKey: "entrydate",
    sortable: true,
    cell: (item) => formatDate(item.entrydate),
  },
  {
    header: "Amount",
    accessorKey: "amount",
    sortable: true,
    cell: (item) => formatCurrency(item.amount),
  },
  { header: "Recorded By", accessorKey: "recordedby_name" },
]

export default async function LedgerPage() {
  const { data, rlsBlocked, error } = await getLedgerEntries()
  const salesTotal = data
    .filter((e) => e.sourcetype === "SALE")
    .reduce((sum, e) => sum + e.amount, 0)
  const payrollTotal = data
    .filter((e) => e.sourcetype === "PAYROLL")
    .reduce((sum, e) => sum + e.amount, 0)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Accounting Ledger
        </h1>
        <p className="text-muted-foreground">
          Every entry here is generated automatically from a Sale or a
          Payroll record -- this view is read-only by design, the same
          cross-department bridge from the EERD.
        </p>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Entries"
          value={data.length}
          icon={<BookText className="h-4 w-4" />}
        />
        <StatCard
          title="From Sales"
          value={formatCurrency(salesTotal)}
          icon={<BookText className="h-4 w-4 text-blue-500" />}
        />
        <StatCard
          title="From Payroll"
          value={formatCurrency(payrollTotal)}
          icon={<BookText className="h-4 w-4 text-purple-500" />}
        />
      </div>

      <DataTable
        data={data}
        columns={columns}
        emptyMessage={
          rlsBlocked
            ? "No ledger entries visible yet -- RLS has no read policy configured."
            : "No ledger entries yet -- these are generated automatically once sales or payroll are recorded."
        }
      />
    </div>
  )
}