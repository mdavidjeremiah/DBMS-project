"use client"

import { Banknote, Plus, ShoppingCart, UserCheck, CreditCard, Receipt, ArrowUpRight } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface SaleRecord {
  saleid: string
  customer_name: string
  cashier_name: string
  branch_name: string
  saledate: string
  payment_method: string
  totalamount: string
}

const mockSales: SaleRecord[] = [
  { saleid: "SL-2841", customer_name: "Muwa Trade Ltd", cashier_name: "Sarah Namusoke", branch_name: "Main Branch", saledate: "Today, 12:14", payment_method: "Cash", totalamount: "UGX 1,450,000" },
  { saleid: "SL-2840", customer_name: "Walk-in Customer", cashier_name: "Sarah Namusoke", branch_name: "Main Branch", saledate: "Today, 11:48", payment_method: "MTN MoMo Pay", totalamount: "UGX 238,000" },
  { saleid: "SL-2839", customer_name: "Kampala Civil Works", cashier_name: "John Kintu", branch_name: "Main Branch", saledate: "Today, 10:22", payment_method: "Bank Transfer", totalamount: "UGX 8,920,000" },
  { saleid: "SL-2838", customer_name: "Walk-in Customer", cashier_name: "John Kintu", branch_name: "Main Branch", saledate: "Yesterday, 16:05", payment_method: "Airtel Money", totalamount: "UGX 75,000" },
  { saleid: "SL-2837", customer_name: "Grace Nakato", cashier_name: "Sarah Namusoke", branch_name: "Downtown Branch", saledate: "Aug 29, 14:30", payment_method: "Cash", totalamount: "UGX 412,000" },
]

const salesColumns: Column<SaleRecord>[] = [
  { header: "Receipt ID", accessorKey: "saleid", sortable: true, cell: (item) => <span className="font-extrabold text-orange-600 dark:text-orange-400">#{item.saleid}</span> },
  { header: "Customer", accessorKey: "customer_name", sortable: true },
  { header: "Cashier", accessorKey: "cashier_name" },
  { header: "Payment Method", accessorKey: "payment_method", cell: (item) => <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">{item.payment_method}</span> },
  { header: "Transaction Date", accessorKey: "saledate" },
  { header: "Total Paid", accessorKey: "totalamount", sortable: true, cell: (item) => <span className="font-black text-slate-900 dark:text-white">{item.totalamount}</span> },
]

export default function SalesPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Receipt className="h-4 w-4" /> Point of Sale (POS)
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Sales & Retail Checkout</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Real-time cashier checkout, line-item sales logs, and customer receipts across branches.
          </p>
        </div>

        <Modal
          title="New Point of Sale (POS) Transaction"
          description="Ring up cash, MoMo, or bank sales for walk-in or account customers."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> New Checkout
            </Button>
          }
          confirmText="Complete Sale & Print Receipt"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="customer" className="font-bold text-xs">Customer Name / Walk-in</Label>
              <Input id="customer" placeholder="e.g. Walk-in Customer / Contractor Co." className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="amount" className="font-bold text-xs">Total Amount (UGX)</Label>
              <Input id="amount" type="number" placeholder="150000" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="method" className="font-bold text-xs">Payment Method</Label>
              <Input id="method" placeholder="Cash / MTN MoMo / Bank Wire" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Sales Today"
          value="UGX 3.84M"
          icon={<Banknote className="h-5 w-5" />}
          trend="up"
          trendValue="+8.2%"
          description="vs yesterday"
        />
        <StatCard
          title="Completed Checkouts"
          value="42 Sales"
          icon={<ShoppingCart className="h-5 w-5 text-orange-500" />}
          trend="up"
          trendValue="Main Till"
          description="average order: 91k"
        />
        <StatCard
          title="Active Cashiers"
          value="3 Cashiers"
          icon={<UserCheck className="h-5 w-5 text-sky-500" />}
          description="Main Branch & Downtown"
        />
        <StatCard
          title="Digital MoMo / Card"
          value="58%"
          icon={<CreditCard className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="Mobile Money"
          description="cashless transactions"
        />
      </div>

      {/* Data Table */}
      <DataTable
        data={mockSales}
        columns={salesColumns}
        searchKey="customer_name"
      />
    </div>
  )
}
