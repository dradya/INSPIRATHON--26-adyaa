// Nova Agent — Supabase Edge Function (optional LLM upgrade)
// Deploy:  supabase functions deploy agent-chat --no-verify-jwt
//          supabase secrets set OPENAI_API_KEY=sk-...
// Frontend: VITE_AGENT_ENDPOINT=https://<ref>.supabase.co/functions/v1/agent-chat
// Works with any OpenAI-compatible API (set OPENAI_BASE_URL + OPENAI_MODEL).
// Without this, the app's built-in local brain answers from live data.

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })
  try {
    const { messages = [], context = {} } = await req.json()
    const apiKey = Deno.env.get('OPENAI_API_KEY')
    if (!apiKey) {
      return Response.json({ reply: null, note: 'OPENAI_API_KEY not set' }, { headers: cors })
    }
    const base = Deno.env.get('OPENAI_BASE_URL') || 'https://api.openai.com/v1'
    const model = Deno.env.get('OPENAI_MODEL') || 'gpt-4o-mini'

    const s = context.stats || {}
    const top = (context.projects || []).slice(0, 5).map((p) => `- ${p.title} (${p.category}, ▲${p.upvotes})`).join('\n')
    const open = (context.tasks || []).filter((t) => t.status !== 'done').slice(0, 8).map((t) => `- [${t.status}] ${t.title}`).join('\n')
    const system = `You are Nova Agent, the in-app AI assistant for a hackathon workspace app.
Answer concisely (under 120 words), with light formatting. Ground every claim in this LIVE data:
Stats: ${s.active_projects ?? 0} active projects, ${s.total_posts ?? 0} posts, ${s.total_users ?? 0} users.
Top projects:\n${top || '(none)'}\nOpen tasks:\n${open || '(none)'}
If asked to do something the app can't do via chat, say how to do it in the UI.`

    const r = await fetch(`${base}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ model, messages: [{ role: 'system', content: system }, ...messages.slice(-12)], temperature: 0.4, max_tokens: 400 })
    })
    if (!r.ok) return Response.json({ reply: null }, { headers: cors })
    const j = await r.json()
    return Response.json({ reply: j.choices?.[0]?.message?.content || null }, { headers: cors })
  } catch {
    return Response.json({ reply: null }, { headers: cors })
  }
})
