export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
export const TOKEN_COOKIE = "hw_access_token"

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  if (typeof window !== "undefined") {
    const token = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${TOKEN_COOKIE}=`))?.split("=")[1]
    if (token) headers.set("Authorization", `Bearer ${decodeURIComponent(token)}`)
  }
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.detail ?? `API request failed (${response.status})`)
  return body as T
}

export async function browserApiRequest<T>(path: string, init: RequestInit = {}) {
  return apiRequest<T>(path, init)
}

export function setAccessToken(token: string) {
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; Path=/; SameSite=Lax; Max-Age=3600`
}

export function clearAccessToken() {
  document.cookie = `${TOKEN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`
}
