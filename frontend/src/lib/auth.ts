import { serverApiRequest } from "@/lib/api-server"

export async function getServerSession() {
  try { return { user: await serverApiRequest<{ employeeid: number; name: string; email: string; roletype: string; branchid: number }>("/users/me") } }
  catch { return { user: null } }
}

export async function signOutServer() {
  return undefined
}
