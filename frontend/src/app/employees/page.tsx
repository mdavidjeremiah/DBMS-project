import { Users } from "lucide-react"
import { DataTable, Column } from "@/components/shared/DataTable"
import { DataNotice } from "@/components/shared/DataNotice"
import { EmployeeForm } from "@/components/employees/EmployeeForm"
import { getEmployees, getOrganisation } from "@/lib/queries"

type Employee = { employeeid: number; name: string; nin: string; phone: string | null; datehired: string; salary: number; roletype: string; department_name: string; branch_name: string; supervisor_name: string | null }
const columns: Column<Employee>[] = [
  { header: "Employee ID", accessorKey: "employeeid", sortable: true },
  { header: "Name", accessorKey: "name", sortable: true },
  { header: "Role", accessorKey: "roletype", sortable: true },
  { header: "Department", accessorKey: "department_name" },
  { header: "Branch", accessorKey: "branch_name" },
  { header: "Phone", accessorKey: "phone" },
  { header: "Date Hired", accessorKey: "datehired", sortable: true },
]

export default async function EmployeesPage() {
  const [employees, organisation] = await Promise.all([getEmployees(), getOrganisation()])
  return <div className="flex flex-col gap-6">
    <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
      <div><div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600"><Users className="h-4 w-4" /> Human resources</div><h1 className="text-2xl font-black text-slate-900 dark:text-white">Staff & Employee Directory</h1><p className="text-sm text-slate-500">Live employees, departments, branches, and role assignments.</p></div>
      <EmployeeForm branches={organisation.branches.data} departments={organisation.departments.data} employees={employees.data.map((employee) => ({ employeeid: employee.employeeid, name: employee.name }))} />
    </header>
    <DataNotice error={employees.error || organisation.branches.error || organisation.departments.error} rlsBlocked={employees.rlsBlocked || organisation.branches.rlsBlocked || organisation.departments.rlsBlocked} />
    <DataTable data={employees.data} columns={columns} searchKey="name" />
  </div>
}