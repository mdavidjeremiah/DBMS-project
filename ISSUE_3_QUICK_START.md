# Issue 3: Quick Start Testing Guide

## Quick Setup (5 minutes)

### Step 1: Deploy Database Migration

Visit your Supabase project SQL editor and run:

```bash
# 1. Open Supabase Dashboard
# 2. Go to SQL Editor
# 3. Run this file: migrations/003_auth_and_rls.sql
```

This adds AuthUserID to EMPLOYEE table and enables RLS on all tables.

### Step 2: Verify Environment Variables

Your `.env.local` should have:
```env
NEXT_PUBLIC_SUPABASE_URL=https://kangmycxzemoonimjrsg.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-anon-key-here]
```

### Step 3: Start Dev Server

```bash
cd hardware-world
npm run dev
# Server runs at http://localhost:3000
```

## Test Authentication Flow

### 1. Sign Up
1. Navigate to http://localhost:3000
2. Should redirect to `/auth/sign-in`
3. Click "Sign up"
4. Enter email: `test@example.com`
5. Enter password: `Test123456`
6. Click "Create Account"
7. See confirmation: "Check Your Email"

### 2. Verify Email (In Supabase)
1. Go to Supabase Dashboard → Authentication → Users
2. Find your test@example.com user
3. Click on user, then "Confirm user email" (or wait for actual email)
4. User status should be "Confirmed"

### 3. Sign In
1. Return to `/auth/sign-in`
2. Enter email: `test@example.com`
3. Enter password: `Test123456`
4. Click "Sign In"
5. Should be redirected to dashboard `/`
6. See "WELCOME BACK" message on dashboard

### 4. Check User Menu
1. Look at top-right corner of page
2. Should see avatar with "test" initials
3. Click dropdown
4. See email and "Loading..." for role (since no EMPLOYEE record exists yet)

## Create Employee Records for Testing

### Via Supabase SQL Editor

**Create HR Staff Employee:**
```sql
-- First, get your auth user ID
SELECT id FROM auth.users WHERE email = 'test@example.com';
-- Copy the UUID

-- Then create employee record (replace [uuid] with actual user ID)
INSERT INTO "EMPLOYEE" (
  "EmployeeID",
  "EmployeeName",
  "RoleType",
  "BranchID",
  "AuthUserID"
) VALUES (
  gen_random_uuid(),
  'Test User',
  'HR Staff',
  (SELECT "BranchID" FROM "BRANCH" LIMIT 1),  -- Pick first branch
  '[paste-uuid-here]'
);
```

**Create HR Staff Subtype Record:**
```sql
-- Get the EmployeeID from the INSERT above, then:
INSERT INTO "HR_STAFF" (
  "EmployeeID",
  "HR_Role"
) VALUES (
  '[employee-id-from-above]',
  'HR Manager'
);
```

### After Creating Employee

1. Refresh browser page
2. Look at user menu again
3. Should now show role badge: "HR Staff" in green
4. Navigate to `/settings`
5. Should see your employee listed in "Team Members"

## Test Team Invitations

### Invite New Team Member

1. Go to `/settings`
2. Click "Invite Team Member" button
3. Enter email: `newmember@example.com`
4. Select role: "Cashier"
5. Click "Send Invite"
6. See success message
7. Check Supabase Auth → Users for invitation status

### Accept Invitation (Manual for now)

Since email might not be configured:
1. In Supabase, find `newmember@example.com` user
2. Manually create matching EMPLOYEE record:

```sql
INSERT INTO "EMPLOYEE" (
  "EmployeeID",
  "EmployeeName",
  "RoleType",
  "BranchID",
  "AuthUserID"
) VALUES (
  gen_random_uuid(),
  'New Member',
  'Cashier',
  (SELECT "BranchID" FROM "BRANCH" LIMIT 1),
  (SELECT id FROM auth.users WHERE email = 'newmember@example.com')
);

-- Create Cashier subtype
INSERT INTO "CASHIER" (
  "EmployeeID",
  "POS_TerminalID"
) VALUES (
  '[employee-id]',
  'TERMINAL-001'
);
```

## Test Role-Based Access

### Current Setup Notes

Since we haven't created sample EMPLOYEE records yet, all role-based access is limited. Once you create EMPLOYEE records, test:

1. **Cashier Access**
   - Sign in as Cashier employee
   - Should see: `/sales`, `/products`, `/categories`
   - Should NOT see: `/purchase-orders`, `/payroll`, `/ledger`

2. **Procurement Officer Access**
   - Sign in as Procurement Officer
   - Should see: `/purchase-orders`, `/suppliers`, `/products`, `/categories`
   - Should NOT see: `/sales`, `/payroll`, `/ledger`

3. **HR Staff Access**
   - Sign in as HR Staff
   - Should see: `/employees`, `/payroll`, `/departments`
   - Should NOT see: `/sales`, `/purchase-orders`, `/suppliers`

4. **Branch Manager Access**
   - Sign in as Branch Manager
   - Should see: All pages (full branch access)

5. **Admin Access**
   - Sign in as Admin
   - Should see: All pages (unrestricted)

## Test Sign Out

1. Click user menu (top-right)
2. Click "Log out"
3. Should be redirected to `/auth/sign-in`
4. Try to access protected route directly (e.g., `/settings`)
5. Should redirect to `/auth/sign-in`

## Test Password Reset

### Request Reset
1. Go to `/auth/forgot-password`
2. Enter email: `test@example.com`
3. Click "Send Reset Link"
4. See confirmation: "Check Your Email"

### Reset Password (Manual)
1. In Supabase SQL Editor:
```sql
-- This would normally come from email link
-- For testing, just update password via Supabase Auth UI
```

2. Or click "Reset Link" from Supabase user details
3. It will provide a reset password page URL
4. Use that to set new password

## Test RLS Policies

### Verify RLS is Enforced

1. Open browser DevTools (F12)
2. Go to Console tab
3. Create a Supabase client and try to query:

```javascript
// In browser console
const { createClient } = window.supabaseClient;
const supabase = createClient();

// This should work (employee can read employee)
await supabase.from('EMPLOYEE').select('*').single();

// This might fail depending on RLS (try to read supplier as cashier)
await supabase.from('SUPPLIER').select('*');
```

### Check Supabase Logs

1. Go to Supabase Dashboard
2. Go to Logs → API Usage
3. Look for `403` responses (RLS policy violations)
4. This means RLS is working!

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load / 500 error | Check console for auth errors, verify Supabase URL/key |
| Can't sign up | Check Supabase Auth settings, verify email configuration |
| User menu shows "Loading..." forever | EMPLOYEE record doesn't exist, create it in SQL |
| Can't access settings page | RLS policy might be blocking read, check PERMISSION_MATRIX.md |
| Redirect loop between auth pages | Clear browser cookies, try incognito mode |
| Role badge not showing color | Refresh page, verify role name matches exactly |

## What's Working

✅ Authentication (sign up, sign in, sign out)
✅ Session management (middleware refresh)
✅ User profile in topbar
✅ Role display with badges
✅ Team member invitations (creates auth.users)
✅ Add member to branch functionality
✅ Password reset flow
✅ RLS database policies (once enabled)

## What Needs Database Data

To fully test Issue 3, you need:

1. ✅ BRANCH records (sample data from Issue #2)
2. ✅ DEPARTMENT records
3. ✅ EMPLOYEE records with:
   - AuthUserID linked to auth.users
   - RoleType set correctly
   - BranchID assigned
4. ✅ Subtype records (CASHIER, PROCUREMENT_OFFICER, etc.)

See [ISSUE_3_IMPLEMENTATION.md](ISSUE_3_IMPLEMENTATION.md) for complete setup steps.

## Next: Issue 4

Once Issue 3 is verified working, you can move to Issue 4: Procurement & Inventory Management, which uses these auth/RLS foundations.
