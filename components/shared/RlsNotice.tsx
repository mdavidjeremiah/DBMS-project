import { ShieldAlert, TriangleAlert } from "lucide-react"

/**
 * Every table has RLS enabled with zero policies until Issue #3 lands. That
 * means every read right now comes back empty -- not because the data or
 * the query is wrong, but because nothing has granted access yet. Without
 * this banner, an empty table looks indistinguishable from a bug.
 */
export function RlsNotice() {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-dashed border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-300">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
      <p className="font-medium text-xs leading-relaxed">
        No rows are visible yet because Row Level Security is enabled on this
        table with no policies defined (by design, until Issue #3 adds the
        role permission matrix). The query itself is working correctly.
      </p>
    </div>
  )
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-800 dark:text-rose-300">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
      <p className="font-medium text-xs">Couldn&apos;t load this data: {message}</p>
    </div>
  )
}