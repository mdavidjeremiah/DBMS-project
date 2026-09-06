"use client"

import Link from "next/link"
import { useState } from "react"
import {
  ArrowUpRight,
  Banknote,
  Boxes,
  CircleDollarSign,
  Clock3,
  Package,
  Plus,
  ShoppingCart,
  Truck,
  Users,
} from "lucide-react"
import { StatCard } from "@/components/shared/StatCard"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const orders = [
  { id: "PO-1048", supplier: "BuildRight Uganda", amount: "UGX 4,820,000", status: "Pending" as const, date: "Today, 09:42" },
  { id: "PO-1047", supplier: "Kampala Cement Co.", amount: "UGX 2,140,000", status: "Approved" as const, date: "Yesterday" },
  { id: "PO-1046", supplier: "Steel & Sons Ltd.", amount: "UGX 6,385,000", status: "Received" as const, date: "Aug 28, 14:18" },
]

const activity = [
  { icon: ShoppingCart, title: "Sale #SL-2841 completed", detail: "Cash sale · Main Branch", time: "12 min ago", tone: "bg-emerald-100 text-emerald-700" },
  { icon: Truck, title: "Purchase order received", detail: "PO-1046 · Steel & Sons Ltd.", time: "38 min ago", tone: "bg-blue-100 text-blue-700" },
  { icon: Users, title: "New employee added", detail: "Sarah Namusoke · Cashier", time: "2 hours ago", tone: "bg-amber-100 text-amber-700" },
]

export default function Page() {
  const [range, setRange] = useState("This month")

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-sm font-medium text-primary">Sunday, September 6, 2026</p>
          <h1 className="text-3xl font-semibold tracking-tight">Good morning, Jonathan</h1>
          <p className="mt-1 text-muted-foreground">Here is what is happening across Main Branch today.</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href="/purchase-orders"><ShoppingCart className="mr-2 h-4 w-4" />View orders</Link>
          </Button>
          <Button asChild>
            <Link href="/sales"><Plus className="mr-2 h-4 w-4" />New sale</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Revenue this month" value="UGX 48.2M" icon={<CircleDollarSign className="h-4 w-4" />} trend="up" trendValue="12.5%" description="from last month" />
        <StatCard title="Sales today" value="UGX 3.84M" icon={<Banknote className="h-4 w-4" />} trend="up" trendValue="8.2%" description="from yesterday" />
        <StatCard title="Low stock items" value="18" icon={<Boxes className="h-4 w-4" />} trend="down" trendValue="4" description="items since yesterday" />
        <StatCard title="Open purchase orders" value="12" icon={<Package className="h-4 w-4" />} trend="neutral" trendValue="3" description="awaiting action" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Revenue overview</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">Sales performance for the current period</p>
            </div>
            <div className="flex rounded-lg border bg-muted/40 p-1 text-xs">
              {["This month", "Last month"].map((item) => (
                <button key={item} onClick={() => setRange(item)} className={`rounded-md px-3 py-1.5 transition-colors ${range === item ? "bg-background font-medium shadow-sm" : "text-muted-foreground"}`}>
                  {item}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3">
              <span className="text-3xl font-semibold">UGX 48.2M</span>
              <span className="mb-1 text-sm font-medium text-emerald-600">+12.5%</span>
            </div>
            <div className="mt-6 flex h-48 items-end gap-2 sm:gap-4">
              {[42, 58, 48, 74, 62, 86, 68, 92, 78, 100, 82, 94].map((height, index) => (
                <div key={index} className="group flex h-full flex-1 flex-col justify-end gap-2">
                  <div className="relative w-full rounded-t-md bg-primary/15 transition-colors group-hover:bg-primary/30" style={{ height: `${height}%` }}>
                    <div className="absolute inset-x-0 bottom-0 rounded-t-md bg-primary" style={{ height: `${Math.max(20, height - 18)}%` }} />
                  </div>
                  <span className="text-center text-[11px] text-muted-foreground">{["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][index]}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent activity</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">Latest updates from your team</p>
            </div>
            <Clock3 className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-5">
            {activity.map(({ icon: Icon, title, detail, time, tone }) => (
              <div key={title} className="flex gap-3">
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${tone}`}><Icon className="h-4 w-4" /></div>
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{title}</p><p className="truncate text-xs text-muted-foreground">{detail}</p></div>
                <span className="whitespace-nowrap text-xs text-muted-foreground">{time}</span>
              </div>
            ))}
            <Button asChild variant="ghost" className="w-full justify-between text-primary">
              <Link href="/ledger">View all activity <ArrowUpRight className="h-4 w-4" /></Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div><CardTitle>Recent purchase orders</CardTitle><p className="mt-1 text-sm text-muted-foreground">Track procurement across your branch</p></div>
            <Button asChild variant="ghost" size="sm"><Link href="/purchase-orders">View all <ArrowUpRight className="ml-1 h-4 w-4" /></Link></Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b text-xs text-muted-foreground"><tr><th className="pb-3 font-medium">Order</th><th className="pb-3 font-medium">Supplier</th><th className="pb-3 font-medium">Amount</th><th className="pb-3 font-medium">Status</th></tr></thead>
                <tbody>{orders.map((order) => <tr key={order.id} className="border-b last:border-0"><td className="py-4 font-medium">{order.id}<div className="text-xs font-normal text-muted-foreground">{order.date}</div></td><td className="py-4">{order.supplier}</td><td className="py-4 font-medium">{order.amount}</td><td className="py-4"><StatusBadge status={order.status} /></td></tr>)}</tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Needs attention</CardTitle><p className="mt-1 text-sm text-muted-foreground">Items that may need your action</p></CardHeader>
          <CardContent className="space-y-3">
            <Link href="/products" className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"><span><span className="block text-sm font-medium">Low stock products</span><span className="text-xs text-muted-foreground">18 products below reorder level</span></span><span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">18</span></Link>
            <Link href="/purchase-orders" className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"><span><span className="block text-sm font-medium">Orders awaiting approval</span><span className="text-xs text-muted-foreground">Requires procurement review</span></span><span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">3</span></Link>
            <Link href="/payroll" className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"><span><span className="block text-sm font-medium">Payroll draft</span><span className="text-xs text-muted-foreground">September payroll is ready</span></span><span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">Ready</span></Link>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
