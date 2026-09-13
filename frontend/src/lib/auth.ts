import { serverApiRequest } from "@/lib/api-server"

export type UserSession = {
  employeeid: number
  name: string
  email: string
  roletype: string
  departmentid?: number | null
  department_name?: string | null
  branchid?: number | null
  branch_name?: string | null
}

export async function getServerSession(): Promise<{ user: UserSession | null }> {
  try {
    const user = await serverApiRequest<UserSession>("/users/me")
    return { user }
  } catch {
    return { user: null }
  }
}

export async function signOutServer() {
  return undefined
}
