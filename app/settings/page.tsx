"use client"

import { useTheme } from "next-themes"
import { Sun, Moon, Laptop } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useHasMounted } from "@/lib/use-has-mounted"

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  // Avoid a hydration mismatch: next-themes only knows the real theme after mount.
  const mounted = useHasMounted()

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "Not configured"

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Application preferences. Branch, role, and account settings arrive
          with Issue #3 (Auth & RBAC).
        </p>
      </div>

      <div className="rounded-xl border bg-card p-4">
        <h2 className="font-medium mb-1">Appearance</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Choose how Hardware World looks on this device.
        </p>
        <div className="flex gap-2">
          <Button
            variant={mounted && theme === "light" ? "default" : "outline"}
            size="sm"
            onClick={() => setTheme("light")}
          >
            <Sun className="mr-2 h-4 w-4" /> Light
          </Button>
          <Button
            variant={mounted && theme === "dark" ? "default" : "outline"}
            size="sm"
            onClick={() => setTheme("dark")}
          >
            <Moon className="mr-2 h-4 w-4" /> Dark
          </Button>
          <Button
            variant={mounted && theme === "system" ? "default" : "outline"}
            size="sm"
            onClick={() => setTheme("system")}
          >
            <Laptop className="mr-2 h-4 w-4" /> System
          </Button>
        </div>
      </div>

      <div className="rounded-xl border bg-card p-4">
        <h2 className="font-medium mb-1">Connection</h2>
        <p className="text-sm text-muted-foreground mb-3">
          This deployment is reading and writing to the Supabase project
          below.
        </p>
        <code className="block rounded-md bg-muted px-3 py-2 text-xs break-all">
          {supabaseUrl}
        </code>
      </div>
    </div>
  )
}