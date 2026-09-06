"use client"

import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface ModalProps {
  title: string
  description?: string
  trigger?: React.ReactNode
  children: React.ReactNode
  isOpen?: boolean
  onOpenChange?: (open: boolean) => void
  onConfirm?: () => void
  confirmText?: string
  cancelText?: string
}

export function Modal({
  title,
  description,
  trigger,
  children,
  isOpen,
  onOpenChange,
  onConfirm,
  confirmText = "Save changes",
  cancelText = "Cancel",
}: ModalProps) {
  const [internalOpen, setInternalOpen] = React.useState(false)
  const open = isOpen !== undefined ? isOpen : internalOpen
  const setOpen = onOpenChange || setInternalOpen

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {trigger && (
        <DialogTrigger render={trigger as React.ReactElement} />
      )}
      <DialogContent className="sm:max-w-[480px] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl p-6 overflow-hidden relative">
        <div className="absolute top-0 inset-x-0 h-1.5 bg-gradient-to-r from-orange-600 via-amber-500 to-orange-500" />
        <DialogHeader className="pt-2">
          <DialogTitle className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">{title}</DialogTitle>
          {description && <DialogDescription className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">{description}</DialogDescription>}
        </DialogHeader>
        <div className="py-4">
          {children}
        </div>
        <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-slate-100 dark:border-slate-800">
          <Button variant="outline" className="rounded-xl font-semibold border-slate-300 dark:border-slate-700" onClick={() => setOpen(false)}>
            {cancelText}
          </Button>
          <Button type="submit" className="rounded-xl font-bold bg-orange-600 hover:bg-orange-700 text-white shadow-md shadow-orange-600/20" onClick={onConfirm}>
            {confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
