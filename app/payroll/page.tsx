import { Wallet, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getPayroll, PayrollRow } from "@/lib/queries"

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-UG", {
    style: "currency",
    currency: "UGX",
    maximumFractionDigits: 0,
  }).format(amount)
}

const columns: Column<PayrollRow>[] = [
  { header: "Employee", accessorKey: "employee_name", sortable: true },
  { header: "Month", accessorKey: "month", sortable: true },
  {
    header: "Gross Pay",
    accessorKey: "grosspay",
    sortable: true,
    cell: (item) => formatCurrency(item.grosspay),
  },
  {
    header: "Deductions",
    accessorKey: "deductions",
    cell: (item) => formatCurrency(item.deductions),
  },
  {
    header: "Net Pay",
    accessorKey: "netpay",
    sortable: true,
    cell: (item) => (
      <span className="font-medium">{formatCurrency(item.netpay)}</span>
    ),
  },
]

export default async function PayrollPage() {
  const { data, rlsBlocked, error } = await getPayroll()
  const totalNetPay = data.reduce((sum, p) => sum + p.netpay, 0)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Payroll</h1>
          <p className="text-muted-foreground">
            Monthly pay records across all employees.
          </p>
        </div>
        <Modal
          title="Generate Payroll"
          description="Create a payroll record for an employee and pay period."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Generate Payroll
            </Button>
          }
          confirmText="Generate"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="month">Pay Period (YYYY-MM)</Label>
              <Input id="month" placeholder="2026-09" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="grosspay">Gross Pay (UGX)</Label>
              <Input id="grosspay" type="number" placeholder="0" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="deductions">Deductions (UGX)</Label>
              <Input id="deductions" type="number" placeholder="0" />
            </div>
          </div>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Payroll Records"
          value={data.length}
          icon={<Wallet className="h-4 w-4" />}
        />
        <StatCard
          title="Total Net Pay"
          value={formatCurrency(totalNetPay)}
          icon={<Wallet className="h-4 w-4 text-green-500" />}
        />
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="employee_name"
        emptyMessage={
          rlsBlocked
            ? "No payroll records visible yet -- RLS has no read policy configured."
            : "No payroll records yet. Generate the first one above."
        }
      />
    </div>
  )
}