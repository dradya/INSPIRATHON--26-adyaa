import { supabase, isSupabaseConfigured } from './supabase.js'

// Optional LLM upgrade: deploy supabase/functions/agent-chat and set
// VITE_AGENT_ENDPOINT to its URL. Otherwise the built-in local brain
// below answers from LIVE workspace data — zero keys needed. Perfect demo.
export const AGENT_ENDPOINT = import.meta.env.VITE_AGENT_ENDPOINT || ''

export const SUGGESTIONS = [
  'What can I delete?',
  'Show duplicates',
  'Is my data private?',
  'How should I organize?',
  'Optimize my storage',
  'Find my resume',
  'File type breakdown',
  'What\'s eating space?'
]

export async function snapshotWorkspace() {
  if (!isSupabaseConfigured) return null
  try {
    const [statsRes, projRes, taskRes, postRes] = await Promise.all([
      supabase.from('dashboard_stats').select('*').single(),
      supabase.from('projects').select('id,title,category,status,upvotes').order('upvotes', { ascending: false }).limit(10),
      supabase.from('tasks').select('id,title,status,priority').order('created_at', { ascending: false }).limit(30),
      supabase.from('posts').select('id,body,kind,upvotes').order('created_at', { ascending: false }).limit(10)
    ])
    return {
      stats: statsRes.data || {},
      projects: projRes.data || [],
      tasks: taskRes.data || [],
      posts: postRes.data || []
    }
  } catch {
    return null
  }
}

export async function queryEndpoint(messages, snap) {
  if (!AGENT_ENDPOINT) return null
  try {
    const res = await fetch(AGENT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages.slice(-12), context: snap })
    })
    if (!res.ok) return null
    const json = await res.json()
    return typeof json?.reply === 'string' ? json.reply : null
  } catch {
    return null
  }
}

const NAV = [
  ['dashboard', '/dashboard', 'dashboard', 'home', 'overview', 'storage'],
  ['explorer', '/explorer', 'explorer', 'browse', 'files', 'folder'],
  ['cleanup', '/cleanup', 'cleanup', 'delete', 'free', 'space'],
  ['insights', '/insights', 'insight', 'suggestion', 'advice', 'recommend'],
  ['privacy', '/privacy', 'privacy', 'pii', 'redact', 'sensitive'],
  ['agent', '/agent'],
  ['profile', '/profile', 'account'],
  ['settings', '/settings', 'setting', 'preference', 'theme']
]

function findNav(text) {
  for (const [label, to, ...keys] of NAV) {
    if (keys.some((k) => text.includes(k))) return { label, to }
  }
  return null
}

// Local brain: deterministic, demo-safe, works offline from a snapshot.
// Returns { reply, action? } where action is executed by the chat hook.
export function runLocalAgent(rawText, snap, userName) {
  const text = rawText.toLowerCase().trim()
  const name = userName ? ` ${userName.split(' ')[0]}` : ''
  const noData = !snap

  if (/(^|\s)(hi|hello|hey|namaste|yo)\b/.test(text) && text.length < 24) {
    return { reply: `Hey${name}! 👋 I live inside your workspace — I can summarize it, find things, create tasks & projects, and take you anywhere. Try “summarize my workspace”.` }
  }
  if (text.includes('what can you') || text.includes('help') || text.includes('capabilit')) {
    return { reply: `Here's my menu:\n• Summarize workspace / stats\n• Top projects & open tasks\n• Find anything (“find hostel”)\n• Create tasks & projects (“create task buy domain”)\n• Navigate (“take me to the board”)\n\nWith VITE_AGENT_ENDPOINT set I upgrade to full LLM answers.` }
  }
  if (noData) {
    return { reply: `I can't see workspace data yet — connect Supabase (.env → npm run dev, schema.sql already run?) and I'll come alive. Meanwhile I can still navigate: try “take me to the board”.` , action: undefined }
  }

  if (text.includes('summar') || text.includes('overview') || text.includes('status report') || text.includes('how is') || text.includes('workspace')) {
    const s = snap.stats
    const open = snap.tasks.filter((t) => t.status !== 'done')
    const top = snap.projects.slice(0, 3).map((p) => `• ${p.title} (▲${p.upvotes})`).join('\n') || '• none yet'
    return { reply: `Workspace pulse 📊\n• ${s.active_projects ?? 0} active projects · ${s.total_posts ?? 0} posts · ${s.total_users ?? 0} users\n• Tasks: ${open.length} open, ${snap.tasks.filter((t) => t.status === 'done').length} done\nTop right now:\n${top}` }
  }
  if (text.includes('top') || text.includes('best') || text.includes('popular') || text.includes('trending')) {
    if (!snap.projects.length) return { reply: 'No projects yet — run seed.sql or say “create project …”.' }
    const list = snap.projects.slice(0, 5).map((p, i) => `${i + 1}. ${p.title} — ▲${p.upvotes} · ${p.category}`).join('\n')
    return { reply: `Leaderboard 🏆\n${list}`, action: { type: 'navigate', to: '/projects' } }
  }
  if (text.includes('open task') || text.includes('pending') || text.includes('todo') || (text.includes('task') && (text.includes('left') || text.includes('remain') || text.includes('what')))) {
    const open = snap.tasks.filter((t) => t.status !== 'done').slice(0, 8)
    if (!open.length) return { reply: 'Inbox zero 🎉 — no open tasks. Say “create task …” to add one.' }
    return { reply: `Open tasks (${snap.tasks.filter((t) => t.status !== 'done').length}):\n${open.map((t) => `• [${t.status}] ${t.title}`).join('\n')}`, action: { type: 'navigate', to: '/tasks' } }
  }
  if (text.includes('done') || text.includes('completed') || text.includes('finished')) {
    const done = snap.tasks.filter((t) => t.status === 'done')
    return { reply: done.length ? `Shipped ✓ (${done.length}):\n${done.slice(0, 6).map((t) => `• ${t.title}`).join('\n')}` : 'Nothing marked done yet — move a card on the board!' }
  }
  if (text.includes('how many')) {
    const s = snap.stats
    return { reply: `Counting… ${s.active_projects ?? snap.projects.length} active projects · ${snap.tasks.length} tasks tracked · ${s.total_posts ?? snap.posts.length} posts · ${s.total_users ?? '?'} users.` }
  }

  const createTask = text.match(/^(create|add|new)\s+(a\s+|me\s+a\s+)?task\s+(.+)/)
  if (createTask) {
    return { reply: `On it — creating task “${createTask[3].trim()}”.`, action: { type: 'createTask', title: createTask[3].trim() } }
  }
  const createProj = text.match(/^(create|add|new)\s+(a\s+|me\s+a\s+)?(project|idea|complaint|case|report)\s+(.+)/)
  if (createProj) {
    return { reply: `Drafting project “${createProj[4].trim()}” now.`, action: { type: 'createProject', title: createProj[4].trim() } }
  }
  const find = text.match(/^(find|search|look for|show me)\s+(.+)/)
  if (find) {
    const q = find[2].replace(/projects?|tasks?|posts?/g, '').trim()
    const hits = [
      ...snap.projects.filter((p) => (p.title || '').toLowerCase().includes(q)).map((p) => `📁 ${p.title} (▲${p.upvotes})`),
      ...snap.tasks.filter((t) => (t.title || '').toLowerCase().includes(q)).map((t) => `✓ [${t.status}] ${t.title}`)
    ].slice(0, 8)
    return { reply: hits.length ? `Found for “${q}”:\n${hits.map((h) => `• ${h}`).join('\n')}` : `Nothing matches “${q}” yet. Want me to create it? Say “create task ${q}”.` }
  }
  const nav = findNav(text)
  if (nav && /(take|go|open|show|navigate|to the|to)/.test(text)) {
    return { reply: `Taking you to ${nav.label} 🚀`, action: { type: 'navigate', to: nav.to } }
  }
  if (text.includes('thank')) return { reply: 'Anytime! Good luck at the hackathon — go ship it 🚀' }
  if (text.includes('who are you') || text.includes('your name')) return { reply: `I'm VaultLens Agent — your on-device file intelligence assistant. I analyze your storage, detect sensitive data, find duplicates, and help you organize. All analysis happens locally on your machine.` }

  // fallback: try a data-grounded guess
  const q = text.replace(/[?.,!]/g, '')
  const hit = snap.projects.find((p) => (p.title || '').toLowerCase().includes(q) && q.length > 3)
  if (hit) return { reply: `Yes — “${hit.title}” exists (${hit.category}, ▲${hit.upvotes}, ${hit.status}). Open Projects to dive in.`, action: { type: 'navigate', to: '/projects' } }
  return { reply: `Hmm, I can help most with workspace stuff — try:\n• “summarize my workspace”\n• “create task prepare pitch deck”\n• “take me to the board”` }
}

// ---- VaultLens file intents: answered from the on-device scan.
// Returns null when the message isn't file-related (caller falls through).
export function runFileAgent(rawText, fs) {
  if (!fs || fs.status !== 'ready' || !fs.files?.length) {
    if (/file|folder|scan|storage|space|duplicate|privacy|delete|free|optimi|breakdown|type/.test(rawText.toLowerCase()))
      return { reply: 'No scan loaded yet — hit “Load demo vault” on the Dashboard and I\'ll dig through it with you.' }
    return null
  }
  const text = rawText.toLowerCase().trim()
  const { files, stats, dups, suggestions, piiFiles } = fs
  const gb = (b) => b >= 1073741824 ? `${(b / 1073741824).toFixed(1)} GB` : `${Math.round(b / 1048576)} MB`
  const isFileQ = /file|find|search|look|where|resume|photo|video|document|pdf|mp4|jpg/.test(text)
  const isSpaceQ = /space|storage|big|largest|size|free|delete|remove|hog/.test(text)
  const isDupQ = /duplicate|duplicat|copy|copies|same/.test(text)
  const isPiiQ = /sensitive|private|privacy|pii|aadhaar|pan|leak|redact|safe|cloud/.test(text)
  const isOrgQ = /organiz|organize|mess|chaos|sort|advice|suggest|should/.test(text)
  const isOptQ = /optimi|compress|reduce|shrink|efficient|save space|tip|how to/.test(text)
  const isBreakdownQ = /breakdown|composition|what type|file type|distribut|categor/.test(text)
  if (!isFileQ && !isSpaceQ && !isDupQ && !isPiiQ && !isOrgQ && !isOptQ && !isBreakdownQ) return null

  if (isPiiQ && !isSpaceQ) {
    if (!piiFiles.length) return { reply: 'Clean bill 🛡️ — no personal identifiers detected in names or sampled content. The Privacy page shows the proof.' }
    const byType = {}
    piiFiles.forEach((f) => (f.pii || []).forEach((p) => { byType[p.label] = (byType[p.label] || 0) + p.count }))
    const top = Object.entries(byType).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => `• ${k}: ${v} hits`).join('\n')
    return { reply: `I found identifiers in ${piiFiles.length} files — all redacted on-device before anything could leave:\n${top}\n\nWorst offenders:\n${piiFiles.slice(0, 3).map((f) => `• ${f.redacted}`).join('\n')}`, action: { type: 'navigate', to: '/privacy' } }
  }
  if (isDupQ) {
    if (!dups.length) return { reply: 'No byte-identical duplicates — suspiciously tidy. 😄' }
    const waste = dups.reduce((a, g) => a + g.waste, 0)
    return { reply: `${dups.length} duplicate groups wasting ${gb(waste)}:\n${dups.slice(0, 4).map((g) => `• ${g.files.length}× ${g.files[0].redacted} (${gb(g.files[0].size)} each)`).join('\n')}\n\nOpening the cleanup queue…`, action: { type: 'navigate', to: '/cleanup' } }
  }
  if (isOptQ && !isDupQ) {
    const tips = []
    const videoSize = files.filter(f => f.kind === 'video').reduce((a, f) => a + f.size, 0)
    const imageSize = files.filter(f => f.kind === 'image').reduce((a, f) => a + f.size, 0)
    if (videoSize > 500 * 1024 * 1024) tips.push(`• Videos take ${gb(videoSize)} — convert to H.265/HEVC for ~50% savings`)
    if (imageSize > 200 * 1024 * 1024) tips.push(`• Images use ${gb(imageSize)} — batch convert PNG→WebP or use tinypng`)
    const dupWaste = dups.reduce((a, g) => a + g.waste, 0)
    if (dupWaste > 0) tips.push(`• Remove ${dups.length} duplicate groups to free ${gb(dupWaste)}`)
    const temps = files.filter(f => f.kind === 'temp')
    if (temps.length) tips.push(`• ${temps.length} temp/log files (${gb(temps.reduce((a,f) => a + f.size, 0))}) safe to delete`)
    const stale = files.filter(f => Date.now() - new Date(f.modified).getTime() > 365 * 864e5)
    if (stale.length > 10) tips.push(`• ${stale.length} files untouched for 1+ year — archive or remove`)
    if (!tips.length) tips.push('Your vault is already well-optimized! Health score: ' + fs.score)
    return { reply: `Storage optimization tips:\n${tips.join('\n')}\n\nTotal: ${gb(stats.total)} across ${stats.count} files.`, action: { type: 'navigate', to: '/insights' } }
  }
  if (isBreakdownQ) {
    const types = Object.entries(stats.byKind).sort((a,b) => b[1] - a[1]).map(([k,v]) => `• ${k}: ${gb(v)} (${files.filter(f=>f.kind===k).length} files)`).join('\n')
    return { reply: `File type breakdown:\n${types}\n\nTotal: ${gb(stats.total)}`, action: { type: 'navigate', to: '/dashboard' } }
  }
  if (isSpaceQ) {
    const big = [...files].sort((a, b) => b.size - a.size).slice(0, 5)
    const waste = dups.reduce((a, g) => a + g.waste, 0)
    return { reply: `Storage: ${gb(stats.total)} across ${stats.count} files.\nBiggest hogs:\n${big.map((f) => `• ${f.redacted} — ${gb(f.size)}`).join('\n')}\nDuplicates alone could free ${gb(waste)}. Say “show duplicates” or open Cleanup.`, action: { type: 'navigate', to: '/cleanup' } }
  }
  if (isOrgQ) {
    if (!suggestions.length) return { reply: 'Honestly? This vault looks organized already. 🎉' }
    return { reply: `My top advice:\n${suggestions.slice(0, 3).map((s, i) => `${i + 1}. ${s.title}`).join('\n')}\n\nFull plan with accept/dismiss is on Insights.`, action: { type: 'navigate', to: '/insights' } }
  }
  // find-a-file (default file intent)
  const q = text.replace(/^(find|search|look for|show me|where is|where's|get|open)\s+/, '').replace(/^(my|the|a|an)\s+/, '').replace(/[?.,!]/g, '').trim()
  if (q.length > 2) {
    // Semantic search: match by category, purpose, or description
    const SEMANTIC_MAP = {
      'resume': ['cv', 'curriculum', 'resume', 'vitae', 'career'],
      'photo': ['img', 'image', 'photo', 'picture', 'pic', 'screenshot', 'snap', 'selfie', 'dsc', 'dcim'],
      'assignment': ['assignment', 'homework', 'hw', 'lab', 'report', 'project', 'submission'],
      'notes': ['notes', 'lecture', 'class', 'study', 'cheat', 'summary'],
      'financial': ['bank', 'statement', 'invoice', 'receipt', 'tax', 'salary', 'pay', 'aadhaar', 'pan'],
      'music': ['song', 'music', 'audio', 'playlist', 'album', 'track'],
      'movie': ['movie', 'film', 'series', 'episode', 'season', 'video'],
      'code': ['code', 'script', 'program', 'source', 'github', 'repo', 'project'],
      'presentation': ['presentation', 'ppt', 'slide', 'deck', 'pitch'],
      'spreadsheet': ['excel', 'spreadsheet', 'sheet', 'csv', 'data', 'budget']
    }

    // Expand search terms if query matches any semantic category or term
    const searchTerms = [q]
    const qLower = q.toLowerCase()
    const qWords = qLower.split(/\s+/)

    for (const [category, synonyms] of Object.entries(SEMANTIC_MAP)) {
      const matchCat = qLower.includes(category) || category.includes(qLower) || qWords.some(w => w.startsWith(category) || category.startsWith(w))
      const matchSyn = synonyms.some(s => qWords.includes(s) || (s.length >= 3 && qLower.includes(s)))
      if (matchCat || matchSyn) {
        searchTerms.push(...synonyms)
      }
    }

    const uniqueTerms = [...new Set(searchTerms.filter(Boolean).map(s => s.toLowerCase()))]

    const hits = files.filter((f) => {
      const name = (f.redacted || f.name || '').toLowerCase()
      const ext = (f.ext || '').toLowerCase()
      const path = (f.path || '').toLowerCase()
      const kind = (f.kind || '').toLowerCase()

      return uniqueTerms.some((term) => {
        const cleanTerm = term.replace(/^\./, '')
        return name.includes(term) || ext === cleanTerm || path.includes(term) || kind === term
      })
    }).slice(0, 6)

    if (hits.length) return { reply: `Found ${hits.length}:\n${hits.map((f) => `• ${f.redacted} (${gb(f.size)})${f.pii?.length ? ' ⚠️PII' : ''}`).join('\n')}\n\nOpening Explorer…`, action: { type: 'navigate', to: '/explorer' } }
    return { reply: `No filename matches “${q}”. Try an extension (“mp4”, “pdf”) or browse the Explorer.` }
  }
  return { reply: `Vault status: ${stats.count} files, ${gb(stats.total)}, health ${fs.score}/100, ${dups.length} dup groups, ${piiFiles.length} PII-flagged. Ask me to find, free, or explain anything.` }
}
