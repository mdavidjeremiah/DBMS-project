import { ShieldAlert, TriangleAlert } from "lucide-react"

/**
 * Every table has RLS enabled with zero policies until Issue #3 lands. That
 * means every read right now comes back empty -- not because the data or
 * the query is wrong, but because nothing has granted access yet. Without
 * this banner, an empty table looks indistinguishable from a bug.
 */
export function RlsNotice() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-dashed bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <p>
        No rows are visible yet because Row Level Security is enabled on this
        table with no policies defined (by design, until Issue #3 adds the
        role permission matrix). The query itself is working correctly.
      </p>
    </div>
  )
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <p>Couldn't load this data: {message}</p>
    </div>
  )
}