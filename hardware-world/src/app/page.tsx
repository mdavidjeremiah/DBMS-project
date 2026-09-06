import Link from "next/link"
import { ArrowRight, Package, ShoppingCart, Users, Wallet } from "lucide-react"
import { StatCard } from "@/components/shared/StatCard"
import { DataNotice } from "@/components/shared/DataNotice"
import { Button } from "@/components/ui/button"
import { getDashboard } from "@/lib/queries"

const money = (value: number) => new Intl.NumberFormat("en-UG", { style: "currency", currency: "UGX", maximumFractionDigits: 0 }).format(value)

export default async function Page() {
  const { sales, orders, stats } = await getDashboard()
  return <div className="grid gap-6">
    <div><p className="text-sm font-medium text-primary">Hardware World</p><h1 className="text-2xl font-semibold tracking-tight">Operations overview</h1><p className="text-muted-foreground">Live figures from your Supabase database.</p></div>
    <DataNotice error={sales.error ?? orders.error} rlsBlocked={sales.rlsBlocked || orders.rlsBlocked} />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard title="Sales today" value={money(stats.salesToday)} description={`${stats.salesCount} transaction${stats.salesCount === 1 ? "" : "s"}`} icon={<Wallet />} />
      <StatCard title="Pending purchase orders" value={stats.pendingOrders} description="awaiting action" icon={<ShoppingCart className="text-amber-500" />} />
      <StatCard title="Employees" value={stats.employeeCount} description="staff records" icon={<Users />} />
      <StatCard title="Products" value={stats.productCount} description="in the catalogue" icon={<Package />} />
    </div>
    <div className="grid gap-4 lg:grid-cols-3">
      <section className="rounded-xl border bg-card p-4 lg:col-span-2"><div className="mb-3 flex items-center justify-between"><h2 className="font-medium">Recent sales</h2><Button variant="ghost" size="sm" render={<Link href="/sales" />}>Open POS <ArrowRight /></Button></div>{sales.data.length ? <div className="divide-y">{sales.data.slice(0, 5).map((sale) => <div className="flex items-center justify-between py-3 text-sm" key={sale.saleid}><div><p className="font-medium">{sale.customer_name}</p><p className="text-muted-foreground">{sale.cashier_name} · {new Date(sale.saledate).toLocaleString("en-UG")}</p></div><strong>{money(sale.totalamount)}</strong></div>)}</div> : <p className="py-8 text-center text-sm text-muted-foreground">No sales have been recorded yet.</p>}</section>
      <section className="rounded-xl border bg-card p-4"><div className="mb-3 flex items-center justify-between"><h2 className="font-medium">Pending orders</h2><Button variant="ghost" size="sm" render={<Link href="/purchase-orders" />}>View all <ArrowRight /></Button></div>{orders.data.filter((order) => order.status === "Pending").slice(0, 5).map((order) => <div key={order.po_id} className="mb-2 rounded-lg bg-muted/60 p-3 text-sm"><p className="font-medium">PO #{order.po_id}</p><p className="text-muted-foreground">{order.supplier_name}</p></div>) || <p className="py-8 text-center text-sm text-muted-foreground">No pending orders.</p>}</section>
    </div>
  </div>
}
