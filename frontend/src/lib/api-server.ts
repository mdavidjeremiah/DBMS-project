import { cookies } from "next/headers"
import { API_URL, TOKEN_COOKIE } from "@/lib/api"

export async function serverApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  const token = (await cookies()).get(TOKEN_COOKIE)?.value
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.detail ?? `API request failed (${response.status})`)
  return body as T
}
