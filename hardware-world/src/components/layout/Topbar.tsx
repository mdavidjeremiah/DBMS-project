"use client"

import { useTheme } from "next-themes"
import { Search, Sun, Moon, Menu, Bell, ShieldCheck, PhoneCall, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import { Sidebar } from "./Sidebar"
import * as React from "react"
import { createClient, isSupabaseConfigured } from "@/utils/supabase/client"

export function Topbar() {
  const { setTheme, theme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  const [user, setUser] = React.useState<any>(null)
  const [userRole, setUserRole] = React.useState<string>("")
  const [loading, setLoading] = React.useState(true)
  const supabase = isSupabaseConfigured ? createClient() : null

  React.useEffect(() => {
    setMounted(true)
    fetchUser()
  }, [])

  const fetchUser = async () => {
    if (!supabase) {
      setLoading(false)
      return
    }

    try {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      setUser(authUser)
      
      if (authUser) {
        // Fetch user's employee role from database
        const { data: employee } = await supabase
          .from("EMPLOYEE")
          .select("RoleType")
          .eq("AuthUserID", authUser.id)
          .single()
        
        if (employee) {
          setUserRole(employee.RoleType)
        }
      }
    } catch (error) {
      console.error("Error fetching user:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleSignOut = async () => {
    if (!supabase) return
    await supabase.auth.signOut()
    window.location.href = "/auth/sign-in"
  }

  const getInitials = (email?: string) => {
    if (!email) return "HW"
    return email.split("@")[0].slice(0, 2).toUpperCase()
  }

  const getRoleBadgeColor = (role: string) => {
    const colors: Record<string, string> = {
      "Cashier": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
      "Procurement Officer": "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
      "Accountant": "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
      "HR Staff": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
      "Branch Manager": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
      "Admin": "bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400",
    }
    return colors[role] || "bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400"
  }

  return (
    <div className="flex flex-col w-full z-20">
      {/* Announcement Marquee Bar */}
      <div className="bg-gradient-to-r from-orange-600 via-amber-600 to-orange-700 text-white text-[11px] font-semibold py-1 px-4 flex items-center justify-between shadow-inner">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="bg-slate-900/40 text-amber-300 text-[10px] uppercase font-extrabold px-2 py-0.5 rounded-full shrink-0">PRO PROMO</span>
          <span className="truncate">🔥 Autumn Trade Sale: Up to 35% Off Bulk Building Materials & Power Tools | Free Express Branch Delivery over UGX 500,000</span>
        </div>
        <div className="hidden md:flex items-center gap-4 text-orange-100 text-xs shrink-0">
          <span className="flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5 text-amber-300" /> 100% Genuine Supplies</span>
          <span className="flex items-center gap-1"><PhoneCall className="h-3.5 w-3.5 text-amber-300" /> 0800-HARDWARE</span>
        </div>
      </div>

      <header className="flex h-16 items-center gap-4 border-b border-slate-200 bg-white/90 dark:bg-slate-900/90 dark:border-slate-800 backdrop-blur-md px-4 lg:px-6 shadow-sm">
        <Sheet>
          <SheetTrigger
            render={
              <Button
                variant="outline"
                size="icon"
                className="shrink-0 md:hidden border-slate-300 dark:border-slate-700"
              />
            }
          >
            <Menu className="h-5 w-5 text-slate-700 dark:text-slate-200" />
            <span className="sr-only">Toggle navigation menu</span>
          </SheetTrigger>
          <SheetContent side="left" className="flex flex-col p-0 border-r border-slate-800 bg-slate-900 text-white">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <Sidebar />
          </SheetContent>
        </Sheet>
        
        <div className="w-full flex-1">
          <form onSubmit={(e) => e.preventDefault()}>
            <div className="relative max-w-xl">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-orange-600 dark:text-orange-400" />
              <Input
                type="search"
                placeholder="Search products, cement, tools, PO-1048, suppliers..."
                className="w-full bg-slate-50 dark:bg-slate-800/80 pl-9 pr-12 text-sm border-slate-200 dark:border-slate-700 focus-visible:ring-2 focus-visible:ring-orange-500 rounded-xl shadow-inner transition-all"
              />
              <kbd className="hidden sm:inline-flex absolute right-2.5 top-2.5 h-5 items-center gap-1 rounded border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800 px-1.5 font-mono text-[10px] font-medium text-slate-500">
                Ctrl K
              </kbd>
            </div>
          </form>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Notifications Button */}
          <Button
            variant="ghost"
            size="icon"
            className="relative rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-600"></span>
            </span>
            <span className="sr-only">Notifications</span>
          </Button>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all text-amber-500 dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all text-orange-400 dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Profile Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button variant="ghost" className="rounded-xl flex items-center gap-2.5 p-1 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200/80 dark:border-slate-800" />
              }
            >
              <div className="relative">
                <Avatar className="h-8 w-8 border border-orange-500/40">
                  <AvatarImage src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.email}`} />
                  <AvatarFallback className="bg-orange-600 text-white font-bold text-xs">
                    {getInitials(user?.email)}
                  </AvatarFallback>
                </Avatar>
                <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900" />
              </div>
              <div className="hidden lg:flex flex-col text-left pr-1">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-100">
                  {user?.email?.split("@")[0] || "Loading..."}
                </span>
                {userRole && (
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${getRoleBadgeColor(userRole)}`}>
                    {userRole}
                  </span>
                )}
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 rounded-xl shadow-xl">
              <DropdownMenuLabel className="font-bold">
                <p className="text-sm text-slate-900 dark:text-white">{user?.email || "User"}</p>
                {userRole && (
                  <p className={`text-xs font-semibold mt-1 px-2 py-1 rounded-full w-fit ${getRoleBadgeColor(userRole)}`}>
                    {userRole}
                  </p>
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="cursor-pointer font-medium">My Profile & Permissions</DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer font-medium">Branch Settings</DropdownMenuItem>
              <DropdownMenuItem className="cursor-pointer font-medium">Support & Knowledgebase</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                className="text-red-600 font-semibold cursor-pointer flex items-center gap-2"
                onClick={handleSignOut}
              >
                <LogOut className="h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
    </div>
  )
}
