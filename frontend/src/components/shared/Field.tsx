import type { InputHTMLAttributes, ReactNode } from "react"
import { Input } from "@/components/ui/input"

export function Field({ label, name, ...props }: { label: string; name: string } & InputHTMLAttributes<HTMLInputElement>) {
  return <label className="grid gap-1.5 text-sm font-medium"><span>{label}</span><Input name={name} {...props} /></label>
}

export function SelectField({ label, name, children, required = false, defaultValue }: { label: string; name: string; children: ReactNode; required?: boolean; defaultValue?: string }) {
  return <label className="grid gap-1.5 text-sm font-medium"><span>{label}</span><select name={name} required={required} defaultValue={defaultValue} className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50">{children}</select></label>
}
