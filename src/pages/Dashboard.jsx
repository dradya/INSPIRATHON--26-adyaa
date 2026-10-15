import { Link, useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { FolderSearch, ShieldCheck, ArrowRight } from 'lucide-react'
import { useFS } from '../context/FSContext.jsx'
import { GlassCard, Stat } from '../components/ui.jsx'
import { KIND_LABEL, fmtBytes } from '../lib/files/insights.js'
import { useToast } from '../components/Toast.jsx'
import { fsSupported } from '../lib/files/scanner.js'

const COLORS = ['#7c6cff', '#3ddc97', '#ffb86b', '#38bdf8', '#f472b6', '#a3e635', '#facc15', '#94a3b8', '#f87171']

export default function Dashboard() {
  const { files, status, progress, source, stats, dups, score, piiFiles, suggestions, loadDemo, scanFolder } = useFS()
  const toast = useToast()
  const nav = useNavigate()

  if (status !== 'ready') {
    return (
      <div className="mx-auto max-w-2xl px-5 py-16 text-center">
        <GlassCard>
          <FolderSearch size={36} className="mx-auto text-mint" />
          <h1 className="mt-3 font-display text-3xl font-bold">Scan something first</h1>
          <p className="mx-auto mt-2 max-w-md text-sm text-white/55">Load the messy demo vault for an instant tour, or point at a real folder — analysis happens on-device either way.</p>
          {status === 'scanning' && <div className="mt-4 text-sm text-mint">Working… {progress?.phase === 'hashing' ? 'hashing duplicate candidates' : progress?.done ? `${progress.done} files` : 'loading demo'}</div>}
          <div className="mt-6 flex justify-center gap-3">
            <button onClick={() => { loadDemo(); nav('/dashboard') }} disabled={status === 'scanning'} className="btn-primary">Load demo vault</button>
            {fsSupported() && <button onClick={async () => { try { await scanFolder(); nav('/dashboard') } catch (e) { toast.err(e.message) } }} disabled={status === 'scanning'} className="btn-ghost">Scan real folder</button>}
          </div>
        </GlassCard>
      </div>
    )
  }

  const dupWaste = dups.reduce((a, g) => a + g.waste, 0)
  const pie = Object.entries(stats.byKind).map(([k, v]) => ({ name: KIND_LABEL[k] || k, value: v })).sort((a, b) => b.value - a.value)
  const bars = Object.entries(stats.byFolder).map(([k, v]) => ({ name: k.slice(0, 14), v })).sort((a, b) => b.v - a.v).slice(0, 7)
  const large = [...files].sort((a, b) => b.size - a.size).slice(0, 5)

  return (
    <div className="mx-auto max-w-7xl space-y-5 px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold md:text-4xl">Storage overview</h1>
          <p className="text-sm text-white/50">{source} · {stats.count} files · analyzed on-device</p>
        </div>
        <div className={`glass rounded-2xl px-5 py-3 text-center ${score >= 70 ? 'ring-1 ring-mint/40' : score >= 40 ? 'ring-1 ring-peach/40' : 'ring-1 ring-red-400/50'}`}>
          <div className="font-display text-3xl font-bold">{score}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-white/45">health score</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Total used" value={fmtBytes(stats.total)} sub={`${stats.count} files`} />
        <Stat label="Recoverable" value={fmtBytes(dupWaste)} sub={`${dups.length} duplicate groups`} />
        <Stat label="PII-flagged" value={piiFiles.length} sub="names or content" />
        <Stat label="Suggestions" value={suggestions.length} sub="actions ready" />
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <GlassCard>
          <div className="font-display text-lg font-bold">Space by type</div>
          <div className="h-60 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                  {pie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#12122b', border: '1px solid #ffffff22', borderRadius: 12 }} formatter={(v) => fmtBytes(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-white/55">
            {pie.slice(0, 6).map((p, i) => <span key={p.name} className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />{p.name} · {fmtBytes(p.value)}</span>)}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="font-display text-lg font-bold">Top folders</div>
          <div className="h-60 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bars} layout="vertical">
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" stroke="#ffffff55" fontSize={12} width={110} />
                <Tooltip contentStyle={{ background: '#12122b', border: '1px solid #ffffff22', borderRadius: 12 }} formatter={(v) => fmtBytes(v)} />
                <Bar dataKey="v" fill="#7c6cff" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <GlassCard>
          <div className="flex items-center justify-between">
            <div className="font-display text-lg font-bold">Largest files</div>
            <Link to="/cleanup" className="text-xs text-mint">cleanup →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {large.map((f) => (
              <div key={f.id} className="glass-soft flex items-center justify-between gap-3 rounded-xl px-4 py-2.5">
                <span className="truncate text-sm">{f.redacted}</span>
                <span className="shrink-0 text-xs font-bold text-white/60">{fmtBytes(f.size)}</span>
              </div>
            ))}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-display text-lg font-bold"><ShieldCheck size={18} className="text-mint" /> Privacy watch</div>
            <Link to="/privacy" className="text-xs text-mint">pipeline →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {piiFiles.slice(0, 5).map((f) => (
              <div key={f.id} className="glass-soft flex items-center justify-between gap-3 rounded-xl px-4 py-2.5">
                <span className="truncate text-sm">{f.redacted}</span>
                <span className="badge shrink-0 bg-red-400/15 text-red-300">{f.pii.map((p) => p.type).join(', ')}</span>
              </div>
            ))}
            {!piiFiles.length && <div className="text-sm text-white/40">No identifiers detected 🎉</div>}
          </div>
          <Link to="/insights" className="btn-primary mt-4 w-full text-sm">Review {suggestions.length} suggestions <ArrowRight size={15} /></Link>
        </GlassCard>
      </div>
    </div>
  )
}
