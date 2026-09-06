'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { createClient } from '@/utils/supabase/client'

const ROLE_ROUTES: Record<string, string[]> = {
  'Cashier': ['/sales', '/products', '/categories'],
  'Procurement Officer': ['/purchase-orders', '/suppliers', '/products', '/categories'],
  'Accountant': ['/ledger', '/payroll'],
  'HR Staff': ['/employees', '/payroll', '/departments'],
  'Branch Manager': ['/dashboard', '/sales', '/purchase-orders', '/employees', '/payroll', '/ledger', '/products', '/categories', '/suppliers'],
  'Admin': ['/*'], // Admin can access everything
}

export function useRoleGuard() {
  const router = useRouter()
  const pathname = usePathname()
  const [authorized, setAuthorized] = useState(true)
  const [loading, setLoading] = useState(true)
  const supabase = createClient()

  useEffect(() => {
    const checkAccess = async () => {
      try {
        const { data: { user } } = await supabase.auth.getUser()

        if (!user) {
          router.push('/auth/sign-in')
          return
        }

        // Skip auth pages
        if (pathname?.startsWith('/auth')) {
          setAuthorized(true)
          setLoading(false)
          return
        }

        // Fetch user's role
        const { data: employee } = await supabase
          .from('EMPLOYEE')
          .select('RoleType')
          .eq('AuthUserID', user.id)
          .single()

        if (!employee) {
          setAuthorized(false)
          setLoading(false)
          return
        }

        const userRole = employee.RoleType
        const allowedRoutes = ROLE_ROUTES[userRole] || []

        // Check if current pathname is in allowed routes
        const hasAccess = 
          allowedRoutes.includes('/*') ||
          allowedRoutes.some((route) => pathname?.startsWith(route))

        if (!hasAccess && !pathname?.startsWith('/')) {
          router.push('/')
        }

        setAuthorized(hasAccess)
      } catch (error) {
        console.error('Error checking access:', error)
        setAuthorized(false)
      } finally {
        setLoading(false)
      }
    }

    checkAccess()
  }, [pathname, router])

  return { authorized, loading }
}
