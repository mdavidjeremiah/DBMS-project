"use client"

import {
  ShoppingCart,
  Plus
} from "lucide-react"
import { StatCard } from "@/components/shared/StatCard"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface Order {
  id: string
  supplier: string
  status: "Pending" | "Approved" | "Received" | "Cancelled"
  total: string
}

const mockOrders: Order[] = [
  { id: "PO-1001", supplier: "Acme Hardware", status: "Pending", total: "$1,250.00" },
  { id: "PO-1002", supplier: "Global Tools", status: "Approved", total: "$3,400.00" },
  { id: "PO-1003", supplier: "Industrial Supply Co", status: "Received", total: "$890.00" },
  { id: "PO-1004", supplier: "Fasteners Inc", status: "Cancelled", total: "$420.00" },
  { id: "PO-1005", supplier: "Acme Hardware", status: "Pending", total: "$2,100.00" },
  { id: "PO-1006", supplier: "Global Tools", status: "Received", total: "$5,000.00" },
]

const orderColumns: Column<Order>[] = [
  { header: "Order ID", accessorKey: "id", sortable: true },
  { header: "Supplier", accessorKey: "supplier", sortable: true },
  { 
    header: "Status", 
    accessorKey: "status", 
    sortable: true,
    cell: (item) => <StatusBadge status={item.status} />
  },
  { header: "Total", accessorKey: "total" },
]

export default function PurchaseOrdersPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <ShoppingCart className="h-4 w-4" /> Procurement & Supply Chain
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Purchase Orders</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Manage and track supplier procurement, restock orders, and branch approvals.
          </p>
        </div>
        
        <Modal
          title="Create Purchase Order"
          description="Issue restock purchase order to approved hardware supplier."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Create New Order
            </Button>
          }
          confirmText="Issue Order"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="supplier" className="font-bold text-xs">Supplier</Label>
              <Input id="supplier" placeholder="e.g. Kampala Cement Co." className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="total" className="font-bold text-xs">Estimated Order Total (UGX)</Label>
              <Input id="total" type="number" placeholder="5000000" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Orders"
          value="1,245"
          icon={<ShoppingCart className="h-5 w-5" />}
          trend="up"
          trendValue="+12"
          description="this month"
        />
        <StatCard
          title="Pending Approval"
          value="12"
          icon={<ShoppingCart className="h-5 w-5 text-amber-500" />}
          trend="down"
          trendValue="Review"
          description="procurement action"
        />
        <StatCard
          title="Received This Month"
          value="45 Orders"
          icon={<ShoppingCart className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="Verified"
          description="in warehouse"
        />
        <StatCard
          title="Cancelled Orders"
          value="3"
          icon={<ShoppingCart className="h-5 w-5 text-rose-500" />}
          description="supplier issues"
        />
      </div>

      <DataTable 
        data={mockOrders} 
        columns={orderColumns} 
        searchKey="supplier"
      />
    </div>
  )
}
