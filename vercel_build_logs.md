11:22:02.906 Running build in Washington, D.C., USA (East) – iad1
11:22:02.907 Build machine configuration: 2 cores, 8 GB
11:22:03.027 Cloning github.com/mdavidjeremiah/DBMS-project (Branch: main, Commit: 6702a4a)
11:22:03.028 Previous build caches not available.
11:22:03.486 Cloning completed: 459.000ms
11:22:03.813 Running "vercel build"
11:22:03.831 Vercel CLI 59.3.0
11:22:04.008 Installing dependencies...
11:22:20.450 
11:22:20.451 added 373 packages in 16s
11:22:20.452 
11:22:20.452 150 packages are looking for funding
11:22:20.452   run `npm fund` for details
11:22:20.452 npm warn allow-scripts 1 package has install scripts not yet covered by allowScripts:
11:22:20.452 npm warn allow-scripts   unrs-resolver@1.12.2 (postinstall: node postinstall.js)
11:22:20.452 npm warn allow-scripts
11:22:20.452 npm warn allow-scripts Run `npm approve-scripts --allow-scripts-pending` to review, or `npm approve-scripts <pkg>` to allow.
11:22:20.499 Detected Next.js version: 16.3.4
11:22:20.507 Running "npm run build"
11:22:20.621 
11:22:20.622 > hardware-world@0.1.0 build
11:22:20.622 > next build
11:22:20.622 
11:22:21.035 ▲ Next.js 16.3.4 (Turbopack)
11:22:21.139   Applying modifyConfig from Vercel
11:22:21.141 ✓ Running next.config.ts took 109ms
11:22:21.194 Attention: Next.js now collects completely anonymous telemetry regarding usage.
11:22:21.194 This information is used to shape Next.js' roadmap and prioritize features.
11:22:21.195 You can learn more, including how to opt-out if you'd not like to participate in this anonymous program, by visiting the following URL:
11:22:21.195 https://nextjs.org/telemetry
11:22:21.195 
11:22:21.209 
11:22:21.242   Creating an optimized production build ...
11:22:29.436 ✓ Compiled successfully in 7.4s
11:22:29.443   Running TypeScript ...
11:22:34.078 src/components/layout/Sidebar.tsx(50,32): error TS2322: Type '{ children: Element; asChild: true; }' is not assignable to type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.079   Property 'asChild' does not exist on type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.080 src/components/layout/Topbar.tsx(31,23): error TS2322: Type '{ children: Element; asChild: true; }' is not assignable to type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.080   Property 'asChild' does not exist on type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.080 src/components/layout/Topbar.tsx(70,30): error TS2322: Type '{ children: Element; asChild: true; }' is not assignable to type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.080   Property 'asChild' does not exist on type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.080 src/components/shared/Modal.tsx(44,34): error TS2322: Type '{ children: string | number | bigint | true | ReactElement<unknown, string | JSXElementConstructor<any>> | Iterable<ReactNode> | ReactPortal | Promise<...>; asChild: true; }' is not assignable to type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.080   Property 'asChild' does not exist on type 'IntrinsicAttributes & Props<unknown>'.
11:22:34.081 src/components/shared/StatusBadge.tsx(1,17): error TS2305: Module '"@/components/ui/badge"' has no exported member 'BadgeProps'.
11:22:34.110 Failed to type check.
11:22:34.110 
11:22:34.155 Error: Command "npm run build" exited with 1
