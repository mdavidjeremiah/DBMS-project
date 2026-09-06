import {
  DollarSign,
  ShoppingCart,
  Users,
  Package,
  ArrowRight,
} from "lucide-react"
import Link from "next/link"
import { StatCard } from "@/components/shared/StatCard"
import { RlsNotice, ErrorNotice } from "@/components/shared/RlsNotice"
import { Button } from "@/components/ui/button"
import {
  getDashboardStats,
  getRecentSales,
  getPendingPurchaseOrders,
} from "@/lib/queries"

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-UG", {
    style: "currency",
    currency: "UGX",
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  })
}

export default async function DashboardPage() {
  const [{ stats, rlsBlocked, error }, recentSales, pendingPOs] =
    await Promise.all([
      getDashboardStats(),
      getRecentSales(5),
      getPendingPurchaseOrders(5),
    ])

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome back
        </h1>
        <p className="text-muted-foreground">
          Here&apos;s what&apos;s happening across Hardware World today.
        </p>
      </div>

      {error && <ErrorNotice message={error} />}
      {rlsBlocked && !error && <RlsNotice />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Sales Today"
          value={formatCurrency(stats.totalSalesToday)}
          description={`${stats.salesCountToday} transaction${stats.salesCountToday === 1 ? "" : "s"}`}
          icon={<DollarSign className="h-4 w-4" />}
        />
        <StatCard
          title="Pending POs"
          value={stats.pendingPurchaseOrders}
          description="awaiting approval"
          icon={<ShoppingCart className="h-4 w-4 text-yellow-500" />}
        />
        <StatCard
          title="Active Employees"
          value={stats.activeEmployees}
          description="across all branches"
          icon={<Users className="h-4 w-4" />}
        />
        <StatCard
          title="Total Products"
          value={stats.totalProducts}
          description="in catalogue"
          icon={<Package className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border bg-card p-4">
          <div className="flex items-center justify-between pb-3">
            <h2 className="font-medium">Recent Sales</h2>
            <Button variant="ghost" size="sm" render={<Link href="/sales" />}>
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
          {recentSales.data.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {recentSales.rlsBlocked
                ? "No sales visible yet -- RLS has no read policy configured."
                : "No sales recorded yet."}
            </p>
          ) : (
            <div className="divide-y">
              {recentSales.data.map((sale) => (
                <div
                  key={sale.saleid}
                  className="flex items-center justify-between py-3 text-sm"
                >
                  <div>
                    <p className="font-medium">
                      {sale.customer_name ?? "Walk-in customer"}
                    </p>
                    <p className="text-muted-foreground">
                      {sale.cashier_name ?? "Unknown cashier"} ·{" "}
                      {formatDate(sale.saledate)}
                    </p>
                  </div>
                  <span className="font-medium">
                    {formatCurrency(sale.totalamount)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border bg-card p-4">
          <div className="flex items-center justify-between pb-3">
            <h2 className="font-medium">Pending Purchase Orders</h2>
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/purchase-orders" />}
            >
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
          {pendingPOs.data.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {pendingPOs.rlsBlocked
                ? "No orders visible yet -- RLS has no read policy configured."
                : "Nothing pending approval."}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {pendingPOs.data.map((po) => (
                <div
                  key={po.po_id}
                  className="rounded-lg bg-muted/50 px-3 py-2 text-sm"
                >
                  <p className="font-medium">PO-{po.po_id}</p>
                  <p className="text-muted-foreground">
                    {po.supplier_name} · {formatDate(po.orderdate)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}