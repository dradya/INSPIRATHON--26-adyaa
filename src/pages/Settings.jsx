import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check, LogOut, Bell, Palette, Info } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../components/Toast.jsx'
import { GlassCard } from '../components/ui.jsx'
import { APP } from '../config.js'

export const ACCENTS = [
  { id: 'midnight', name: 'Midnight', swatch: 'linear-gradient(135deg,#a99bff,#7c6cff,#3ddc97)' },
  { id: 'ocean', name: 'Ocean', swatch: 'linear-gradient(135deg,#7dd3fc,#38bdf8,#22d3ee)' },
  { id: 'sunset', name: 'Sunset', swatch: 'linear-gradient(135deg,#fda4af,#fb7185,#fbbf24)' }
]

export function applyAccent(id) {
  document.documentElement.dataset.accent = id
  try { localStorage.setItem('nova-accent', id) } catch { /* ignore */ }
}
export function initAccent() {
  try {
    const saved = localStorage.getItem('nova-accent')
    if (saved) document.documentElement.dataset.accent = saved
  } catch { /* ignore */ }
}

export default function Settings() {
  const { user, profile, signOut } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const [accent, setAccent] = useState(() => { try { return localStorage.getItem('nova-accent') || 'midnight' } catch { return 'midnight' } })
  const [notifs, setNotifs] = useState(() => { try { return localStorage.getItem('nova-notifs') !== 'off' } catch { return true } })

  useEffect(() => { applyAccent(accent) }, [accent])
  const toggleNotifs = (v) => {
    setNotifs(v)
    try { localStorage.setItem('nova-notifs', v ? 'on' : 'off') } catch { /* ignore */ }
    toast.info(v ? 'Notifications on 🔔' : 'Notifications muted 🔕')
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Settings</h1>

      <GlassCard>
        <div className="flex items-center gap-2 font-display font-bold"><Palette size={16} className="text-mint" /> Appearance</div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {ACCENTS.map((a) => (
            <button key={a.id} onClick={() => setAccent(a.id)} className={`rounded-2xl border p-3 text-left ${accent === a.id ? 'border-mint' : 'border-white/10 hover:border-white/25'}`}>
              <span className="block h-10 rounded-xl" style={{ background: a.swatch }} />
              <span className="mt-2 flex items-center gap-1 text-xs font-bold">{a.name}{accent === a.id && <Check size={12} className="text-mint" />}</span>
            </button>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <div className="flex items-center gap-2 font-display font-bold"><Bell size={16} className="text-mint" /> Notifications</div>
        <label className="mt-3 flex cursor-pointer items-center justify-between rounded-xl bg-white/5 px-4 py-3 text-sm">
          <span className="text-white/75">In-app activity alerts <span className="text-white/35">(comments on your {APP.entityPlural.toLowerCase()})</span></span>
          <input type="checkbox" checked={notifs} onChange={(e) => toggleNotifs(e.target.checked)} className="h-4 w-4 accent-[#7c6cff]" />
        </label>
      </GlassCard>

      <GlassCard>
        <div className="flex items-center gap-2 font-display font-bold"><Info size={16} className="text-mint" /> Account</div>
        <div className="mt-2 text-sm text-white/60">Signed in as <span className="font-semibold text-white">{profile?.full_name || user?.email}</span></div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to="/profile" className="btn-ghost !py-2 text-xs">Edit profile</Link>
          <button onClick={async () => { await signOut(); nav('/') }} className="btn-ghost !py-2 text-xs text-red-300"><LogOut size={13} /> Sign out</button>
        </div>
      </GlassCard>
    </div>
  )
}
