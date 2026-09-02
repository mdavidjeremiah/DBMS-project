"use client"

import {
  DollarSign,
  Package,
  ShoppingCart,
  Users,
  Plus
} from "lucide-react"
import { StatCard } from "@/components/shared/StatCard"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// --- Mock Data ---
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
]

interface Task {
  id: string
  title: string
  assignee: string
  role: "Cashier" | "Procurement Officer" | "Accountant" | "HR Staff" | "Branch Manager" | "Admin"
}

const mockTasks: Task[] = [
  { id: "1", title: "Review PO-1001", assignee: "Alice", role: "Procurement Officer" },
  { id: "2", title: "Run Month-end Payroll", assignee: "Bob", role: "HR Staff" },
  { id: "3", title: "Approve Timesheets", assignee: "Charlie", role: "Branch Manager" },
  { id: "4", title: "Reconcile Register 2", assignee: "Diana", role: "Accountant" },
]

// --- Columns ---
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

const taskColumns: Column<Task>[] = [
  { header: "Task", accessorKey: "title" },
  { 
    header: "Assignee Role", 
    accessorKey: "role",
    cell: (item) => (
      <div className="flex flex-col gap-1">
        <span className="text-sm">{item.assignee}</span>
        <StatusBadge role={item.role} className="w-fit text-[10px] h-4 py-0" />
      </div>
    )
  }
]

export default function Dashboard() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard Overview</h1>
        
        <Modal
          title="Create New Order"
          description="Create a new purchase order manually."
          trigger={<Button><Plus className="mr-2 h-4 w-4" /> Create New Order</Button>}
          confirmText="Create Order"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="supplier">Supplier</Label>
              <Input id="supplier" placeholder="e.g. Acme Hardware" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="total">Estimated Total</Label>
              <Input id="total" type="number" placeholder="0.00" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Sales Today"
          value="$12,450"
          icon={<DollarSign className="h-4 w-4" />}
          trend="up"
          trendValue="+12%"
          description="vs last week"
        />
        <StatCard
          title="Low Stock Items"
          value="24"
          icon={<Package className="h-4 w-4" />}
          trend="down"
          trendValue="-2"
          description="needs reorder"
        />
        <StatCard
          title="Pending POs"
          value="12"
          icon={<ShoppingCart className="h-4 w-4" />}
          trend="neutral"
          description="awaiting approval"
        />
        <StatCard
          title="Overdue Payroll"
          value="0"
          icon={<Users className="h-4 w-4" />}
          trend="neutral"
          description="all caught up"
        />
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_300px] lg:grid-cols-[1fr_400px]">
        {/* Overview Panel */}
        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold tracking-tight">Recent Purchase Orders</h2>
          <DataTable 
            data={mockOrders} 
            columns={orderColumns} 
            searchKey="supplier"
          />
        </div>

        {/* My Tasks Panel */}
        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold tracking-tight">My Tasks</h2>
          <DataTable
            data={mockTasks}
            columns={taskColumns}
          />
        </div>
      </div>
    </div>
  )
}
