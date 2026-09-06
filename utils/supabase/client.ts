import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "@/lib/database.types";

// NOTE: these must carry the NEXT_PUBLIC_ prefix -- this file runs in the
// browser bundle, and Next.js only inlines env vars into client code when
// they're prefixed that way. The previous version read `SUPABASE_URL` /
// `SUPABASE_PUBLISHABLE_KEY` (no prefix), which are never defined in the
// browser, so every client-side Supabase call was silently getting
// `undefined` for both args.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export const createClient = () =>
  createBrowserClient<Database>(supabaseUrl!, supabaseKey!);