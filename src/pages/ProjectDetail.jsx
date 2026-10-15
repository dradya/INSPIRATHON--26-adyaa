import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowUp, ArrowLeft, Send, Plus, Pencil, Trash2 } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../components/Toast.jsx'
import { notifyUser } from '../lib/notify.js'
import { GlassCard } from '../components/ui.jsx'
import { APP } from '../config.js'

export default function ProjectDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const [project, setProject] = useState(null)
  const [ownerName, setOwnerName] = useState('')
  const [comments, setComments] = useState([])
  const [names, setNames] = useState({})
  const [tasks, setTasks] = useState([])
  const [draft, setDraft] = useState('')
  const [taskTitle, setTaskTitle] = useState('')
  const [editing, setEditing] = useState(false)
  const [edit, setEdit] = useState({ title: '', description: '', category: 'General', status: 'active' })

  const load = async () => {
    const { data: p } = await supabase.from('projects').select('*').eq('id', id).single()
    if (!p) return
    setProject(p)
    setEdit({ title: p.title, description: p.description || '', category: p.category, status: p.status })
    if (p.owner_id) {
      const { data: o } = await supabase.from('profiles').select('full_name').eq('id', p.owner_id).single()
      if (o) setOwnerName(o.full_name)
    }
    const { data: c } = await supabase.from('comments').select('*').eq('project_id', id).order('created_at')
    setComments(c || [])
    const aids = [...new Set((c || []).map((x) => x.author_id).filter(Boolean))]
    if (aids.length) {
      const { data: profs } = await supabase.from('profiles').select('id,full_name').in('id', aids)
      setNames(Object.fromEntries((profs || []).map((x) => [x.id, x.full_name])))
    }
    const { data: t } = await supabase.from('tasks').select('*').eq('project_id', id).order('created_at', { ascending: false })
    setTasks(t || [])
  }

  useEffect(() => { load() }, [id])

  if (!project) return <div className="mx-auto max-w-3xl px-5 py-14 text-center text-sm text-white/40">Loading…</div>
  const isOwner = user && project.owner_id === user.id

  const vote = async () => {
    if (!user) return toast.err('Sign in to upvote!')
    await supabase.rpc('toggle_vote', { p_target_type: 'project', p_target_id: id, p_value: 1 })
    load()
  }
  const comment = async (e) => {
    e.preventDefault()
    if (!user) return toast.err('Sign in to comment!')
    if (!draft.trim()) return
    const { error } = await supabase.from('comments').insert({ project_id: id, author_id: user.id, body: draft.trim() })
    if (error) return toast.err(error.message)
    setDraft(''); load()
    toast.ok('Comment posted ✓')
    if (project.owner_id && project.owner_id !== user.id) {
      notifyUser(project.owner_id, { title: `New comment on “${project.title}”`, body: draft.trim().slice(0, 120), link: `/projects/${id}` })
    }
  }
  const addTask = async (e) => {
    e.preventDefault()
    if (!user) return toast.err('Sign in first!')
    if (!taskTitle.trim()) return
    await supabase.from('tasks').insert({ project_id: id, title: taskTitle.trim(), created_by: user.id })
    setTaskTitle(''); load()
    toast.ok('Task added ✓')
  }
  const saveEdit = async (e) => {
    e.preventDefault()
    const { error } = await supabase.from('projects').update(edit).eq('id', id)
    if (error) return toast.err(error.message)
    setEditing(false); load()
    toast.ok('Updated ✓')
  }
  const remove = async () => {
    if (!confirm(`Delete “${project.title}”?`)) return
    await supabase.from('projects').delete().eq('id', id)
    toast.ok('Deleted')
    nav('/projects')
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8">
      <Link to="/projects" className="inline-flex items-center gap-1.5 text-xs text-white/50 hover:text-white"><ArrowLeft size={13} /> All {APP.entityPlural}</Link>

      <GlassCard className="mt-3">
        {editing ? (
          <form onSubmit={saveEdit} className="space-y-2">
            <input className="input" value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} />
            <textarea className="input min-h-[80px]" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} />
            <div className="flex gap-2">
              <select className="input" value={edit.category} onChange={(e) => setEdit({ ...edit, category: e.target.value })}>{APP.categories.map((c) => <option key={c} className="bg-ink">{c}</option>)}</select>
              <select className="input" value={edit.status} onChange={(e) => setEdit({ ...edit, status: e.target.value })}>{['draft', 'active', 'in_review', 'completed', 'archived'].map((s) => <option key={s} className="bg-ink">{s}</option>)}</select>
            </div>
            <div className="flex gap-2">
              <button className="btn-primary !py-2 text-sm">Save</button>
              <button type="button" onClick={() => setEditing(false)} className="btn-ghost !py-2 text-sm">Cancel</button>
            </div>
          </form>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2 text-[11px]">
              <span className="badge bg-neon/20 text-[#c9c2ff]">{project.category}</span>
              <span className="badge bg-white/10 text-white/60">{project.status}</span>
              {ownerName && <span className="text-white/40">by {ownerName}</span>}
              <span className="ml-auto flex gap-1.5">
                {isOwner && (
                  <>
                    <button onClick={() => setEditing(true)} className="rounded-lg bg-white/5 p-2 text-white/60 hover:text-white" title="Edit"><Pencil size={13} /></button>
                    <button onClick={remove} className="rounded-lg bg-white/5 p-2 text-white/60 hover:text-red-300" title="Delete"><Trash2 size={13} /></button>
                  </>
                )}
              </span>
            </div>
            <h1 className="mt-2 font-display text-3xl font-bold">{project.title}</h1>
            <p className="mt-2 leading-relaxed text-white/60">{project.description || 'No description yet.'}</p>
            <div className="mt-4 flex items-center gap-3">
              <button onClick={vote} className="inline-flex items-center gap-1.5 rounded-xl bg-white/5 px-4 py-2 font-bold hover:bg-neon hover:text-ink"><ArrowUp size={15} /> {project.upvotes}</button>
              <span className="text-xs text-white/35">{comments.length} comments · {tasks.length} tasks</span>
            </div>
          </>
        )}
      </GlassCard>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <GlassCard>
          <div className="font-display font-bold">Discussion ({comments.length})</div>
          <div className="mt-3 max-h-80 space-y-2 overflow-y-auto scroll-thin pr-1">
            {comments.map((c) => (
              <div key={c.id} className="glass-soft rounded-xl px-3 py-2.5">
                <div className="text-[11px] font-semibold text-white/45">{names[c.author_id] || 'Someone'} · {new Date(c.created_at).toLocaleString()}</div>
                <div className="mt-0.5 text-sm text-white/85">{c.body}</div>
              </div>
            ))}
            {!comments.length && <div className="text-xs text-white/35">No comments yet — start the thread 👇</div>}
          </div>
          <form onSubmit={comment} className="mt-3 flex gap-2">
            <input className="input !py-2 text-sm" placeholder="Write a comment…" value={draft} onChange={(e) => setDraft(e.target.value)} />
            <button className="btn-primary shrink-0 !px-3.5 !py-2"><Send size={14} /></button>
          </form>
        </GlassCard>
        <GlassCard>
          <div className="font-display font-bold">Linked tasks ({tasks.length})</div>
          <form onSubmit={addTask} className="mt-3 flex gap-2">
            <input className="input !py-2 text-sm" placeholder={`Task for this ${APP.entityLabel.toLowerCase()}…`} value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
            <button className="btn-primary shrink-0 !px-3.5 !py-2"><Plus size={14} /></button>
          </form>
          <div className="mt-3 space-y-1.5">
            {tasks.map((t) => (
              <div key={t.id} className="glass-soft flex items-center gap-2 rounded-xl px-3 py-2 text-sm">
                <span className={`badge ${t.status === 'done' ? 'bg-mint/15 text-mint' : t.status === 'doing' ? 'bg-peach/20 text-peach' : 'bg-white/10 text-white/60'}`}>{t.status}</span>
                <span className="truncate">{t.title}</span>
              </div>
            ))}
            {!tasks.length && <div className="text-xs text-white/35">No tasks linked yet.</div>}
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
