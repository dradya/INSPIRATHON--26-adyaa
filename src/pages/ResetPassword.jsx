import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase.js'
import { GlassCard } from '../components/ui.jsx'

export default function ResetPassword() {
  const nav = useNavigate()
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const go = async (e) => {
    e.preventDefault(); setBusy(true); setMsg('')
    const { error } = await supabase.auth.updateUser({ password })
    setBusy(false)
    if (error) setMsg(error.message + ' — open this page from the reset link in your email, on this device.')
    else { setMsg('Password updated ✓ — redirecting to sign in…'); setTimeout(() => nav('/login'), 1200) }
  }

  return (
    <div className="mx-auto max-w-md px-5 py-16">
      <GlassCard>
        <h1 className="font-display text-2xl font-bold">Set new password</h1>
        <p className="mt-1 text-xs text-white/50">You landed here from the reset email. Choose a new password below.</p>
        <form onSubmit={go} className="mt-4 space-y-3">
          <input className="input" type="password" placeholder="New password (min 6 chars)" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Saving…' : 'Update password'}</button>
        </form>
        {msg && <div className="mt-3 rounded-xl bg-white/5 p-3 text-xs text-white/70">{msg}</div>}
        <Link to="/login" className="mt-4 block text-center text-xs text-white/40 hover:text-white/70">← back to sign in</Link>
      </GlassCard>
    </div>
  )
}
