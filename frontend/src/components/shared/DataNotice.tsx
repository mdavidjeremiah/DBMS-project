import { ShieldAlert, TriangleAlert } from "lucide-react"

export function DataNotice({ error, rlsBlocked }: { error: string | null; rlsBlocked: boolean }) {
  if (error) return <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"><TriangleAlert className="mt-0.5 size-4 shrink-0" />Couldn&apos;t load this data: {error}</div>
  if (rlsBlocked) return <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-300"><ShieldAlert className="mt-0.5 size-4 shrink-0" />Your Supabase Row Level Security policy does not currently permit this view. Configure the policy for the signed-in role.</div>
  return null
}
