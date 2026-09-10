"use client"

import { Tags, Plus, Boxes, Wrench, Zap, Droplet, Paintbrush, ShieldCheck, Layers, ChevronRight } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface CategoryItem {
  id: string
  categoryname: string
  itemsCount: number
  description: string
  topBrand: string
}

const mockCategories: CategoryItem[] = [
  { id: "CAT-10", categoryname: "Building Supplies & Cement", itemsCount: 142, description: "Portland cement, lime, gravel, sand & aggregates", topBrand: "Tororo / Simba" },
  { id: "CAT-11", categoryname: "Power Tools & Equipment", itemsCount: 98, description: "Cordless drills, angle grinders, circular saws & batteries", topBrand: "DeWalt / Bosch" },
  { id: "CAT-12", categoryname: "Electrical & Lighting", itemsCount: 76, description: "Conduit pipes, copper wiring, breakers & LED fixtures", topBrand: "Chint / Schneider" },
  { id: "CAT-13", categoryname: "Plumbing & Water Tanks", itemsCount: 115, description: "Pipes, HDPE fittings, PVC valves & Crestanks", topBrand: "Uganda Clays" },
  { id: "CAT-14", categoryname: "Paints, Solvents & Sealants", itemsCount: 64, description: "Interior emulsion, weather guard & wood varnishes", topBrand: "Crown / Sadolin" },
  { id: "CAT-15", categoryname: "Safety Gear & PPE", itemsCount: 52, description: "Hard hats, steel-toe boots, gloves & eye protection", topBrand: "SafetyPro" },
  { id: "CAT-16", categoryname: "Structural Steel & Iron", itemsCount: 88, description: "High-tensile rebar, iron sheets & hollow sections", topBrand: "Roofings Ltd" },
]

const categoryColumns: Column<CategoryItem>[] = [
  { header: "Category Code", accessorKey: "id", sortable: true },
  { header: "Category Name", accessorKey: "categoryname", sortable: true },
  { header: "Total Products", accessorKey: "itemsCount", sortable: true, cell: (item) => <span className="font-extrabold text-orange-600 dark:text-orange-400">{item.itemsCount} SKUs</span> },
  { header: "Description", accessorKey: "description" },
  { header: "Primary Supplier", accessorKey: "topBrand" },
]

export default function CategoriesPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Tags className="h-4 w-4" /> Taxonomy & Departments
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Product Categories</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Classification groups used to organize hardware stock across departments and POS tills.
          </p>
        </div>

        <Modal
          title="Add New Product Category"
          description="Create a product department classification group."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Add Category
            </Button>
          }
          confirmText="Add Category"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="categoryname" className="font-bold text-xs">Category Title</Label>
              <Input id="categoryname" placeholder="e.g. Roofing & Timber Supplies" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description" className="font-bold text-xs">Category Description</Label>
              <Input id="description" placeholder="Iron sheets, timber beams, nails..." className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Category Visual Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Departments"
          value="7 Main Groups"
          icon={<Tags className="h-5 w-5" />}
          description="organizing 1,428 total SKUs"
        />
        <StatCard
          title="Top Sales Category"
          value="Building Supplies"
          icon={<Boxes className="h-5 w-5 text-orange-500" />}
          trend="up"
          trendValue="UGX 22.4M"
          description="sales this month"
        />
        <StatCard
          title="Fastest Growing"
          value="Power Tools"
          icon={<Wrench className="h-5 w-5 text-sky-500" />}
          trend="up"
          trendValue="+28%"
          description="demand surge"
        />
        <StatCard
          title="Unassigned Items"
          value="0"
          icon={<Layers className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="Clean"
          description="all items catalogued"
        />
      </div>

      {/* Table */}
      <DataTable
        data={mockCategories}
        columns={categoryColumns}
        searchKey="categoryname"
      />
    </div>
  )
}
