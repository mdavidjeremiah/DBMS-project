"use client"

import { Truck, Plus, Building2, PhoneCall, ShieldCheck, MapPin } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface SupplierItem {
  id: string
  suppliername: string
  contactperson: string
  phone: string
  email: string
  rating: string
  status: string
}

const mockSuppliers: SupplierItem[] = [
  { id: "SUP-101", suppliername: "Kampala Cement Co. Ltd", contactperson: "David Ssebaggala", phone: "+256 772 100 200", email: "orders@kampalacement.co.ug", rating: "4.9 ⭐", status: "Active" },
  { id: "SUP-102", suppliername: "Steel & Sons Uganda Ltd", contactperson: "Robert Kintu", phone: "+256 701 445 889", email: "sales@steelsons.co.ug", rating: "4.8 ⭐", status: "Active" },
  { id: "SUP-103", suppliername: "Crown Paints Uganda", contactperson: "Jane Namugga", phone: "+256 414 250 300", email: "trade@crownpaints.co.ug", rating: "4.7 ⭐", status: "Active" },
  { id: "SUP-104", suppliername: "BuildRight Uganda Distributors", contactperson: "Alex Okello", phone: "+256 782 990 112", email: "info@buildright.ug", rating: "4.6 ⭐", status: "Active" },
  { id: "SUP-105", suppliername: "Uganda Clays & Pipe Factory", contactperson: "Peter Mugisha", phone: "+256 414 200 120", email: "procurement@ugandaclays.co.ug", rating: "4.9 ⭐", status: "Active" },
]

const supplierColumns: Column<SupplierItem>[] = [
  { header: "Supplier ID", accessorKey: "id", sortable: true },
  { header: "Company Name", accessorKey: "suppliername", sortable: true, cell: (item) => <span className="font-extrabold text-slate-900 dark:text-white">{item.suppliername}</span> },
  { header: "Contact Person", accessorKey: "contactperson" },
  { header: "Phone", accessorKey: "phone" },
  { header: "Email", accessorKey: "email" },
  { header: "Rating", accessorKey: "rating" },
]

export default function SuppliersPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Truck className="h-4 w-4" /> Vendor Directory
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Suppliers & Manufacturers</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Manage certified building material manufacturers and hardware supply partners.
          </p>
        </div>

        <Modal
          title="Register New Hardware Supplier"
          description="Add a verified manufacturer or wholesale distributor to the vendor registry."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Add Supplier
            </Button>
          }
          confirmText="Save Supplier"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="suppliername" className="font-bold text-xs">Company Name</Label>
              <Input id="suppliername" placeholder="e.g. Roofings Uganda Ltd" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="contact" className="font-bold text-xs">Primary Contact Person</Label>
              <Input id="contact" placeholder="e.g. Moses Opio" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="phone" className="font-bold text-xs">Phone Number</Label>
              <Input id="phone" placeholder="+256 700 000 000" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Active Suppliers"
          value="24 Vendors"
          icon={<Truck className="h-5 w-5" />}
          trend="up"
          trendValue="Verified"
          description="contracted partners"
        />
        <StatCard
          title="Avg Lead Time"
          value="1.8 Days"
          icon={<Building2 className="h-5 w-5 text-orange-500" />}
          trend="up"
          trendValue="Fast"
          description="order fulfillment"
        />
        <StatCard
          title="Monthly Procurement"
          value="UGX 98.4M"
          icon={<PhoneCall className="h-5 w-5 text-sky-500" />}
          description="total restock spending"
        />
        <StatCard
          title="Quality Score"
          value="99.2%"
          icon={<ShieldCheck className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="A+ Rating"
          description="defect-free rate"
        />
      </div>

      <DataTable
        data={mockSuppliers}
        columns={supplierColumns}
        searchKey="suppliername"
      />
    </div>
  )
}
