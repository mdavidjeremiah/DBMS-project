"use client"

import { Briefcase, Plus, CircleDollarSign, Calendar, CheckCircle2, FileText } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

interface PayrollRecord {
  payrollid: string
  period: string
  totalstaff: number
  totalamount: string
  status: "Approved" | "Pending" | "Received"
  disbursedate: string
}

const mockPayroll: PayrollRecord[] = [
  { payrollid: "PAY-2026-08", period: "August 2026", totalstaff: 38, totalamount: "UGX 34,500,000", status: "Received", disbursedate: "Aug 28, 2026" },
  { payrollid: "PAY-2026-07", period: "July 2026", totalstaff: 37, totalamount: "UGX 33,200,000", status: "Approved", disbursedate: "Jul 29, 2026" },
  { payrollid: "PAY-2026-06", period: "June 2026", totalstaff: 36, totalamount: "UGX 32,800,000", status: "Received", disbursedate: "Jun 28, 2026" },
]

const payrollColumns: Column<PayrollRecord>[] = [
  { header: "Payroll Reference", accessorKey: "payrollid", sortable: true, cell: (item) => <span className="font-extrabold text-orange-600 dark:text-orange-400">{item.payrollid}</span> },
  { header: "Pay Period", accessorKey: "period", sortable: true },
  { header: "Employees Covered", accessorKey: "totalstaff", cell: (item) => <span className="font-bold">{item.totalstaff} staff</span> },
  { header: "Disbursed Amount", accessorKey: "totalamount", sortable: true, cell: (item) => <span className="font-black text-slate-900 dark:text-white">{item.totalamount}</span> },
  { header: "Disbursement Date", accessorKey: "disbursedate" },
  { header: "Status", accessorKey: "status", cell: (item) => <StatusBadge status={item.status} /> },
]

export default function PayrollPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Briefcase className="h-4 w-4" /> HR Compensation
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Payroll & Salary Accounting</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Monthly employee salary processing feeds directly into the master accounting ledger.
          </p>
        </div>

        <Modal
          title="Run Monthly Payroll Draft"
          description="Generate draft payroll batch for all active hardware store personnel."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Run Payroll Draft
            </Button>
          }
          confirmText="Process & Send to Ledger"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="period" className="font-bold text-xs">Payroll Period</Label>
              <Input id="period" placeholder="September 2026" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Current Month Payroll"
          value="UGX 34.5M"
          icon={<CircleDollarSign className="h-5 w-5" />}
          trend="up"
          trendValue="Ready"
          description="38 active personnel"
        />
        <StatCard
          title="NSSF & Tax Deductions"
          value="UGX 4.2M"
          icon={<FileText className="h-5 w-5 text-orange-500" />}
          description="statutory compliance"
        />
        <StatCard
          title="Pay Date"
          value="28th Monthly"
          icon={<Calendar className="h-5 w-5 text-sky-500" />}
          description="scheduled disbursement"
        />
        <StatCard
          title="Ledger Sync Status"
          value="Automated"
          icon={<CheckCircle2 className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="100% Synced"
          description="HR to Accounting"
        />
      </div>

      <DataTable
        data={mockPayroll}
        columns={payrollColumns}
        searchKey="period"
      />
    </div>
  )
}
