import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"
import { ShieldCheck, Truck, Clock, RefreshCw, Mail, Phone, MapPin, Heart } from "lucide-react"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen w-full md:grid-cols-[240px_1fr] lg:grid-cols-[270px_1fr] bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      <div className="flex flex-col flex-1 h-screen overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-slate-50/80 dark:bg-slate-950/80 flex flex-col justify-between">
          <div className="max-w-[1600px] w-full mx-auto space-y-8">
            {children}
          </div>

          {/* Footer Section */}
          <footer className="mt-16 pt-8 border-t border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 text-sm max-w-[1600px] w-full mx-auto">
            {/* Trust Badges */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white shadow-lg mb-10">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-orange-500/20 text-orange-400 flex items-center justify-center shrink-0 border border-orange-500/30">
                  <Truck className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-bold text-xs text-white uppercase tracking-wider">Free Delivery</h4>
                  <p className="text-[11px] text-slate-300">Orders over UGX 500k</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 border border-amber-500/30">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-bold text-xs text-white uppercase tracking-wider">100% Genuine</h4>
                  <p className="text-[11px] text-slate-300">Certified supplier stock</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-sky-500/20 text-sky-400 flex items-center justify-center shrink-0 border border-sky-500/30">
                  <RefreshCw className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-bold text-xs text-white uppercase tracking-wider">Easy Returns</h4>
                  <p className="text-[11px] text-slate-300">30-day money back guarantee</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-bold text-xs text-white uppercase tracking-wider">Trade Support</h4>
                  <p className="text-[11px] text-slate-300">24/7 dedicated assistance</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-8 border-b border-slate-200 dark:border-slate-800">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-lg bg-orange-600 flex items-center justify-center text-white font-bold text-xs">HW</div>
                  <span className="font-extrabold text-slate-900 dark:text-white tracking-tight">HARDWARE WORLD</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  Uganda&apos;s leading hardware, building materials, power tools, and DIY supplies retailer. Serving contractors and homeowners since 2010.
                </p>
              </div>

              <div>
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-900 dark:text-white mb-3">Quick Navigation</h4>
                <ul className="space-y-2 text-xs">
                  <li><a href="/products" className="hover:text-orange-600 transition-colors">Products Catalogue</a></li>
                  <li><a href="/categories" className="hover:text-orange-600 transition-colors">Building Categories</a></li>
                  <li><a href="/sales" className="hover:text-orange-600 transition-colors">POS & Retail Sales</a></li>
                  <li><a href="/purchase-orders" className="hover:text-orange-600 transition-colors">Purchase Orders</a></li>
                </ul>
              </div>

              <div>
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-900 dark:text-white mb-3">Main Branch</h4>
                <ul className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                  <li className="flex items-center gap-2"><MapPin className="h-3.5 w-3.5 text-orange-600 shrink-0" /> Plot 42 Jinja Road, Kampala</li>
                  <li className="flex items-center gap-2"><Phone className="h-3.5 w-3.5 text-orange-600 shrink-0" /> +256 414 500 100</li>
                  <li className="flex items-center gap-2"><Mail className="h-3.5 w-3.5 text-orange-600 shrink-0" /> sales@hardwareworld.co.ug</li>
                </ul>
              </div>

              <div>
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-900 dark:text-white mb-3">Newsletter & Offers</h4>
                <p className="text-xs text-slate-500 mb-3">Subscribe for weekly trade discounts and restock alerts.</p>
                <div className="flex gap-2">
                  <input type="email" placeholder="Enter your email" className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-xs px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-orange-500" />
                  <button className="bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs px-3 py-2 rounded-lg transition-colors shrink-0">Join</button>
                </div>
              </div>
            </div>

            <div className="py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
              <p>© 2026 Hardware World Ltd. All rights reserved.</p>
              <div className="flex items-center gap-4">
                <span className="hover:text-slate-800 cursor-pointer">Privacy Policy</span>
                <span className="hover:text-slate-800 cursor-pointer">Terms of Supply</span>
                <span className="hover:text-slate-800 cursor-pointer">System Status</span>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
