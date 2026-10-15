import { useNavigate } from 'react-router-dom'
import { Lightbulb, Check, X, Sparkles, ShieldAlert, HardDrive, FolderCog } from 'lucide-react'
import { useFS } from '../context/FSContext.jsx'
import { GlassCard, Empty } from '../components/ui.jsx'
import { fmtBytes } from '../lib/files/insights.js'
import { supabase, isSupabaseConfigured } from '../lib/supabase.js'

const KIND_ICON = { space: HardDrive, organize: FolderCog, privacy: ShieldAlert, cleanup: Sparkles }
const ROUTES = {
  dup: '/cleanup', media: '/cleanup', stale: '/cleanup', temp: '/cleanup',
  pii: '/privacy', rename: '/explorer', sort: '/explorer'
}

export default function Insights() {
  const navigate = useNavigate()
  const { suggestions, sugState, setSuggestion, status, sessionId } = useFS()
  if (status !== 'ready') return <div className="mx-auto max-w-3xl px-5 py-14"><Empty title="No scan loaded" hint="Load the demo vault or scan a folder from the Dashboard." /></div>

  const open = suggestions.filter((s) => (sugState[s.id] || 'open') === 'open')
  const done = suggestions.filter((s) => (sugState[s.id] || 'open') !== 'open')

  const decide = async (s, state) => {
    setSuggestion(s.id, state)
    if (isSupabaseConfigured && sessionId) {
      try {
        const { data } = await supabase.from('suggestions').insert({
          session_id: sessionId, kind: s.kind, title: s.title, detail: s.detail,
          impact_bytes: s.impact || 0, status: state
        }).select('id').single()
        if (data && state === 'accepted') await supabase.from('suggestions').update({ upvotes: 1 }).eq('id', data.id)
      } catch { /* local-first */ }
    }
    // Navigate to relevant page when accepted
    if (state === 'accepted') {
      const routes = {
        dup: '/cleanup', media: '/cleanup', stale: '/cleanup', temp: '/cleanup',
        pii: '/privacy', rename: '/explorer', sort: '/explorer'
      }
      const target = routes[s.id]
      if (target) {
        setTimeout(() => navigate(target), 400)
      }
    }
  }

  const card = (s) => {
    const Icon = KIND_ICON[s.kind] || Lightbulb
    const st = sugState[s.id] || 'open'
    return (
      <GlassCard key={s.id}>
        <div className="flex items-center gap-2">
          <Icon size={17} className={s.kind === 'privacy' ? 'text-red-300' : s.kind === 'space' ? 'text-peach' : 'text-mint'} />
          <span className="badge bg-white/10 text-white/55">{s.kind}</span>
          {s.impact > 0 && <span className="badge ml-auto bg-mint/15 text-mint">{fmtBytes(s.impact)}</span>}
        </div>
        <div className="mt-2 font-display text-lg font-bold leading-snug">{s.title}</div>
        <p className="mt-1 text-sm leading-relaxed text-white/55">{s.detail}</p>
        {st === 'open' ? (
          <div className="mt-4 flex gap-2">
            <button onClick={() => decide(s, 'accepted')} className="btn-primary flex-1 !py-2 text-sm"><Check size={15} /> {s.action || 'Accept'}</button>
            <button onClick={() => decide(s, 'dismissed')} className="btn-ghost !px-3.5 !py-2 text-sm"><X size={15} /></button>
          </div>
        ) : (
          <div className={`mt-4 rounded-xl px-3 py-2 text-center text-xs font-bold ${st === 'accepted' ? 'bg-mint/15 text-mint' : 'bg-white/5 text-white/40'}`}>
            {st === 'accepted'
              ? (ROUTES[s.id] ? '✓ Accepted — opening relevant view…' : '✓ Accepted — queued as your organization plan')
              : 'Dismissed'}
          </div>
        )}
      </GlassCard>
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Insights</h1>
      <p className="mt-1 text-sm text-white/50">Generated on-device from your scan. Accept to build your organization plan — synced (redacted) when Supabase is connected.</p>
      {suggestions.length > 0 && (
        <div className="mt-4 glass rounded-2xl px-5 py-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-white/60">Organization progress</span>
            <span className="font-bold text-mint">{done.length}/{suggestions.length} reviewed</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gradient-to-r from-neon to-mint transition-all duration-500" style={{ width: `${(done.length / suggestions.length) * 100}%` }} />
          </div>
        </div>
      )}
      <div className="mt-5 grid gap-4 md:grid-cols-2">{open.map(card)}</div>
      {!open.length && <div className="mt-5"><Empty title="All caught up 🎉" hint="Every suggestion reviewed. Rescan anytime." /></div>}
      {done.length > 0 && (
        <>
          <h2 className="mt-8 font-display text-xl font-bold text-white/70">Reviewed ({done.length})</h2>
          <div className="mt-3 grid gap-4 opacity-70 md:grid-cols-2">{done.map(card)}</div>
        </>
      )}
    </div>
  )
}
