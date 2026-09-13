"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  Package,
  Tags,
  Truck,
  ShoppingCart,
  Banknote,
  Users,
  Briefcase,
  BookOpen,
  Settings,
  Building2,
  ChevronDown,
  Shield,
  UserCheck
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { browserApiRequest } from "@/lib/api"

type UserProfile = {
  employeeid: number
  name: string
  email: string
  roletype: string
  department_name?: string | null
  branch_name?: string | null
}

const ALL_NAV_ITEMS = [
  { title: "Dashboard", href: "/", icon: LayoutDashboard, roles: ["*"] },
  { title: "Products", href: "/products", icon: Package, roles: ["Admin", "Cashier", "Procurement Officer", "Branch Manager"] },
  { title: "Categories", href: "/categories", icon: Tags, roles: ["Admin", "Procurement Officer", "Branch Manager"] },
  { title: "Suppliers", href: "/suppliers", icon: Truck, roles: ["Admin", "Procurement Officer", "Branch Manager"] },
  { title: "Purchase Orders", href: "/purchase-orders", icon: ShoppingCart, roles: ["Admin", "Procurement Officer", "Branch Manager"] },
  { title: "Sales (POS)", href: "/sales", icon: Banknote, roles: ["Admin", "Cashier", "Branch Manager", "Accountant"] },
  { title: "Employees", href: "/employees", icon: Users, roles: ["Admin", "HR Staff", "Branch Manager"] },
  { title: "Payroll", href: "/payroll", icon: Briefcase, roles: ["Admin", "HR Staff", "Accountant"] },
  { title: "Ledger", href: "/ledger", icon: BookOpen, roles: ["Admin", "Accountant"] },
  { title: "Settings", href: "/settings", icon: Settings, roles: ["Admin"] },
]

export function Sidebar() {
  const pathname = usePathname()
  const [user, setUser] = useState<UserProfile | null>(null)

  useEffect(() => {
    browserApiRequest<UserProfile>("/users/me")
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  // Filter items according to user role
  const userRole = user?.roletype || "Admin"
  const visibleNavItems = ALL_NAV_ITEMS.filter((item) => {
    if (item.roles.includes("*")) return true
    if (userRole === "Admin") return true
    return item.roles.includes(userRole)
  })

  return (
    <div className="flex h-full w-64 flex-col border-r border-slate-200/80 bg-slate-900 text-slate-100 dark:border-slate-800 dark:bg-slate-950 shadow-xl">
      {/* Brand & Workspace */}
      <div className="flex h-16 items-center border-b border-slate-800 px-4 lg:px-6">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button variant="ghost" className="w-full justify-between p-1.5 font-bold text-base hover:bg-slate-800/80 text-white rounded-xl" />
            }
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 text-white shadow-md shadow-orange-500/25">
                <Building2 className="h-5 w-5" />
              </div>
              <div className="flex flex-col text-left truncate">
                <span className="truncate font-extrabold tracking-tight text-white text-sm">HARDWARE WORLD</span>
                <span className="text-[10px] font-medium text-amber-400 uppercase tracking-widest">
                  {user?.branch_name ?? "Main Branch"}
                </span>
              </div>
            </div>
            <ChevronDown className="h-4 w-4 text-slate-400" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56 bg-slate-900 text-slate-100 border-slate-800">
            <DropdownMenuLabel className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
              Assigned Workspace
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-slate-800" />
            <DropdownMenuItem className="focus:bg-orange-500 focus:text-white cursor-pointer font-medium">
              Main Industrial Branch
            </DropdownMenuItem>
            <DropdownMenuItem className="focus:bg-orange-500 focus:text-white cursor-pointer font-medium">
              Downtown Retail Store
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Navigation Links Filtered by ABAC/RBAC */}
      <div className="flex-1 overflow-auto py-3">
        <div className="px-4 mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
          <span>{userRole === "Admin" ? "Master Navigation" : `${userRole} Access`}</span>
          <span className="text-[9px] text-amber-500 font-normal lowercase bg-amber-500/10 px-1.5 py-0.5 rounded">
            {user?.department_name ?? "general"}
          </span>
        </div>
        <nav className="grid gap-1 px-3 text-sm font-medium">
          {visibleNavItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3.5 py-2.5 transition-all duration-200",
                  isActive
                    ? "bg-gradient-to-r from-orange-600 to-amber-600 text-white font-semibold shadow-md shadow-orange-600/30"
                    : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-transform duration-200 group-hover:scale-110",
                    isActive ? "text-white" : "text-amber-500/80 group-hover:text-amber-400"
                  )}
                />
                <span className="truncate">{item.title}</span>
                {isActive && (
                  <span className="ml-auto h-2 w-2 rounded-full bg-white animate-pulse" />
                )}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* User ABAC Status Card */}
      <div className="p-3 m-3 rounded-2xl bg-slate-800/60 border border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30 shrink-0">
            {userRole === "Admin" ? <Shield className="h-5 w-5" /> : <UserCheck className="h-5 w-5" />}
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-bold text-white truncate block">
              {user?.name ?? "Authenticated Staff"}
            </span>
            <span className="text-[10px] text-amber-400 font-semibold block truncate">
              {user?.department_name ?? "Administration"}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
