import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, FolderSearch, ShieldCheck, Sparkles, HardDrive, Bot, Zap } from 'lucide-react'
import { APP } from '../config.js'
import { GlassCard } from '../components/ui.jsx'
import { ArtifactCard } from '../ArjunTheme.jsx'
import { useFS } from '../context/FSContext.jsx'
import { fsSupported } from '../lib/files/scanner.js'
import { useToast } from '../components/Toast.jsx'

const feats = [
  { icon: FolderSearch, t: 'On-device scan', d: 'Point at any folder — or load the demo vault. Metadata analyzed locally, contents never uploaded.' },
  { icon: ShieldCheck, t: 'Hybrid privacy', d: 'Aadhaar, PAN, emails, secrets detected & redacted on-device. Only scrubbed metadata ever reaches any cloud API.' },
  { icon: HardDrive, t: 'Space recovery', d: 'Byte-identical duplicates, 4K videos, stale downloads and temp debris — quantified in GB, one queue to clear.' },
  { icon: Sparkles, t: 'Organization insights', d: 'Rename batches, auto-sort plans and archive suggestions generated from your actual mess.' },
  { icon: Zap, t: 'Instant search', d: 'Find “that file from last sem” by name, type, size or age — no more guessing filenames.' },
  { icon: Bot, t: 'Vault agent', d: 'Ask in plain English: “what can I delete?”, “find my resume”, “is my data private?”' },
]

export default function Landing() {
  const { loadDemo, scanFolder, status } = useFS()
  const toast = useToast()
  const nav = useNavigate()
  const busy = status === 'scanning'

  const demo = () => { loadDemo(); nav('/dashboard') }
  const real = async () => {
    try { await scanFolder(); nav('/dashboard') }
    catch (e) { toast.err(e.message) }
  }

  return (
    <div>
      <section className="mx-auto max-w-7xl px-5 pb-10 pt-16 text-center md:pt-24">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <span className="badge bg-mint/15 text-mint ring-1 ring-mint/40">✦ PS3 · FILE SYSTEM INTELLIGENCE</span>
          <h1 className="mx-auto mt-5 max-w-3xl font-display text-5xl font-bold leading-[1.02] tracking-tight md:text-7xl">
            End local file chaos. <span className="bg-gradient-to-r from-[#a99bff] via-neon to-mint bg-clip-text text-transparent">Keep it private.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-white/60 md:text-lg">
            {APP.name} scans your folders on-device, finds duplicates, hogs and leaks, redacts personal identifiers before anything touches the cloud — then tells you exactly what to do.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <button onClick={demo} disabled={busy} className="btn-primary">Try the demo vault <ArrowRight size={16} /></button>
            {fsSupported() && <button onClick={real} disabled={busy} className="btn-ghost">{busy ? 'Scanning…' : 'Scan a real folder'}</button>}
            <Link to="/privacy" className="btn-ghost text-sm">How privacy works</Link>
          </div>
          <div className="mx-auto mt-6 max-w-lg text-xs text-white/40">
            No signup · runs 100% in your browser · raw files never leave this machine
          </div>
        </motion.div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-5 pb-20 md:grid-cols-3">
        {feats.map((f, i) => (
          <GlassCard key={f.t} delay={i * 0.06}>
            <f.icon className="text-mint" size={22} />
            <div className="mt-3 font-display text-lg font-bold">{f.t}</div>
            <div className="mt-1 text-sm leading-relaxed text-white/55">{f.d}</div>
          </GlassCard>
        ))}
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-24">
        <ArtifactCard title="The 3-Minute Judge Demo" subtitle="Gandiva precision & on-device telemetry">
          <p className="max-w-2xl text-sm leading-relaxed text-white/70">
            1. Load the demo vault → 2. Watch duplicates + PII surface on the dashboard → 3. Open Privacy to prove nothing raw left the device → 4. Ask the agent “what can I delete?”
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button onClick={demo} className="btn-primary">Start demo</button>
            <Link to="/agent" className="btn-ghost">Meet the agent</Link>
          </div>
        </ArtifactCard>
      </section>
    </div>
  )
}
