"use client"

import { Users, Plus, UserCheck, Shield, Briefcase, Award } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface EmployeeItem {
  id: string
  name: string
  role: "Cashier" | "Procurement Officer" | "Accountant" | "HR Staff" | "Branch Manager"
  branch: string
  phone: string
  hiredate: string
}

const mockEmployees: EmployeeItem[] = [
  { id: "EMP-001", name: "Jonathan Akena", role: "Branch Manager", branch: "Main Branch", phone: "+256 772 400 100", hiredate: "Jan 15, 2022" },
  { id: "EMP-002", name: "Sarah Namusoke", role: "Cashier", branch: "Main Branch", phone: "+256 701 334 221", hiredate: "Mar 10, 2024" },
  { id: "EMP-003", name: "David Jeremiah Muwanguzi", role: "Procurement Officer", branch: "Main Branch", phone: "+256 782 556 778", hiredate: "Jun 01, 2023" },
  { id: "EMP-004", name: "Emmanuel Dila Okuja", role: "Accountant", branch: "Main Branch", phone: "+256 774 990 123", hiredate: "Sep 20, 2023" },
  { id: "EMP-005", name: "Steven Mutebi", role: "HR Staff", branch: "Downtown Branch", phone: "+256 702 112 445", hiredate: "Feb 05, 2024" },
]

const employeeColumns: Column<EmployeeItem>[] = [
  { header: "Staff ID", accessorKey: "id", sortable: true },
  { header: "Full Name", accessorKey: "name", sortable: true, cell: (item) => <span className="font-extrabold text-slate-900 dark:text-white">{item.name}</span> },
  { header: "Department Role", accessorKey: "role", cell: (item) => <StatusBadge role={item.role} /> },
  { header: "Assigned Branch", accessorKey: "branch" },
  { header: "Contact Phone", accessorKey: "phone" },
  { header: "Joined Date", accessorKey: "hiredate" },
]

export default function EmployeesPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Users className="h-4 w-4" /> Human Resources
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Staff & Employee Directory</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Manage store team members, department roles, and branch access privileges.
          </p>
        </div>

        <Modal
          title="Onboard New Staff Member"
          description="Register a new employee into Hardware World HR records."
          trigger={
            <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
              <Plus className="mr-2 h-4 w-4" /> Add Employee
            </Button>
          }
          confirmText="Register Employee"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="name" className="font-bold text-xs">Full Name</Label>
              <Input id="name" placeholder="e.g. Godwin Ssemwogere" className="rounded-xl" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="role" className="font-bold text-xs">Assigned Role</Label>
              <Input id="role" placeholder="Cashier / Accountant / Procurement" className="rounded-xl" />
            </div>
          </div>
        </Modal>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Active Personnel"
          value="38 Staff"
          icon={<Users className="h-5 w-5" />}
          trend="up"
          trendValue="Full Team"
          description="across 3 branches"
        />
        <StatCard
          title="POS Cashiers"
          value="14 Active"
          icon={<UserCheck className="h-5 w-5 text-orange-500" />}
          description="front-desk team"
        />
        <StatCard
          title="Procurement & Ops"
          value="12 Officers"
          icon={<Briefcase className="h-5 w-5 text-sky-500" />}
          description="warehouse & stock"
        />
        <StatCard
          title="System Access"
          value="100% RLS"
          icon={<Shield className="h-5 w-5 text-emerald-500" />}
          trend="up"
          trendValue="Secured"
          description="Postgres permissioned"
        />
      </div>

      <DataTable
        data={mockEmployees}
        columns={employeeColumns}
        searchKey="name"
      />
    </div>
  )
}
