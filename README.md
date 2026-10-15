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

## Run locally

```bash
npm install
npm run setup          # creates .env from .env.example; keeps existing .env unchanged
npm start              # → http://localhost:5173
```

After `npm run setup`, add your Supabase project URL and anon/public key to `.env`.
Create the Supabase backend by running `supabase/schema.sql` in the Supabase SQL Editor;
run `supabase/seed.sql` too if you want demo data. See [Supabase setup](supabase/README.md)
for the full backend and authentication setup.

`npm run dev` remains available for development. To verify a production bundle locally,
run `npm run build` followed by `npm run preview`.

> Before a commercial launch, configure your real production environment and authentication
> URLs, review the database RLS policies for your business requirements, and never put a
> Supabase service-role key in this frontend. Vite variables prefixed with `VITE_` are
> included in the browser bundle; use only the Supabase anon/publishable key here.

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
