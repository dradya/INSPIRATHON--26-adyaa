import { useEffect, useState } from 'react'
import { ArrowUp, Send } from 'lucide-react'
import { supabase } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { GlassCard } from '../components/ui.jsx'

export default function Feed() {
  const { user } = useAuth()
  const [posts, setPosts] = useState([])
  const [body, setBody] = useState('')
  const [kind, setKind] = useState('discussion')

  const load = async () => {
    const { data } = await supabase.from('posts').select('*, profiles(full_name)').order('created_at', { ascending: false }).limit(50)
    if (data) setPosts(data)
  }
  useEffect(() => {
    load()
    const ch = supabase.channel('feed').on('postgres_changes', { event: '*', schema: 'public', table: 'posts' }, load).subscribe()
    return () => supabase.removeChannel(ch)
  }, [])

  const post = async (e) => {
    e.preventDefault()
    if (!user) return alert('Sign in first!')
    if (!body.trim()) return
    await supabase.from('posts').insert({ body, kind, author_id: user.id })
    setBody(''); load()
  }
  const vote = async (id) => {
    if (!user) return alert('Sign in to upvote!')
    await supabase.rpc('toggle_vote', { p_target_type: 'post', p_target_id: id, p_value: 1 })
    load()
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-8">
      <h1 className="font-display text-3xl font-bold md:text-4xl">Community feed</h1>
      <p className="mt-1 text-sm text-white/50">Use as discussions, issue reports, Q&A or announcements.</p>
      <GlassCard className="mt-5">
        <form onSubmit={post} className="space-y-2">
          <div className="flex gap-2">
            {['discussion', 'question', 'announcement', 'issue', 'feedback'].map(k => (
              <button type="button" key={k} onClick={() => setKind(k)} className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${kind === k ? 'bg-mint text-ink' : 'bg-white/5 text-white/50'}`}>{k}</button>
            ))}
          </div>
          <textarea className="input min-h-[80px]" placeholder="Share an update, ask a question, report an issue…" value={body} onChange={e => setBody(e.target.value)} />
          <button className="btn-primary w-full text-sm"><Send size={14} /> Post</button>
        </form>
      </GlassCard>
      <div className="mt-5 space-y-3">
        {posts.map(p => (
          <GlassCard key={p.id} className="!p-4">
            <div className="flex items-center gap-2 text-[11px]">
              <span className="badge bg-neon/20 text-[#c9c2ff]">{p.kind}</span>
              <span className="text-white/40">{p.profiles?.full_name || 'Anonymous'} · {new Date(p.created_at).toLocaleString()}</span>
            </div>
            {p.title && <div className="mt-1.5 font-display font-bold">{p.title}</div>}
            <p className="mt-1 text-sm leading-relaxed text-white/75">{p.body}</p>
            <button onClick={() => vote(p.id)} className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-white/5 px-3 py-1.5 text-sm font-bold hover:bg-neon hover:text-ink"><ArrowUp size={14} /> {p.upvotes}</button>
          </GlassCard>
        ))}
        {!posts.length && <div className="glass-soft rounded-2xl p-8 text-center text-sm text-white/40">No posts yet — run seed.sql or be the first ✍️</div>}
      </div>
    </div>
  )
}
