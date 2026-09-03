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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Purchase Orders</h1>
          <p className="text-muted-foreground">Manage and track your supplier orders.</p>
        </div>
        
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Orders"
          value="1,245"
          icon={<ShoppingCart className="h-4 w-4" />}
        />
        <StatCard
          title="Pending Approval"
          value="12"
          icon={<ShoppingCart className="h-4 w-4 text-yellow-500" />}
        />
        <StatCard
          title="Received This Month"
          value="45"
          icon={<ShoppingCart className="h-4 w-4 text-green-500" />}
        />
        <StatCard
          title="Cancelled"
          value="3"
          icon={<ShoppingCart className="h-4 w-4 text-red-500" />}
        />
      </div>

      <div className="flex flex-col gap-4">
        <DataTable 
          data={mockOrders} 
          columns={orderColumns} 
          searchKey="supplier"
        />
      </div>
    </div>
  )
}
