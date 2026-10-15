# ⚡ INSPIRATHON '26 — Universal Hackathon Starter

Aesthetic full-stack kit that works for **any problem statement**. Frontend in Vite + React + Tailwind, backend in Supabase (one SQL paste).

```
INSPIRATHON '26/
├── supabase/
│   ├── schema.sql   ← PASTE THIS into Supabase SQL Editor (your whole backend)
│   ├── seed.sql     ← demo data (optional, recommended)
│   ├── migration_agent.sql ← agent chat memory (optional)
│   ├── functions/agent-chat ← agent LLM upgrade (optional)
│   └── README.md    ← 5-min Supabase setup
├── src/
│   ├── config.js           ← REBRAND HERE (1 file, 5 lines)
│   ├── lib/supabase.js + notify.js + agent.js (agent brain)
│   ├── context/AuthContext.jsx + components/Toast.jsx
│   ├── components/Navbar, ui, CommandPalette (⌘K), NotificationsBell, AgentWidget
│   └── pages/Landing, Login, ResetPassword, Dashboard, Projects, ProjectDetail,
│             Tasks, Feed, Teams, Agent, Profile, Settings, NotFound
├── .env.example
└── HACKATHON_GUIDE.md  ← statement → rebrand cheat-sheet
```

## 60-second start

```bash
npm install
cp .env.example .env   # paste Supabase URL + anon key
npm run dev            # → http://localhost:5173
```

Supabase side: **SQL Editor → paste `supabase/schema.sql` → Run → paste `seed.sql` → Run.** Done.

## Why this wins hackathons
- **Statement-proof:** `projects` table is generic — becomes Complaints / Patients / Cases / Ideas with zero migrations (use `metadata` JSONB + rename `src/config.js`).
- **Demo-proof:** permissive RLS (public read, auth write), seed data, realtime boards, upvotes, charts.
- **Looks designed:** glassmorphism, gradients, Space Grotesk, Framer Motion, Lucide icons, dark aesthetic.
- **Complete app basics:** auth guard, profile + avatar uploads, password reset, settings + accent themes, notifications bell, ⌘K global search, project detail with comments, toasts, 404.
- **Nova Agent 🤖:** floating assistant + `/agent` page. Answers from LIVE Supabase data with zero keys (“summarize my workspace”, “create task buy domain”, “take me to the board”). Optional LLM upgrade via edge function.

## Rebrand in 5 minutes
1. `src/config.js` → app name, tagline, entity labels (`Project` → `Complaint` etc.)
2. `.env` → `VITE_APP_NAME`, `VITE_ENTITY_LABEL`
3. `supabase/seed.sql` → rename demo titles to your domain
4. Landing headline in `src/pages/Landing.jsx` (one `<h1>`)

Full mapping table → see `HACKATHON_GUIDE.md`.
