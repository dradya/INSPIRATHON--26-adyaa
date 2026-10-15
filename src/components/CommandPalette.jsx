import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, FolderKanban, CheckSquare, MessagesSquare, FileText } from 'lucide-react'
import { supabase, isSupabaseConfigured } from '../lib/supabase.js'
import { useFS } from '../context/FSContext.jsx'
import { fmtBytes } from '../lib/files/insights.js'

// Global ⌘K / Ctrl+K search across files, projects, tasks, posts.
export default function CommandPalette() {
  const nav = useNavigate()
  const { files = [] } = useFS() || {}
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [res, setRes] = useState({ projects: [], tasks: [], posts: [] })
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen((o) => !o) }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (!open || q.trim().length < 2 || !isSupabaseConfigured) { setRes({ projects: [], tasks: [], posts: [] }); return }
    setBusy(true)
    const t = setTimeout(async () => {
      const like = `%${q.trim()}%`
      const [p, ta, po] = await Promise.all([
        supabase.from('projects').select('id,title,category').ilike('title', like).limit(5),
        supabase.from('tasks').select('id,title,status').ilike('title', like).limit(5),
        supabase.from('posts').select('id,body,kind').ilike('body', like).limit(5)
      ])
      setRes({ projects: p.data || [], tasks: ta.data || [], posts: po.data || [] })
      setBusy(false)
    }, 250)
    return () => clearTimeout(t)
  }, [q, open])

  const go = (to) => { setOpen(false); setQ(''); nav(to) }
  if (!open) return null

  const fileMatches = (files || [])
    .filter((f) => q.trim().length >= 2 && (f.redacted || '').toLowerCase().includes(q.trim().toLowerCase()))
    .slice(0, 8)
    .map((f) => ({
      t: f.redacted,
      s: f.size ? fmtBytes(f.size) : (f.kind || 'file'),
      to: '/explorer'
    }))

  const groups = [
    { label: 'Files', icon: FileText, items: fileMatches },
    { label: 'Projects', icon: FolderKanban, items: res.projects.map((r) => ({ t: r.title, s: r.category, to: `/projects/${r.id}` })) },
    { label: 'Tasks', icon: CheckSquare, items: res.tasks.map((r) => ({ t: r.title, s: r.status, to: '/tasks' })) },
    { label: 'Posts', icon: MessagesSquare, items: res.posts.map((r) => ({ t: r.body.slice(0, 60), s: r.kind, to: '/feed' })) }
  ]

  return (
    <div className="fixed inset-0 z-[95] bg-black/60 p-4 backdrop-blur-sm" onClick={() => setOpen(false)}>
      <div className="glass mx-auto mt-20 max-w-xl overflow-hidden rounded-2xl shadow-card" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-white/10 px-4">
          <Search size={16} className="text-white/40" />
          <input autoFocus className="w-full bg-transparent py-3.5 text-sm outline-none placeholder:text-white/30" placeholder="Search files, actions…" value={q} onChange={(e) => setQ(e.target.value)} />
          <kbd className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-white/50">ESC</kbd>
        </div>
        <div className="max-h-[50vh] overflow-y-auto scroll-thin p-2">
          {!isSupabaseConfigured && !files?.length && q.trim().length >= 2 && <div className="p-4 text-center text-xs text-white/40">Connect Supabase or load a vault to enable search.</div>}
          {q.trim().length < 2 && (
            <div className="space-y-1 p-1 text-sm">
              {[['/dashboard', 'Go to Dashboard'], ['/explorer', 'Go to Explorer'], ['/cleanup', 'Go to Cleanup'], ['/insights', 'Go to Insights'], ['/privacy', 'Privacy Pipeline'], ['/agent', 'Ask VaultLens Agent']].map(([to, l]) => (
                <button key={to} onClick={() => go(to)} className="block w-full rounded-xl px-3 py-2 text-left text-white/70 hover:bg-white/5 hover:text-white">{l}</button>
              ))}
            </div>
          )}
          {busy && <div className="p-4 text-center text-xs text-white/40">searching…</div>}
          {groups.map((g) => g.items.length > 0 && (
            <div key={g.label} className="mt-1">
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white/35">{g.label}</div>
              {g.items.map((it, i) => (
                <button key={i} onClick={() => go(it.to)} className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm hover:bg-white/5">
                  <g.icon size={14} className="shrink-0 text-mint" />
                  <span className="truncate text-white/85">{it.t}</span>
                  <span className="ml-auto shrink-0 text-[11px] text-white/35">{it.s}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function openPalette() {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
}
