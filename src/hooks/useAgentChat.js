import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase, isSupabaseConfigured } from '../lib/supabase.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../components/Toast.jsx'
import { useFS } from '../context/FSContext.jsx'
import { snapshotWorkspace, runLocalAgent, runFileAgent, queryEndpoint } from '../lib/agent.js'

// Shared brain for AgentWidget + /agent page.
// Persists to agent_threads/agent_messages when migration_agent.sql is run;
// silently stays in-memory otherwise.
export function useAgentChat() {
  const { user, profile } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const fs = useFS()
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `Hey! I'm the VaultLens agent 🤖 — ask me to find files, free space, explain duplicates, or prove your data stays private.` }
  ])
  const [typing, setTyping] = useState(false)
  const threadId = useRef(null)
  const persistOk = useRef(true)

  useEffect(() => {
    if (!user || !isSupabaseConfigured || threadId.current) return
    ;(async () => {
      try {
        const { data } = await supabase.from('agent_threads')
          .select('id').eq('user_id', user.id).order('updated_at', { ascending: false }).limit(1).single()
        if (data) {
          threadId.current = data.id
          const { data: msgs } = await supabase.from('agent_messages')
            .select('role,content').eq('thread_id', data.id).order('created_at').limit(40)
          if (msgs?.length) setMessages(msgs)
        } else {
          const { data: t } = await supabase.from('agent_threads').insert({ user_id: user.id, title: 'Workspace chat' }).select('id').single()
          if (t) threadId.current = t.id
        }
      } catch { persistOk.current = false }
    })()
  }, [user])

  const persist = useCallback(async (role, content) => {
    if (!persistOk.current || !threadId.current) return
    try {
      await supabase.from('agent_messages').insert({ thread_id: threadId.current, role, content })
      await supabase.from('agent_threads').update({ updated_at: new Date().toISOString() }).eq('id', threadId.current)
    } catch { persistOk.current = false }
  }, [])

  const runAction = useCallback(async (action) => {
    if (!action) return null
    if (action.type === 'navigate') { nav(action.to); return null }
    if (!isSupabaseConfigured) return 'Supabase is not connected, so I could not save that.'
    if (!user) return 'Sign in first, then I can create things for you.'
    try {
      if (action.type === 'createTask') {
        await supabase.from('tasks').insert({ title: action.title, created_by: user.id })
        nav('/tasks')
        return `Task “${action.title}” created and waiting on the board ✓`
      }
      if (action.type === 'createProject') {
        const { data } = await supabase.from('projects').insert({ title: action.title, owner_id: user.id }).select('id').single()
        nav(data ? `/projects/${data.id}` : '/projects')
        return `Project “${action.title}” created ✓ — opening it now.`
      }
    } catch (e) {
      toast.err('Agent action failed: ' + e.message)
      return 'I tried, but saving failed — check RLS / sign-in and retry.'
    }
    return null
  }, [nav, user, toast])

  const send = useCallback(async (text) => {
    const clean = text.trim()
    if (!clean || typing) return
    setMessages((m) => [...m, { role: 'user', content: clean }])
    persist('user', clean)
    setTyping(true)
    try {
      // File intents first (VaultLens) — answered from the on-device scan.
      const fr = runFileAgent(clean, fs)
      if (fr) {
        const followUp = await runAction(fr.action)
        const fFinal = followUp ? `${fr.reply}\n${followUp}` : fr.reply
        setMessages((m) => [...m, { role: 'assistant', content: fFinal }])
        persist('assistant', fFinal)
        return
      }
      const snap = await snapshotWorkspace()
      const history = [...messages.slice(-10), { role: 'user', content: clean }]
        .map(({ role, content }) => ({ role, content }))
      let reply = await queryEndpoint(history, snap)
      let action = null
      if (!reply) {
        const out = runLocalAgent(clean, snap, profile?.full_name)
        reply = out.reply
        action = out.action
      }
      const followUp = await runAction(action)
      const final = followUp ? `${reply}\n${followUp}` : reply
      setMessages((m) => [...m, { role: 'assistant', content: final }])
      persist('assistant', final)
    } finally {
      setTyping(false)
    }
  }, [messages, persist, profile, runAction, typing, fs])

  const clear = useCallback(async () => {
    setMessages([{ role: 'assistant', content: 'Fresh slate 🧹 — what are we building?' }])
    threadId.current = null
  }, [])

  return { messages, typing, send, clear }
}
