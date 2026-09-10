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
  Wrench,
  Zap,
  Droplet,
  Paintbrush,
  ShieldCheck,
  Star,
  Sparkles,
  ChevronRight,
  Flame
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
  { icon: ShoppingCart, title: "Sale #SL-2841 completed", detail: "Cash sale · Main Branch", time: "12 min ago", tone: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30" },
  { icon: Truck, title: "Purchase order received", detail: "PO-1046 · Steel & Sons Ltd.", time: "38 min ago", tone: "bg-sky-500/15 text-sky-700 dark:text-sky-400 border border-sky-500/30" },
  { icon: Users, title: "New employee added", detail: "Sarah Namusoke · Cashier", time: "2 hours ago", tone: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30" },
]

const categories = [
  { name: "Building Materials & Cement", count: "142 Items", icon: Boxes, bg: "from-amber-500/20 to-orange-500/20 text-orange-600", image: "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400&auto=format&fit=crop&q=80" },
  { name: "Power & Hand Tools", count: "98 Items", icon: Wrench, bg: "from-sky-500/20 to-blue-500/20 text-sky-600", image: "https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=400&auto=format&fit=crop&q=80" },
  { name: "Electrical & Lighting", count: "76 Items", icon: Zap, bg: "from-yellow-500/20 to-amber-500/20 text-amber-600", image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&auto=format&fit=crop&q=80" },
  { name: "Plumbing & Fixtures", count: "115 Items", icon: Droplet, bg: "from-cyan-500/20 to-teal-500/20 text-teal-600", image: "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=400&auto=format&fit=crop&q=80" },
  { name: "Paints & Chemicals", count: "64 Items", icon: Paintbrush, bg: "from-rose-500/20 to-orange-500/20 text-rose-600", image: "https://images.unsplash.com/photo-1562259949-e8e7689d7828?w=400&auto=format&fit=crop&q=80" },
  { name: "Safety & PPE Gear", count: "52 Items", icon: ShieldCheck, bg: "from-emerald-500/20 to-teal-500/20 text-emerald-600", image: "https://images.unsplash.com/photo-1618090584126-129cd173f248?w=400&auto=format&fit=crop&q=80" },
]

const featuredProducts = [
  { name: "Portland Cement 50kg Bag", category: "Building Supplies", price: "UGX 38,500", rating: "4.9", badge: "BEST SELLER", image: "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=300&auto=format&fit=crop&q=80" },
  { name: "DeWalt 20V MAX Cordless Drill Kit", category: "Power Tools", price: "UGX 680,000", rating: "4.8", badge: "PRO CHOICE", image: "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=300&auto=format&fit=crop&q=80" },
  { name: "Crown Weather Guard Paint 20L", category: "Paints", price: "UGX 245,000", rating: "4.7", badge: "POPULAR", image: "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=300&auto=format&fit=crop&q=80" },
  { name: "Heavy Duty High-Tensile Steel Rebar 12mm", category: "Structural", price: "UGX 42,000", rating: "5.0", badge: "TRADE ITEM", image: "https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=300&auto=format&fit=crop&q=80" },
]

export default function Page() {
  const [range, setRange] = useState("This month")

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8">
      {/* Hero Banner Header */}
      <section className="relative overflow-hidden rounded-3xl bg-slate-900 text-white border border-slate-800 shadow-2xl p-6 sm:p-8 lg:p-10">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 h-96 w-96 rounded-full bg-gradient-to-br from-orange-600/30 via-amber-500/20 to-transparent blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-10 h-64 w-64 rounded-full bg-blue-600/20 blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-orange-500/15 border border-orange-500/30 px-3.5 py-1 text-xs font-bold text-orange-400 backdrop-blur-md">
              <Sparkles className="h-3.5 w-3.5 text-amber-400" />
              <span>Sunday, September 6, 2026 · Main Industrial Branch</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-white leading-tight">
              Good morning, <span className="bg-gradient-to-r from-orange-400 via-amber-300 to-orange-200 bg-clip-text text-transparent">Jonathan</span>
            </h1>
            <p className="text-sm sm:text-base text-slate-300 font-medium leading-relaxed">
              Here is real-time inventory, procurement, and POS transaction performance across Main Branch today.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Button asChild variant="outline" className="bg-slate-800/80 border-slate-700 text-white hover:bg-slate-700 hover:text-white rounded-xl shadow-md font-bold text-xs sm:text-sm">
              <Link href="/purchase-orders"><ShoppingCart className="mr-2 h-4 w-4 text-orange-400" />View orders</Link>
            </Button>
            <Button asChild className="bg-gradient-to-r from-orange-600 to-amber-600 text-white hover:from-orange-700 hover:to-amber-700 rounded-xl shadow-lg shadow-orange-600/30 font-bold text-xs sm:text-sm">
              <Link href="/sales"><Plus className="mr-2 h-4 w-4" />New sale</Link>
            </Button>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-semibold text-slate-300">
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>POS Till #1: Online</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-amber-400" />
            <span>Stock Health: 96% OK</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-sky-400" />
            <span>3 Deliveries Scheduled</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-purple-400" />
            <span>Shift: Day Cashiers</span>
          </div>
        </div>
      </section>

      {/* Core Operational Stat Cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Revenue this month" value="UGX 48.2M" icon={<CircleDollarSign className="h-5 w-5" />} trend="up" trendValue="12.5%" description="from last month" />
        <StatCard title="Sales today" value="UGX 3.84M" icon={<Banknote className="h-5 w-5" />} trend="up" trendValue="8.2%" description="from yesterday" />
        <StatCard title="Low stock items" value="18" icon={<Boxes className="h-5 w-5" />} trend="down" trendValue="4" description="items since yesterday" />
        <StatCard title="Open purchase orders" value="12" icon={<Package className="h-5 w-5" />} trend="neutral" trendValue="3" description="awaiting action" />
      </section>

      {/* Building & DIY Categories Showcase */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">Shop by Department</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Explore hardware, building supplies & heavy equipment categories</p>
          </div>
          <Link href="/categories" className="text-xs font-bold text-orange-600 dark:text-orange-400 hover:underline flex items-center gap-1">
            All Categories <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {categories.map(({ name, count, icon: Icon, bg, image }) => (
            <Link
              key={name}
              href="/categories"
              className="group relative overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-orange-500/40 flex flex-col justify-between h-40"
            >
              <div className="absolute inset-0 opacity-10 group-hover:opacity-20 transition-opacity bg-cover bg-center" style={{ backgroundImage: `url(${image})` }} />
              <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${bg} flex items-center justify-center shadow-sm shrink-0 z-10 transition-transform group-hover:scale-110`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="z-10 mt-3">
                <h3 className="font-extrabold text-xs text-slate-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors line-clamp-1">{name}</h3>
                <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">{count}</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Featured / Best Seller Hardware Showcase Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-orange-600 animate-pulse" />
            <h2 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">Best Selling Supplies</h2>
          </div>
          <Link href="/products" className="text-xs font-bold text-orange-600 dark:text-orange-400 hover:underline flex items-center gap-1">
            View Catalogue <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {featuredProducts.map((prod) => (
            <div
              key={prod.name}
              className="group relative rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between"
            >
              <div className="relative aspect-4/3 overflow-hidden rounded-xl bg-slate-100 dark:bg-slate-800 mb-3">
                <img
                  src={prod.image}
                  alt={prod.name}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
                <span className="absolute top-2 left-2 bg-gradient-to-r from-orange-600 to-amber-600 text-white font-extrabold text-[10px] px-2 py-0.5 rounded-md shadow-md">
                  {prod.badge}
                </span>
                <div className="absolute top-2 right-2 bg-slate-900/80 backdrop-blur-md text-amber-400 text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1">
                  <Star className="h-3 w-3 fill-amber-400" /> {prod.rating}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-orange-600 dark:text-orange-400">{prod.category}</span>
                <h3 className="font-extrabold text-sm text-slate-900 dark:text-white line-clamp-1 group-hover:text-orange-600 transition-colors">{prod.name}</h3>
              </div>

              <div className="mt-4 flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800">
                <span className="text-base font-black text-slate-900 dark:text-white">{prod.price}</span>
                <Button size="xs" className="rounded-lg font-bold bg-slate-900 text-white hover:bg-orange-600 transition-colors">
                  Add Item
                </Button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Main Charts & Activity Grid */}
      <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
          <CardHeader className="flex flex-row items-center justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
            <div>
              <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Revenue overview</CardTitle>
              <p className="mt-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">Sales performance for the current period</p>
            </div>
            <div className="flex rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800 p-1 text-xs font-semibold">
              {["This month", "Last month"].map((item) => (
                <button
                  key={item}
                  onClick={() => setRange(item)}
                  className={`rounded-lg px-3 py-1.5 transition-all duration-200 ${
                    range === item ? "bg-orange-600 text-white font-bold shadow-md" : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex items-end gap-3 mb-6">
              <span className="text-4xl font-black text-slate-900 dark:text-white tracking-tight">UGX 48.2M</span>
              <span className="mb-1 text-xs font-extrabold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">+12.5% vs prev</span>
            </div>
            <div className="mt-6 flex h-52 items-end gap-2 sm:gap-4 pt-4 px-2">
              {[42, 58, 48, 74, 62, 86, 68, 92, 78, 100, 82, 94].map((height, index) => (
                <div key={index} className="group flex h-full flex-1 flex-col justify-end gap-2">
                  <div className="relative w-full rounded-t-lg bg-orange-500/15 transition-all duration-300 group-hover:bg-orange-500/30" style={{ height: `${height}%` }}>
                    <div className="absolute inset-x-0 bottom-0 rounded-t-lg bg-gradient-to-t from-orange-600 to-amber-500 group-hover:from-orange-700 group-hover:to-amber-600 transition-colors" style={{ height: `${Math.max(20, height - 18)}%` }} />
                  </div>
                  <span className="text-center text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">{["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][index]}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
          <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
            <div>
              <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Recent activity</CardTitle>
              <p className="mt-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">Latest updates from your team</p>
            </div>
            <div className="p-2 rounded-xl bg-orange-500/10 text-orange-600">
              <Clock3 className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-5">
            {activity.map(({ icon: Icon, title, detail, time, tone }) => (
              <div key={title} className="flex items-center gap-3.5 p-2.5 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl font-bold shadow-2xs ${tone}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-slate-900 dark:text-white">{title}</p>
                  <p className="truncate text-xs text-slate-500 font-medium">{detail}</p>
                </div>
                <span className="whitespace-nowrap text-[11px] font-semibold text-slate-400">{time}</span>
              </div>
            ))}
            <Button asChild variant="ghost" className="w-full justify-between text-orange-600 hover:text-orange-700 dark:text-orange-400 font-bold rounded-xl pt-2">
              <Link href="/ledger">View all activity <ArrowUpRight className="h-4 w-4" /></Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Orders & Action Items Section */}
      <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
          <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
            <div>
              <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Recent purchase orders</CardTitle>
              <p className="mt-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">Track procurement across your branch</p>
            </div>
            <Button asChild variant="ghost" size="sm" className="text-xs font-bold text-orange-600">
              <Link href="/purchase-orders">View all <ArrowUpRight className="ml-1 h-4 w-4" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 dark:border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <tr>
                    <th className="pb-3">Order</th>
                    <th className="pb-3">Supplier</th>
                    <th className="pb-3">Amount</th>
                    <th className="pb-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-orange-500/5 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 font-bold text-slate-900 dark:text-white">
                        {order.id}
                        <div className="text-xs font-normal text-slate-500">{order.date}</div>
                      </td>
                      <td className="py-3.5 font-medium text-slate-700 dark:text-slate-300">{order.supplier}</td>
                      <td className="py-3.5 font-extrabold text-slate-900 dark:text-white">{order.amount}</td>
                      <td className="py-3.5"><StatusBadge status={order.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-slate-200/90 dark:border-slate-800 shadow-md">
          <CardHeader className="pb-4 border-b border-slate-100 dark:border-slate-800">
            <CardTitle className="text-lg font-extrabold text-slate-900 dark:text-white">Needs attention</CardTitle>
            <p className="mt-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">Items that may need your action</p>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            <Link href="/products" className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 transition-all hover:border-orange-500/50 hover:bg-orange-500/5 hover:shadow-md">
              <span>
                <span className="block text-sm font-bold text-slate-900 dark:text-white">Low stock products</span>
                <span className="text-xs font-medium text-slate-500">18 products below reorder level</span>
              </span>
              <span className="rounded-full bg-amber-500/15 border border-amber-500/30 px-3 py-1 text-xs font-extrabold text-amber-700 dark:text-amber-400">18</span>
            </Link>

            <Link href="/purchase-orders" className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 transition-all hover:border-orange-500/50 hover:bg-orange-500/5 hover:shadow-md">
              <span>
                <span className="block text-sm font-bold text-slate-900 dark:text-white">Orders awaiting approval</span>
                <span className="text-xs font-medium text-slate-500">Requires procurement review</span>
              </span>
              <span className="rounded-full bg-sky-500/15 border border-sky-500/30 px-3 py-1 text-xs font-extrabold text-sky-700 dark:text-sky-400">3</span>
            </Link>

            <Link href="/payroll" className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 transition-all hover:border-orange-500/50 hover:bg-orange-500/5 hover:shadow-md">
              <span>
                <span className="block text-sm font-bold text-slate-900 dark:text-white">Payroll draft</span>
                <span className="text-xs font-medium text-slate-500">September payroll is ready</span>
              </span>
              <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1 text-xs font-extrabold text-emerald-700 dark:text-emerald-400">Ready</span>
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
