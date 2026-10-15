import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, ShieldAlert, ArrowUpDown } from 'lucide-react'
import { useFS } from '../context/FSContext.jsx'
import { GlassCard, Empty } from '../components/ui.jsx'
import { KIND_LABEL, fmtBytes, isUnnamed } from '../lib/files/insights.js'

const KINDS = ['all', 'image', 'video', 'audio', 'document', 'archive', 'code', 'app', 'temp', 'other']

export default function Explorer() {
  const { files, status } = useFS()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('all')
  const [flag, setFlag] = useState('all') // all | pii | unnamed | large
  const [sort, setSort] = useState('size') // size | recent | name

  const list = useMemo(() => {
    let r = files.filter((f) =>
      (kind === 'all' || f.kind === kind) &&
      (!q || (f.redacted || '').toLowerCase().includes(q.toLowerCase()) || (f.ext || '').includes(q.toLowerCase())) &&
      (flag === 'all' || (flag === 'pii' && f.pii?.length) || (flag === 'unnamed' && isUnnamed(f.name)) || (flag === 'large' && f.size > 100 * 1024 * 1024))
    )
    r = [...r].sort((a, b) => sort === 'size' ? b.size - a.size : sort === 'recent' ? new Date(b.modified) - new Date(a.modified) : (a.redacted || '').localeCompare(b.redacted || ''))
    return r.slice(0, 300)
  }, [files, q, kind, flag, sort])

  if (status !== 'ready') return <div className="mx-auto max-w-3xl px-5 py-14"><Empty title="No scan loaded" hint="Load the demo vault or scan a folder from the Dashboard." /></div>

  return (
    <div className="mx-auto max-w-7xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Explorer</h1>
      <p className="mt-1 text-sm text-white/50">Every file below was read on-device. Names shown are the redacted versions — the exact strings any cloud service would see.</p>

      <GlassCard className="mt-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="relative grow sm:max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
            <input className="input !pl-9" placeholder="Search name or extension… e.g. resume, mp4" value={q} onChange={(e) => setQ(e.target.value)} />
          </span>
          <select className="input !w-auto" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => <option key={k} value={k} className="bg-ink">{k === 'all' ? 'All types' : KIND_LABEL[k]}</option>)}
          </select>
          <select className="input !w-auto" value={flag} onChange={(e) => setFlag(e.target.value)}>
            {[['all', 'All files'], ['pii', '⚠ PII-flagged'], ['unnamed', 'Auto-named'], ['large', '> 100 MB']].map(([v, l]) => <option key={v} value={v} className="bg-ink">{l}</option>)}
          </select>
          <button onClick={() => setSort(sort === 'size' ? 'recent' : sort === 'recent' ? 'name' : 'size')} className="btn-ghost !px-3 !py-2.5 text-xs"><ArrowUpDown size={14} /> {sort}</button>
        </div>
      </GlassCard>

      <div className="mt-2 text-xs text-white/40">{list.length} shown{files.length > 300 ? ` of ${files.length} (top 300)` : ` of ${files.length}`}</div>
      <div className="glass mt-2 overflow-hidden rounded-2xl">
        <div className="hidden grid-cols-[1fr_90px_90px_110px_120px] gap-3 border-b border-white/10 px-4 py-2.5 text-[10px] font-bold uppercase tracking-widest text-white/35 md:grid">
          <span>Name (redacted)</span><span>Type</span><span className="text-right">Size</span><span>Modified</span><span>Flags</span>
        </div>
        <div className="max-h-[60vh] overflow-y-auto scroll-thin">
          {list.map((f) => (
            <div key={f.id} className="grid grid-cols-1 gap-1 border-b border-white/5 px-4 py-2.5 text-sm hover:bg-white/[.03] md:grid-cols-[1fr_90px_90px_110px_120px] md:items-center md:gap-3">
              <span className="truncate font-medium text-white/90" title={f.redacted}>{f.redacted}</span>
              <span className="text-xs text-white/45">{KIND_LABEL[f.kind] || f.kind} · .{f.ext}</span>
              <span className="text-xs font-bold text-white/70 md:text-right">{fmtBytes(f.size)}</span>
              <span className="text-xs text-white/40">{new Date(f.modified).toLocaleDateString()}</span>
              <span className="flex gap-1">
                {f.pii?.length > 0 && <span className="badge bg-red-400/15 text-red-300"><ShieldAlert size={10} /> {f.pii.length}</span>}
                {isUnnamed(f.name) && <span className="badge bg-peach/15 text-peach">auto-name</span>}
                {f.contentHash && <span className="badge bg-neon/15 text-[#c9c2ff]">hashed</span>}
              </span>
            </div>
          ))}
          {!list.length && <div className="p-8 text-center text-sm text-white/40">No matches — try a different query.</div>}
        </div>
      </div>
      <p className="mt-3 text-center text-xs text-white/35">Power-user note: connect network drives by mounting them in your OS first, then “Scan real folder”. <Link to="/privacy" className="text-mint">Privacy proof →</Link></p>
    </div>
  )
}
