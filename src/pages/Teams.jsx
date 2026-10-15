import { useEffect, useState } from 'react'
import { Plus, Copy, Check } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { GlassCard } from '../components/ui.jsx'

export default function Teams() {
  const { user } = useAuth()
  const [teams, setTeams] = useState([])
  const [name, setName] = useState('')
  const [copied, setCopied] = useState('')

  const load = async () => {
    const { data } = await supabase.from('teams').select('*, team_members(count)').order('created_at', { ascending: false }).limit(30)
    if (data) setTeams(data)
  }
  useEffect(() => { load() }, [])

  const create = async (e) => {
    e.preventDefault()
    if (!user) return alert('Sign in first!')
    if (!name.trim()) return
    const { data, error } = await supabase.from('teams').insert({ name, created_by: user.id }).select().single()
    if (!error && data) {
      await supabase.from('team_members').insert({ team_id: data.id, user_id: user.id, role: 'owner' })
      setName(''); load()
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Teams</h1>
      <p className="mt-1 text-sm text-white/50">Groups, departments, classes or orgs — with invite codes for demo.</p>
      <GlassCard className="mt-5">
        <form onSubmit={create} className="flex gap-2">
          <input className="input" placeholder="New team name… e.g. Team Nova" value={name} onChange={e => setName(e.target.value)} />
          <button className="btn-primary shrink-0 text-sm"><Plus size={15} /> Create</button>
        </form>
      </GlassCard>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {teams.map(t => (
          <GlassCard key={t.id}>
            <div className="font-display text-xl font-bold">{t.name}</div>
            <p className="mt-1 text-sm text-white/55">{t.description || 'No description yet.'}</p>
            <div className="mt-4 flex items-center gap-2">
              <code className="rounded-lg bg-white/5 px-3 py-1.5 text-xs ring-1 ring-white/10">invite: {t.invite_code}</code>
              <button
                onClick={() => { navigator.clipboard.writeText(t.invite_code); setCopied(t.id); setTimeout(() => setCopied(''), 1200) }}
                className="rounded-lg bg-white/5 p-2 hover:bg-white/10"
              >{copied === t.id ? <Check size={14} className="text-mint" /> : <Copy size={14} />}</button>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  )
}
