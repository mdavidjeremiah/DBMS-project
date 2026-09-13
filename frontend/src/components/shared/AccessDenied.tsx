import Link from "next/link"
import { ShieldX, ArrowLeft, Building2, UserCheck } from "lucide-react"
import { Button } from "@/components/ui/button"

interface AccessDeniedProps {
  userRole?: string
  userDepartment?: string
  requiredDepartment?: string
}

export function AccessDenied({
  userRole = "Staff Member",
  userDepartment = "General Staff",
  requiredDepartment
}: AccessDeniedProps) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center p-6 text-center">
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-rose-500/10 text-rose-500 border border-rose-500/20 shadow-xl">
        <ShieldX className="h-10 w-10" />
      </div>

      <h1 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">
        Access Denied (ABAC / RBAC)
      </h1>
      <p className="mt-2 text-xs font-bold uppercase tracking-widest text-rose-500">
        Departmental Boundary Policy Violation
      </p>

      <div className="mt-6 w-full rounded-2xl border border-slate-200 bg-white p-6 text-left shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <span className="text-xs text-slate-500">Active Account Role:</span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-800 dark:bg-slate-800 dark:text-slate-200">
            {userRole}
          </span>
        </div>
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <span className="text-xs text-slate-500">Assigned Department:</span>
          <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-600 dark:text-amber-400">
            {userDepartment}
          </span>
        </div>
        {requiredDepartment && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Target Area Requirement:</span>
            <span className="rounded-full bg-rose-500/10 px-3 py-1 text-xs font-bold text-rose-600 dark:text-rose-400">
              {requiredDepartment} Only
            </span>
          </div>
        )}
        <p className="pt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          Under Attribute-Based Access Control (ABAC), employees cannot access dashboards or records assigned to another department. Only the <strong>System Administrator</strong> possesses cross-departmental clearance.
        </p>
      </div>

      <div className="mt-6 flex gap-3">
        <Link href="/">
          <Button className="rounded-xl bg-orange-600 text-white hover:bg-orange-700">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Return to My Department Dashboard
          </Button>
        </Link>
      </div>
    </div>
  )
}
