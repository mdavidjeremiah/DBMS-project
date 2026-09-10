'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AlertCircle, Loader2 } from 'lucide-react'

interface AddMemberToBranchModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function AddMemberToBranchModal({
  open,
  onOpenChange,
  onSuccess,
}: AddMemberToBranchModalProps) {
  const [employees, setEmployees] = useState<any[]>([])
  const [branches, setBranches] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [selectedEmployee, setSelectedEmployee] = useState<string>('')
  const [selectedBranch, setSelectedBranch] = useState<string>('')
  const [selectedDepartment, setSelectedDepartment] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [fetchingData, setFetchingData] = useState(false)
  const supabase = createClient()

  useEffect(() => {
    if (open) {
      fetchData()
    }
  }, [open])

  const fetchData = async () => {
    setFetchingData(true)
    if (!supabase) {
      setFetchingData(false)
      return
    }
    try {
      const [empResult, branchResult, deptResult] = await Promise.all([
        supabase.from('EMPLOYEE').select('*'),
        supabase.from('BRANCH').select('*'),
        supabase.from('DEPARTMENT').select('*'),
      ])

      if (empResult.data) setEmployees(empResult.data)
      if (branchResult.data) setBranches(branchResult.data)
      if (deptResult.data) setDepartments(deptResult.data)
    } catch (err) {
      console.error('Error fetching data:', err)
    } finally {
      setFetchingData(false)
    }
  }

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (!selectedEmployee || !selectedBranch) {
        setError('Please select an employee and branch')
        return
      }

      if (!supabase) {
        setError('Supabase is not configured')
        setLoading(false)
        return
      }

      // Update employee with branch and optionally department
      const updateData: any = { BranchID: selectedBranch }
      if (selectedDepartment) {
        updateData.DepartmentID = selectedDepartment
      }

      const { error: updateError } = await supabase
        .from('EMPLOYEE')
        .update(updateData)
        .eq('EmployeeID', selectedEmployee)

      if (updateError) {
        setError(updateError.message)
        return
      }

      setSuccess(true)
      setTimeout(() => {
        setSelectedEmployee('')
        setSelectedBranch('')
        setSelectedDepartment('')
        setSuccess(false)
        onOpenChange(false)
        onSuccess?.()
      }, 2000)
    } catch (err) {
      setError('An unexpected error occurred')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl p-6 relative max-h-[85vh] flex flex-col">
        <div className="absolute top-0 inset-x-0 h-1.5 bg-gradient-to-r from-orange-600 via-amber-500 to-orange-500" />
        <DialogHeader className="pt-2 shrink-0">
          <DialogTitle className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">Add Member to Branch/Department</DialogTitle>
          <DialogDescription className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">
            Assign an existing employee to a branch and/or department
          </DialogDescription>
        </DialogHeader>

        {success ? (
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-center h-16 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <p className="text-emerald-700 dark:text-emerald-400 font-semibold">
                Assignment successful
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleAssign} className="space-y-4">
            {error && (
              <div className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="employee">Employee</Label>
              <Select value={selectedEmployee} onValueChange={(v) => setSelectedEmployee(v ?? '')} disabled={loading || fetchingData}>
                <SelectTrigger id="employee">
                  <SelectValue placeholder="Select an employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((emp) => (
                    <SelectItem key={emp.EmployeeID} value={emp.EmployeeID}>
                      {emp.EmployeeName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="branch">Branch</Label>
              <Select value={selectedBranch} onValueChange={(v) => setSelectedBranch(v ?? '')} disabled={loading || fetchingData}>
                <SelectTrigger id="branch">
                  <SelectValue placeholder="Select a branch" />
                </SelectTrigger>
                <SelectContent>
                  {branches.map((branch) => (
                    <SelectItem key={branch.BranchID} value={branch.BranchID}>
                      {branch.BranchName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="department">Department (Optional)</Label>
              <Select value={selectedDepartment} onValueChange={(v) => setSelectedDepartment(v ?? '')} disabled={loading || fetchingData}>
                <SelectTrigger id="department">
                  <SelectValue placeholder="Select a department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {departments.map((dept) => (
                    <SelectItem key={dept.DepartmentID} value={dept.DepartmentID}>
                      {dept.DepartmentName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={loading}
                className="bg-orange-600 hover:bg-orange-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Assigning...
                  </>
                ) : (
                  'Assign'
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
