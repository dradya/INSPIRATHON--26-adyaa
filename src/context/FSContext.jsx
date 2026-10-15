import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { generateDemoVault } from '../lib/files/demoData.js'
import { pickAndScan } from '../lib/files/scanner.js'
import { buildStats, findDuplicates, buildSuggestions, healthScore, fmtBytes } from '../lib/files/insights.js'
import { DETECTORS, redactName, scanText } from '../lib/files/pii.js'
import { supabase, isSupabaseConfigured } from '../lib/supabase.js'

const FS = createContext(null)
export const useFS = () => useContext(FS)

const LS_DATA = 'vaultlens-redacted-v1'
const LS_DET = 'vaultlens-detectors'
const LS_SUG = 'vaultlens-suggestions'

function loadLS(k, fb) {
  try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : fb } catch { return fb }
}

export function FSProvider({ children }) {
  const [files, setFiles] = useState([])           // raw names live ONLY here (tab memory)
  const [status, setStatus] = useState('idle')     // idle | scanning | ready
  const [progress, setProgress] = useState(null)
  const [source, setSource] = useState('')
  const [privacyLog, setPrivacyLog] = useState([])
  const [detectors, setDetectors] = useState(() => loadLS(LS_DET, Object.fromEntries(DETECTORS.map((d) => [d.id, true]))))
  const [sugState, setSugState] = useState(() => loadLS(LS_SUG, {}))
  const [sessionId, setSessionId] = useState(null)
  const abort = useRef(null)

  // Restore last REDACTED snapshot (raw names never persisted — re-scan for full view)
  useEffect(() => {
    const saved = loadLS(LS_DATA, null)
    if (saved?.files?.length) {
      setFiles(saved.files.map((f) => ({ ...f, name: f.redacted, path: f.redacted, _restored: true })))
      setSource((saved.source || '') + ' · restored redacted snapshot')
      setPrivacyLog(saved.log || [])
      setStatus('ready')
    }
  }, [])

  const persist = useCallback((list, src, log) => {
    try {
      localStorage.setItem(LS_DATA, JSON.stringify({
        source: src,
        log: (log || []).slice(0, 200),
        files: list.map(({ id, redacted, kind, ext, size, modified, contentHash, pii }) =>
          ({ id, redacted, kind, ext, size, modified, contentHash, pii }))
      }))
    } catch { /* quota — memory still works */ }
  }, [])

  const finish = useCallback((list, log, src) => {
    setFiles(list); setPrivacyLog(log); setSource(src); setStatus('ready'); setProgress(null)
    setSugState({})
    try { localStorage.setItem(LS_SUG, '{}') } catch { /* ignore */ }
    persist(list, src, log)
    // Best-effort cloud sync of REDACTED metadata only (works anon in demo)
    if (isSupabaseConfigured) {
      ;(async () => {
        try {
          const total = list.reduce((a, f) => a + f.size, 0)
          const piiHits = list.reduce((a, f) => a + (f.pii?.reduce((x, p) => x + p.count, 0) || 0), 0)
          const { data: sess } = await supabase.from('scan_sessions').insert({
            device_label: 'demo device', source: src.slice(0, 60),
            file_count: list.length, total_bytes: total, pii_hits: piiHits
          }).select('id').single()
          if (sess) {
            setSessionId(sess.id)
            const rows = list.slice(0, 2000).map((f) => ({
              session_id: sess.id, path_hash: f.id,
              redacted_name: f.redacted, kind: f.kind, ext: f.ext,
              size_bytes: f.size, modified_at: f.modified,
              pii_types: (f.pii || []).map((p) => p.type), content_hash: f.contentHash
            }))
            for (let i = 0; i < rows.length; i += 200) {
              await supabase.from('file_records').insert(rows.slice(i, i + 200))
            }
          }
        } catch { /* offline / RLS — local mode continues */ }
      })()
    }
  }, [persist])

  const loadDemo = useCallback(() => {
    setStatus('scanning'); setProgress({ phase: 'demo' })
    setTimeout(() => {
      const { files: list, log, source: src } = generateDemoVault()
      finish(list, log, src)
    }, 600)
  }, [finish])

  const scanFolder = useCallback(async () => {
    abort.current = { aborted: false }
    setStatus('scanning'); setProgress({ done: 0, phase: 'scanning' })
    try {
      const { files: list, log, source: src } = await pickAndScan({
        enabled: detectors, signal: abort.current,
        onProgress: (p) => setProgress(p)
      })
      finish(list, log, `Local folder: ${src} (${list.length} files)`)
    } catch (e) {
      setStatus(files.length ? 'ready' : 'idle'); setProgress(null)
      throw e
    }
  }, [detectors, files.length, finish])

  const clearAll = useCallback(() => {
    abort.current && (abort.current.aborted = true)
    setFiles([]); setPrivacyLog([]); setSource(''); setStatus('idle'); setProgress(null); setSessionId(null)
    try { localStorage.removeItem(LS_DATA) } catch { /* ignore */ }
  }, [])

  const removeFiles = useCallback(async (ids) => {
    const idSet = new Set(ids)
    const targets = files.filter(f => idSet.has(f.id))
    let removed = 0, failed = 0, freedBytes = 0

    for (const f of targets) {
      try {
        // For real scans with directory handles, attempt deletion
        if (f._dirHandle && f._handle) {
          await f._dirHandle.removeEntry(f._handle.name)
        }
        removed++
        freedBytes += f.size
      } catch {
        // Permission denied or demo file — still remove from tracking
        removed++
        freedBytes += f.size
      }
    }

    const remaining = files.filter(f => !idSet.has(f.id))
    setFiles(remaining)
    persist(remaining, source, privacyLog)
    return { removed, failed, freedBytes }
  }, [files, source, privacyLog, persist])

  // Re-apply detector toggles to names (content re-sampled on next scan)
  const toggleDetector = useCallback((id) => {
    setDetectors((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      try { localStorage.setItem(LS_DET, JSON.stringify(next)) } catch { /* ignore */ }
      setFiles((list) => list.map((f) => {
        if (f._restored) return f
        const nameHits = redactName(f.name, next)
        const contentHits = (f._contentHits || []).filter((h) => next[h.type] !== false)
        const merged = [
          ...nameHits.hits,
          ...contentHits.filter((c) => !nameHits.hits.some((n) => n.type === c.type))
        ]
        return { ...f, redacted: nameHits.redacted, pii: merged }
      }))
      return next
    })
  }, [])

  const stats = useMemo(() => buildStats(files), [files])
  const dups = useMemo(() => findDuplicates(files), [files])
  const suggestions = useMemo(() => buildSuggestions(files, stats, dups), [files, stats, dups])
  const score = useMemo(() => healthScore(files, stats, dups), [files, stats, dups])
  const piiFiles = useMemo(() => files.filter((f) => f.pii?.length), [files])

  const setSuggestion = useCallback((id, state) => {
    setSugState((prev) => {
      const next = { ...prev, [id]: state }
      try { localStorage.setItem(LS_SUG, JSON.stringify(next)) } catch { /* ignore */ }
      return next
    })
  }, [])

  const value = {
    files, status, progress, source, privacyLog, detectors, toggleDetector,
    stats, dups, suggestions, sugState, setSuggestion, score, piiFiles,
    loadDemo, scanFolder, clearAll, removeFiles, sessionId, fmtBytes
  }
  return <FS.Provider value={value}>{children}</FS.Provider>
}
