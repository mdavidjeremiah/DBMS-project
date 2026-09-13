"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { LogOut, Menu, Moon, Search, Sun, Shield, UserCheck } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Sidebar } from "./Sidebar"
import { browserApiRequest, clearAccessToken } from "@/lib/api"

type UserProfile = {
  employeeid: number
  name: string
  email: string
  roletype: string
  department_name?: string | null
  branch_name?: string | null
}

export function Topbar() {
  const router = useRouter()
  const { setTheme, theme } = useTheme()
  const [user, setUser] = React.useState<UserProfile | null>(null)

  React.useEffect(() => {
    browserApiRequest<UserProfile>("/users/me")
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  async function signOut() {
    clearAccessToken()
    router.push("/auth/sign-in")
    router.refresh()
  }

  return (
    <div className="flex h-16 items-center gap-4 border-b bg-white/90 px-4 shadow-sm backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 lg:px-6">
      <Sheet>
        <SheetTrigger render={<Button variant="outline" size="icon" className="md:hidden" />}>
          <Menu className="h-5 w-5" />
        </SheetTrigger>
        <SheetContent side="left" className="p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Sidebar />
        </SheetContent>
      </Sheet>

      <div className="flex-1">
        <div className="relative max-w-xl">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-orange-600" />
          <Input placeholder="Search live records, products, customers..." className="pl-9 rounded-xl border-slate-200 dark:border-slate-800" />
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        aria-label="Toggle theme"
        className="rounded-xl"
      >
        {theme === "dark" ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-600" />}
      </Button>

      {/* User ABAC Profile Badge */}
      <div className="hidden sm:flex items-center gap-3 border-l border-slate-200 pl-4 dark:border-slate-800">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400 font-bold">
          {user?.roletype === "Admin" ? <Shield className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight">
            {user?.name ?? "Hardware Staff"}
          </p>
          <div className="flex items-center justify-end gap-1.5 mt-0.5">
            <span className="text-[11px] font-semibold text-orange-600 dark:text-orange-400">
              {user?.roletype ?? "Staff"}
            </span>
            <span className="text-[10px] text-slate-400">·</span>
            <span className="text-[11px] text-slate-500 dark:text-slate-400">
              {user?.department_name ?? "General"}
            </span>
          </div>
        </div>
      </div>

      {/* Sign Out Action */}
      <Button
        variant="ghost"
        size="icon"
        onClick={signOut}
        aria-label="Sign out"
        className="rounded-xl text-slate-500 hover:text-rose-600 hover:bg-rose-500/10"
        title="Sign out of system"
      >
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  )
}
