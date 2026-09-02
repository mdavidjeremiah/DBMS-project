import { Badge, BadgeProps } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface StatusBadgeProps extends BadgeProps {
  status?: "Pending" | "Approved" | "Received" | "Cancelled"
  role?: "Cashier" | "Procurement Officer" | "Accountant" | "HR Staff" | "Branch Manager" | "Admin"
  className?: string
}

export function StatusBadge({ status, role, className, ...props }: StatusBadgeProps) {
  let colorClass = "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300" // default

  if (status) {
    switch (status) {
      case "Pending":
        colorClass = "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-500"
        break
      case "Approved":
        colorClass = "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-500"
        break
      case "Received":
        colorClass = "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-500"
        break
      case "Cancelled":
        colorClass = "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-500"
        break
    }
  } else if (role) {
    switch (role) {
      case "Admin":
        colorClass = "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
        break
      case "Branch Manager":
        colorClass = "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400"
        break
      case "Procurement Officer":
        colorClass = "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400"
        break
      case "HR Staff":
        colorClass = "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400"
        break
      case "Accountant":
        colorClass = "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400"
        break
      case "Cashier":
        colorClass = "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400"
        break
    }
  }

  return (
    <Badge
      variant="outline"
      className={cn("font-medium border-transparent", colorClass, className)}
      {...props}
    >
      {status || role}
    </Badge>
  )
}
