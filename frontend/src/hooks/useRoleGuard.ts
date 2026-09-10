"use client"

import { useRouter, usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { browserApiRequest } from "@/lib/api"

const ROLE_ROUTES: Record<string, string[]> = { Cashier: ["/sales", "/products", "/categories"], "Procurement Officer": ["/purchase-orders", "/suppliers", "/products", "/categories"], Accountant: ["/ledger", "/payroll"], "HR Staff": ["/employees", "/payroll", "/departments"], "Branch Manager": ["/"], Admin: ["/*"] }

export function useRoleGuard() {
  const router = useRouter(); const pathname = usePathname(); const [authorized, setAuthorized] = useState(true); const [loading, setLoading] = useState(true)
  useEffect(() => { const timer = window.setTimeout(() => { void browserApiRequest<{ roletype: string }>("/users/me").then((user) => { const routes = ROLE_ROUTES[user.roletype] ?? []; setAuthorized(routes.includes("/*") || routes.some((route) => pathname.startsWith(route))); setLoading(false) }).catch(() => { setAuthorized(false); setLoading(false); router.push("/auth/sign-in") }) }, 0); return () => window.clearTimeout(timer) }, [pathname, router])
  return { authorized, loading }
}
