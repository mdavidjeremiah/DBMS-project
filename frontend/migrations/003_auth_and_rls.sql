-- Issue 3: Authentication & Multi-User Role-Based Access Control
-- This migration adds authentication support and RLS policies

-- 1. Add AuthUserID to EMPLOYEE table (if not exists)
ALTER TABLE "EMPLOYEE"
ADD COLUMN IF NOT EXISTS "AuthUserID" UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. Enable RLS on all tables
ALTER TABLE "BRANCH" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DEPARTMENT" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "EMPLOYEE" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "CASHIER" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "PROCUREMENT_OFFICER" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "ACCOUNTANT" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "HR_STAFF" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "BRANCH_MANAGER" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "SUPPLIER" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "PURCHASE_ORDER" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "CATEGORY" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "PRODUCT" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "SUPPLY" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "CUSTOMER" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "SALE" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "SALE_ITEM" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "PAYROLL" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "LEDGER_ENTRY" ENABLE ROW LEVEL SECURITY;

-- 3. Helper function to get current user's role
CREATE OR REPLACE FUNCTION get_user_role()
RETURNS TEXT AS $$
  SELECT "RoleType" FROM "EMPLOYEE"
  WHERE "AuthUserID" = auth.uid()
  LIMIT 1;
$$ LANGUAGE SQL SECURITY DEFINER;

-- 4. Helper function to get current user's branch
CREATE OR REPLACE FUNCTION get_user_branch()
RETURNS UUID AS $$
  SELECT "BranchID" FROM "EMPLOYEE"
  WHERE "AuthUserID" = auth.uid()
  LIMIT 1;
$$ LANGUAGE SQL SECURITY DEFINER;

-- 5. EMPLOYEE RLS Policies
-- Admins can see all employees
CREATE POLICY "Admins can view all employees"
ON "EMPLOYEE" FOR SELECT
USING (
  get_user_role() = 'Admin' OR
  get_user_role() = 'Branch Manager' OR
  auth.uid() = "AuthUserID"
);

-- Specific roles can insert employees
CREATE POLICY "HR and Admins can create employees"
ON "EMPLOYEE" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'HR Staff')
);

-- Specific roles can update employees
CREATE POLICY "HR and Admins can update employees"
ON "EMPLOYEE" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'HR Staff') OR
  auth.uid() = "AuthUserID"
);

-- 6. BRANCH RLS Policies
CREATE POLICY "Users can view branches"
ON "BRANCH" FOR SELECT
USING (true);

CREATE POLICY "Only Branch Managers and Admins can update branches"
ON "BRANCH" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'Branch Manager')
);

-- 7. DEPARTMENT RLS Policies
CREATE POLICY "Users can view departments in their branch"
ON "DEPARTMENT" FOR SELECT
USING (
  get_user_role() = 'Admin' OR
  "BranchID" = get_user_branch()
);

CREATE POLICY "HR and Branch Managers can manage departments"
ON "DEPARTMENT" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'HR Staff', 'Branch Manager')
);

-- 8. SUPPLIER RLS Policies
CREATE POLICY "Procurement Officers can view suppliers"
ON "SUPPLIER" FOR SELECT
USING (true);

CREATE POLICY "Procurement Officers can manage suppliers"
ON "SUPPLIER" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

CREATE POLICY "Procurement Officers can update suppliers"
ON "SUPPLIER" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

-- 9. PRODUCT RLS Policies
CREATE POLICY "All authenticated users can view products"
ON "PRODUCT" FOR SELECT
USING (auth.role() = 'authenticated');

CREATE POLICY "Procurement Officers can manage products"
ON "PRODUCT" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

CREATE POLICY "Procurement Officers can update products"
ON "PRODUCT" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

-- 10. CATEGORY RLS Policies
CREATE POLICY "All authenticated users can view categories"
ON "CATEGORY" FOR SELECT
USING (auth.role() = 'authenticated');

CREATE POLICY "Procurement Officers can manage categories"
ON "CATEGORY" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

CREATE POLICY "Procurement Officers can update categories"
ON "CATEGORY" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

-- 11. PURCHASE_ORDER RLS Policies
CREATE POLICY "Procurement Officers can view POs"
ON "PURCHASE_ORDER" FOR SELECT
USING (
  get_user_role() = 'Admin' OR
  get_user_role() = 'Procurement Officer' OR
  get_user_role() = 'Branch Manager'
);

CREATE POLICY "Procurement Officers can create POs"
ON "PURCHASE_ORDER" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

CREATE POLICY "Procurement Officers can update POs"
ON "PURCHASE_ORDER" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

-- 12. SALE RLS Policies
CREATE POLICY "Cashiers can view sales in their branch"
ON "SALE" FOR SELECT
USING (
  get_user_role() = 'Admin' OR
  get_user_role() = 'Branch Manager' OR
  (get_user_role() = 'Cashier' AND "BranchID" = get_user_branch())
);

CREATE POLICY "Cashiers can create sales"
ON "SALE" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Cashier')
);

-- 13. SALE_ITEM RLS Policies
CREATE POLICY "Users can view sale items for their sales"
ON "SALE_ITEM" FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM "SALE"
    WHERE "SALE"."SaleID" = "SALE_ITEM"."SaleID"
    AND (
      get_user_role() = 'Admin' OR
      get_user_role() = 'Branch Manager' OR
      (get_user_role() = 'Cashier' AND "SALE"."BranchID" = get_user_branch())
    )
  )
);

CREATE POLICY "Cashiers can create sale items"
ON "SALE_ITEM" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Cashier')
);

-- 14. PAYROLL RLS Policies
CREATE POLICY "HR Staff can view payroll"
ON "PAYROLL" FOR SELECT
USING (
  get_user_role() IN ('Admin', 'HR Staff', 'Accountant')
);

CREATE POLICY "HR Staff can manage payroll"
ON "PAYROLL" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'HR Staff')
);

CREATE POLICY "HR Staff can update payroll"
ON "PAYROLL" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'HR Staff')
);

-- 15. LEDGER_ENTRY RLS Policies
CREATE POLICY "Accountants can view ledger entries"
ON "LEDGER_ENTRY" FOR SELECT
USING (
  get_user_role() IN ('Admin', 'Accountant', 'Branch Manager')
);

CREATE POLICY "System can create ledger entries"
ON "LEDGER_ENTRY" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Accountant')
);

-- 16. SUPPLY RLS Policies
CREATE POLICY "Procurement Officers can view supplies"
ON "SUPPLY" FOR SELECT
USING (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

CREATE POLICY "Procurement Officers can manage supplies"
ON "SUPPLY" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

CREATE POLICY "Procurement Officers can update supplies"
ON "SUPPLY" FOR UPDATE
USING (
  get_user_role() IN ('Admin', 'Procurement Officer')
);

-- 17. CUSTOMER RLS Policies
CREATE POLICY "All authenticated users can view customers"
ON "CUSTOMER" FOR SELECT
USING (auth.role() = 'authenticated');

CREATE POLICY "Cashiers and Admins can create customers"
ON "CUSTOMER" FOR INSERT
WITH CHECK (
  get_user_role() IN ('Admin', 'Cashier')
);

-- 18. Subtype table policies (CASHIER, PROCUREMENT_OFFICER, etc.)
CREATE POLICY "View cashier records"
ON "CASHIER" FOR SELECT
USING (true);

CREATE POLICY "View procurement officer records"
ON "PROCUREMENT_OFFICER" FOR SELECT
USING (true);

CREATE POLICY "View accountant records"
ON "ACCOUNTANT" FOR SELECT
USING (true);

CREATE POLICY "View HR staff records"
ON "HR_STAFF" FOR SELECT
USING (true);

CREATE POLICY "View branch manager records"
ON "BRANCH_MANAGER" FOR SELECT
USING (true);
