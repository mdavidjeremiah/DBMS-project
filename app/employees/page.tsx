import { Users, Plus } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { StatCard } from "@/components/shared/StatCard"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Modal } from "@/components/shared/Modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { getEmployees, EmployeeRow } from "@/lib/queries"

type Role = "Cashier" | "Procurement Officer" | "Accountant" | "HR Staff" | "Branch Manager"

const columns: Column<EmployeeRow>[] = [
  { header: "Name", accessorKey: "name", sortable: true },
  {
    header: "Role",
    accessorKey: "roletype",
    sortable: true,
    cell: (item) => <StatusBadge role={item.roletype as Role} />,
  },
  { header: "Department", accessorKey: "department_name", sortable: true },
  { header: "Branch", accessorKey: "branch_name", sortable: true },
]

export default async function EmployeesPage() {
  const { data, rlsBlocked, error } = await getEmployees()
  const roleCounts = data.reduce<Record<string, number>>((acc, e) => {
    acc[e.roletype] = (acc[e.roletype] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Employees</h1>
          <p className="text-muted-foreground">
            Staff across every branch and department.
          </p>
        </div>
        <Modal
          title="Add New Employee"
          description="Create an employee record. Role-specific fields (POS terminal, approval limit, etc.) are added once Issue #3/#5 wire this up to auth."
          trigger={
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Add Employee
            </Button>
          }
          confirmText="Add Employee"
        >
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="name">Full Name</Label>
              <Input id="name" placeholder="e.g. Brian Okuja" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="nin">NIN</Label>
              <Input id="nin" placeholder="National ID number" />
            </div>
          </div>
        </Modal>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Employees"
          value={data.length}
          icon={<Users className="h-4 w-4" />}
        />
        {Object.entries(roleCounts)
          .slice(0, 3)
          .map(([role, count]) => (
            <StatCard
              key={role}
              title={role}
              value={count}
              icon={<Users className="h-4 w-4" />}
            />
          ))}
      </div>

      <DataTable
        data={data}
        columns={columns}
        searchKey="name"
        emptyMessage={
          rlsBlocked
            ? "No employees visible yet -- RLS has no read policy configured."
            : "No employees yet. Add your first one above."
        }
      />
    </div>
  )
}