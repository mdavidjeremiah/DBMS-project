// Hand-authored to exactly match supabase/migrations/*.sql from Issue #2.
//
// This is a stand-in for `supabase gen types typescript --project-id <ref>`,
// which needs a Docker-capable machine or a logged-in CLI session to run.
// Once someone runs that command for real, it should produce something
// structurally equivalent to this file -- diff the two and replace this file
// if they've drifted, rather than hand-editing both forever.

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type RoleType =
  | "Cashier"
  | "Procurement Officer"
  | "Accountant"
  | "HR Staff"
  | "Branch Manager"

export type POStatus = "Pending" | "Approved" | "Received" | "Cancelled"

export type LedgerSourceType = "SALE" | "PAYROLL"

export interface Database {
  public: {
    Tables: {
      branch: {
        Row: {
          branchid: number
          branchname: string
          location: string
          contactnumber: string | null
          manageremployeeid: number | null
        }
        Insert: {
          branchid?: number
          branchname: string
          location: string
          contactnumber?: string | null
          manageremployeeid?: number | null
        }
        Update: Partial<Database["public"]["Tables"]["branch"]["Insert"]>
      }
      department: {
        Row: {
          departmentid: number
          departmentname: string
          branchid: number
        }
        Insert: {
          departmentid?: number
          departmentname: string
          branchid: number
        }
        Update: Partial<Database["public"]["Tables"]["department"]["Insert"]>
      }
      employee: {
        Row: {
          employeeid: number
          name: string
          nin: string
          phone: string | null
          datehired: string
          salary: number
          departmentid: number
          branchid: number
          supervisorid: number | null
          roletype: RoleType
        }
        Insert: {
          employeeid?: number
          name: string
          nin: string
          phone?: string | null
          datehired?: string
          salary: number
          departmentid: number
          branchid: number
          supervisorid?: number | null
          roletype: RoleType
        }
        Update: Partial<Database["public"]["Tables"]["employee"]["Insert"]>
      }
      cashier: {
        Row: { employeeid: number; pos_terminalid: string }
        Insert: { employeeid: number; pos_terminalid: string }
        Update: Partial<Database["public"]["Tables"]["cashier"]["Insert"]>
      }
      procurement_officer: {
        Row: { employeeid: number; approvallimit: number }
        Insert: { employeeid: number; approvallimit: number }
        Update: Partial<
          Database["public"]["Tables"]["procurement_officer"]["Insert"]
        >
      }
      accountant: {
        Row: { employeeid: number; certificationnumber: string | null }
        Insert: { employeeid: number; certificationnumber?: string | null }
        Update: Partial<Database["public"]["Tables"]["accountant"]["Insert"]>
      }
      hr_staff: {
        Row: { employeeid: number; hr_role: string }
        Insert: { employeeid: number; hr_role: string }
        Update: Partial<Database["public"]["Tables"]["hr_staff"]["Insert"]>
      }
      branch_manager: {
        Row: { employeeid: number; managementlevel: string | null }
        Insert: { employeeid: number; managementlevel?: string | null }
        Update: Partial<
          Database["public"]["Tables"]["branch_manager"]["Insert"]
        >
      }
      supplier: {
        Row: {
          supplierid: number
          suppliername: string
          contactperson: string | null
          phone: string | null
          address: string | null
        }
        Insert: {
          supplierid?: number
          suppliername: string
          contactperson?: string | null
          phone?: string | null
          address?: string | null
        }
        Update: Partial<Database["public"]["Tables"]["supplier"]["Insert"]>
      }
      purchase_order: {
        Row: {
          po_id: number
          orderdate: string
          supplierid: number
          employeeid: number
          status: POStatus
        }
        Insert: {
          po_id?: number
          orderdate?: string
          supplierid: number
          employeeid: number
          status?: POStatus
        }
        Update: Partial<
          Database["public"]["Tables"]["purchase_order"]["Insert"]
        >
      }
      category: {
        Row: { categoryid: number; categoryname: string }
        Insert: { categoryid?: number; categoryname: string }
        Update: Partial<Database["public"]["Tables"]["category"]["Insert"]>
      }
      product: {
        Row: {
          itemid: number
          itemname: string
          description: string | null
          unitprice: number
          reorderlevel: number
          quantityonhand: number
          categoryid: number
        }
        Insert: {
          itemid?: number
          itemname: string
          description?: string | null
          unitprice: number
          reorderlevel?: number
          quantityonhand?: number
          categoryid: number
        }
        Update: Partial<Database["public"]["Tables"]["product"]["Insert"]>
      }
      supply: {
        Row: {
          supplierid: number
          itemid: number
          costprice: number
          leadtimedays: number | null
        }
        Insert: {
          supplierid: number
          itemid: number
          costprice: number
          leadtimedays?: number | null
        }
        Update: Partial<Database["public"]["Tables"]["supply"]["Insert"]>
      }
      customer: {
        Row: { customerid: number; name: string | null; phone: string | null }
        Insert: {
          customerid?: number
          name?: string | null
          phone?: string | null
        }
        Update: Partial<Database["public"]["Tables"]["customer"]["Insert"]>
      }
      sale: {
        Row: {
          saleid: number
          saledate: string
          totalamount: number
          customerid: number | null
          employeeid: number
          branchid: number
        }
        Insert: {
          saleid?: number
          saledate?: string
          totalamount?: number
          customerid?: number | null
          employeeid: number
          branchid: number
        }
        Update: Partial<Database["public"]["Tables"]["sale"]["Insert"]>
      }
      sale_item: {
        Row: {
          saleid: number
          itemid: number
          quantity: number
          unitpriceatsale: number
        }
        Insert: {
          saleid: number
          itemid: number
          quantity: number
          unitpriceatsale: number
        }
        Update: Partial<Database["public"]["Tables"]["sale_item"]["Insert"]>
      }
      payroll: {
        Row: {
          payrollid: number
          employeeid: number
          month: string
          grosspay: number
          deductions: number
          netpay: number
        }
        Insert: {
          payrollid?: number
          employeeid: number
          month: string
          grosspay: number
          deductions?: number
          netpay: number
        }
        Update: Partial<Database["public"]["Tables"]["payroll"]["Insert"]>
      }
      ledger_entry: {
        Row: {
          entryid: number
          entrydate: string
          sourcetype: LedgerSourceType
          saleid: number | null
          payrollid: number | null
          amount: number
          recordedby: number
        }
        Insert: {
          entryid?: number
          entrydate?: string
          sourcetype: LedgerSourceType
          saleid?: number | null
          payrollid?: number | null
          amount: number
          recordedby: number
        }
        Update: Partial<
          Database["public"]["Tables"]["ledger_entry"]["Insert"]
        >
      }
    }
    Views: Record<string, never>
    Functions: Record<string, never>
    Enums: {
      role_type: RoleType
      po_status: POStatus
      ledger_source_type: LedgerSourceType
    }
  }
}