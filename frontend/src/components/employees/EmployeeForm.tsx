"use client"

import { useState } from "react"
import { createEmployee } from "@/app/actions"
import { Field, SelectField } from "@/components/shared/Field"
import { FormDialog } from "@/components/shared/FormDialog"
import { Button } from "@/components/ui/button"
import { Plus, Shield, Lock } from "lucide-react"

type Branch = { branchid: number; branchname: string }
type Department = { departmentid: number; departmentname: string; branchid: number }
type Employee = { employeeid: number; name: string }

export function EmployeeForm({
  branches,
  departments,
  employees
}: {
  branches: Branch[]
  departments: Department[]
  employees: Employee[]
}) {
  const [role, setRole] = useState("Cashier")

  return (
    <FormDialog
      title="Provision New Employee & Assign Access"
      description="Only Administrators can create new accounts and assign department credentials."
      trigger={
        <Button className="bg-gradient-to-r from-orange-600 to-amber-600 text-white font-bold hover:from-orange-500 hover:to-amber-500">
          <Plus className="mr-1.5 h-4 w-4" /> Add Employee
        </Button>
      }
      action={createEmployee}
      submitLabel="Provision Account"
      className="sm:max-w-2xl"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Full name" name="name" placeholder="e.g. Samuel Okello" required />
        <Field label="National ID (NIN)" name="nin" placeholder="CM..." required />
        
        {/* Email & Initial Password for system login */}
        <Field label="Email Address (Login Username)" name="email" type="email" placeholder="samuel@hardwareworld.com" required />
        <Field label="Initial Password (Assigned by Admin)" name="password" type="password" placeholder="At least 6 characters" required />

        <Field label="Phone Number" name="phone" type="tel" placeholder="+256 700..." />
        <Field label="Date hired" name="datehired" type="date" />
        <Field label="Salary (UGX)" name="salary" type="number" min="0" placeholder="e.g. 2500000" required />

        <label className="grid gap-1.5 text-sm font-medium">
          Assigned Role (RBAC)
          <select
            className="h-9 rounded-xl border border-slate-700 bg-background px-3 text-sm focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="Cashier">Cashier (Sales & POS)</option>
            <option value="Procurement Officer">Procurement Officer (Procurement & Inventory)</option>
            <option value="Accountant">Accountant (Finance & Accounting)</option>
            <option value="HR Staff">HR Staff (Human Resources)</option>
            <option value="Branch Manager">Branch Manager (Operations)</option>
          </select>
        </label>

        <SelectField label="Branch Assignment" name="branchid" required>
          <option value="">Select branch</option>
          {branches.map((branch) => (
            <option key={branch.branchid} value={branch.branchid}>
              {branch.branchname}
            </option>
          ))}
        </SelectField>

        <SelectField label="Department (ABAC Policy)" name="departmentid" required>
          <option value="">Select assigned department</option>
          {departments.map((department) => (
            <option key={department.departmentid} value={department.departmentid}>
              {department.departmentname}
            </option>
          ))}
        </SelectField>

        <SelectField label="Supervisor (optional)" name="supervisorid">
          <option value="">No supervisor</option>
          {employees.map((employee) => (
            <option key={employee.employeeid} value={employee.employeeid}>
              {employee.name}
            </option>
          ))}
        </SelectField>
      </div>

      {/* Role-Specific Subtype Fields */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-sm mt-3">
        <div className="flex items-center gap-2 mb-3 text-xs font-bold uppercase tracking-wider text-amber-400">
          <Shield className="h-3.5 w-3.5" />
          <span>Role Subtype Attributes</span>
        </div>
        <input type="hidden" name="roletype" value={role} />
        {role === "Cashier" && (
          <Field label="Assigned POS Terminal ID" name="pos_terminalid" placeholder="e.g. POS-TERMINAL-02" required />
        )}
        {role === "Procurement Officer" && (
          <Field label="Approval Limit (UGX)" name="approvallimit" type="number" min="0" placeholder="e.g. 50000000" required />
        )}
        {role === "Accountant" && (
          <Field label="CPA / Accounting Certification Number" name="certificationnumber" placeholder="e.g. CPA-UG-9842" />
        )}
        {role === "HR Staff" && (
          <Field label="HR Designation" name="hr_role" placeholder="e.g. Senior HR Generalist" required />
        )}
        {role === "Branch Manager" && (
          <Field label="Management Level" name="managementlevel" placeholder="e.g. General Manager" />
        )}
      </div>
    </FormDialog>
  )
}
