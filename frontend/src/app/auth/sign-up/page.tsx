import Link from "next/link"
import { ShieldAlert, ArrowLeft, Building2, Lock, UserCheck } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-stone-900 p-4 text-slate-100">
      <div className="w-full max-w-lg rounded-3xl border border-slate-800/80 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <ShieldAlert className="h-8 w-8" />
        </div>

        <h1 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
          Account Provisioning Restricted
        </h1>
        <p className="mt-2 text-xs font-semibold uppercase tracking-widest text-amber-500">
          Access Control Policy Notice (RBAC & ABAC)
        </p>

        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-left text-xs leading-relaxed text-slate-300 space-y-3">
          <div className="flex items-start gap-3">
            <Lock className="h-4 w-4 text-orange-400 shrink-0 mt-0.5" />
            <p>
              In accordance with Hardware World enterprise security rules, <strong>public self-registration is disabled</strong>.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <UserCheck className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <p>
              Only the <strong>System Administrator</strong> can create new employee credentials, assign role privileges, and authorize department access.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Building2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
            <p>
              Once your account has been provisioned, your administrator will supply your login name, assigned department, and initial password.
            </p>
          </div>
        </div>

        <div className="mt-8 space-y-3">
          <Link href="/auth/sign-in" className="block w-full">
            <Button className="h-12 w-full rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 text-sm font-bold text-white shadow-lg shadow-orange-600/30 hover:from-orange-500 hover:to-amber-500">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Return to Sign In Portal
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
