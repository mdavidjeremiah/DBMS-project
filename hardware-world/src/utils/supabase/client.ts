import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_PUBLISHABLE_KEY;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseKey);

export const createClient = () => {
  if (!isSupabaseConfigured) {
    return null;
  }

  return createBrowserClient(supabaseUrl!, supabaseKey!);
};
