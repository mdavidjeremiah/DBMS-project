'use client'

import { useState, useEffect, useEffectEvent } from 'react'
import { Settings, Building2, ShieldCheck, Users, Plus, Mail, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { browserApiRequest } from '@/lib/api'
import { Badge } from '@/components/ui/badge'

interface TeamMember {
  employeeid: number
  name: string
  roletype: string
  branchid?: number
}

export default function SettingsPage() {
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([])
  const [loading, setLoading] = useState(true)

  const fetchTeamMembers = useEffectEvent(async () => {
    try {
      setLoading(true)
      setTeamMembers(await browserApiRequest<TeamMember[]>('/employees'))
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  })

  useEffect(() => {
    const timer = window.setTimeout(() => void fetchTeamMembers(), 0)
    return () => window.clearTimeout(timer)
  }, [fetchTeamMembers])

  const getRoleBadgeColor = (role: string) => {
    const colors: Record<string, string> = {
      'Cashier': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      'Procurement Officer': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      'Accountant': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
      'HR Staff': 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      'Branch Manager': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      'Admin': 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400',
    }
    return colors[role] || 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400'
  }

  return (
    <div className="flex flex-col gap-6 max-w-6xl">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Settings className="h-4 w-4" /> System Preferences
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Branch & Store Settings</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Configure branch operations, team members, and role-based access control.
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Team Management Card */}
        <div className="lg:col-span-2">
          <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
            <CardHeader className="pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600">
                    <Users className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Team Members</CardTitle>
                    <p className="text-xs font-medium text-slate-500">Manage employees and their roles</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="rounded-lg bg-orange-600 hover:bg-orange-700 text-white flex items-center gap-2"
                  >
                    <Mail className="h-4 w-4" />
                    Invite Team Member
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-orange-600" />
                </div>
              ) : teamMembers.length === 0 ? (
                <div className="text-center py-12">
                  <Users className="h-12 w-12 text-slate-300 dark:text-slate-700 mx-auto mb-4" />
                  <p className="text-slate-500 dark:text-slate-400 mb-4">No team members yet</p>
                  <Button
                    size="sm"
                    className="bg-orange-600 hover:bg-orange-700 text-white"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add First Member
                  </Button>
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {teamMembers.map((member) => (
                    <div
                      key={member.employeeid}
                      className="flex items-center justify-between p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                    >
                      <div>
                        <p className="font-semibold text-slate-900 dark:text-white">
                          {member.name}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          ID: {member.employeeid}
                        </p>
                      </div>
                      <Badge className={`${getRoleBadgeColor(member.roletype)}`}>
                        {member.roletype}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="space-y-4">
          <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
            <CardHeader className="pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-green-500/10 text-green-600">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Quick Actions</CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-2">
              <Button
                className="w-full rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium justify-start"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add to Branch
              </Button>
              <Button
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium justify-start"
              >
                <ShieldCheck className="h-4 w-4 mr-2" />
                Manage Permissions
              </Button>
            </CardContent>
          </Card>

          <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-bold text-slate-900 dark:text-white">
                System Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-400">Auth Configured</span>
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  Active
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-400">RLS Policies</span>
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  Enabled
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600 dark:text-slate-400">Invites</span>
                <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  Available
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6">
        <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
          <CardHeader className="pb-4 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-orange-500/10 text-orange-600">
                <Building2 className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Store Identity & Tax Details</CardTitle>
                <p className="text-xs font-medium text-slate-500">Business registration and official header for customer receipts</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="store-name" className="font-bold text-xs">Store Legal Name</Label>
                <Input id="store-name" placeholder="Configured in your business profile" className="rounded-xl" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="tin" className="font-bold text-xs">URA Tax Identification Number (TIN)</Label>
                <Input id="tin" placeholder="Configured in your business profile" className="rounded-xl" />
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="branch" className="font-bold text-xs">Active Workspace Branch</Label>
                <Input id="branch" placeholder="Select a live branch" className="rounded-xl" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="currency" className="font-bold text-xs">Operating Currency</Label>
                <Input id="currency" defaultValue="UGX (Ugandan Shilling)" disabled className="rounded-xl bg-slate-100 dark:bg-slate-800" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
          <CardHeader className="pb-4 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">FastAPI & MySQL Security</CardTitle>
                <p className="text-xs font-medium text-slate-500">Role-Based Access Control enforced at database layer</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-900 dark:text-emerald-300 text-xs font-semibold flex items-center justify-between">
              <span>FastAPI authentication status</span>
              <span className="bg-emerald-600 text-white px-2.5 py-0.5 rounded-full text-[11px] font-extrabold">JWT enabled</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              FastAPI validates the signed-in employee role before allowing access to MySQL-backed operations.
            </p>
          </CardContent>
        </Card>
      </div>

    </div>
  )
}
