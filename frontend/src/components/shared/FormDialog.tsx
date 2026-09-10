"use client"

import type { ReactNode } from "react"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

type Action = (formData: FormData) => void | Promise<void>

export function FormDialog({ title, description, trigger, action, submitLabel, children, className = "" }: { title: string; description: string; trigger: ReactNode; action: Action; submitLabel: string; children: ReactNode; className?: string }) {
  return <Dialog>
    <DialogTrigger render={trigger as React.ReactElement} />
    <DialogContent className={`max-h-[90vh] overflow-y-auto sm:max-w-lg ${className}`}>
      <form action={action} className="grid gap-4">
        <DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>{description}</DialogDescription></DialogHeader>
        <div className="grid gap-3">{children}</div>
        <DialogFooter>
          <DialogClose render={<Button type="button" variant="outline" />}>Cancel</DialogClose>
          <Button type="submit">{submitLabel}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
