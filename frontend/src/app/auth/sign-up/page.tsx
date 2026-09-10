"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { API_URL } from "@/lib/api"

export default function SignUpPage() {
  const router = useRouter(); const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(false)
  async function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); setLoading(true); setError(null); const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries()); try { const response = await fetch(`${API_URL}/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, salary: Number(payload.salary), departmentid: Number(payload.departmentid), branchid: Number(payload.branchid), roletype: "HR Staff" }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Registration failed"); router.push("/auth/sign-in") } catch (err) { setError(err instanceof Error ? err.message : "Registration failed") } finally { setLoading(false) } }
  return <div className="flex min-h-screen items-center justify-center bg-slate-900 p-4"><form onSubmit={submit} className="grid w-full max-w-lg gap-4 rounded-2xl bg-white p-8 dark:bg-slate-800"><h1 className="text-2xl font-black">Register backend user</h1><p className="text-sm text-slate-500">This creates an employee record in MySQL.</p>{error && <div className="flex gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700"><AlertCircle className="h-4 w-4" />{error}</div>}<Label>Name<Input name="name" required /></Label><Label>NIN<Input name="nin" required /></Label><Label>Email<Input name="email" type="email" required /></Label><Label>Password<Input name="password" type="password" minLength={8} required /></Label><Label>Salary<Input name="salary" type="number" min="0" required /></Label><Label>Department ID<Input name="departmentid" type="number" min="1" required /></Label><Label>Branch ID<Input name="branchid" type="number" min="1" required /></Label><Button disabled={loading}>{loading ? "Registering..." : "Register"}</Button><Link className="text-center text-sm text-orange-600" href="/auth/sign-in">Back to sign in</Link></form></div>
}
