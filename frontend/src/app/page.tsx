import Link from "next/link"
import { ArrowUpRight, Boxes, Package, ShoppingCart, Users } from "lucide-react"
import { DataNotice } from "@/components/shared/DataNotice"
import { getDashboard } from "@/lib/queries"

const money = (value: number) => `UGX ${value.toLocaleString()}`

export default async function DashboardPage() {
  const dashboard = await getDashboard()
  const latestSales = dashboard.sales.data.slice(0, 5)
  const latestOrders = dashboard.orders.data.slice(0, 5)
  const errors = [dashboard.sales.error, dashboard.orders.error].filter(Boolean).join("; ") || null
  const rlsBlocked = dashboard.sales.rlsBlocked || dashboard.orders.rlsBlocked
  return <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
    <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-white shadow-xl"><p className="text-xs font-bold uppercase tracking-wider text-orange-400">Operations dashboard</p><h1 className="mt-2 text-3xl font-black">Live business overview</h1><p className="mt-2 text-sm text-slate-300">These figures are calculated from the current MySQL records.</p></header>
    <DataNotice error={errors} rlsBlocked={rlsBlocked} />
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Sales today" value={money(dashboard.stats.salesToday)} icon={<ArrowUpRight />} />
      <Metric label="Sales count today" value={String(dashboard.stats.salesCount)} icon={<ShoppingCart />} />
      <Metric label="Pending orders" value={String(dashboard.stats.pendingOrders)} icon={<Package />} />
      <Metric label="Employees" value={String(dashboard.stats.employeeCount)} icon={<Users />} />
    </section>
    <section className="grid gap-6 xl:grid-cols-2">
      <LiveList title="Recent sales" href="/sales">{latestSales.map((sale) => <li key={sale.saleid} className="flex items-center justify-between border-b py-3 last:border-0"><span><span className="block font-semibold">Sale #{sale.saleid}</span><span className="text-xs text-slate-500">{sale.customer_name} · {sale.cashier_name}</span></span><strong>{money(sale.totalamount)}</strong></li>)}</LiveList>
      <LiveList title="Recent purchase orders" href="/purchase-orders">{latestOrders.map((order) => <li key={order.po_id} className="flex items-center justify-between border-b py-3 last:border-0"><span><span className="block font-semibold">Order #{order.po_id}</span><span className="text-xs text-slate-500">{order.supplier_name} · {order.officer_name}</span></span><strong>{order.status}</strong></li>)}</LiveList>
    </section>
    <div className="flex items-center gap-2 text-sm text-slate-500"><Boxes className="h-4 w-4" /> <span>{dashboard.stats.productCount} products currently in the live catalogue.</span></div>
  </div>
}

function Metric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) { return <div className="rounded-2xl border bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="mb-4 flex items-center justify-between text-orange-600"><span className="text-sm font-semibold text-slate-500">{label}</span>{icon}</div><strong className="text-2xl font-black text-slate-900 dark:text-white">{value}</strong></div> }
function LiveList({ title, href, children }: { title: string; href: string; children: React.ReactNode }) { return <div className="rounded-2xl border bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="mb-3 flex items-center justify-between"><h2 className="font-black text-slate-900 dark:text-white">{title}</h2><Link href={href} className="text-xs font-bold text-orange-600">View all</Link></div><ul>{children}</ul></div> }