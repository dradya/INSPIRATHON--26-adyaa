import { useMemo, useState } from 'react'
import { Copy, HardDrive, Clock, FileX } from 'lucide-react'
import { useFS } from '../context/FSContext.jsx'
import { GlassCard, Empty } from '../components/ui.jsx'
import { fmtBytes } from '../lib/files/insights.js'
import { useToast } from '../components/Toast.jsx'

export default function Cleanup() {
  const { files, status, dups, removeFiles } = useFS()
  const toast = useToast()
  const [tab, setTab] = useState('dups')
  const [checked, setChecked] = useState({})
  const [confirming, setConfirming] = useState(false)
  const [cleaning, setCleaning] = useState(false)

  const large = useMemo(() => [...files].filter((f) => f.size > 100 * 1024 * 1024).sort((a, b) => b.size - a.size).slice(0, 30), [files])
  const stale = useMemo(() => files.filter((f) => Date.now() - new Date(f.modified).getTime() > 180 * 864e5).sort((a, b) => b.size - a.size).slice(0, 30), [files])
  const temps = useMemo(() => files.filter((f) => f.kind === 'temp').sort((a, b) => b.size - a.size), [files])

  if (status !== 'ready') return <div className="mx-auto max-w-3xl px-5 py-14"><Empty title="No scan loaded" hint="Load the demo vault or scan a folder from the Dashboard." /></div>

  const rows = tab === 'dups' ? null : tab === 'large' ? large : tab === 'stale' ? stale : temps
  const toggle = (id) => setChecked((c) => ({ ...c, [id]: !c[id] }))

  const selectedBytes = () => {
    if (tab === 'dups') {
      let b = 0
      dups.forEach((g, gi) => g.files.forEach((f, fi) => { if (fi > 0 && checked[`${gi}:${f.id}`]) b += f.size }))
      return b
    }
    return (rows || []).filter((f) => checked[f.id]).reduce((a, f) => a + f.size, 0)
  }

  const getSelectedIds = () => {
    if (tab === 'dups') {
      const ids = []
      dups.forEach((g, gi) => g.files.forEach((f, fi) => {
        if (fi > 0 && checked[`${gi}:${f.id}`]) ids.push(f.id)
      }))
      return ids
    }
    return (rows || []).filter(f => checked[f.id]).map(f => f.id)
  }

  const queue = async () => {
    const ids = getSelectedIds()
    if (!ids.length) return toast.info('Select files first ☝️')
    if (!confirming) {
      setConfirming(true)
      return
    }
    setCleaning(true)
    try {
      const result = await removeFiles(ids)
      toast.ok(`✓ Removed ${result.removed} files · freed ${fmtBytes(result.freedBytes)}`)
    } catch (e) {
      toast.err('Cleanup failed: ' + e.message)
    }
    setCleaning(false)
    setConfirming(false)
    setChecked({})
  }

  const cancelConfirm = () => { setConfirming(false) }

  const sb = selectedBytes()

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold md:text-4xl">Cleanup queue</h1>
          <p className="mt-1 text-sm text-white/50">Review → select → confirm. Files are removed from tracking and deleted when folder access permits.</p>
        </div>
        <div className="glass rounded-2xl px-5 py-3 text-center ring-1 ring-mint/30">
          <div className="font-display text-2xl font-bold text-mint">{fmtBytes(sb)}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-white/45">selected to free</div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {[
          ['dups', `Duplicates (${dups.length})`, Copy],
          ['large', `Large files (${large.length})`, HardDrive],
          ['stale', `Stale 6m+ (${stale.length})`, Clock],
          ['temp', `Temp & logs (${temps.length})`, FileX]
        ].map(([id, label, Icon]) => (
          <button key={id} onClick={() => { setTab(id); setChecked({}); setConfirming(false) }} className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold ${tab === id ? 'bg-neon text-ink' : 'bg-white/5 text-white/60 hover:text-white'}`}>
            <Icon size={14} /> {label}
          </button>
        ))}
        {confirming ? (
          <>
            <button onClick={cancelConfirm} className="btn-ghost ml-auto !py-2 text-sm">Cancel</button>
            <button onClick={queue} disabled={cleaning} className="btn-primary !py-2 text-sm !bg-red-500/80 hover:!bg-red-500">
              {cleaning ? 'Cleaning…' : `Confirm delete ${getSelectedIds().length} files`}
            </button>
          </>
        ) : (
          <button onClick={queue} className="btn-primary ml-auto !py-2 text-sm">Queue cleanup</button>
        )}
      </div>

      {tab === 'dups' ? (
        <div className="mt-4 space-y-3">
          {dups.map((g, gi) => (
            <GlassCard key={gi} className="!p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-bold">{g.files.length} identical files · {fmtBytes(g.files[0].size)} each</div>
                <span className="badge bg-mint/15 text-mint">frees {fmtBytes(g.waste)}</span>
              </div>
              <div className="mt-2 space-y-1.5">
                {g.files.map((f, fi) => (
                  <label key={f.id} className={`flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm ${fi === 0 ? 'bg-mint/10 ring-1 ring-mint/30' : 'bg-white/[.03] hover:bg-white/[.06]'}`}>
                    <input type="checkbox" checked={!!checked[`${gi}:${f.id}`]} onChange={() => fi !== 0 && toggle(`${gi}:${f.id}`)} disabled={fi === 0} className="h-4 w-4 accent-[#7c6cff]" />
                    <span className="truncate">{f.redacted}</span>
                    <span className="ml-auto shrink-0 text-[11px] text-white/35">{fi === 0 ? '★ keep original' : f.path.split('/')[0]}</span>
                  </label>
                ))}
              </div>
            </GlassCard>
          ))}
          {!dups.length && <Empty title="No duplicates" hint="Byte-identical files would group here." />}
        </div>
      ) : (
        <div className="glass mt-4 overflow-hidden rounded-2xl">
          {(rows || []).map((f) => (
            <label key={f.id} className="flex cursor-pointer items-center gap-3 border-b border-white/5 px-4 py-2.5 text-sm hover:bg-white/[.03]">
              <input type="checkbox" checked={!!checked[f.id]} onChange={() => toggle(f.id)} className="h-4 w-4 shrink-0 accent-[#7c6cff]" />
              <span className="truncate">{f.redacted}</span>
              <span className="ml-auto shrink-0 text-xs font-bold text-white/60">{fmtBytes(f.size)}</span>
            </label>
          ))}
          {!(rows || []).length && <div className="p-8 text-center text-sm text-white/40">Nothing in this bucket 🎉</div>}
        </div>
      )}
    </div>
  )
}
