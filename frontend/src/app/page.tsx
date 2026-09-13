import Link from "next/link"
import { redirect } from "next/navigation"
import { 
  ArrowUpRight, 
  Boxes, 
  Package, 
  ShoppingCart, 
  Users, 
  Shield, 
  UserCheck, 
  Building2,
  Banknote,
  Briefcase,
  BookOpen,
  Plus
} from "lucide-react"
import { DataNotice } from "@/components/shared/DataNotice"
import { ContinuousStatGraph } from "@/components/shared/ContinuousStatGraph"
import { getDashboard } from "@/lib/queries"
import { getServerSession } from "@/lib/auth"
import { Button } from "@/components/ui/button"

const money = (value: number) => `UGX ${value.toLocaleString()}`

export default async function DashboardPage() {
  const session = await getServerSession()
  if (!session.user) {
    redirect("/auth/sign-in")
  }

  const user = session.user
  const dashboard = await getDashboard()
  const latestSales = dashboard.sales.data.slice(0, 5)
  const latestOrders = dashboard.orders.data.slice(0, 5)
  const errors = [dashboard.sales.error, dashboard.orders.error].filter(Boolean).join("; ") || null
  const rlsBlocked = dashboard.sales.rlsBlocked || dashboard.orders.rlsBlocked

  const isAdmin = user.roletype === "Admin"
  const userDept = user.department_name ?? (isAdmin ? "Administration" : "General Staff")

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
      {/* Dynamic Role & Department Hero Header */}
      <header className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-stone-900 p-7 text-white shadow-2xl">
        <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 rounded-full bg-orange-500/20 px-3 py-1 text-xs font-bold text-orange-400 border border-orange-500/30">
                {isAdmin ? <Shield className="h-3.5 w-3.5" /> : <UserCheck className="h-3.5 w-3.5" />}
                {isAdmin ? "Admin Oversight Authority" : `${user.roletype} Scope`}
              </span>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-300">
                {userDept}
              </span>
            </div>
            <h1 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl text-white">
              Welcome back, {user.name}
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              {isAdmin
                ? "Full cross-departmental RBAC & ABAC administrative oversight."
                : `Assigned departmental workspace: ${userDept}.`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isAdmin && (
              <Link href="/employees">
                <Button className="rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 text-white font-bold hover:from-orange-500 hover:to-amber-500 shadow-lg shadow-orange-600/30">
                  <Plus className="mr-1.5 h-4 w-4" /> Provision New User
                </Button>
              </Link>
            )}
            {userDept === "Sales & POS" && (
              <Link href="/sales">
                <Button className="rounded-xl bg-orange-600 text-white font-bold hover:bg-orange-500">
                  <Banknote className="mr-1.5 h-4 w-4" /> Open POS Register
                </Button>
              </Link>
            )}
            {userDept === "Procurement & Inventory" && (
              <Link href="/purchase-orders">
                <Button className="rounded-xl bg-orange-600 text-white font-bold hover:bg-orange-500">
                  <ShoppingCart className="mr-1.5 h-4 w-4" /> Create Purchase Order
                </Button>
              </Link>
            )}
          </div>
        </div>
      </header>

      <DataNotice error={errors} rlsBlocked={rlsBlocked} />

      {/* Continuous Plotted Statistical Graph Component */}
      <section>
        <ContinuousStatGraph initialData={dashboard.graphData} />
      </section>

      {/* KPI Cards Strip */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Sales Today"
          value={money(dashboard.stats.salesToday)}
          icon={<ArrowUpRight className="h-5 w-5" />}
          subtext="Processed in active branch"
        />
        <Metric
          label="Transactions Today"
          value={String(dashboard.stats.salesCount)}
          icon={<ShoppingCart className="h-5 w-5" />}
          subtext="Customer checkout entries"
        />
        <Metric
          label="Pending Purchase Orders"
          value={String(dashboard.stats.pendingOrders)}
          icon={<Package className="h-5 w-5" />}
          subtext="Awaiting officer sign-off"
        />
        <Metric
          label="Total Staff in System"
          value={String(dashboard.stats.employeeCount)}
          icon={<Users className="h-5 w-5" />}
          subtext="Across all 6 departments"
        />
      </section>

      {/* Admin Cross-Department Summary Cards (Only visible to Admin) */}
      {isAdmin && (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black text-slate-900 dark:text-white">Departmental Access Control Hub</h2>
              <p className="text-xs text-slate-500">All 6 departments managed under ABAC policies</p>
            </div>
            <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
              ABAC Enforced
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <DeptCard
              name="Sales & POS"
              role="Cashier"
              description="Manages point-of-sale checkout, customer receipts, and daily sales intake."
              href="/sales"
              count="Cashier Portal"
            />
            <DeptCard
              name="Procurement & Inventory"
              role="Procurement Officer"
              description="Issues supplier purchase orders, product restocking, and vendor catalogs."
              href="/purchase-orders"
              count="Inventory Control"
            />
            <DeptCard
              name="Finance & Accounting"
              role="Accountant"
              description="Maintains double-entry ledgers, payroll debit entries, and transaction journals."
              href="/ledger"
              count="Financial Ledger"
            />
            <DeptCard
              name="Human Resources"
              role="HR Staff"
              description="Oversees employee staffing records, salary adjustments, and monthly payroll cycles."
              href="/employees"
              count="Staff & Payroll"
            />
            <DeptCard
              name="Operations & Branch"
              role="Branch Manager"
              description="Branch performance metrics, localized staff tracking, and multi-dept oversight."
              href="/products"
              count="Store Operations"
            />
            <DeptCard
              name="Administration"
              role="Admin (Akena)"
              description="Master system administration, employee account provisioning, and access policies."
              href="/settings"
              count="Full Clearance"
            />
          </div>
        </section>
      )}

      {/* Live Business Lists */}
      <section className="grid gap-6 xl:grid-cols-2">
        <LiveList title="Recent Point-of-Sale Transactions" href="/sales">
          {latestSales.length > 0 ? (
            latestSales.map((sale) => (
              <li key={sale.saleid} className="flex items-center justify-between border-b border-slate-100 py-3.5 last:border-0 dark:border-slate-800">
                <span>
                  <span className="block font-bold text-slate-900 dark:text-white">Sale #{sale.saleid}</span>
                  <span className="text-xs text-slate-500">
                    {sale.customer_name} · Cashier: {sale.cashier_name}
                  </span>
                </span>
                <strong className="text-sm font-extrabold text-orange-600 dark:text-orange-400">
                  {money(sale.totalamount)}
                </strong>
              </li>
            ))
          ) : (
            <p className="py-4 text-center text-xs text-slate-400">No recent sales found.</p>
          )}
        </LiveList>

        <LiveList title="Recent Procurement Purchase Orders" href="/purchase-orders">
          {latestOrders.length > 0 ? (
            latestOrders.map((order) => (
              <li key={order.po_id} className="flex items-center justify-between border-b border-slate-100 py-3.5 last:border-0 dark:border-slate-800">
                <span>
                  <span className="block font-bold text-slate-900 dark:text-white">PO #{order.po_id}</span>
                  <span className="text-xs text-slate-500">
                    {order.supplier_name} · Officer: {order.officer_name}
                  </span>
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {order.status}
                </span>
              </li>
            ))
          ) : (
            <p className="py-4 text-center text-xs text-slate-400">No recent purchase orders found.</p>
          )}
        </LiveList>
      </section>

      {/* Footer Info */}
      <div className="flex items-center gap-2 text-xs text-slate-500 pb-4">
        <Boxes className="h-4 w-4 text-orange-600" />
        <span>{dashboard.stats.productCount} active products in live database inventory.</span>
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  icon,
  subtext
}: {
  label: string
  value: string
  icon: React.ReactNode
  subtext?: string
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between text-orange-600 dark:text-orange-400">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10">
          {icon}
        </div>
      </div>
      <strong className="text-2xl font-black text-slate-900 dark:text-white">{value}</strong>
      {subtext && <p className="mt-1 text-[11px] text-slate-400">{subtext}</p>}
    </div>
  )
}

function DeptCard({
  name,
  role,
  description,
  href,
  count
}: {
  name: string
  role: string
  description: string
  href: string
  count: string
}) {
  return (
    <Link
      href={href}
      className="group rounded-2xl border border-slate-100 bg-slate-50/70 p-4 transition-all duration-200 hover:border-orange-500/40 hover:bg-orange-500/5 dark:border-slate-800/80 dark:bg-slate-950/40"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-sm text-slate-900 dark:text-white group-hover:text-orange-600 transition-colors">
          {name}
        </h3>
        <span className="text-[10px] font-bold text-orange-500 uppercase tracking-wider">
          {count}
        </span>
      </div>
      <span className="mt-0.5 block text-[11px] font-semibold text-slate-500 dark:text-slate-400">
        Role: {role}
      </span>
      <p className="mt-2 text-xs text-slate-500 leading-snug line-clamp-2">
        {description}
      </p>
    </Link>
  )
}

function LiveList({
  title,
  href,
  children
}: {
  title: string
  href: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-black text-slate-900 dark:text-white">{title}</h2>
        <Link href={href} className="text-xs font-bold text-orange-600 hover:underline">
          View all &rarr;
        </Link>
      </div>
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">{children}</ul>
    </div>
  )
}