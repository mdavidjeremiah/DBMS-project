"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import {
  AlertCircle,
  Loader2,
  Shield,
  UserCheck,
  Building2,
  Lock,
  User,
  Eye,
  EyeOff,
  CheckCircle2,
  Sparkles
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { API_URL, setAccessToken } from "@/lib/api"

type Department = {
  departmentid: number
  departmentname: string
  branchid: number
}

const FALLBACK_DEPARTMENTS: Department[] = [
  { departmentid: 1, departmentname: "Sales & POS", branchid: 1 },
  { departmentid: 2, departmentname: "Procurement & Inventory", branchid: 1 },
  { departmentid: 3, departmentname: "Finance & Accounting", branchid: 1 },
  { departmentid: 4, departmentname: "Human Resources", branchid: 1 },
  { departmentid: 5, departmentname: "Operations & Branch Management", branchid: 1 },
  { departmentid: 6, departmentname: "Administration", branchid: 1 },
]

export default function SignInPage() {
  const router = useRouter()
  const [loginType, setLoginType] = useState<"staff" | "admin">("staff")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [department, setDepartment] = useState("")
  const [departments, setDepartments] = useState<Department[]>(FALLBACK_DEPARTMENTS)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingDepts, setLoadingDepts] = useState(true)

  useEffect(() => {
    async function loadDepartments() {
      try {
        const res = await fetch(`${API_URL}/departments/public`, { cache: "no-store" })
        if (res.ok) {
          const data = await res.json()
          if (Array.isArray(data) && data.length > 0) {
            setDepartments(data)
            // Default to first staff department if not set
            const firstStaffDept = data.find((d: Department) => d.departmentname !== "Administration")
            if (firstStaffDept && !department) {
              setDepartment(firstStaffDept.departmentname)
            }
            return
          }
        }
      } catch {
        // Use fallback departments
      } finally {
        setLoadingDepts(false)
      }
      if (!department) {
        setDepartment("Sales & POS")
      }
    }
    loadDepartments()
  }, [])

  function quickFill(type: "admin" | "staff", userVal: string, passVal: string, deptVal: string) {
    setLoginType(type)
    setUsername(userVal)
    setPassword(passVal)
    setDepartment(deptVal)
    setError(null)
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const payload = {
        username: username.trim(),
        password: password.trim(),
        department: loginType === "staff" ? department : "Administration",
        login_type: loginType
      }

      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail ?? "Authentication failed. Please verify credentials.")
      }

      setAccessToken(data.access_token)
      router.push("/")
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-stone-900 p-4 text-slate-100">
      <div className="w-full max-w-lg rounded-3xl border border-slate-800/80 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl">
        {/* Brand Header */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-orange-600 to-amber-500 font-extrabold text-white shadow-lg shadow-orange-600/30">
            <Building2 className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white sm:text-3xl">Hardware World</h1>
          <p className="mt-1 text-xs font-semibold uppercase tracking-widest text-amber-500">
            Enterprise DBMS Portal
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Role-Based & Attribute-Based Access Control (RBAC & ABAC)
          </p>
        </div>

        {/* Login Type Switcher (Admin vs Staff) */}
        <div className="mb-6 grid grid-cols-2 gap-2 rounded-2xl bg-slate-950/70 p-1.5 border border-slate-800">
          <button
            type="button"
            onClick={() => {
              setLoginType("staff")
              setError(null)
              if (!department || department === "Administration") {
                setDepartment("Sales & POS")
              }
            }}
            className={`flex items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-bold transition-all duration-200 ${loginType === "staff"
                ? "bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25"
                : "text-slate-400 hover:text-slate-200"
              }`}
          >
            <UserCheck className="h-4 w-4" />
            Staff Member
          </button>
          <button
            type="button"
            onClick={() => {
              setLoginType("admin")
              setError(null)
              setDepartment("Administration")
            }}
            className={`flex items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-bold transition-all duration-200 ${loginType === "admin"
                ? "bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25"
                : "text-slate-400 hover:text-slate-200"
              }`}
          >
            <Shield className="h-4 w-4" />
            Administrator
          </button>
        </div>

        {/* Error Alert with ABAC/RBAC breakdown */}
        {error && (
          <div className="mb-6 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-xs leading-relaxed text-rose-300">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <strong className="block font-bold text-rose-200">Security Access Verification Error</strong>
                <span>{error}</span>
              </div>
            </div>
          </div>
        )}

        {/* Main Authentication Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username or Email Input */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              {loginType === "admin" ? "Admin Name or Email" : "Full Name or Email"}
            </Label>
            <div className="relative">
              <User className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={loginType === "admin" ? "Akena or akena@hardwareworld.com" : "e.g. Sarah Nakato or email"}
                className="h-11 rounded-xl border-slate-700 bg-slate-950/70 pl-10 text-sm text-slate-100 placeholder:text-slate-500 focus:border-orange-500 focus:ring-orange-500/20"
                required
              />
            </div>
          </div>

          {/* Department Selection (ABAC for Staff, Fixed for Admin) */}
          {loginType === "staff" ? (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Assigned Department (ABAC Verification)
                </Label>
                <span className="text-[10px] text-amber-400 font-medium">Must match DB Profile</span>
              </div>
              <div className="relative">
                <Building2 className="absolute left-3.5 top-3 h-4 w-4 text-slate-400 pointer-events-none" />
                <select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  disabled={loadingDepts}
                  className="h-11 w-full rounded-xl border border-slate-700 bg-slate-950/70 pl-10 pr-4 text-sm text-slate-100 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20 disabled:opacity-50"
                  required
                >
                  {departments
                    .filter((d) => d.departmentname !== "Administration")
                    .map((d) => (
                      <option key={d.departmentid} value={d.departmentname} className="bg-slate-900 text-slate-100">
                        {d.departmentname}
                      </option>
                    ))}
                </select>
              </div>
              <p className="text-[11px] text-slate-400">
                ABAC policy ensures staff can only log into their assigned department dashboard.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-amber-400" />
                  <span className="text-xs font-semibold text-slate-200">System Administrator Scope</span>
                </div>
                <span className="rounded-full bg-orange-500/20 px-2.5 py-0.5 text-[10px] font-bold text-orange-400 border border-orange-500/30">
                  Full Multi-Dept Access
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-400">
                Administrator credentials have unrestricted oversight across all store departments.
              </p>
            </div>
          )}

          {/* Password Input */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Password
            </Label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter account password"
                className="h-11 rounded-xl border-slate-700 bg-slate-950/70 pl-10 pr-10 text-sm text-slate-100 placeholder:text-slate-500 focus:border-orange-500 focus:ring-orange-500/20"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-200"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={loading}
            className="h-12 w-full rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 text-sm font-bold text-white shadow-lg shadow-orange-600/30 transition-all duration-200 hover:from-orange-500 hover:to-amber-500 hover:shadow-orange-600/40 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Validating RBAC & ABAC Policies...
              </>
            ) : (
              `Sign in as ${loginType === "admin" ? "Administrator" : "Staff Member"}`
            )}
          </Button>
        </form>

        {/* Demo Fast-Fill Test Accounts */}
        <div className="mt-8 border-t border-slate-800/80 pt-5">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-400">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Fast-Fill Test Credentials</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <button
              type="button"
              onClick={() => quickFill("admin", "Akena", "adminpassword", "Administration")}
              className="flex items-center gap-2 rounded-xl border border-orange-500/30 bg-orange-500/10 p-2 text-left text-orange-200 hover:bg-orange-500/20 transition-colors"
            >
              <Shield className="h-3.5 w-3.5 shrink-0 text-orange-400" />
              <div className="truncate">
                <span className="font-bold block text-white">Akena (Admin)</span>
                <span className="text-[10px] text-orange-300">All Departments</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => quickFill("staff", "Sarah Nakato", "staff123", "Sales & POS")}
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/40 p-2 text-left text-slate-300 hover:bg-slate-800/80 transition-colors"
            >
              <UserCheck className="h-3.5 w-3.5 shrink-0 text-amber-400" />
              <div className="truncate">
                <span className="font-bold block text-white">Sarah Nakato</span>
                <span className="text-[10px] text-slate-400">Sales & POS</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => quickFill("staff", "John Kato", "staff123", "Procurement & Inventory")}
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/40 p-2 text-left text-slate-300 hover:bg-slate-800/80 transition-colors"
            >
              <UserCheck className="h-3.5 w-3.5 shrink-0 text-amber-400" />
              <div className="truncate">
                <span className="font-bold block text-white">John Kato</span>
                <span className="text-[10px] text-slate-400">Procurement</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => quickFill("staff", "Grace Apio", "staff123", "Finance & Accounting")}
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/40 p-2 text-left text-slate-300 hover:bg-slate-800/80 transition-colors"
            >
              <UserCheck className="h-3.5 w-3.5 shrink-0 text-amber-400" />
              <div className="truncate">
                <span className="font-bold block text-white">Grace Apio</span>
                <span className="text-[10px] text-slate-400">Finance & Acc.</span>
              </div>
            </button>
          </div>
        </div>

        {/* Security Notice: Admin Provisioning Only */}
        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/50 p-3.5 text-center text-xs text-slate-400">
          <p>
            User accounts and passwords are created exclusively by the <strong>System Administrator</strong>.
          </p>
          <Link href="/auth/sign-up" className="mt-1 inline-block text-xs font-semibold text-orange-400 hover:text-orange-300 hover:underline">
            Inquire about account provisioning &rarr;
          </Link>
        </div>
      </div>
    </div>
  )
}
