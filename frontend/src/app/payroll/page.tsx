import { Briefcase, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createPayroll } from "@/app/actions"
import { getPayroll, getEmployees } from "@/lib/queries"

type Payroll = { payrollid: number; employeeid: number; employee_name: string; month: string; grosspay: number; deductions: number; netpay: number }
const columns: Column<Payroll>[] = [
  { header: "Payroll ID", accessorKey: "payrollid", sortable: true },
  { header: "Employee", accessorKey: "employee_name", sortable: true },
  { header: "Month", accessorKey: "month", sortable: true },
  { header: "Gross Pay", accessorKey: "grosspay", cell: (row) => `UGX ${row.grosspay.toLocaleString()}` },
  { header: "Deductions", accessorKey: "deductions", cell: (row) => `UGX ${row.deductions.toLocaleString()}` },
  { header: "Net Pay", accessorKey: "netpay", cell: (row) => `UGX ${row.netpay.toLocaleString()}` },
]

export default async function PayrollPage() {
  const [payroll, employees] = await Promise.all([getPayroll(), getEmployees()])
  return <div className="flex flex-col gap-6">
    <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between"><div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><Briefcase className="h-4 w-4" /> HR compensation</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Payroll & Salary Accounting</h1><p className="text-sm text-slate-500">Live payroll records linked to employees.</p></div><FormDialog title="Create payroll record" description="Record payroll for one live employee." trigger={<Button><Plus className="mr-2 h-4 w-4" /> Add Payroll</Button>} action={createPayroll} submitLabel="Save payroll"><Label htmlFor="employeeid">Employee ID</Label><Input id="employeeid" name="employeeid" type="number" min="1" required placeholder={employees.data[0] ? String(employees.data[0].employeeid) : undefined} /><Label htmlFor="month">Month</Label><Input id="month" name="month" placeholder="2026-09" required /><Label htmlFor="grosspay">Gross pay</Label><Input id="grosspay" name="grosspay" type="number" min="0" required /><Label htmlFor="deductions">Deductions</Label><Input id="deductions" name="deductions" type="number" min="0" required /></FormDialog></header>
    <DataNotice error={payroll.error || employees.error} rlsBlocked={payroll.rlsBlocked || employees.rlsBlocked} />
    <DataTable data={payroll.data} columns={columns} searchKey="employee_name" />
  </div>
}