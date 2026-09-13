"use client"

import { useRouter, usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { browserApiRequest } from "@/lib/api"

export type CurrentUserInfo = {
  employeeid: number
  name: string
  email: string
  roletype: string
  departmentid?: number | null
  department_name?: string | null
  branchid?: number | null
  branch_name?: string | null
}

const ROLE_ROUTES: Record<string, string[]> = {
  "Admin": ["/*"],
  "Cashier": ["/", "/sales", "/products"],
  "Procurement Officer": ["/", "/purchase-orders", "/suppliers", "/products", "/categories"],
  "Accountant": ["/", "/ledger", "/sales", "/payroll"],
  "HR Staff": ["/", "/employees", "/payroll"],
  "Branch Manager": ["/", "/sales", "/purchase-orders", "/employees", "/products", "/categories", "/suppliers"],
}

export function useRoleGuard() {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<CurrentUserInfo | null>(null)
  const [authorized, setAuthorized] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    async function checkAuth() {
      try {
        const currentUser = await browserApiRequest<CurrentUserInfo>("/users/me")
        if (!isMounted) return

        setUser(currentUser)

        const allowedRoutes = ROLE_ROUTES[currentUser.roletype] || []

        if (allowedRoutes.includes("/*")) {
          setAuthorized(true)
        } else {
          // Check route match carefully
          const isAllowed = allowedRoutes.some((route) => {
            if (route === "/") {
              return pathname === "/"
            }
            return pathname === route || pathname.startsWith(`${route}/`)
          })
          setAuthorized(isAllowed)
        }
      } catch {
        if (!isMounted) return
        setAuthorized(false)
        router.push("/auth/sign-in")
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    checkAuth()

    return () => {
      isMounted = false
    }
  }, [pathname, router])

  return { user, authorized, loading }
}
