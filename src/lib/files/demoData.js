// Synthetic "messy student laptop" vault — instant demo, zero setup.
// Seeded RNG so every judge sees the same numbers.
import { redactName } from './pii.js'

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const rnd = mulberry32(20260214)
const pick = (arr) => arr[Math.floor(rnd() * arr.length)]
const MB = 1024 * 1024
const GB = 1024 * MB

const now = Date.now()
const daysAgo = (d) => new Date(now - d * 864e5 - Math.floor(rnd() * 864e5)).toISOString()

let seq = 0
function F(folder, name, size, ageDays, opts = {}) {
  const ext = (name.split('.').pop() || '').toLowerCase()
  const { redacted, hits } = redactName(name)
  const pii = [...hits.map((h) => ({ type: h.type, label: h.label, count: h.count }))]
  if (opts.contentPii) pii.push(...opts.contentPii)
  return {
    id: `demo-${++seq}`,
    name,
    redacted,
    path: `${folder}/${name}`,
    kind: opts.kind || 'other',
    ext,
    size,
    modified: daysAgo(ageDays),
    contentHash: opts.hash || null,
    pii,
    _contentHits: opts.contentPii || []
  }
}

export function generateDemoVault() {
  const files = []
  seq = 0

  // --- intentional duplicate families (same contentHash, different names/places)
  const dupFam = [
    { names: ['IMG_20240512_143210.jpg', 'IMG_20240512_143210 (1).jpg', 'whatsapp_img_may12.jpg'], folder: 'Pictures', size: 4.2 * MB },
    { names: ['resume_final.pdf', 'resume_final_FINAL2.pdf', 'resume (1).pdf'], folder: 'Documents', size: 0.4 * MB },
    { names: ['Screen Recording 2024-03-01.mp4', 'Screen Recording 2024-03-01 (copy).mp4'], folder: 'Videos', size: 812 * MB },
    { names: ['notes_sem4.txt', 'notes_sem4 - Copy.txt', 'notes_sem4 - Copy (2).txt'], folder: 'Documents', size: 0.09 * MB },
    { names: ['project_Default Project.zip', 'project_Default Project (1).zip'], folder: 'Downloads', size: 240 * MB }
  ]
  let h = 0
  for (const fam of dupFam) {
    const hash = `demo-hash-${++h}`
    fam.names.forEach((n, i) => files.push(F(fam.folder, n, fam.size, [40, 41, 200][i] || 90, { kind: fam.folder === 'Videos' ? 'video' : fam.folder === 'Pictures' ? 'image' : 'document', hash })))
  }

  // --- Downloads chaos: installers, zips, unnamed
  const dl = ['Setup.exe', 'installer (2).exe', 'dataset_part1.zip', 'dataset_part2.zip', 'Untitled spreadsheet.xlsx', 'Document1.docx', 'photo.png', 'screenshot_12-01.png', 'Invoice-Dec.pdf', 'coupon_QR.jpg', 'live_wallpaper_4k.mp4', 'song_final_mix_v7.mp3', 'notes.txt', 'todo.txt', 'college_form_filled.pdf', 'fee_receipt_2023.pdf', 'hostel_allotment.pdf']
  dl.forEach((n) => files.push(F('Downloads', n, Math.floor(rnd() * 90 * MB) + 50 * 1024, Math.floor(rnd() * 500), { kind: guessKind(n) })))
  for (let i = 0; i < 26; i++) files.push(F('Downloads', `download_${1000 + i}.bin`, Math.floor(rnd() * 40 * MB), Math.floor(rnd() * 400), { kind: 'other' }))
  for (let i = 0; i < 8; i++) files.push(F('Downloads', `~temp_${i}.tmp`, Math.floor(rnd() * 5 * MB), Math.floor(rnd() * 300), { kind: 'temp' }))
  files.push(F('Downloads', 'app-debug.log', 320 * MB, 120, { kind: 'temp' }))

  // --- Documents: semesters + sensitive leaks (the privacy story)
  const docs = ['Maths_M2_unit3.pdf', 'DBMS_lab_manual.docx', 'timetable_even_sem.pdf', 'presentation_draft.pptx', 'presentation_draft_v2.pptx', 'internship_certificate.pdf', 'bonafide_request.docx', 'Aadhaar_Card_Rahul.pdf', 'PAN_verma.pdf', 'bank_statement_mar.pdf', 'rent_agreement_2024.pdf', 'passport_photo.jpg', 'rahul.verma98@gmail.com_cv.pdf', 'upi_rahulverma@okhdfc_receipts.xlsx']
  docs.forEach((n) => {
    const extra = n.includes('bank_statement') ? [{ type: 'card', label: 'Card number', count: 3 }] : n.includes('api') ? [{ type: 'secret', label: 'API secret / key', count: 1 }] : []
    files.push(F('Documents', n, Math.floor(rnd() * 8 * MB) + 60 * 1024, Math.floor(rnd() * 600), { kind: guessKind(n), contentPii: extra }))
  })
  files.push(F('Documents', 'api_keys.txt', 2048, 60, { kind: 'code', contentPii: [{ type: 'secret', label: 'API secret / key', count: 2 }, { type: 'password', label: 'Embedded password', count: 1 }] }))
  files.push(F('Documents', 'passwords_backup.txt', 1024, 300, { kind: 'code', contentPii: [{ type: 'password', label: 'Embedded password', count: 6 }] }))

  // --- Pictures: camera dumps, screenshots, memes
  for (let i = 0; i < 34; i++) files.push(F('Pictures', `IMG_2024${String(101 + i).slice(1)}_${100000 + Math.floor(rnd() * 899999)}.jpg`, Math.floor(rnd() * 6 * MB) + MB, Math.floor(rnd() * 500), { kind: 'image' }))
  for (let i = 0; i < 18; i++) files.push(F('Pictures', `Screenshot 2024-0${1 + (i % 9)}-${10 + (i % 18)} at 10.2${i % 10} AM.png`, Math.floor(rnd() * 3 * MB) + 200 * 1024, Math.floor(rnd() * 300), { kind: 'image' }))
  for (let i = 0; i < 6; i++) files.push(F('Pictures', `DSC_00${i}.jpg`, 5 * MB, 700 + i, { kind: 'image' }))

  // --- Videos / Music: the space hogs
  const vids = [['trip_goa_day1.mp4', 1.4 * GB, 200], ['trip_goa_day2.mp4', 1.1 * GB, 200], ['birthday_vlog.mp4', 900 * MB, 400], ['lecture_recording DBMS.mp4', 650 * MB, 90], ['movie_night.mkv', 2.2 * GB, 350], ['tutorial_react_part1.mp4', 480 * MB, 30]]
  vids.forEach(([n, s, a]) => files.push(F('Videos', n, Math.floor(s), a, { kind: 'video' })))
  for (let i = 0; i < 22; i++) files.push(F('Music', `track_${i + 1}.mp3`, Math.floor(rnd() * 9 * MB) + 3 * MB, Math.floor(rnd() * 700), { kind: 'audio' }))

  // --- Desktop + Projects clutter
  const desk = ['TODO.txt', 'imp_links.txt', 'wallpaper_hd.jpg', 'New folder (3)', 'hackathon_idea.md', 'Untitled-1.py', 'paytm_98765XXXXX_qr.png']
  desk.forEach((n) => files.push(F('Desktop', n, Math.floor(rnd() * 4 * MB) + 1024, Math.floor(rnd() * 250), { kind: guessKind(n) })))
  const proj = ['node_modules_backup.zip', 'old_project_final.zip', 'site_v1.tar.gz', 'main.py', 'App.jsx', 'README.md', '.env.local']
  proj.forEach((n, i) => files.push(F('Projects', n, [180 * MB, 210 * MB, 90 * MB, 12 * 1024, 9 * 1024, 3 * 1024, 512][i], [300, 320, 250, 12, 12, 12, 12][i], {
    kind: guessKind(n),
    contentPii: n === '.env.local' ? [{ type: 'secret', label: 'API secret / key', count: 3 }] : []
  })))

  const log = files.flatMap((f) => f.pii.map((p) => ({ file: f.redacted, type: p.label, count: p.count }))).slice(0, 200)
  return { files, log, source: 'Demo Vault (messy student laptop)' }
}

function guessKind(name) {
  const ext = (name.split('.').pop() || '').toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'bmp', 'svg'].includes(ext)) return 'image'
  if (['mp4', 'mkv', 'mov', 'avi', 'webm'].includes(ext)) return 'video'
  if (['mp3', 'wav', 'flac', 'ogg', 'm4a'].includes(ext)) return 'audio'
  if (['pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'].includes(ext)) return 'document'
  if (['zip', 'rar', 'tar', 'gz', '7z'].includes(ext)) return 'archive'
  if (['js', 'jsx', 'py', 'java', 'c', 'cpp', 'ts', 'html', 'css', 'json', 'env', 'local'].includes(ext) || name.startsWith('.env')) return 'code'
  if (['exe', 'msi', 'dmg', 'apk'].includes(ext)) return 'app'
  if (['tmp', 'log', 'bak', 'cache'].includes(ext) || name.startsWith('~')) return 'temp'
  return 'other'
}

export { pick }
