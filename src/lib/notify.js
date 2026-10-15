import { supabase } from './supabase.js'

// Fire-and-forget in-app notification. Never throws (safe for demo paths).
export async function notifyUser(to, { title, body = '', link = '' } = {}) {
  if (!to || !title) return
  try {
    await supabase.from('notifications').insert({ user_id: to, title, body, link })
  } catch {
    /* notifications table / realtime optional — never break the main flow */
  }
}
