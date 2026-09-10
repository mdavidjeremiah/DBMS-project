"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AlertCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { API_URL, setAccessToken } from "@/lib/api"

export default function SignInPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setLoading(true); setError(null)
    try {
      const body = new URLSearchParams({ username: email, password })
      const response = await fetch(`${API_URL}/login`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? "Unable to sign in")
      setAccessToken(data.access_token); router.push("/"); router.refresh()
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to sign in") } finally { setLoading(false) }
  }

  return <div className="flex min-h-screen items-center justify-center bg-slate-900 p-4"><div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl dark:bg-slate-800"><div className="mb-6 flex items-center justify-center gap-3"><div className="rounded-xl bg-orange-600 p-3 font-bold text-white">HW</div><span className="text-2xl font-black">Hardware World</span></div><h1 className="text-2xl font-bold">Sign in</h1><p className="mt-1 text-sm text-slate-500">Connect to the FastAPI/MySQL operations system.</p>{error && <div className="mt-4 flex gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700"><AlertCircle className="h-4 w-4" />{error}</div>}<form onSubmit={submit} className="mt-6 grid gap-4"><Label>Email<Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></Label><Label>Password<Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></Label><Button disabled={loading}>{loading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Signing in...</> : "Sign in"}</Button></form><p className="mt-6 text-center text-sm text-slate-500">Need an account? <Link className="text-orange-600" href="/auth/sign-up">Register through the backend</Link></p></div></div>
}
