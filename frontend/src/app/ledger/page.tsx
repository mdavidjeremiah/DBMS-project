import { BookOpen, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createLedgerEntry } from "@/app/actions"
import { getLedger, getEmployees } from "@/lib/queries"

type Entry = { entryid: number; entrydate: string; sourcetype: string; amount: number; source_label: string; accountant_name: string }
const columns: Column<Entry>[] = [
  { header: "Entry ID", accessorKey: "entryid", sortable: true },
  { header: "Date", accessorKey: "entrydate", sortable: true },
  { header: "Source", accessorKey: "sourcetype" },
  { header: "Reference", accessorKey: "source_label" },
  { header: "Recorded By", accessorKey: "accountant_name" },
  { header: "Amount", accessorKey: "amount", sortable: true, cell: (row) => `UGX ${row.amount.toLocaleString()}` },
]

export default async function LedgerPage() {
  const [ledger, employees] = await Promise.all([getLedger(), getEmployees()])
  return <div className="flex flex-col gap-6">
    <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between"><div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><BookOpen className="h-4 w-4" /> Accounting</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Master Accounting Ledger</h1><p className="text-sm text-slate-500">Live entries sourced from sales and payroll.</p></div><FormDialog title="Post ledger entry" description="Link a ledger entry to an existing sale or payroll record." trigger={<Button><Plus className="mr-2 h-4 w-4" /> Add Entry</Button>} action={createLedgerEntry} submitLabel="Post entry"><Label htmlFor="sourcetype">Source type</Label><select id="sourcetype" name="sourcetype" className="h-9 rounded-lg border bg-background px-2.5 text-sm"><option value="SALE">Sale</option><option value="PAYROLL">Payroll</option></select><Label htmlFor="sourceid">Sale or payroll ID</Label><Input id="sourceid" name="sourceid" type="number" min="1" required /><Label htmlFor="amount">Amount</Label><Input id="amount" name="amount" type="number" min="0" required /><Label htmlFor="recordedby">Recorded by employee ID</Label><Input id="recordedby" name="recordedby" type="number" min="1" required placeholder={employees.data[0] ? String(employees.data[0].employeeid) : undefined} /></FormDialog></header>
    <DataNotice error={ledger.error || employees.error} rlsBlocked={ledger.rlsBlocked || employees.rlsBlocked} />
    <DataTable data={ledger.data} columns={columns} searchKey="source_label" />
  </div>
}