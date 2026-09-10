'use client'

import { useState } from 'react'
import { createClient } from '@/utils/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AlertCircle, Loader2 } from 'lucide-react'

const ROLES = [
  { value: 'Cashier', label: 'Cashier' },
  { value: 'Procurement Officer', label: 'Procurement Officer' },
  { value: 'Accountant', label: 'Accountant' },
  { value: 'HR Staff', label: 'HR Staff' },
  { value: 'Branch Manager', label: 'Branch Manager' },
  { value: 'Admin', label: 'Admin' },
]

interface InviteTeamMemberModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function InviteTeamMemberModal({
  open,
  onOpenChange,
  onSuccess,
}: InviteTeamMemberModalProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const supabase = createClient()

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (!email || !role) {
        setError('Please fill in all fields')
        return
      }

      if (!supabase) {
        setError('Supabase is not configured')
        setLoading(false)
        return
      }

      // Invite user via Supabase Auth
      const { data, error: inviteError } = await supabase.auth.admin.inviteUserByEmail(email, {
        redirectTo: `${window.location.origin}/auth/callback`,
      })

      if (inviteError) {
        setError(inviteError.message)
        return
      }

      // Create employee record linked to the invited user
      if (data.user) {
        const { error: employeeError } = await supabase
          .from('EMPLOYEE')
          .insert({
            AuthUserID: data.user.id,
            RoleType: role,
            // Additional fields can be set via a separate form or defaults
          })

        if (employeeError) {
          setError(employeeError.message)
          return
        }
      }

      setSuccess(true)
      setTimeout(() => {
        setEmail('')
        setRole('')
        setSuccess(false)
        onOpenChange(false)
        onSuccess?.()
      }, 2000)
    } catch (err) {
      setError('An unexpected error occurred')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px] rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl p-6 relative max-h-[85vh] flex flex-col">
        <div className="absolute top-0 inset-x-0 h-1.5 bg-gradient-to-r from-orange-600 via-amber-500 to-orange-500" />
        <DialogHeader className="pt-2 shrink-0">
          <DialogTitle className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">Invite Team Member</DialogTitle>
          <DialogDescription className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">
            Send an invitation to a new team member to join Hardware World
          </DialogDescription>
        </DialogHeader>

        {success ? (
          <div className="space-y-4 py-4">
            <div className="flex items-center justify-center h-16 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <p className="text-emerald-700 dark:text-emerald-400 font-semibold">
                Invitation sent to {email}
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleInvite} className="space-y-4">
            {error && (
              <div className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="colleague@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select value={role} onValueChange={(v) => setRole(v ?? '')} disabled={loading}>
                <SelectTrigger id="role">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={loading}
                className="bg-orange-600 hover:bg-orange-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Inviting...
                  </>
                ) : (
                  'Send Invite'
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
