import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUp, Plus, Search } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { GlassCard, Empty } from '../components/ui.jsx'
import { APP } from '../config.js'

export default function Projects() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('All')
  const [form, setForm] = useState({ title: '', description: '', category: 'General' })

  const load = async () => {
    const { data } = await supabase.from('projects').select('*').order('created_at', { ascending: false }).limit(50)
    if (data) setRows(data)
  }
  useEffect(() => {
    load()
    const ch = supabase.channel('proj').on('postgres_changes', { event: '*', schema: 'public', table: 'projects' }, load).subscribe()
    return () => supabase.removeChannel(ch)
  }, [])

  const create = async (e) => {
    e.preventDefault()
    if (!user) return alert('Sign in first!')
    if (!form.title.trim()) return
    const { error } = await supabase.from('projects').insert({ ...form, owner_id: user.id })
    if (!error) { setForm({ title: '', description: '', category: 'General' }); load() }
  }
  const vote = async (id) => {
    if (!user) return alert('Sign in to upvote!')
    await supabase.rpc('toggle_vote', { p_target_type: 'project', p_target_id: id, p_value: 1 })
    load()
  }

  const list = rows.filter(r =>
    (cat === 'All' || r.category === cat) &&
    (r.title?.toLowerCase().includes(q.toLowerCase()) || r.description?.toLowerCase().includes(q.toLowerCase()))
  )

  return (
    <div className="mx-auto max-w-7xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">{APP.entityPlural}</h1>
      <p className="mt-1 text-sm text-white/50">Rebrand this page by editing <code className="rounded bg-white/10 px-1">APP.entityPlural</code> — e.g. Complaints, Cases, Ideas, Reports.</p>

      <GlassCard className="mt-5">
        <form onSubmit={create} className="grid gap-2 md:grid-cols-[1fr_1fr_160px_auto]">
          <input className="input" placeholder={`New ${APP.entityLabel.toLowerCase()} title…`} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          <input className="input" placeholder="One-line description…" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          <select className="input" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            {APP.categories.map(c => <option key={c} className="bg-ink">{c}</option>)}
          </select>
          <button className="btn-primary text-sm"><Plus size={15} /> Add</button>
        </form>
      </GlassCard>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <span className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
          <input className="input !w-56 !pl-9" placeholder="Search…" value={q} onChange={e => setQ(e.target.value)} />
        </span>
        {['All', ...APP.categories].map(c => (
          <button key={c} onClick={() => setCat(c)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${cat === c ? 'bg-neon text-ink' : 'bg-white/5 text-white/60 hover:text-white'}`}>{c}</button>
        ))}
      </div>

      {list.length === 0 ? <div className="mt-5"><Empty title={`No ${APP.entityPlural.toLowerCase()} yet`} hint="Run supabase/seed.sql for instant demo data, or add one above." /></div> : (
        <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {list.map((p, i) => (
            <GlassCard key={p.id} delay={Math.min(i * 0.04, 0.3)}>
              <div className="flex items-center justify-between text-[11px]">
                <span className="badge bg-neon/20 text-[#c9c2ff]">{p.category}</span>
                <span className={`badge ${p.status === 'active' ? 'bg-mint/15 text-mint' : 'bg-white/10 text-white/60'}`}>{p.status}</span>
              </div>
              <Link to={`/projects/${p.id}`} className="mt-2 block font-display text-lg font-bold leading-snug hover:text-[#c9c2ff]">{p.title}</Link>
              <p className="mt-1 line-clamp-2 text-sm text-white/55">{p.description}</p>
              <div className="mt-3 flex flex-wrap gap-1">{(p.tags || []).map(t => <span key={t} className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-white/50">#{t}</span>)}</div>
              <div className="mt-4 flex items-center justify-between">
                <button onClick={() => vote(p.id)} className="inline-flex items-center gap-1.5 rounded-xl bg-white/5 px-3 py-1.5 text-sm font-bold hover:bg-neon hover:text-ink"><ArrowUp size={14} /> {p.upvotes}</button>
                <span className="text-[11px] text-white/35">{new Date(p.created_at).toLocaleDateString()}</span>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  )
}
