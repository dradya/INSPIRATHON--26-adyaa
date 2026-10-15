# Supabase Setup — 5 minutes ⏱️

You only need to touch Supabase **once**. Everything else lives in the frontend.

## 1. Create project
1. Go to https://supabase.com → New project
2. Save the **Project URL** + **anon public key** (Settings → API)

## 2. Run the backend (1 paste)
1. Open **SQL Editor → New query**
2. Paste the entire contents of `schema.sql` → **Run** ✅
3. (Optional) Paste `seed.sql` → **Run** for instant demo data 🌊

That's your whole backend: 9 tables, RLS, triggers, upvote RPC, storage buckets, stats view.

## 2b. Agent memory (optional, 30 sec)
Paste `migration_agent.sql` → **Run**. Gives Nova Agent persistent chat history.
Skip it and the agent still works (in-memory mode).

## 2c. Agent LLM upgrade (optional, 5 min)
The agent answers from live data with zero keys. For GPT-grade answers:
```bash
supabase functions deploy agent-chat --no-verify-jwt
supabase secrets set OPENAI_API_KEY=sk-...
# optional: supabase secrets set OPENAI_BASE_URL=... OPENAI_MODEL=...
```
Then set `VITE_AGENT_ENDPOINT=https://<ref>.supabase.co/functions/v1/agent-chat` in `.env`.

## 3. Auth (2 min)
- **Authentication → Providers**: enable `Email`, enable `Google` (add Client ID/Secret)
- **Authentication → URL Configuration**:
  - Site URL: `http://localhost:5173`
  - Redirect URLs: `http://localhost:5173/**`

## 4. Realtime (30 sec, makes judges go wow)
- **Database → Replication** → enable for: `projects`, `tasks`, `posts`, `comments`, `notifications`

## 5. Storage
Buckets are created by `schema.sql` (`avatars`, `project-images` public; `attachments` private).
Upload test: `project-images/test.txt` via Dashboard → Storage.

## 6. Connect frontend
```bash
cp .env.example .env
# paste VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
npm install
npm run dev
```

## Claim seed data as yourself
After signing up in the app, run in SQL Editor (replace email):
```sql
update public.projects set owner_id =
  (select id from public.profiles where email='YOU@EMAIL.COM')
where metadata->>'demo'='true';
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| Empty tables / no data | Run `seed.sql`; check anon key |
| Sign-up hangs | Enable Email provider; disable "Confirm email" for hackathon (Auth → Settings) |
| RLS error on insert | You pasted schema but are logged out — sign in first |
| Images won't load | Buckets are public except `attachments`; check Storage policies |
| Realtime not updating | Enable tables in Database → Replication |
