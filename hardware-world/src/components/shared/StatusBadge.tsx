import { Badge, BadgeProps } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface StatusBadgeProps extends BadgeProps {
  status?: "Pending" | "Approved" | "Received" | "Cancelled"
  role?: "Cashier" | "Procurement Officer" | "Accountant" | "HR Staff" | "Branch Manager" | "Admin"
  className?: string
}

export function StatusBadge({ status, role, className, ...props }: StatusBadgeProps) {
  let colorClass = "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700"
  let dotColor = "bg-slate-400"

  if (status) {
    switch (status) {
      case "Pending":
        colorClass = "bg-amber-50 text-amber-800 border-amber-200/80 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800/50"
        dotColor = "bg-amber-500 animate-pulse"
        break
      case "Approved":
        colorClass = "bg-sky-50 text-sky-800 border-sky-200/80 dark:bg-sky-950/40 dark:text-sky-400 dark:border-sky-800/50"
        dotColor = "bg-sky-500"
        break
      case "Received":
        colorClass = "bg-emerald-50 text-emerald-800 border-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800/50"
        dotColor = "bg-emerald-500"
        break
      case "Cancelled":
        colorClass = "bg-rose-50 text-rose-800 border-rose-200/80 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800/50"
        dotColor = "bg-rose-500"
        break
    }
  } else if (role) {
    switch (role) {
      case "Admin":
        colorClass = "bg-purple-50 text-purple-800 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800"
        dotColor = "bg-purple-500"
        break
      case "Branch Manager":
        colorClass = "bg-indigo-50 text-indigo-800 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800"
        dotColor = "bg-indigo-500"
        break
      case "Procurement Officer":
        colorClass = "bg-orange-50 text-orange-800 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800"
        dotColor = "bg-orange-500"
        break
      case "HR Staff":
        colorClass = "bg-pink-50 text-pink-800 border-pink-200 dark:bg-pink-950/40 dark:text-pink-300 dark:border-pink-800"
        dotColor = "bg-pink-500"
        break
      case "Accountant":
        colorClass = "bg-teal-50 text-teal-800 border-teal-200 dark:bg-teal-950/40 dark:text-teal-300 dark:border-teal-800"
        dotColor = "bg-teal-500"
        break
      case "Cashier":
        colorClass = "bg-amber-50 text-amber-900 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800"
        dotColor = "bg-amber-500"
        break
    }
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        "font-semibold text-xs px-2.5 py-0.5 rounded-full inline-flex items-center gap-1.5 shadow-2xs transition-transform hover:scale-105",
        colorClass,
        className
      )}
      {...props}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", dotColor)} />
      {status || role}
    </Badge>
  )
}
