import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { GlassCard } from '../components/ui.jsx'

export default function Login() {
  const { signIn, signUp, signInGoogle } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState('in') // in | up | forgot
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const go = async (e) => {
    e.preventDefault(); setBusy(true); setMsg('')
    try {
      if (mode === 'forgot') {
        const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/reset-password` })
        setMsg(error ? error.message : 'Reset link sent ✓ — check your inbox.')
      } else {
        const { error } = mode === 'in' ? await signIn(email, password) : await signUp(email, password, name)
        if (error) setMsg(error.message)
        else { setMsg(mode === 'in' ? 'Welcome back ✓' : 'Account created ✓ — check email if confirmation is on'); setTimeout(() => nav('/dashboard'), 700) }
      }
    } finally { setBusy(false) }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6 px-5 py-14 md:grid-cols-2">
      <div className="flex flex-col justify-center">
        <h1 className="font-display text-4xl font-bold leading-tight md:text-5xl">Judges remember <span className="bg-gradient-to-r from-neon to-mint bg-clip-text text-transparent">polished auth.</span></h1>
        <p className="mt-3 text-white/55">Email + Google via Supabase Auth. Profiles auto-created by the SQL trigger — no extra code.</p>
        <ul className="mt-6 space-y-2 text-sm text-white/60">
          <li>✓ Enable Email provider in Supabase</li>
          <li>✓ Enable Google provider (optional, 2 min)</li>
          <li>✓ Add <code className="rounded bg-white/10 px-1">http://localhost:5173</code> to redirect URLs</li>
        </ul>
      </div>
      <GlassCard>
        <div className="flex rounded-xl bg-white/5 p-1 text-sm">
          {[['in','Sign in'],['up','Sign up']].map(([m,l]) => (
            <button key={m} onClick={() => setMode(m)} className={`flex-1 rounded-lg px-3 py-2 font-semibold ${mode===m?'bg-white/10 text-white':'text-white/50'}`}>{l}</button>
          ))}
        </div>
        <form onSubmit={go} className="mt-4 space-y-3">
          {mode === 'up' && <input className="input" placeholder="Full name" value={name} onChange={e => setName(e.target.value)} />}
          <input className="input" placeholder="you@college.edu" value={email} onChange={e => setEmail(e.target.value)} required />
          {mode !== 'forgot' && <input className="input" type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />}
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Please wait…' : mode === 'in' ? 'Sign in' : mode === 'up' ? 'Create account' : 'Send reset link'}</button>
        </form>
        {mode === 'in' && <button onClick={() => { setMode('forgot'); setMsg('') }} className="mt-2 w-full text-center text-xs text-white/40 hover:text-white/70">Forgot password?</button>}
        {mode === 'forgot' && <button onClick={() => { setMode('in'); setMsg('') }} className="mt-2 w-full text-center text-xs text-white/40 hover:text-white/70">← back to sign in</button>}
        <button onClick={signInGoogle} className="btn-ghost mt-3 w-full text-sm">Continue with Google</button>
        {msg && <div className="mt-3 rounded-xl bg-white/5 p-3 text-xs text-white/70">{msg}</div>}
        <Link to="/" className="mt-4 block text-center text-xs text-white/40 hover:text-white/70">← back home</Link>
      </GlassCard>
    </div>
  )
}
