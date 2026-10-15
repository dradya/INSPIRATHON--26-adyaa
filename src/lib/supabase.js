import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!url || !anon) {
  console.warn('[supabase] Missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY — copy .env.example to .env')
}

export const supabase = createClient(url || 'https://placeholder.supabase.co', anon || 'placeholder-key')
export const isSupabaseConfigured = Boolean(url && anon && url.includes('.supabase.co'))
