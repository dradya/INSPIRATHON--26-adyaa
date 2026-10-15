import { useEffect, useRef, useState } from 'react'
import { Bot, Send, Trash2, Sparkles, Search, ShieldCheck, Navigation } from 'lucide-react'
import { useAgentChat } from '../hooks/useAgentChat.js'
import { SUGGESTIONS, AGENT_ENDPOINT } from '../lib/agent.js'
import { GlassCard } from '../components/ui.jsx'

const CAPS = [
  { icon: Sparkles, t: 'Summarize', d: 'Workspace pulse, stats & leaderboard in one answer.' },
  { icon: Search, t: 'Find', d: '“find hostel” searches projects & tasks live.' },
  { icon: ShieldCheck, t: 'Privacy', d: '“is my data private?” audits identifiers with proof.' },
  { icon: Navigation, t: 'Navigate', d: '“take me to the board” moves you there.' }
]

export default function Agent() {
  const { messages, typing, send, clear } = useAgentChat()
  const [draft, setDraft] = useState('')
  const bottom = useRef(null)
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, typing])

  return (
    <div className="mx-auto max-w-5xl px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 font-display text-3xl font-bold md:text-4xl"><Bot className="text-mint" /> Vault Agent</h1>
          <p className="mt-1 text-sm text-white/50">
            {AGENT_ENDPOINT ? 'LLM mode (edge function) with live scan context.' : 'Local-brain mode — answers from your on-device scan, no API key needed.'}
          </p>
        </div>
        <button onClick={clear} className="btn-ghost !py-2 text-xs"><Trash2 size={13} /> New chat</button>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-4">
        {CAPS.map((c) => (
          <div key={c.t} className="glass-soft rounded-2xl p-3.5">
            <c.icon size={17} className="text-mint" />
            <div className="mt-1.5 text-sm font-bold">{c.t}</div>
            <div className="text-xs leading-relaxed text-white/50">{c.d}</div>
          </div>
        ))}
      </div>

      <GlassCard className="mt-4 flex h-[52vh] flex-col !p-0">
        <div className="flex-1 space-y-3 overflow-y-auto scroll-thin p-5">
          {messages.map((m, i) => (
            <div key={i} className={`max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-3 text-sm leading-relaxed ${m.role === 'user' ? 'ml-auto bg-neon text-ink' : 'bg-white/5 text-white/85'}`}>{m.content}</div>
          ))}
          {typing && <div className="w-fit animate-pulse rounded-2xl bg-white/5 px-4 py-3 text-sm text-white/50">thinking…</div>}
          <div ref={bottom} />
        </div>
        <div className="flex gap-2 overflow-x-auto scroll-thin px-4 pb-1">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => send(s)} className="shrink-0 rounded-full bg-white/5 px-3 py-1.5 text-xs text-white/60 hover:bg-white/10 hover:text-white">{s}</button>
          ))}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); send(draft); setDraft('') }} className="flex gap-2 border-t border-white/10 p-3">
          <input className="input" placeholder="Ask anything or give a command…" value={draft} onChange={(e) => setDraft(e.target.value)} />
          <button className="btn-primary shrink-0"><Send size={15} /> Send</button>
        </form>
      </GlassCard>
      {!AGENT_ENDPOINT && (
        <p className="mt-3 text-center text-xs text-white/35">Want GPT-grade answers? Deploy <code className="rounded bg-white/10 px-1">supabase/functions/agent-chat</code> and set <code className="rounded bg-white/10 px-1">VITE_AGENT_ENDPOINT</code> — see supabase/README.</p>
      )}
    </div>
  )
}
