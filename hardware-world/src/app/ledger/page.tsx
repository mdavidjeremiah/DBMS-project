"use client"

import { BookOpen, Plus, CircleDollarSign, ArrowUpRight, ArrowDownLeft, Scale } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

interface LedgerEntry {
  entryid: string
  sourcetype: "Sale" | "Payroll" | "Procurement"
  description: string
  entrydate: string
  type: "Credit (Income)" | "Debit (Expense)"
  amount: string
}

const mockLedger: LedgerEntry[] = [
  { entryid: "LDG-9081", sourcetype: "Sale", description: "POS Cash Sale #SL-2841", entrydate: "Today, 12:14", type: "Credit (Income)", amount: "+UGX 1,450,000" },
  { entryid: "LDG-9080", sourcetype: "Procurement", description: "Supplier Restock PO-1046 Steel & Sons", entrydate: "Aug 28, 14:18", type: "Debit (Expense)", amount: "-UGX 6,385,000" },
  { entryid: "LDG-9079", sourcetype: "Payroll", description: "Monthly Staff Salaries PAY-2026-08", entrydate: "Aug 28, 09:00", type: "Debit (Expense)", amount: "-UGX 34,500,000" },
  { entryid: "LDG-9078", sourcetype: "Sale", description: "Contractor Order #SL-2839", entrydate: "Aug 27, 16:20", type: "Credit (Income)", amount: "+UGX 8,920,000" },
]

const ledgerColumns: Column<LedgerEntry>[] = [
  { header: "Entry Ref", accessorKey: "entryid", sortable: true, cell: (item) => <span className="font-extrabold text-orange-600 dark:text-orange-400">{item.entryid}</span> },
  { header: "Source Type", accessorKey: "sourcetype", cell: (item) => (
    <Badge variant="outline" className={`font-bold text-xs ${item.sourcetype === "Sale" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-rose-50 text-rose-700 border-rose-200"}`}>
      {item.sourcetype}
    </Badge>
  )},
  { header: "Transaction Description", accessorKey: "description", sortable: true },
  { header: "Posting Date", accessorKey: "entrydate" },
  { header: "Entry Type", accessorKey: "type" },
  { header: "Amount (UGX)", accessorKey: "amount", sortable: true, cell: (item) => (
    <span className={`font-black ${item.amount.startsWith("+") ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
      {item.amount}
    </span>
  )},
]

export default function LedgerPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <BookOpen className="h-4 w-4" /> Accounting & Finance
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Master Accounting Ledger</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Single unified ledger fed by sales income, procurement restock expenses, and monthly HR payroll.
          </p>
        </div>

        <Modal
          title="Post Manual Adjustment Entry"
          description="Record a manual journal entry into the accounting ledger."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Add Journal Entry
            </Button>
          }
          confirmText="Post Entry"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="description" className="font-bold text-xs">Description / Reason</Label>
              <Input id="description" placeholder="e.g. Utility Payment / Store Repairs" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="amount" className="font-bold text-xs">Amount (UGX)</Label>
              <Input id="amount" type="number" placeholder="500000" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Cash Inflow (Sales)"
          value="UGX 48.2M"
          icon={<ArrowUpRight className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="+12.5%"
          description="credits this month"
        />
        <StatCard
          title="Total Outflow (Expenses)"
          value="UGX 40.8M"
          icon={<ArrowDownLeft className="h-5 w-5 text-rose-500" />}
          description="procurement + payroll"
        />
        <StatCard
          title="Net Branch Profit"
          value="UGX 7.4M"
          icon={<CircleDollarSign className="h-5 w-5 text-amber-500" />}
          trend="up"
          trendValue="Positive"
          description="operating margin"
        />
        <StatCard
          title="Ledger Balance Status"
          value="Balanced"
          icon={<Scale className="h-5 w-5 text-sky-500" />}
          trend="up"
          trendValue="3NF Check OK"
          description="exactly 1 source ID"
        />
      </div>

      <DataTable
        data={mockLedger}
        columns={ledgerColumns}
        searchKey="description"
      />
    </div>
  )
}
