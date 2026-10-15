import { useEffect, useState } from 'react'
import { Camera, Save } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../components/Toast.jsx'
import { GlassCard, Stat } from '../components/ui.jsx'

export default function Profile() {
  const { user } = useAuth()
  const toast = useToast()
  const [form, setForm] = useState({ full_name: '', bio: '', avatar_url: '' })
  const [counts, setCounts] = useState({ projects: 0, tasks: 0 })
  const [busy, setBusy] = useState(false)
  const [upbusy, setUpbusy] = useState(false)

  useEffect(() => {
    if (!user) return
    supabase.from('profiles').select('*').eq('id', user.id).single().then(({ data }) => {
      if (data) setForm({ full_name: data.full_name || '', bio: data.bio || '', avatar_url: data.avatar_url || '' })
    })
    Promise.all([
      supabase.from('projects').select('id', { count: 'exact', head: true }).eq('owner_id', user.id),
      supabase.from('tasks').select('id', { count: 'exact', head: true }).eq('created_by', user.id)
    ]).then(([p, t]) => setCounts({ projects: p.count || 0, tasks: t.count || 0 }))
  }, [user])

  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    const { error } = await supabase.from('profiles').update({ full_name: form.full_name, bio: form.bio, avatar_url: form.avatar_url }).eq('id', user.id)
    setBusy(false)
    error ? toast.err(error.message) : toast.ok('Profile saved ✓')
  }

  const upload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUpbusy(true)
    try {
      const ext = file.name.split('.').pop()
      const path = `${user.id}/avatar.${ext}`
      const { error } = await supabase.storage.from('avatars').upload(path, file, { upsert: true })
      if (error) throw error
      const { data: { publicUrl } } = supabase.storage.from('avatars').getPublicUrl(path)
      setForm((f) => ({ ...f, avatar_url: `${publicUrl}?t=${Date.now()}` }))
      toast.ok('Photo uploaded — hit Save 📸')
    } catch (err) { toast.err('Upload failed: ' + err.message) }
    finally { setUpbusy(false) }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Profile</h1>
      <p className="mt-1 text-sm text-white/50">{user?.email}</p>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <Stat label="My projects" value={counts.projects} />
        <Stat label="Tasks created" value={counts.tasks} />
      </div>
      <GlassCard className="mt-4">
        <form onSubmit={save} className="space-y-3">
          <div className="flex items-center gap-4">
            {form.avatar_url
              ? <img src={form.avatar_url} alt="avatar" className="h-20 w-20 rounded-2xl object-cover ring-2 ring-neon/50" />
              : <div className="grid h-20 w-20 place-items-center rounded-2xl bg-white/5 font-display text-2xl font-bold text-white/50">{(form.full_name?.[0] || user?.email?.[0] || '?').toUpperCase()}</div>}
            <label className="btn-ghost cursor-pointer !py-2 text-xs">
              <Camera size={14} /> {upbusy ? 'Uploading…' : 'Change photo'}
              <input type="file" accept="image/*" className="hidden" onChange={upload} />
            </label>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-widest text-white/40">Display name</label>
            <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Your name" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-widest text-white/40">Bio</label>
            <textarea className="input min-h-[90px]" value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} placeholder="Team role, skills, one-line intro…" />
          </div>
          <button className="btn-primary" disabled={busy}><Save size={15} /> {busy ? 'Saving…' : 'Save profile'}</button>
        </form>
      </GlassCard>
    </div>
  )
}
