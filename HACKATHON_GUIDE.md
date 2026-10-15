# 🎯 Hackathon Rebrand Guide — statement drops → you ship in 30 min

## The trick
Everything generic maps to your statement. No new tables needed.

| If statement is… | `ENTITY_LABEL` → | `projects` becomes | `tasks` becomes | `posts` becomes |
|---|---|---|---|---|
| Civic complaints | Complaint | Complaint | Resolution steps | Citizen reports |
| Healthcare | Patient / Case | Case | Treatment checklist | Doctor notes |
| Education | Course / Idea | Idea | Build steps | Doubts / Q&A |
| Agriculture | Advisory | Crop report | Field tasks | Farmer questions |
| Disaster mgmt | Incident | Incident | Rescue tasks | Field updates |
| Fintech | Goal / Loan | Loan case | Verification steps | Support tickets |
| Environment | Report | Cleanup report | Volunteer tasks | Sightings |

## 30-minute playbook
**0–5 min:** read statement, pick labels, edit `src/config.js` (5 lines).
**5–10 min:** paste `schema.sql` (already done before hackathon ideally) + tweak `seed.sql` titles → re-run.
**10–25 min:** build the ONE statement-specific widget:
- Map? Add Leaflet snippet to Projects page.
- Chatbot? Add one Edge Function call.
- QR / upload? Use `project-images` bucket (already has policies).
- Put statement-specific fields in `metadata` JSONB — **no migration needed**: `insert ... metadata = '{"crop":"wheat","soil_ph":6.5}'`.
**25–30 min:** pitch: Dashboard stats screenshot + live upvote + realtime board move = judges clap.

## Queries you'll need (copy-paste)
```js
// Search (uses the full-text index from schema.sql)
const { data } = await supabase.from('projects')
  .select('*').ilike('title', `%${q}%`).limit(20)

// Upvote (handles toggle + counter atomically)
await supabase.rpc('toggle_vote', { p_target_type: 'project', p_target_id: id, p_value: 1 })

// Kanban move
await supabase.from('tasks').update({ status: 'done' }).eq('id', taskId)

// Upload image
const file = e.target.files[0]
await supabase.storage.from('project-images').upload(`${Date.now()}_${file.name}`, file)
const { data: { publicUrl } } = supabase.storage.from('project-images').getPublicUrl(path)

// One-query dashboard numbers
const { data } = await supabase.from('dashboard_stats').select('*').single()
```

## Demo-day checklist
- [ ] Seed data loaded, claimed as your user
- [ ] Google login works on demo laptop (test incognito)
- [ ] Realtime enabled (move a task, show it update on second tab)
- [ ] Landing headline mentions the actual problem statement
- [ ] One chart visible (Dashboard already has it)
- [ ] `console.log` cleaned, `.env` NOT committed
- [ ] Pitch: problem → live demo (upvote + board move) → impact numbers
