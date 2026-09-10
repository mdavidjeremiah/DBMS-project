# Issue 3 Implementation Guide - Authentication & RBAC

## Overview

This guide covers the complete implementation of Issue 3: Authentication & Multi-User Role-Based Access Control for the Hardware World system.

## What's Been Implemented

### 1. **Authentication System**

#### Auth Pages Created
- **Sign In** (`/auth/sign-in`) - Email/password login
- **Sign Up** (`/auth/sign-up`) - New user registration with email confirmation
- **Forgot Password** (`/auth/forgot-password`) - Password reset request
- **Reset Password** (`/auth/reset-password`) - Set new password
- **Auth Callback** (`/auth/callback`) - Supabase callback handler
- **Auth Layout** - Special layout without AppShell for auth pages

#### Client-Side Setup
- ✅ Supabase client initialization (`utils/supabase/client.ts`)
- ✅ Server-side client creation (`utils/supabase/server.ts`)
- ✅ Middleware for session management (`middleware.ts`)
- ✅ Auth helper functions (`lib/auth.ts`)

### 2. **Session Management**

**Middleware (`middleware.ts`)**
- Protects routes from unauthenticated users
- Redirects logged-in users away from auth pages
- Handles session refresh across requests
- Uses Supabase SSR for proper cookie handling

**Protected Routes**
- All routes except `/auth/*` require authentication
- Users attempting to access protected routes are redirected to `/auth/sign-in`

### 3. **User Menu & Profile**

**Updated Topbar Component**
- Displays current user email
- Shows user's role with color-coded badge
- Fetches role from database in real-time
- Includes sign-out button
- Role colors by type:
  - Cashier: Blue
  - Procurement Officer: Amber
  - Accountant: Purple
  - HR Staff: Green
  - Branch Manager: Red
  - Admin: Slate

### 4. **Team Management**

#### Invite Modal (`InviteTeamMemberModal`)
- Email input for new team member
- Role selection from 6 available roles
- Sends Supabase Auth invitation email
- Automatically creates EMPLOYEE record with role
- Confirmation feedback

#### Add Member to Branch Modal (`AddMemberToBranchModal`)
- Select existing employee
- Assign to a branch
- Optional department assignment
- Updates employee record with branch/dept references

#### Settings Page Enhanced
- Displays all team members with roles
- Quick actions for inviting and assigning
- System status indicators
- Role-based color badges

### 5. **Role-Based Access Control**

#### Role Definition
```
- Cashier: POS operations, limited branch access
- Procurement Officer: Supplier, product, PO management
- Accountant: Ledger and financial records
- HR Staff: Employee and payroll management
- Branch Manager: Full branch operations access
- Admin: Unrestricted access
```

#### Client-Side Route Guards
- `useRoleGuard()` hook checks user's role
- Prevents unauthorized page access
- Automatic redirect to homepage for unauthorized access

### 6. **Database Security**

#### SQL Migration File (`migrations/003_auth_and_rls.sql`)

**Changes**
- Adds `AuthUserID` (UUID FK to `auth.users`) to EMPLOYEE table
- Enables RLS on all 18 tables
- Creates helper functions for permission checks

**Helper Functions**
```sql
get_user_role() → Returns EMPLOYEE.RoleType for current user
get_user_branch() → Returns EMPLOYEE.BranchID for current user
```

**RLS Policies Implemented**
- EMPLOYEE table: Role-specific read/write access
- BRANCH table: Read all, branch-specific updates
- DEPARTMENT table: Branch-scoped access for HR/managers
- SUPPLIER table: Procurement officer only
- CATEGORY & PRODUCT table: Read-all, procurement-edit
- PURCHASE_ORDER table: Procurement create/update, manager approve
- SALE & SALE_ITEM table: Cashier-scoped per branch
- PAYROLL table: HR create, accountant/manager view
- LEDGER_ENTRY table: Accountant view, system-only insert
- SUPPLY table: Procurement officer only
- CUSTOMER table: Authenticated read, cashier/admin create/update

### 7. **Permission Matrix**

See `PERMISSION_MATRIX.md` for detailed permission matrix showing:
- Role × Table × Operation (SELECT/INSERT/UPDATE/DELETE)
- Approval workflows (PO approval limits)
- Branch/department scoping rules
- Ledger entry constraints

## Next Steps to Complete

### 1. **Deploy Database Migrations**

Before the app can fully function, you must run the migration:

```bash
# If using Supabase CLI (recommended)
supabase migration up

# Or execute the SQL directly in Supabase dashboard:
# 1. Go to SQL Editor
# 2. Run contents of migrations/003_auth_and_rls.sql
```

**What This Does**
- Adds `AuthUserID` column to EMPLOYEE table
- Enables row-level security on all tables
- Creates helper functions for permission checks
- Creates RLS policies for each role/table combination

### 2. **Set Environment Variables**

Create/update `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://[project-id].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-anon-key]
```

These are already in your Supabase project settings.

### 3. **Test Authentication Flow**

```bash
# Start development server
npm run dev

# Test sequence:
1. Visit http://localhost:3000 - should redirect to /auth/sign-in
2. Click "Sign up" - register a test account
3. Verify email (check Supabase Auth logs or email)
4. Sign in with credentials
5. Should see dashboard with user menu showing your email and role
6. Click sign out - should redirect to /auth/sign-in
```

### 4. **Seed Test Data**

After migration, create test employees with different roles:

```sql
-- Example: Create HR Staff for testing
INSERT INTO "EMPLOYEE" (
  "EmployeeID", 
  "EmployeeName", 
  "RoleType", 
  "BranchID", 
  "AuthUserID"
) VALUES (
  gen_random_uuid(),
  'Test HR Staff',
  'HR Staff',
  '[branch-id]',
  '[auth-user-id-from-supabase]'
);

-- Subtype table for HR Staff
INSERT INTO "HR_STAFF" (
  "EmployeeID",
  "HR_Role"
) VALUES ('[employee-id]', 'Manager');
```

### 5. **Test RLS Policies**

You can verify RLS is working by:

```bash
# Sign in as different roles
# Attempt to access protected pages
# Check browser console for API errors (403 Forbidden = RLS working)

# Test directly in Supabase SQL editor:
-- This will fail if you're not an admin/procurement officer
SELECT * FROM "SUPPLIER";

-- Create a test policy check:
SET ROLE authenticated;  -- simulate authenticated user
SELECT current_user_id();
```

### 6. **Verify Invite Workflow**

1. Go to Settings page
2. Click "Invite Team Member"
3. Enter email and select role
4. Check Supabase Auth → Users to see invitation
5. User receives email with sign-up link
6. On acceptance, EMPLOYEE record is auto-created

### 7. **Test Role-Based Access**

1. Create employees with different roles
2. Sign in as each role
3. Verify:
   - Cashier sees only POS/sales pages
   - Procurement Officer sees procurement pages
   - HR Staff sees employee/payroll pages
   - Branch Manager sees branch dashboard
   - Admin sees everything

## Testing Checklist

- [ ] Database migration (`003_auth_and_rls.sql`) deployed
- [ ] Environment variables set
- [ ] Sign-up flow works (account created in Supabase Auth)
- [ ] Sign-in flow works (redirected to dashboard)
- [ ] User menu shows current user email and role
- [ ] Sign-out works (redirected to sign-in)
- [ ] Invite modal creates employee records
- [ ] Add to Branch modal updates employee assignments
- [ ] RLS policies prevent unauthorized data access
- [ ] Unauthorized users can't access pages via direct URL
- [ ] Role-based navigation reflects database roles

## Architecture Overview

```
┌─────────────────────────────────────────┐
│ Authentication Pages (/auth/*)          │
│ - Sign In, Sign Up, Password Reset      │
└──────────────┬──────────────────────────┘
               │ Supabase Auth
               ▼
┌─────────────────────────────────────────┐
│ Middleware (middleware.ts)              │
│ - Session refresh                       │
│ - Route protection                      │
└──────────────┬──────────────────────────┘
               │ Checks auth.uid()
               ▼
┌─────────────────────────────────────────┐
│ Protected Routes & Components           │
│ - Topbar (shows user + role)            │
│ - Settings (team management)            │
│ - Role-guarded pages                    │
└──────────────┬──────────────────────────┘
               │ Fetch from DB
               ▼
┌─────────────────────────────────────────┐
│ Supabase Database                       │
│ - EMPLOYEE (with AuthUserID)            │
│ - RLS Policies (role-based filtering)   │
│ - Helper functions (get_user_role)      │
└─────────────────────────────────────────┘
```

## File Structure

```
hardware-world/
├── middleware.ts                 ← Session management
├── src/
│   ├── app/
│   │   ├── auth/
│   │   │   ├── sign-in/page.tsx
│   │   │   ├── sign-up/page.tsx
│   │   │   ├── forgot-password/page.tsx
│   │   │   ├── reset-password/page.tsx
│   │   │   ├── callback/page.tsx
│   │   │   └── layout.tsx
│   │   ├── settings/page.tsx     ← Team management
│   │   └── ...other pages
│   ├── components/
│   │   ├── layout/
│   │   │   └── Topbar.tsx        ← Shows user menu + role
│   │   └── shared/
│   │       ├── InviteTeamMemberModal.tsx
│   │       └── AddMemberToBranchModal.tsx
│   ├── hooks/
│   │   └── useRoleGuard.ts       ← Client-side route protection
│   ├── lib/
│   │   └── auth.ts               ← Auth helpers
│   └── utils/
│       └── supabase/
│           ├── client.ts
│           ├── server.ts
│           └── middleware.ts
├── migrations/
│   └── 003_auth_and_rls.sql      ← Database setup
└── PERMISSION_MATRIX.md           ← Role-permission documentation
```

## Troubleshooting

### Issue: "AuthUserID column doesn't exist"
**Solution**: Run migration `003_auth_and_rls.sql` in Supabase SQL editor

### Issue: "RLS policy violation" errors
**Solution**: This is expected - RLS is working! Check PERMISSION_MATRIX.md to verify access is correct

### Issue: Can't sign out
**Solution**: Check console for errors, verify Supabase session is being cleared

### Issue: Role not showing in topbar
**Solution**: 
1. Verify EMPLOYEE record has an AuthUserID linked to auth.users
2. Check that RoleType is set on EMPLOYEE record
3. Check browser console for fetch errors

### Issue: Invites not being sent
**Solution**:
1. Verify NEXT_PUBLIC_SUPABASE_ANON_KEY has correct permissions
2. Check Supabase Auth settings for email configuration
3. Review Supabase logs for invitation errors

## Security Notes

✅ **Passwords**: Hashed by Supabase Auth (bcrypt)
✅ **Sessions**: Managed via HTTP-only cookies (Supabase SSR)
✅ **Permissions**: Enforced at database level (RLS policies)
✅ **Tokens**: Automatically refreshed via middleware
✅ **Branch Scoping**: Applied at database level, not just UI

⚠️ **Remember**: Never remove RLS policies or helper functions without updating all dependent code

## Support

For issues with this implementation, refer to:
- Supabase Auth Docs: https://supabase.com/docs/guides/auth
- Supabase RLS Docs: https://supabase.com/docs/guides/auth/row-level-security
- Issue 3 Requirements: See GitHub issue #3
- PERMISSION_MATRIX.md: Local permission reference
