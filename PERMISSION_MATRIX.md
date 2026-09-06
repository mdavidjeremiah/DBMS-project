# Hardware World - Role Permission Matrix

## Overview
This document defines the permission matrix for all roles in the Hardware World system. Permissions are enforced at the database level via PostgreSQL Row Level Security (RLS) policies.

## Roles

1. **Cashier** - POS operator, handles customer sales
2. **Procurement Officer** - Manages inventory, suppliers, and purchase orders
3. **Accountant** - Manages financial records and ledger
4. **HR Staff** - Manages employee records and payroll
5. **Branch Manager** - Full access to branch operations, manages staff
6. **Admin** - Unrestricted access to all tables and operations

---

## Permission Matrix by Table

### EMPLOYEE
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | Only self | ❌ | Only self | ❌ |
| Procurement Officer | Only self | ❌ | Only self | ❌ |
| Accountant | Only self | ❌ | Only self | ❌ |
| HR Staff | ✅ All | ✅ | ✅ All | ✅ |
| Branch Manager | ✅ Branch | ❌ | ✅ Branch | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### BRANCH
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ✅ All | ❌ | ❌ | ❌ |
| Procurement Officer | ✅ All | ❌ | ❌ | ❌ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ✅ All | ❌ | ❌ | ❌ |
| Branch Manager | ✅ All | ❌ | ✅ Own branch | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### DEPARTMENT
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ❌ | ❌ | ❌ | ❌ |
| Procurement Officer | ❌ | ❌ | ❌ | ❌ |
| Accountant | ❌ | ❌ | ❌ | ❌ |
| HR Staff | ✅ All | ✅ | ✅ All | ✅ |
| Branch Manager | ✅ Own branch | ✅ | ✅ Own branch | ✅ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### SUPPLIER
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ❌ | ❌ | ❌ | ❌ |
| Procurement Officer | ✅ All | ✅ | ✅ All | ✅ |
| Accountant | ❌ | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ All | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### CATEGORY
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ✅ All | ❌ | ❌ | ❌ |
| Procurement Officer | ✅ All | ✅ | ✅ All | ✅ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ All | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### PRODUCT
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ✅ All | ❌ | ❌ | ❌ |
| Procurement Officer | ✅ All | ✅ | ✅ All | ✅ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ All | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### SUPPLY (Associative Entity: Supplier × Product)
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ❌ | ❌ | ❌ | ❌ |
| Procurement Officer | ✅ All | ✅ | ✅ All | ✅ |
| Accountant | ❌ | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ❌ | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### PURCHASE_ORDER
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ❌ | ❌ | ❌ | ❌ |
| Procurement Officer | ✅ All | ✅ | ✅ (up to ApprovalLimit) | ✅ |
| Accountant | ❌ | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ Branch | ❌ | ✅ Approve | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

**Note on Procurement Officer approval**: Cannot approve a PO if the total exceeds their `ApprovalLimit` - enforced at API level.

### SALE
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ✅ Own branch | ✅ Own branch | ✅ Own branch | ❌ |
| Procurement Officer | ❌ | ❌ | ❌ | ❌ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ Own branch | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### SALE_ITEM
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ✅ Own sales | ✅ Own sales | ✅ Own sales | ✅ |
| Procurement Officer | ❌ | ❌ | ❌ | ❌ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ Branch sales | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### PAYROLL
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ❌ | ❌ | ❌ | ❌ |
| Procurement Officer | ❌ | ❌ | ❌ | ❌ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ✅ All | ✅ | ✅ All | ✅ |
| Branch Manager | ✅ Branch | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### LEDGER_ENTRY
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ❌ | ❌ | ❌ | ❌ |
| Procurement Officer | ❌ | ❌ | ❌ | ❌ |
| Accountant | ✅ All | ✅ (via system) | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ Branch | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### CUSTOMER
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| Cashier | ✅ All | ✅ | ✅ All | ❌ |
| Procurement Officer | ❌ | ❌ | ❌ | ❌ |
| Accountant | ✅ All | ❌ | ❌ | ❌ |
| HR Staff | ❌ | ❌ | ❌ | ❌ |
| Branch Manager | ✅ All | ❌ | ❌ | ❌ |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

### Subtype Tables (CASHIER, PROCUREMENT_OFFICER, ACCOUNTANT, HR_STAFF, BRANCH_MANAGER)
| Role | SELECT | INSERT | UPDATE | DELETE |
|------|--------|--------|--------|--------|
| All authenticated | ✅ All | ✅ (for own role) | ✅ (for own role) | ✅ (for own role) |
| Admin | ✅ All | ✅ | ✅ All | ✅ |

---

## Approval Workflows

### Purchase Order Approval Limits
- **Procurement Officer**: Limited by their `ApprovalLimit` field
- **Branch Manager**: Can approve any PO in their branch
- **Admin**: No limits, can approve all POs
- **Other Roles**: Cannot approve POs

### Ledger Entry Sources
- **SALE**: Created when a `SALE` + `SALE_ITEM` transaction is completed
- **PAYROLL**: Created when a `PAYROLL` record is finalized
- Constraint: `LEDGER_ENTRY` must have exactly one of `SaleID` or `PayrollID` populated, matching `SourceType`

---

## Key Constraints

1. **Branch Scoping**: Cashiers and Branch Managers are scoped to their assigned branch
2. **Self-Reference**: Employees can always view and update their own records
3. **Approval Hierarchy**: Lower-level approvers cannot exceed their approval limits
4. **Department Access**: Employees can only access departments in their assigned branch
5. **Ledger Immutability**: Accountants cannot delete or modify `LEDGER_ENTRY` records (audit trail)
6. **Supervisor Chain**: `EMPLOYEE.SupervisorID` creates a self-referencing FK; HR Staff can manage this

---

## Implementation Notes

All policies are implemented using PostgreSQL RLS with helper functions:
- `get_user_role()`: Returns the authenticated user's role from `EMPLOYEE.RoleType`
- `get_user_branch()`: Returns the authenticated user's branch from `EMPLOYEE.BranchID`

These functions ensure that all permission checks are database-level and cannot be bypassed from the application layer.
