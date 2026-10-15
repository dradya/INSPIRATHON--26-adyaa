// Insights engine — pure functions over the in-memory file list.

export const KIND_LABEL = {
  image: 'Images', video: 'Videos', audio: 'Audio', document: 'Documents',
  archive: 'Archives', code: 'Code', app: 'Apps & installers', temp: 'Temp & logs', other: 'Other'
}

export function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(u.length - 1, Math.floor(Math.log(b) / Math.log(1024)))
  return `${(b / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${u[i]}`
}

export function buildStats(files) {
  const byKind = {}
  const byFolder = {}
  let total = 0
  for (const f of files) {
    total += f.size
    byKind[f.kind] = (byKind[f.kind] || 0) + f.size
    const top = (f.path || '').split('/')[0] || 'Root'
    byFolder[top] = (byFolder[top] || 0) + f.size
  }
  return { total, count: files.length, byKind, byFolder }
}

export function findDuplicates(files) {
  const byHash = new Map()
  files.forEach((f) => {
    if (!f.contentHash) return
    if (!byHash.has(f.contentHash)) byHash.set(f.contentHash, [])
    byHash.get(f.contentHash).push(f)
  })
  return [...byHash.values()]
    .filter((g) => g.length > 1)
    .map((g) => ({ files: g, waste: g[0].size * (g.length - 1), size: g[0].size }))
    .sort((a, b) => b.waste - a.waste)
}

const UNNAMED = /^(img_|dsc_|screenshot|document\d*|untitled|new folder|download_|track_|photo|image)/i
export const isUnnamed = (n) => UNNAMED.test(n || '')
const isStale = (f, days = 180) => Date.now() - new Date(f.modified).getTime() > days * 864e5

export function buildSuggestions(files, stats, dups) {
  const out = []
  const dupWaste = dups.reduce((a, g) => a + g.waste, 0)
  const dupFiles = dups.reduce((a, g) => a + g.files.length, 0)
  if (dupFiles) out.push({
    id: 'dup', kind: 'space', title: `${dups.length} duplicate groups wasting ${fmtBytes(dupWaste)}`,
    detail: `${dupFiles} files are byte-identical copies. Keep one, clear the rest.`, impact: dupWaste, action: 'Review duplicates'
  })
  const bigMedia = files.filter((f) => (f.kind === 'video' || f.kind === 'audio') && f.size > 400 * 1024 * 1024)
  if (bigMedia.length) out.push({
    id: 'media', kind: 'space',
    title: `${bigMedia.length} heavy media files (${fmtBytes(bigMedia.reduce((a, f) => a + f.size, 0))})`,
    detail: `e.g. ${bigMedia.slice(0, 3).map((f) => f.redacted).join(', ')}. Move to external drive or compress.`,
    impact: bigMedia.reduce((a, f) => a + f.size, 0), action: 'Review large files'
  })
  const stale = files.filter((f) => /downloads/i.test(f.path) && isStale(f))
  if (stale.length > 5) out.push({
    id: 'stale', kind: 'organize', title: `${stale.length} stale files in Downloads`,
    detail: `Untouched for 6+ months (${fmtBytes(stale.reduce((a, f) => a + f.size, 0))}). Archive the keepers, drop the rest.`,
    impact: stale.reduce((a, f) => a + f.size, 0), action: 'Review stale files'
  })
  const unnamed = files.filter((f) => isUnnamed(f.name))
  if (unnamed.length > 10) out.push({
    id: 'rename', kind: 'organize', title: `${unnamed.length} auto-named files (IMG_, Screenshot, Document…)`,
    detail: 'Unsearchable names are why “that file from last sem” is unfindable. Batch-rename by event or subject.',
    impact: 0, action: 'See unnamed files'
  })
  const temps = files.filter((f) => f.kind === 'temp')
  if (temps.length) out.push({
    id: 'temp', kind: 'cleanup', title: `${temps.length} temp & log files safe to delete`,
    detail: `${fmtBytes(temps.reduce((a, f) => a + f.size, 0))} of .tmp / .log / ~ debris. Zero-risk cleanup.`,
    impact: temps.reduce((a, f) => a + f.size, 0), action: 'Review temp files'
  })
  const piiNames = files.filter((f) => f.pii?.length)
  if (piiNames.length) out.push({
    id: 'pii', kind: 'privacy',
    title: `${piiNames.length} files expose personal identifiers`,
    detail: 'Aadhaar, PAN, emails, secrets found in names or content. Rename + move to an encrypted folder before any cloud backup.',
    impact: 0, action: 'Review flagged files'
  })
  // extension sprawl: one folder, many types
  const sprawl = {}
  files.forEach((f) => {
    const top = (f.path || '').split('/')[0]
    sprawl[top] = sprawl[top] || new Set()
    sprawl[top].add(f.kind)
  })
  const messy = Object.entries(sprawl).filter(([, s]) => s.size >= 5).sort((a, b) => b[1].size - a[1].size)[0]
  if (messy) out.push({
    id: 'sort', kind: 'organize', title: `“${messy[0]}” mixes ${messy[1].size} file types`,
    detail: 'Auto-sort into type folders (Images, Videos, Docs…) in one click-equivalent pass.', impact: 0, action: 'Open explorer'
  })
  return out
}

export function healthScore(files, stats, dups) {
  let s = 100
  const dupWaste = dups.reduce((a, g) => a + g.waste, 0)
  if (stats.total) s -= Math.min(25, (dupWaste / stats.total) * 100)
  s -= Math.min(15, files.filter((f) => f.kind === 'temp').length * 0.8)
  s -= Math.min(15, files.filter((f) => isUnnamed(f.name)).length * 0.15)
  s -= Math.min(15, files.filter((f) => f.pii?.length).length * 1.2)
  s -= Math.min(10, files.filter((f) => isStale(f, 365)).length * 0.1)
  return Math.max(5, Math.round(s))
}
