import { ShieldCheck, Lock, Eye, EyeOff, Server, Laptop } from 'lucide-react'
import { useFS } from '../context/FSContext.jsx'
import { GlassCard, Empty } from '../components/ui.jsx'
import { DETECTORS } from '../lib/files/pii.js'
import { AGENT_ENDPOINT } from '../lib/agent.js'

export default function Privacy() {
  const { files, status, privacyLog, detectors, toggleDetector, piiFiles, sessionId } = useFS()
  if (status !== 'ready') return <div className="mx-auto max-w-3xl px-5 py-14"><Empty title="No scan loaded" hint="Load the demo vault or scan a folder to see the privacy pipeline in action." /></div>

  const piiByType = {}
  files.forEach((f) => (f.pii || []).forEach((p) => { piiByType[p.label] = (piiByType[p.label] || 0) + p.count }))

  // The EXACT shape of anything allowed to leave the device:
  const cloudPayload = {
    note: 'This is the maximum that ever reaches Supabase / any cloud AI. No raw names, paths, or contents.',
    session: { file_count: files.length, source: 'redacted' },
    aggregates: { kinds: {}, pii_types: Object.keys(piiByType) },
    sample_records: files.filter((f) => f.pii?.length).slice(0, 3).map((f) => ({
      redacted_name: f.redacted, kind: f.kind, size_bytes: f.size,
      pii_types: f.pii.map((p) => p.type), content_hash: f.contentHash ? f.contentHash.slice(0, 12) + '…' : null
    }))
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Hybrid privacy pipeline</h1>
      <p className="text-sm text-white/50">Sensitive data is detected and redacted <span className="font-bold text-mint">on this device</span> before anything non-sensitive is eligible for cloud APIs.</p>

      <div className="grid gap-3 md:grid-cols-4">
        {[
          { icon: Laptop, t: '1 · Scan locally', d: `${files.length} files read in this browser tab. Raw names live in tab memory only.` },
          { icon: EyeOff, t: '2 · Detect PII', d: `${piiFiles.length} files flagged across ${Object.keys(piiByType).length} identifier types.` },
          { icon: Lock, t: '3 · Redact on-device', d: 'Names, samples and payloads scrubbed to [REDACTED:TYPE] before use.' },
          { icon: Server, t: '4 · Cloud sees scraps', d: AGENT_ENDPOINT ? 'LLM endpoint gets aggregates + redacted samples only.' : 'No cloud endpoint configured — literally nothing has left.' }
        ].map((s, i) => (
          <GlassCard key={s.t} delay={i * 0.05}>
            <s.icon size={20} className="text-mint" />
            <div className="mt-2 font-display font-bold">{s.t}</div>
            <div className="mt-1 text-xs leading-relaxed text-white/55">{s.d}</div>
          </GlassCard>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <GlassCard>
          <div className="flex items-center gap-2 font-display font-bold"><Eye size={16} className="text-mint" /> Detectors (toggle, re-runs instantly)</div>
          <div className="mt-3 space-y-1.5">
            {DETECTORS.map((d) => (
              <label key={d.id} className="flex cursor-pointer items-center justify-between rounded-xl bg-white/5 px-3.5 py-2.5 text-sm">
                <span>{d.label} <span className="text-white/35">· {piiByType[d.label] || 0} hits</span></span>
                <input type="checkbox" checked={detectors[d.id] !== false} onChange={() => toggleDetector(d.id)} className="h-4 w-4 accent-[#7c6cff]" />
              </label>
            ))}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="flex items-center gap-2 font-display font-bold"><ShieldCheck size={16} className="text-mint" /> Redaction log ({privacyLog.length})</div>
          <div className="mt-3 max-h-80 space-y-1.5 overflow-y-auto scroll-thin pr-1">
            {privacyLog.slice(0, 60).map((l, i) => (
              <div key={i} className="glass-soft flex items-center gap-2 rounded-xl px-3 py-2 text-xs">
                <span className="truncate text-white/80">{l.file}</span>
                <span className="badge ml-auto shrink-0 bg-red-400/15 text-red-300">{l.type} ×{l.count}</span>
              </div>
            ))}
            {!privacyLog.length && <div className="text-xs text-white/40">No redactions — nothing sensitive found.</div>}
          </div>
        </GlassCard>
      </div>

      <GlassCard>
        <div className="flex items-center gap-2 font-display font-bold"><Server size={16} className="text-mint" /> What leaves this machine — exact payload shape</div>
        <p className="mt-1 text-xs text-white/45">Show this to the judges. Filenames below are already redacted; types are labels, never values.{sessionId ? ` Synced as session ${sessionId.slice(0, 8)}…` : ' Not synced (no backend) — payload preview only.'}</p>
        <pre className="mt-3 max-h-72 overflow-auto scroll-thin rounded-xl bg-black/40 p-4 text-[11px] leading-relaxed text-mint/90">{JSON.stringify(cloudPayload, null, 2)}</pre>
      </GlassCard>
    </div>
  )
}
