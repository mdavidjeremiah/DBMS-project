import { ReactNode } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface StatCardProps {
  title: string
  value: string | number
  icon: ReactNode
  description?: string
  trend?: "up" | "down" | "neutral"
  trendValue?: string
  className?: string
}

export function StatCard({
  title,
  value,
  icon,
  description,
  trend,
  trendValue,
  className
}: StatCardProps) {
  return (
    <Card className={cn(
      "overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-900/5 border-slate-200/90 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900 relative group",
      className
    )}>
      <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</CardTitle>
        <div className="p-2.5 rounded-xl bg-gradient-to-br from-orange-500/10 to-amber-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 shadow-sm transition-transform duration-300 group-hover:scale-110">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">{value}</div>
        {(description || trendValue) && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1.5 font-medium">
            {trendValue && (
              <span
                className={cn(
                  "font-bold text-[11px] px-2 py-0.5 rounded-full inline-flex items-center gap-0.5",
                  trend === "up" && "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20",
                  trend === "down" && "bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/20",
                  trend === "neutral" && "bg-slate-500/15 text-slate-700 dark:text-slate-400 border border-slate-500/20"
                )}
              >
                {trend === "up" && "↑ "}
                {trend === "down" && "↓ "}
                {trendValue}
              </span>
            )}
            <span>{description}</span>
          </p>
        )}
      </CardContent>
    </Card>
  )
}
