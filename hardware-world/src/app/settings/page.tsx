"use client"

import { Settings, Building2, ShieldCheck, Printer, Bell, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
            <Settings className="h-4 w-4" /> System Preferences
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">Branch & Store Settings</h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Configure branch operations, tax receipts, printer profiles, and Postgres RLS security policies.
          </p>
        </div>

        <Button className="rounded-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25 hover:from-orange-700 hover:to-amber-700">
          <Save className="mr-2 h-4 w-4" /> Save Preferences
        </Button>
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
                <Input id="store-name" defaultValue="Hardware World Uganda Ltd" className="rounded-xl" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="tin" className="font-bold text-xs">URA Tax Identification Number (TIN)</Label>
                <Input id="tin" defaultValue="1004829104" className="rounded-xl" />
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="branch" className="font-bold text-xs">Active Workspace Branch</Label>
                <Input id="branch" defaultValue="Main Branch - Plot 42 Jinja Road, Kampala" className="rounded-xl" />
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
                <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Supabase RLS & Security Policies</CardTitle>
                <p className="text-xs font-medium text-slate-500">Role-Based Access Control enforced at database layer</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-5">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-900 dark:text-emerald-300 text-xs font-semibold flex items-center justify-between">
              <span>Postgres Row Level Security (RLS) Status</span>
              <span className="bg-emerald-600 text-white px-2.5 py-0.5 rounded-full text-[11px] font-extrabold">Active & Enforced</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every table (SALE, PAYROLL, PURCHASE_ORDER, PRODUCT) uses row-level policies so Cashiers, Procurement Officers, Accountants, and HR Staff only access their authorized branch rows.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
