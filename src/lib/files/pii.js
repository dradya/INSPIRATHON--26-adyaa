// On-device PII detection + redaction. Runs 100% locally —
// nothing in this file ever touches the network.

export const DETECTORS = [
  { id: 'email', label: 'Email address', re: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g },
  { id: 'phone', label: 'Phone number', re: /(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b/g },
  { id: 'aadhaar', label: 'Aadhaar number', re: /\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b/g },
  { id: 'pan', label: 'PAN number', re: /\b[A-Z]{5}[0-9]{4}[A-Z]\b/g },
  { id: 'card', label: 'Card number', re: /\b(?:\d[ -]?){15,19}\b/g },
  { id: 'upi', label: 'UPI ID', re: /\b[a-zA-Z0-9._-]{2,30}@[a-zA-Z]{2,}(?![a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g },
  { id: 'secret', label: 'API secret / key', re: /\b(sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{16,}|xox[bap]-[A-Za-z0-9-]{8,}|AIza[A-Za-z0-9_-]{16,})\b/g },
  { id: 'password', label: 'Embedded password', re: /\b(password|passwd|pwd)\s*[:=]\s*\S+/gi },
  { id: 'ssn', label: 'SSN (US)', re: /\b\d{3}-\d{2}-\d{4}\b/g },
  { id: 'passport', label: 'Passport number', re: /\b[A-Z][0-9]{7}\b/g },
  { id: 'ip', label: 'IP address', re: /\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b/g },
  { id: 'jwt', label: 'JWT token', re: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g }
]

export function scanText(text, enabled) {
  const hits = []
  if (!text) return hits
  for (const d of DETECTORS) {
    if (enabled && enabled[d.id] === false) continue
    d.re.lastIndex = 0
    let n = 0
    while (d.re.exec(text) !== null) { n++; if (n > 50) break }
    if (n) hits.push({ type: d.id, label: d.label, count: n })
  }
  return hits
}

export function redactText(text, enabled) {
  if (!text) return text
  let out = text
  for (const d of DETECTORS) {
    if (enabled && enabled[d.id] === false) continue
    d.re.lastIndex = 0
    out = out.replace(d.re, `[REDACTED:${d.id.toUpperCase()}]`)
  }
  return out
}

// Filenames often leak identity ("Aadhaar_Rahul.pdf") — scrub them too.
export function redactName(name, enabled) {
  const hits = scanText(name, enabled)
  return { redacted: redactText(name, enabled), hits }
}

export async function sha256Hex(str) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str))
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')
}
