15:18:18.362 Running build in Washington, D.C., USA (East) – iad1
15:18:18.363 Build machine configuration: 2 cores, 8 GB
15:18:18.494 Cloning github.com/mdavidjeremiah/DBMS-project (Branch: main, Commit: 18143c1)
15:18:19.495 Cloning completed: 1.000s
15:18:19.714 Restored build cache from previous deployment (9xvsvh1G3Fjtgyp5RXFGEE8h6NYE)
15:18:20.151 Running "vercel build"
15:18:20.171 Vercel CLI 59.11.7
15:18:20.378 Installing dependencies...
15:18:21.358 
15:18:21.359 up to date in 817ms
15:18:21.359 
15:18:21.360 154 packages are looking for funding
15:18:21.360   run `npm fund` for details
15:18:21.361 npm warn allow-scripts 1 package has install scripts not yet covered by allowScripts:
15:18:21.361 npm warn allow-scripts   unrs-resolver@1.12.2 (postinstall: node postinstall.js)
15:18:21.361 npm warn allow-scripts
15:18:21.361 npm warn allow-scripts Run `npm approve-scripts --allow-scripts-pending` to review, or `npm approve-scripts <pkg>` to allow.
15:18:21.390 Detected Next.js version: 16.3.4
15:18:21.396 Running "npm run build"
15:18:21.501 
15:18:21.502 > hardware-world@0.1.0 build
15:18:21.502 > next build
15:18:21.502 
15:18:22.014 ▲ Next.js 16.3.4 (Turbopack)
15:18:22.217   Applying modifyConfig from Vercel
15:18:22.219 ✓ Running next.config.ts took 204ms
15:18:22.235 
15:18:22.268   Creating an optimized production build ...
15:18:31.637 ✓ Compiled successfully in 8.5s
15:18:31.648   Running TypeScript ...
15:18:37.801 src/app/auth/callback/page.tsx(30,17): error TS2552: Cannot find name 'request'. Did you mean 'Request'?
15:18:37.801 src/app/auth/forgot-password/page.tsx(24,43): error TS18047: 'supabase' is possibly 'null'.
15:18:37.801 src/app/auth/reset-password/page.tsx(50,44): error TS18047: 'supabase' is possibly 'null'.
15:18:37.801 src/app/auth/sign-in/page.tsx(26,42): error TS18047: 'supabase' is possibly 'null'.
15:18:37.802 src/app/auth/sign-up/page.tsx(52,42): error TS18047: 'supabase' is possibly 'null'.
15:18:37.802 src/app/settings/page.tsx(36,37): error TS18047: 'supabase' is possibly 'null'.
15:18:37.802 src/components/layout/Topbar.tsx(64,11): error TS18047: 'supabase' is possibly 'null'.
15:18:37.802 src/components/shared/AddMemberToBranchModal.tsx(57,9): error TS18047: 'supabase' is possibly 'null'.
15:18:37.803 src/components/shared/AddMemberToBranchModal.tsx(58,9): error TS18047: 'supabase' is possibly 'null'.
15:18:37.803 src/components/shared/AddMemberToBranchModal.tsx(59,9): error TS18047: 'supabase' is possibly 'null'.
15:18:37.803 src/components/shared/AddMemberToBranchModal.tsx(89,44): error TS18047: 'supabase' is possibly 'null'.
15:18:37.804 src/components/shared/AddMemberToBranchModal.tsx(145,48): error TS2322: Type 'Dispatch<SetStateAction<string>>' is not assignable to type '(value: string | null, eventDetails: SelectRootChangeEventDetails) => void'.
15:18:37.804   Types of parameters 'value' and 'value' are incompatible.
15:18:37.804     Type 'string | null' is not assignable to type 'SetStateAction<string>'.
15:18:37.804       Type 'null' is not assignable to type 'SetStateAction<string>'.
15:18:37.804 src/components/shared/AddMemberToBranchModal.tsx(161,46): error TS2322: Type 'Dispatch<SetStateAction<string>>' is not assignable to type '(value: string | null, eventDetails: SelectRootChangeEventDetails) => void'.
15:18:37.804   Types of parameters 'value' and 'value' are incompatible.
15:18:37.805     Type 'string | null' is not assignable to type 'SetStateAction<string>'.
15:18:37.805       Type 'null' is not assignable to type 'SetStateAction<string>'.
15:18:37.805 src/components/shared/AddMemberToBranchModal.tsx(177,50): error TS2322: Type 'Dispatch<SetStateAction<string>>' is not assignable to type '(value: string | null, eventDetails: SelectRootChangeEventDetails) => void'.
15:18:37.806   Types of parameters 'value' and 'value' are incompatible.
15:18:37.806     Type 'string | null' is not assignable to type 'SetStateAction<string>'.
15:18:37.806       Type 'null' is not assignable to type 'SetStateAction<string>'.
15:18:37.807 src/components/shared/InviteTeamMemberModal.tsx(64,50): error TS18047: 'supabase' is possibly 'null'.
15:18:37.807 src/components/shared/InviteTeamMemberModal.tsx(75,48): error TS18047: 'supabase' is possibly 'null'.
15:18:37.807 src/components/shared/InviteTeamMemberModal.tsx(147,36): error TS2322: Type 'Dispatch<SetStateAction<string>>' is not assignable to type '(value: string | null, eventDetails: SelectRootChangeEventDetails) => void'.
15:18:37.807   Types of parameters 'value' and 'value' are incompatible.
15:18:37.807     Type 'string | null' is not assignable to type 'SetStateAction<string>'.
15:18:37.807       Type 'null' is not assignable to type 'SetStateAction<string>'.
15:18:37.808 src/hooks/useRoleGuard.ts(26,42): error TS18047: 'supabase' is possibly 'null'.
15:18:37.808 src/hooks/useRoleGuard.ts(41,42): error TS18047: 'supabase' is possibly 'null'.
15:18:37.834 Failed to type check.
15:18:37.835 
15:18:37.881 Error: Command "npm run build" exited with 1
