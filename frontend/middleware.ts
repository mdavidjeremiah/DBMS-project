import { NextRequest, NextResponse } from "next/server"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
const PUBLIC_ROUTES = ["/auth"]

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) return NextResponse.next()
  const token = request.cookies.get("hw_access_token")?.value
  if (!token) return NextResponse.redirect(new URL("/auth/sign-in", request.url))
  try {
    const response = await fetch(`${API_URL}/users/me`, { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) return NextResponse.redirect(new URL("/auth/sign-in", request.url))
  } catch { return NextResponse.redirect(new URL("/auth/sign-in", request.url)) }
  return NextResponse.next()
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|svg|ico|webp|woff2?|ttf|otf|eot|css|js)$).*)"] }
