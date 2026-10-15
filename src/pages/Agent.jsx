import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Bot,
  Send,
  Trash2,
  Sparkles,
  Search,
  ShieldCheck,
  Navigation,
  ArrowRight,
  LayoutDashboard
} from 'lucide-react'
import { useAgentChat } from '../hooks/useAgentChat.js'
import { SUGGESTIONS, AGENT_ENDPOINT } from '../lib/agent.js'
import { GlassCard } from '../components/ui.jsx'

const CAPS = [
  { icon: Sparkles, t: 'Summarize', d: 'Workspace pulse, stats & leaderboard in one answer.' },
  { icon: Search, t: 'Find', d: '“find hostel” searches projects & tasks live.' },
  { icon: ShieldCheck, t: 'Privacy', d: '“is my data private?” audits identifiers with proof.' },
  { icon: Navigation, t: 'Navigate', d: '“take me to the board” moves you there.' }
]

function parseInline(str) {
  if (!str) return str
  const regex = /(\*\*.*?\*\*|`.*?`|⚠️\s*PII)/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      parts.push(str.substring(lastIndex, match.index))
    }
    const token = match[0]
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-semibold text-white">
          {token.slice(2, -2)}
        </strong>
      )
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-xs text-mint">
          {token.slice(1, -1)}
        </code>
      )
    } else if (token.includes('PII')) {
      parts.push(
        <span
          key={match.index}
          className="inline-flex items-center gap-1 rounded bg-peach/15 px-1.5 py-0.5 text-[11px] font-semibold text-peach border border-peach/30 mx-1 align-baseline"
        >
          ⚠️ PII
        </span>
      )
    }
    lastIndex = regex.lastIndex
  }
  if (lastIndex < str.length) {
    parts.push(str.substring(lastIndex))
  }
  return parts.length > 0 ? parts : str
}

function FormattedContent({ text }) {
  if (!text) return null
  const lines = text.split('\n')

  return (
    <div className="space-y-1.5 leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim()
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />
        }

        // Bullet item (•, -, *)
        if (/^[•\-*]\s+/.test(trimmed)) {
          const itemText = trimmed.replace(/^[•\-*]\s+/, '')
          return (
            <div key={idx} className="flex items-start gap-2.5 pl-1 py-0.5">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-mint shadow-[0_0_6px_rgba(61,220,151,0.7)]" />
              <div className="flex-1 text-white/90">{parseInline(itemText)}</div>
            </div>
          )
        }

        // Numbered item (e.g. "1. ")
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/)
        if (numMatch) {
          return (
            <div key={idx} className="flex items-start gap-2.5 pl-1 py-0.5">
              <span className="font-mono text-xs font-bold text-neon shrink-0 mt-0.5 min-w-[1.2rem]">
                {numMatch[1]}.
              </span>
              <div className="flex-1 text-white/90">{parseInline(numMatch[2])}</div>
            </div>
          )
        }

        // Section header ending with colon or special header prefixes
        if (
          trimmed.endsWith(':') ||
          /^(Storage optimization tips|File type breakdown|Workspace pulse|Leaderboard|Open tasks|Shipped|Vault status|My top advice)/i.test(
            trimmed
          )
        ) {
          return (
            <div key={idx} className="font-semibold text-white/95 pt-1 text-sm tracking-wide">
              {parseInline(trimmed)}
            </div>
          )
        }

        // Regular line
        return (
          <div key={idx} className="text-white/85">
            {parseInline(line)}
          </div>
        )
      })}
    </div>
  )
}

function getQuickActions(text) {
  if (!text) return []
  const lower = text.toLowerCase()
  const actions = []

  if (/duplicate|cleanup|waste|byte-identical|cleanup queue/i.test(lower)) {
    actions.push({
      label: 'Go to Cleanup',
      to: '/cleanup',
      icon: Trash2,
      style: 'bg-peach/10 text-peach border-peach/30 hover:bg-peach/20 hover:border-peach/50'
    })
  }

  if (/privacy|redact|pii|identifier|clean bill|sensitive|proof/i.test(lower)) {
    actions.push({
      label: 'View Privacy Pipeline',
      to: '/privacy',
      icon: ShieldCheck,
      style: 'bg-mint/10 text-mint border-mint/30 hover:bg-mint/20 hover:border-mint/50'
    })
  }

  if (/optimi|tip|advice|health|h\.265|webp|untouched|archive|insights?/i.test(lower)) {
    actions.push({
      label: 'View Insights',
      to: '/insights',
      icon: Sparkles,
      style: 'bg-neon/10 text-neon border-neon/30 hover:bg-neon/20 hover:border-neon/50'
    })
  }

  if (/explorer|found \d+|opening explorer|browse the explorer/i.test(lower)) {
    actions.push({
      label: 'Open Explorer',
      to: '/explorer',
      icon: Search,
      style: 'bg-mint/10 text-mint border-mint/30 hover:bg-mint/20 hover:border-mint/50'
    })
  }

  if (/breakdown|file type|bykind|workspace pulse|dashboard/i.test(lower)) {
    actions.push({
      label: 'Go to Dashboard',
      to: '/dashboard',
      icon: LayoutDashboard,
      style: 'bg-neon/10 text-neon border-neon/30 hover:bg-neon/20 hover:border-neon/50'
    })
  }

  const seen = new Set()
  return actions.filter((a) => {
    if (seen.has(a.to)) return false
    seen.add(a.to)
    return true
  }).slice(0, 2)
}

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
          {messages.map((m, i) => {
            const isUser = m.role === 'user'
            const actions = !isUser ? getQuickActions(m.content) : []

            return (
              <div
                key={i}
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  isUser
                    ? 'ml-auto bg-neon font-medium text-ink shadow-sm'
                    : 'bg-white/5 border border-white/5 text-white/90 shadow-sm'
                }`}
              >
                {isUser ? (
                  <div className="whitespace-pre-line">{m.content}</div>
                ) : (
                  <>
                    <FormattedContent text={m.content} />
                    {actions.length > 0 && (
                      <div className="mt-3 flex flex-wrap items-center gap-2 pt-2.5 border-t border-white/10">
                        <span className="text-[10px] font-semibold text-white/40 uppercase tracking-wider">
                          Quick action:
                        </span>
                        {actions.map((act) => {
                          const Icon = act.icon
                          return (
                            <Link
                              key={act.to}
                              to={act.to}
                              className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1 text-xs font-semibold transition shadow-sm active:scale-95 ${act.style}`}
                            >
                              <Icon size={13} />
                              <span>{act.label}</span>
                              <ArrowRight size={11} className="opacity-70" />
                            </Link>
                          )
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            )
          })}

          {typing && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex w-fit items-center gap-3 rounded-2xl bg-white/5 border border-white/10 px-4 py-3 text-sm shadow-sm"
            >
              <div className="grid h-6 w-6 place-items-center rounded-lg bg-neon/20 text-neon">
                <Bot size={14} className="animate-pulse" />
              </div>
              <div className="flex items-center gap-1.5 py-1">
                <span className="h-2 w-2 rounded-full bg-neon animate-bounce [animation-delay:-0.32s]" />
                <span className="h-2 w-2 rounded-full bg-mint animate-bounce [animation-delay:-0.16s]" />
                <span className="h-2 w-2 rounded-full bg-peach animate-bounce" />
              </div>
              <span className="text-xs text-white/40">VaultLens is thinking…</span>
            </motion.div>
          )}
          <div ref={bottom} />
        </div>

        <div className="flex gap-2 overflow-x-auto scroll-thin px-4 pb-2 pt-1 border-t border-white/5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="shrink-0 rounded-full bg-white/5 border border-white/5 px-3 py-1.5 text-xs text-white/60 hover:bg-white/10 hover:text-white hover:border-white/20 transition"
            >
              {s}
            </button>
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
