"use client"

import { Package, Plus, AlertTriangle, Layers, Filter, Search, CheckCircle2, ShoppingBag } from "lucide-react"
import { StatCard } from "@/components/shared/StatCard"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { useState } from "react"

interface ProductItem {
  id: string
  itemname: string
  category: string
  unitprice: string
  quantityonhand: number
  reorderlevel: number
  supplier: string
}

const mockProducts: ProductItem[] = [
  { id: "PRD-501", itemname: "Portland Cement 50kg (Tororo/Simba)", category: "Building Supplies", unitprice: "UGX 38,500", quantityonhand: 420, reorderlevel: 100, supplier: "Kampala Cement Co." },
  { id: "PRD-502", itemname: "DeWalt 20V MAX Cordless Drill Combo Kit", category: "Power Tools", unitprice: "UGX 680,000", quantityonhand: 14, reorderlevel: 5, supplier: "BuildRight Uganda" },
  { id: "PRD-503", itemname: "Crown Weather Guard Vinyl Paint 20L", category: "Paints & Finishes", unitprice: "UGX 245,000", quantityonhand: 8, reorderlevel: 15, supplier: "Crown Paints Ltd" },
  { id: "PRD-504", itemname: "High-Tensile Steel Rebar 12mm x 12m", category: "Structural Steel", unitprice: "UGX 42,000", quantityonhand: 350, reorderlevel: 50, supplier: "Steel & Sons Ltd." },
  { id: "PRD-505", itemname: "HDPE Pressure Water Pipe 50mm (100m roll)", category: "Plumbing Supplies", unitprice: "UGX 320,000", quantityonhand: 4, reorderlevel: 10, supplier: "Uganda Clays & Pipes" },
  { id: "PRD-506", itemname: "Heavy-Duty Construction Safety Helmet & Visor", category: "Safety & PPE", unitprice: "UGX 45,000", quantityonhand: 85, reorderlevel: 20, supplier: "SafetyPro East Africa" },
  { id: "PRD-507", itemname: "Brass Gate Valve 2-Inch Heavy Duty", category: "Plumbing Supplies", unitprice: "UGX 65,000", quantityonhand: 62, reorderlevel: 15, supplier: "Uganda Clays & Pipes" },
]

const productColumns: Column<ProductItem>[] = [
  { header: "Product Code", accessorKey: "id", sortable: true },
  { header: "Item Name", accessorKey: "itemname", sortable: true },
  { header: "Category", accessorKey: "category", sortable: true },
  { header: "Unit Price", accessorKey: "unitprice", sortable: true },
  {
    header: "Stock Status",
    accessorKey: "quantityonhand",
    sortable: true,
    cell: (item) => {
      const isLowStock = item.quantityonhand <= item.reorderlevel
      return (
        <div className="flex items-center gap-2 font-bold text-xs">
          <span>{item.quantityonhand} units</span>
          {isLowStock ? (
            <Badge variant="destructive" className="bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30 px-2 py-0.5">
              <AlertTriangle className="mr-1 h-3 w-3" /> Low Stock
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 px-2 py-0.5">
              <CheckCircle2 className="mr-1 h-3 w-3" /> In Stock
            </Badge>
          )}
        </div>
      )
    },
  },
  { header: "Supplier", accessorKey: "supplier" },
]

export default function ProductsPage() {
  const [activeTab, setActiveTab] = useState("all")

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Package className="h-4 w-4" /> Hardware Catalogue
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Products & Stock Inventory</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Manage the item catalogue Hardware World stocks, prices, and sells across all retail branches.
          </p>
        </div>

        <Modal
          title="Add New Hardware Product"
          description="Enter product details to append to Hardware World catalogue."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Add Product
            </Button>
          }
          confirmText="Add Product"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="itemname" className="font-bold text-xs">Item Name & Brand</Label>
              <Input id="itemname" placeholder="e.g. Tororo Cement 50kg" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="unitprice" className="font-bold text-xs">Unit Selling Price (UGX)</Label>
              <Input id="unitprice" type="number" placeholder="38500" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="quantityonhand" className="font-bold text-xs">Initial Warehouse Stock</Label>
              <Input id="quantityonhand" type="number" placeholder="100" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="reorderlevel" className="font-bold text-xs">Minimum Reorder Threshold</Label>
              <Input id="reorderlevel" type="number" placeholder="20" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Catalogue Items"
          value="1,428"
          icon={<Package className="h-5 w-5" />}
          trend="up"
          trendValue="+34 items"
          description="added this month"
        />
        <StatCard
          title="Low Stock Items"
          value="18"
          icon={<AlertTriangle className="h-5 w-5 text-rose-500" />}
          trend="down"
          trendValue="Action Needed"
          description="below reorder level"
        />
        <StatCard
          title="Top Category"
          value="Building Materials"
          icon={<Layers className="h-5 w-5 text-orange-500" />}
          description="42% of total sales"
        />
        <StatCard
          title="Stock Valuation"
          value="UGX 384.2M"
          icon={<ShoppingBag className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="Healthy"
          description="total asset value"
        />
      </div>

      {/* Filter Tabs & Data Table */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
          {["All Items", "Building Supplies", "Power Tools", "Plumbing", "Paints", "Low Stock Alerts"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab.toLowerCase())}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === tab.toLowerCase()
                  ? "bg-slate-900 text-white dark:bg-orange-600 shadow-md"
                  : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <DataTable
          data={mockProducts}
          columns={productColumns}
          searchKey="itemname"
        />
      </div>
    </div>
  )
}
