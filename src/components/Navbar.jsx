import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bot, LayoutDashboard, FolderSearch, Trash2, Lightbulb, ShieldCheck, LogOut, Search, Settings, Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useFS } from '../context/FSContext.jsx'
import { APP } from '../config.js'
import NotificationsBell from './NotificationsBell.jsx'
import { openPalette } from './CommandPalette.jsx'

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, profile, signOut } = useAuth()
  const { status } = useFS()
  const nav = useNavigate()
  const links = [
    ['/dashboard', 'Dashboard', LayoutDashboard],
    ['/explorer', 'Explorer', FolderSearch],
    ['/cleanup', 'Cleanup', Trash2],
    ['/insights', 'Insights', Lightbulb],
    ['/privacy', 'Privacy', ShieldCheck],
    ['/agent', 'Agent', Bot]
  ]
  return (
    <header className="sticky top-0 z-40 border-b border-[#d4af37]/20 bg-[#090a0f]/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 px-5 py-3">
        <Link to="/" className="flex shrink-0 items-center gap-3">
          <div className="w-9 h-9 rounded-lg border border-[#d4af37]/50 bg-[#12141f] flex items-center justify-center shadow-[0_0_15px_rgba(212,175,55,0.25)] shrink-0">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
              <path d="M4 16C7 6 17 6 20 16" stroke="#d4af37" strokeWidth="2" strokeLinecap="round" />
              <line x1="12" y1="19" x2="12" y2="5" stroke="#38bdf8" strokeWidth="1.8" strokeLinecap="round" />
              <polygon points="12,3 9,7 15,7" fill="#f3e5ab" />
            </svg>
          </div>
          <span className="leading-tight">
            <span className="artifact-title block text-lg font-extrabold tracking-wider">{APP.name}</span>
            <span className="hidden text-[10px] tracking-[0.2em] uppercase text-[#9c7a44] sm:block">Gandiva Protocol Active</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-1 text-sm lg:flex">
          {links.map(([to, l, Icon]) => (
            <Link key={to} to={to} className="rounded-lg px-3 py-2 text-white/70 hover:bg-white/5 hover:text-white"><span className="inline-flex items-center gap-1.5"><Icon size={15} />{l}</span>
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {status === 'ready'
            ? <span className="badge hidden bg-mint/15 text-mint sm:inline-flex">● vault loaded</span>
            : <Link to="/dashboard" className="badge bg-peach/15 text-peach hover:text-white">○ no scan</Link>}
          <button onClick={openPalette} className="hidden items-center gap-1.5 rounded-xl bg-white/5 px-3 py-2 text-xs text-white/50 hover:text-white sm:inline-flex" title="Search (Ctrl+K)">
            <Search size={14} /> <kbd className="rounded bg-white/10 px-1 text-[10px]">⌘K</kbd>
          </button>
          {user ? (
            <>
              <NotificationsBell />
              <Link to="/settings" className="rounded-xl bg-white/5 p-2.5 text-white/70 hover:bg-white/10 hover:text-white" title="Settings"><Settings size={16} /></Link>
              <Link to="/profile" className="flex items-center gap-2 rounded-xl bg-white/5 py-1.5 pl-1.5 pr-3 hover:bg-white/10" title="Profile">
                {profile?.avatar_url
                  ? <img src={profile.avatar_url} alt="" className="h-7 w-7 rounded-lg object-cover" />
                  : <span className="grid h-7 w-7 place-items-center rounded-lg bg-neon/30 font-display text-xs font-bold">{(profile?.full_name?.[0] || user.email?.[0] || '?').toUpperCase()}</span>}
                <span className="hidden max-w-24 truncate text-xs text-white/70 xl:block">{profile?.full_name || user.email}</span>
              </Link>
              <button onClick={async () => { await signOut(); nav('/') }} className="rounded-xl bg-white/5 p-2.5 text-white/70 hover:text-white" title="Sign out"><LogOut size={16} /></button>
            </>
          ) : (
            <span className="badge bg-mint/15 text-mint">Local mode · on-device</span>
          )}
          <button onClick={() => setMobileOpen(!mobileOpen)} className="rounded-xl bg-white/5 p-2.5 text-white/70 hover:text-white lg:hidden">
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>
      {mobileOpen && (
        <div className="border-t border-white/10 bg-ink/95 px-4 py-3 lg:hidden">
          <div className="grid grid-cols-2 gap-2">
            {links.map(([to, l, Icon]) => (
              <Link key={to} to={to} onClick={() => setMobileOpen(false)} className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2.5 text-sm text-white/70 hover:bg-white/10 hover:text-white">
                <Icon size={15} /> {l}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  )
}
