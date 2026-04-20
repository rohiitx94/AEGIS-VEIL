import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://apuotrfgrsmmeywxlcmh.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "sb_publishable_Kc3o_ZEEW-k2mKeP7dYwAA_9BU5hWpv";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
