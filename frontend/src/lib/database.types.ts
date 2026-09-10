/**
 * Database types matching the deployed Hardware World schema.  These are
 * deliberately limited to the columns that exist in Supabase; inventory
 * quantities and purchase-order line items are not part of this schema.
 */
export type RoleType = "Cashier" | "Procurement Officer" | "Accountant" | "HR Staff" | "Branch Manager"
export type POStatus = "Pending" | "Approved" | "Received" | "Cancelled"
export type LedgerSourceType = "SALE" | "PAYROLL"

type Table<Row, Insert> = { Row: Row; Insert: Insert; Update: Partial<Insert>; Relationships: [] }

export interface Database {
  public: {
    Tables: {
      category: Table<{ categoryid: number; categoryname: string }, { categoryid?: never; categoryname: string }>
      supplier: Table<{ supplierid: number; suppliername: string; contactperson: string | null; phone: string | null; address: string | null }, { supplierid?: never; suppliername: string; contactperson?: string | null; phone?: string | null; address?: string | null }>
      customer: Table<{ customerid: number; name: string | null; phone: string | null }, { customerid?: never; name?: string | null; phone?: string | null }>
      branch: Table<{ branchid: number; branchname: string; location: string; contactnumber: string | null; manageremployeeid: number | null }, { branchid?: never; branchname: string; location: string; contactnumber?: string | null; manageremployeeid?: number | null }>
      department: Table<{ departmentid: number; departmentname: string; branchid: number }, { departmentid?: never; departmentname: string; branchid: number }>
      employee: Table<{ employeeid: number; name: string; nin: string; phone: string | null; datehired: string; salary: number; departmentid: number; branchid: number; supervisorid: number | null; roletype: RoleType }, { employeeid?: never; name: string; nin: string; phone?: string | null; datehired?: string; salary: number; departmentid: number; branchid: number; supervisorid?: number | null; roletype: RoleType }>
      cashier: Table<{ employeeid: number; pos_terminalid: string }, { employeeid: number; pos_terminalid: string }>
      procurement_officer: Table<{ employeeid: number; approvallimit: number }, { employeeid: number; approvallimit: number }>
      accountant: Table<{ employeeid: number; certificationnumber: string | null }, { employeeid: number; certificationnumber?: string | null }>
      hr_staff: Table<{ employeeid: number; hr_role: string }, { employeeid: number; hr_role: string }>
      branch_manager: Table<{ employeeid: number; managementlevel: string | null }, { employeeid: number; managementlevel?: string | null }>
      product: Table<{ itemid: number; itemname: string; description: string | null; unitprice: number; reorderlevel: number; categoryid: number }, { itemid?: never; itemname: string; description?: string | null; unitprice: number; reorderlevel?: number; categoryid: number }>
      supply: Table<{ supplierid: number; itemid: number; costprice: number; leadtimedays: number | null }, { supplierid: number; itemid: number; costprice: number; leadtimedays?: number | null }>
      purchase_order: Table<{ po_id: number; orderdate: string; supplierid: number; employeeid: number; status: POStatus }, { po_id?: never; orderdate?: string; supplierid: number; employeeid: number; status?: POStatus }>
      sale: Table<{ saleid: number; saledate: string; totalamount: number; customerid: number | null; employeeid: number; branchid: number }, { saleid?: never; saledate?: string; totalamount?: number; customerid?: number | null; employeeid: number; branchid: number }>
      sale_item: Table<{ saleid: number; itemid: number; quantity: number; unitpriceatsale: number }, { saleid: number; itemid: number; quantity: number; unitpriceatsale: number }>
      payroll: Table<{ payrollid: number; employeeid: number; month: string; grosspay: number; deductions: number; netpay: number }, { payrollid?: never; employeeid: number; month: string; grosspay: number; deductions?: number; netpay: number }>
      ledger_entry: Table<{ entryid: number; entrydate: string; sourcetype: LedgerSourceType; saleid: number | null; payrollid: number | null; amount: number; recordedby: number }, { entryid?: never; entrydate?: string; sourcetype: LedgerSourceType; saleid?: number | null; payrollid?: number | null; amount: number; recordedby: number }>
    }
    Views: Record<string, never>
    Functions: Record<string, never>
    Enums: { roletype: RoleType; po_status: POStatus; ledger_source_type: LedgerSourceType }
    CompositeTypes: Record<string, never>
  }
}
