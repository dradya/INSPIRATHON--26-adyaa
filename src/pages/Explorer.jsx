import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, ShieldAlert, ArrowUpDown, FolderTree, List } from 'lucide-react'
import { useFS } from '../context/FSContext.jsx'
import { GlassCard, Empty } from '../components/ui.jsx'
import { KIND_LABEL, fmtBytes, isUnnamed } from '../lib/files/insights.js'

const KINDS = ['all', 'image', 'video', 'audio', 'document', 'archive', 'code', 'app', 'temp', 'other']

function TreeNode({ name, node, depth = 0 }) {
  const [open, setOpen] = useState(depth < 2)
  const folders = Object.entries(node.children)
  const totalSize = [...node.files, ...Object.values(node.children).flatMap(c => c.files)].reduce((a, f) => a + (f.size || 0), 0)
  return (
    <div style={{ paddingLeft: depth * 16 }}>
      {folders.length > 0 || node.files.length > 0 ? (
        <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-sm hover:bg-white/5">
          <span className="text-mint">{open ? '▾' : '▸'}</span>
          <span className="font-medium">📁 {name}</span>
          <span className="ml-auto text-xs text-white/35">{fmtBytes(totalSize)}</span>
        </button>
      ) : null}
      {open && (
        <>
          {folders.map(([k, child]) => <TreeNode key={k} name={k} node={child} depth={depth + 1} />)}
          {node.files.map(f => (
            <div key={f.id} style={{ paddingLeft: (depth + 1) * 16 }} className="flex items-center gap-2 px-3 py-1 text-sm text-white/70">
              <span className="truncate">{f.redacted}</span>
              <span className="ml-auto shrink-0 text-xs text-white/40">{fmtBytes(f.size)}</span>
              {f.pii?.length > 0 && <span className="badge bg-red-400/15 text-red-300 text-[10px]">PII</span>}
            </div>
          ))}
        </>
      )}
    </div>
  )
}

const SEMANTIC_TAGS = {
  image: ['photo', 'picture', 'image', 'pic', 'screenshot', 'snap', 'selfie', 'wallpaper'],
  video: ['video', 'movie', 'film', 'clip', 'recording', 'footage'],
  audio: ['music', 'song', 'audio', 'podcast', 'recording', 'track', 'album'],
  document: ['document', 'doc', 'report', 'essay', 'paper', 'thesis', 'assignment', 'homework', 'notes', 'lecture'],
  code: ['code', 'script', 'program', 'source', 'project', 'repo', 'dev'],
  archive: ['archive', 'backup', 'compressed', 'zip'],
  temp: ['temporary', 'temp', 'cache', 'log', 'junk', 'trash'],
}

function semanticMatch(file, query) {
  const q = query.toLowerCase()
  // Direct match on name or extension
  if ((file.redacted || '').toLowerCase().includes(q) || (file.ext || '') === q.replace(/^\./, '')) return 2
  // Semantic match on file kind
  for (const [kind, tags] of Object.entries(SEMANTIC_TAGS)) {
    if (tags.some(t => q.includes(t)) && file.kind === kind) return 1
  }
  // Match common search intent
  if (q.includes('recent') && Date.now() - new Date(file.modified).getTime() < 7 * 864e5) return 1
  if (q.includes('old') && Date.now() - new Date(file.modified).getTime() > 365 * 864e5) return 1
  if (q.includes('large') && file.size > 100 * 1024 * 1024) return 1
  if (q.includes('small') && file.size < 1024 * 1024) return 1
  if ((q.includes('sensitive') || q.includes('private') || q.includes('pii')) && file.pii?.length) return 1
  return 0
}

export default function Explorer() {
  const { files, status } = useFS()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('all')
  const [flag, setFlag] = useState('all') // all | pii | unnamed | large
  const [sort, setSort] = useState('size') // size | recent | name
  const [view, setView] = useState('list')

  const list = useMemo(() => {
    let r = files.filter(f => {
      const kindMatch = kind === 'all' || f.kind === kind
      const flagMatch = flag === 'all' || (flag === 'pii' && f.pii?.length) || (flag === 'unnamed' && isUnnamed(f.name)) || (flag === 'large' && f.size > 100 * 1024 * 1024)
      if (!kindMatch || !flagMatch) return false
      if (!q) return true
      return semanticMatch(f, q) > 0
    })
    // Sort with semantic relevance when searching
    if (q) {
      r = r.map(f => ({ ...f, _relevance: semanticMatch(f, q) })).sort((a, b) => b._relevance - a._relevance || b.size - a.size)
    } else {
      r = [...r].sort((a, b) => sort === 'size' ? b.size - a.size : sort === 'recent' ? new Date(b.modified) - new Date(a.modified) : (a.redacted || '').localeCompare(b.redacted || ''))
    }
    return r.slice(0, 300)
  }, [files, q, kind, flag, sort])

  const tree = useMemo(() => {
    if (view !== 'tree') return null
    const root = { name: 'Root', children: {}, files: [] }
    for (const f of list) {
      const parts = (f.path || f.redacted).split('/')
      let node = root
      for (let i = 0; i < parts.length - 1; i++) {
        if (!node.children[parts[i]]) node.children[parts[i]] = { name: parts[i], children: {}, files: [] }
        node = node.children[parts[i]]
      }
      node.files.push(f)
    }
    return root
  }, [list, view])

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
            {q && <span className="text-[10px] text-mint/60">✨ semantic search active</span>}
          </span>
          <select className="input !w-auto" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => <option key={k} value={k} className="bg-ink">{k === 'all' ? 'All types' : KIND_LABEL[k]}</option>)}
          </select>
          <select className="input !w-auto" value={flag} onChange={(e) => setFlag(e.target.value)}>
            {[['all', 'All files'], ['pii', '⚠ PII-flagged'], ['unnamed', 'Auto-named'], ['large', '> 100 MB']].map(([v, l]) => <option key={v} value={v} className="bg-ink">{l}</option>)}
          </select>
          <button onClick={() => setSort(sort === 'size' ? 'recent' : sort === 'recent' ? 'name' : 'size')} className="btn-ghost !px-3 !py-2.5 text-xs"><ArrowUpDown size={14} /> {sort}</button>
          <button onClick={() => setView(v => v === 'list' ? 'tree' : 'list')} className="btn-ghost !px-3 !py-2.5 text-xs">
            {view === 'list' ? <FolderTree size={14} /> : <List size={14} />} {view}
          </button>
        </div>
      </GlassCard>

      <div className="mt-2 text-xs text-white/40">{list.length} shown{files.length > 300 ? ` of ${files.length} (top 300)` : ` of ${files.length}`}</div>
      {view === 'list' && (
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
      )}
      {view === 'tree' && tree && (
        <div className="glass mt-2 max-h-[60vh] overflow-y-auto scroll-thin rounded-2xl p-2">
          {Object.entries(tree.children).map(([k, child]) => <TreeNode key={k} name={k} node={child} />)}
          {tree.files.map(f => (
            <div key={f.id} className="flex items-center gap-2 px-3 py-1 text-sm text-white/70">
              <span className="truncate">{f.redacted}</span>
              <span className="ml-auto shrink-0 text-xs text-white/40">{fmtBytes(f.size)}</span>
            </div>
          ))}
        </div>
      )}
      <div className="mt-3 glass-soft rounded-xl px-4 py-3">
        <p className="text-xs text-white/50"><span className="font-bold text-mint">💡 Power user:</span> Mount network shares (SMB/NFS/SSHFS) as local drives first, then use "Scan real folder" to analyze them. VaultLens treats all mounted volumes as local — your data never leaves the machine.</p>
      </div>
    </div>
  )
}
