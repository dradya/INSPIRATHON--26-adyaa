import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Bot, X, Send, Maximize2 } from 'lucide-react'
import { useAgentChat } from '../hooks/useAgentChat.js'
import { SUGGESTIONS } from '../lib/agent.js'

export default function AgentWidget() {
  const [open, setOpen] = useState(false)
  const { messages, typing, send } = useAgentChat()
  const [draft, setDraft] = useState('')
  const bottom = useRef(null)
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, typing, open])

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Open AI agent"
        className="fixed bottom-5 right-5 z-[80] grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-neon to-mint text-ink shadow-glow transition hover:-translate-y-0.5"
      >
        {open ? <X size={22} /> : <Bot size={24} />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 24, scale: 0.97 }}
            className="glass fixed bottom-[92px] right-5 z-[80] flex h-[480px] w-[min(380px,calc(100vw-40px))] flex-col overflow-hidden rounded-2xl shadow-card"
          >
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-neon to-mint text-ink"><Bot size={17} /></span>
                <div>
                  <div className="font-display text-sm font-bold">Vault Agent</div>
                  <div className="text-[11px] text-mint">● online · reads your scan</div>
                </div>
              </div>
              <Link to="/agent" onClick={() => setOpen(false)} className="rounded-lg bg-white/5 p-2 text-white/60 hover:text-white" title="Full screen"><Maximize2 size={14} /></Link>
            </div>
            <div className="flex-1 space-y-2.5 overflow-y-auto scroll-thin px-3.5 py-3">
              {messages.map((m, i) => (
                <div key={i} className={`max-w-[88%] whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${m.role === 'user' ? 'ml-auto bg-neon text-ink' : 'bg-white/5 text-white/85'}`}>{m.content}</div>
              ))}
              {typing && <div className="w-fit animate-pulse rounded-2xl bg-white/5 px-3.5 py-2.5 text-[13px] text-white/50">thinking…</div>}
              <div ref={bottom} />
            </div>
            <div className="flex gap-1.5 overflow-x-auto scroll-thin px-3 pb-1">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="shrink-0 rounded-full bg-white/5 px-2.5 py-1 text-[11px] text-white/60 hover:bg-white/10 hover:text-white">{s}</button>
              ))}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); send(draft); setDraft('') }} className="flex gap-2 border-t border-white/10 p-2.5">
              <input className="input !py-2 text-[13px]" placeholder="Ask or command…" value={draft} onChange={(e) => setDraft(e.target.value)} />
              <button className="btn-primary shrink-0 !px-3.5 !py-2"><Send size={15} /></button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
