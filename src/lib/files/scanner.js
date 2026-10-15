// Real on-device folder scan via the File System Access API (Chromium).
// Only METADATA is collected; tiny samples of small text files are read
// LOCALLY for PII detection and never stored raw.
import { redactName, scanText } from './pii.js'

const TEXT_EXTS = new Set(['txt', 'md', 'csv', 'json', 'js', 'jsx', 'ts', 'py', 'env', 'local', 'log', 'html', 'css'])
const SAMPLE_BYTES = 65536
const MAX_FILES = 5000
let seq = 0

function kindOf(ext, name) {
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'bmp', 'svg'].includes(ext)) return 'image'
  if (['mp4', 'mkv', 'mov', 'avi', 'webm'].includes(ext)) return 'video'
  if (['mp3', 'wav', 'flac', 'ogg', 'm4a'].includes(ext)) return 'audio'
  if (['pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'].includes(ext)) return 'document'
  if (['zip', 'rar', 'tar', 'gz', '7z'].includes(ext)) return 'archive'
  if (['js', 'jsx', 'py', 'java', 'c', 'cpp', 'ts', 'html', 'css', 'json'].includes(ext) || name.startsWith('.env')) return 'code'
  if (['exe', 'msi', 'dmg', 'apk'].includes(ext)) return 'app'
  if (['tmp', 'log', 'bak', 'cache'].includes(ext) || name.startsWith('~')) return 'temp'
  return 'other'
}

export function fsSupported() {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window
}

export async function pickAndScan({ onProgress, enabled, signal } = {}) {
  if (!fsSupported()) throw new Error('Use Chrome or Edge for real folder access — or load the Demo Vault.')
  const root = await window.showDirectoryPicker({ mode: 'read' })
  const files = []
  const log = []
  let done = 0

  async function walk(dirHandle, rel) {
    for await (const entry of dirHandle.values()) {
      if (signal?.aborted || files.length >= MAX_FILES) return
      const entryRel = rel ? `${rel}/${entry.name}` : entry.name
      try {
        if (entry.kind === 'directory') {
          await walk(entry, entryRel)
        } else {
          const fh = await dirHandle.getFileHandle(entry.name)
          const blob = await fh.getFile()
          const ext = (entry.name.split('.').pop() || '').toLowerCase()
          const { redacted, hits } = redactName(entry.name, enabled)
          const contentHits = []
          if (TEXT_EXTS.has(ext) && blob.size < 1024 * 1024) {
            try {
              const sample = await blob.slice(0, SAMPLE_BYTES).text()
              contentHits.push(...scanText(sample, enabled))
            } catch { /* unreadable — metadata only */ }
          }
          const pii = [...hits, ...contentHits.filter((c) => !hits.some((n) => n.type === c.type))]
          pii.forEach((p) => { if (log.length < 300) log.push({ file: redacted, type: p.label, count: p.count }) })
          files.push({
            id: `scan-${++seq}`,
            name: entry.name,
            redacted,
            path: entryRel,
            kind: kindOf(ext, entry.name),
            ext,
            size: blob.size,
            modified: new Date(blob.lastModified).toISOString(),
            contentHash: null,
            pii,
            _contentHits: contentHits,
            _handle: fh,
            _dirHandle: dirHandle
          })
          done++
          if (done % 25 === 0) onProgress?.({ done, phase: 'scanning' })
        }
      } catch { /* permission denied on entry — skip */ }
    }
  }

  await walk(root, root.name)
  onProgress?.({ done, phase: 'hashing' })
  await hashDuplicateCandidates(files, onProgress)
  return { files, log, source: root.name }
}

// Only same-size groups get hashed — fast even on huge folders.
export async function hashDuplicateCandidates(files, onProgress) {
  const bySize = new Map()
  files.forEach((f) => {
    if (!f._handle || f.size === 0 || f.size > 200 * 1024 * 1024) return
    if (!bySize.has(f.size)) bySize.set(f.size, [])
    bySize.get(f.size).push(f)
  })
  let hashed = 0
  for (const group of bySize.values()) {
    if (group.length < 2) continue
    for (const f of group) {
      try {
        const blob = await f._handle.getFile()
        const buf = await blob.arrayBuffer()
        const digest = await crypto.subtle.digest('SHA-256', buf)
        f.contentHash = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
      } catch { /* unreadable */ }
      hashed++
      if (hashed % 10 === 0) onProgress?.({ phase: 'hashing' })
    }
  }
}
