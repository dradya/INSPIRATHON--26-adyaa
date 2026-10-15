import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function NotificationsBell() {
  const { user } = useAuth()
  const nav = useNavigate()
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)

  const load = async () => {
    if (!user) return
    const { data } = await supabase.from('notifications')
      .select('*').eq('user_id', user.id).order('created_at', { ascending: false }).limit(15)
    if (data) setItems(data)
  }

  useEffect(() => {
    load()
    if (!user) return
    const ch = supabase.channel(`notif-${user.id}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'notifications', filter: `user_id=eq.${user.id}` }, load)
      .subscribe()
    return () => supabase.removeChannel(ch)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id])

  if (!user) return null
  const unread = items.filter((n) => !n.is_read).length

  const markAll = async () => {
    await supabase.from('notifications').update({ is_read: true }).eq('user_id', user.id).eq('is_read', false)
    load()
  }
  const openItem = async (n) => {
    if (!n.is_read) await supabase.from('notifications').update({ is_read: true }).eq('id', n.id)
    setOpen(false); load()
    if (n.link) nav(n.link)
  }

  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="relative rounded-xl bg-white/5 p-2.5 text-white/70 hover:bg-white/10 hover:text-white" aria-label="Notifications">
        <Bell size={16} />
        {unread > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-red-400 px-1 text-[10px] font-bold text-ink">{unread}</span>}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-[60]" onClick={() => setOpen(false)} />
          <div className="glass absolute right-0 z-[61] mt-2 max-h-[60vh] w-[320px] overflow-y-auto scroll-thin rounded-2xl p-2 shadow-card">
            <div className="flex items-center justify-between px-2 py-1.5">
              <span className="font-display text-sm font-bold">Notifications</span>
              <button onClick={markAll} className="inline-flex items-center gap-1 text-[11px] text-mint hover:text-white"><CheckCheck size={12} /> Mark all read</button>
            </div>
            {items.length === 0 && <div className="p-5 text-center text-xs text-white/40">All quiet 🔕 — comments on your projects will land here live.</div>}
            {items.map((n) => (
              <button key={n.id} onClick={() => openItem(n)} className={`block w-full rounded-xl px-3 py-2.5 text-left hover:bg-white/5 ${n.is_read ? 'opacity-55' : ''}`}>
                <div className="flex items-center gap-2 text-[13px] font-semibold">{!n.is_read && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-mint" />}{n.title}</div>
                {n.body && <div className="mt-0.5 line-clamp-2 text-xs text-white/55">{n.body}</div>}
                <div className="mt-1 text-[10px] text-white/30">{new Date(n.created_at).toLocaleString()}</div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
