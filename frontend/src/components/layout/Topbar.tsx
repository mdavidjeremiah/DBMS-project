"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { LogOut, Menu, Moon, Search, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Sidebar } from "./Sidebar"
import { browserApiRequest, clearAccessToken } from "@/lib/api"

type User = { name: string; email: string; roletype: string }
export function Topbar() {
  const router = useRouter(); const { setTheme, theme } = useTheme(); const [user, setUser] = React.useState<User | null>(null)
  React.useEffect(() => { const timer = window.setTimeout(() => { void browserApiRequest<User>("/users/me").then(setUser).catch(() => setUser(null)) }, 0); return () => window.clearTimeout(timer) }, [])
  async function signOut() { clearAccessToken(); router.push("/auth/sign-in"); router.refresh() }
  return <div className="flex h-16 items-center gap-4 border-b bg-white/90 px-4 shadow-sm backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 lg:px-6"><Sheet><SheetTrigger render={<Button variant="outline" size="icon" className="md:hidden" />}><Menu className="h-5 w-5" /></SheetTrigger><SheetContent side="left" className="p-0"><SheetTitle className="sr-only">Navigation</SheetTitle><Sidebar /></SheetContent></Sheet><div className="flex-1"><div className="relative max-w-xl"><Search className="absolute left-3 top-2.5 h-4 w-4 text-orange-600" /><Input placeholder="Search live records..." className="pl-9" /></div></div><Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">{theme === "dark" ? <Sun /> : <Moon />}</Button><div className="hidden text-right sm:block"><p className="text-sm font-semibold">{user?.name ?? "Loading..."}</p><p className="text-xs text-slate-500">{user?.roletype ?? ""}</p></div><Button variant="ghost" size="icon" onClick={signOut} aria-label="Sign out"><LogOut /></Button></div>
}
