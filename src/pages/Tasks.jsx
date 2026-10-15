import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { GlassCard } from '../components/ui.jsx'

const COLS = [
  { id: 'todo', title: 'To do', color: 'bg-white/10 text-white/70' },
  { id: 'doing', title: 'Doing', color: 'bg-peach/20 text-peach' },
  { id: 'done', title: 'Done ✓', color: 'bg-mint/15 text-mint' }
]

export default function Tasks() {
  const { user } = useAuth()
  const [tasks, setTasks] = useState([])
  const [title, setTitle] = useState('')

  const load = async () => {
    const { data } = await supabase.from('tasks').select('*').order('created_at', { ascending: false }).limit(100)
    if (data) setTasks(data)
  }
  useEffect(() => {
    load()
    const ch = supabase.channel('tasks').on('postgres_changes', { event: '*', schema: 'public', table: 'tasks' }, load).subscribe()
    return () => supabase.removeChannel(ch)
  }, [])

  const add = async (e) => {
    e.preventDefault()
    if (!user) return alert('Sign in first!')
    if (!title.trim()) return
    await supabase.from('tasks').insert({ title, created_by: user.id })
    setTitle(''); load()
  }
  const move = async (t, dir) => {
    const order = ['todo', 'doing', 'done']
    const next = order[Math.min(2, Math.max(0, order.indexOf(t.status) + dir))]
    if (next === t.status) return
    await supabase.from('tasks').update({ status: next }).eq('id', t.id)
    load()
  }
  const remove = async (id) => { await supabase.from('tasks').delete().eq('id', id); load() }

  return (
    <div className="mx-auto max-w-7xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Task board</h1>
      <p className="mt-1 text-sm text-white/50">Realtime Kanban — move cards live during your demo.</p>
      <form onSubmit={add} className="glass mt-5 flex gap-2 rounded-2xl p-3">
        <input className="input" placeholder="New task… e.g. Wire payment API" value={title} onChange={e => setTitle(e.target.value)} />
        <button className="btn-primary shrink-0 text-sm"><Plus size={15} /> Add</button>
      </form>
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {COLS.map(c => (
          <div key={c.id} className="glass-soft rounded-2xl p-3">
            <div className={`mb-3 inline-block rounded-full px-3 py-1 text-xs font-bold ${c.color}`}>{c.title} · {tasks.filter(t => t.status === c.id).length}</div>
            <div className="space-y-2">
              {tasks.filter(t => t.status === c.id).map(t => (
                <GlassCard key={t.id} className="!p-3">
                  <div className="text-sm font-semibold leading-snug">{t.title}</div>
                  {t.description && <div className="mt-1 text-xs text-white/50">{t.description}</div>}
                  <div className="mt-3 flex items-center gap-1.5">
                    <button onClick={() => move(t, -1)} className="rounded-lg bg-white/5 px-2 py-1 text-xs hover:bg-white/10">←</button>
                    <button onClick={() => move(t, 1)} className="rounded-lg bg-white/5 px-2 py-1 text-xs hover:bg-white/10">→</button>
                    <button onClick={() => remove(t.id)} className="ml-auto rounded-lg px-2 py-1 text-[11px] text-white/35 hover:text-red-300">delete</button>
                  </div>
                </GlassCard>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
