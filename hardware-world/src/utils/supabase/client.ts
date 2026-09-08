import { createBrowserClient } from "@supabase/ssr";

// Use NEXT_PUBLIC_ prefix so these are accessible in both client and server
// components. Must match the env vars set in Vercel / .env.local.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const createClient = () => {
  if (!isSupabaseConfigured) {
    return null;
  }

  return createBrowserClient(supabaseUrl!, supabaseAnonKey!);
};
