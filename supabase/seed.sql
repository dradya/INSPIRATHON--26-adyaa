-- =============================================================
-- SEED DATA (optional but recommended for demo)
-- Run AFTER schema.sql. Safe to re-run (upserts where possible).
-- Creates 1 demo team, 6 projects, tasks, posts, comments.
-- NOTE: demo rows use a placeholder owner. After you sign up
-- in the app, run Section B to claim them as your user.
-- =============================================================

-- A) Demo team -------------------------------------------------
insert into public.teams (id, name, description)
values ('11111111-1111-1111-1111-111111111111','Nova Builders','Hackathon core team — rename me!')
on conflict (id) do update set name = excluded.name;

-- B) Demo projects (generic → rebrand titles per statement) ----
insert into public.projects (title, description, category, status, priority, tags, upvotes, team_id, metadata) values
('Campus Navigator','Indoor navigation + class finder for freshers.','Education','active','high',array['maps','mobile'],42,'11111111-1111-1111-1111-111111111111','{"demo": true}'),
('MediQueue','Token + queue management for clinics, SMS alerts.','Health','active','critical',array['health','queue'],35,'11111111-1111-1111-1111-111111111111','{"demo": true}'),
('AgriSense','Soil + weather advisory for small farmers.','Agriculture','in_review','medium',array['iot','advisory'],28,'11111111-1111-1111-1111-111111111111','{"demo": true}'),
('WasteWise','Ward-level waste pickup tracker with rewards.','Civic','active','high',array['civic','rewards'],19,'11111111-1111-1111-1111-111111111111','{"demo": true}'),
('SkillSwap','Peer skill-exchange marketplace for students.','Education','draft','low',array['marketplace'],11,'11111111-1111-1111-1111-111111111111','{"demo": true}'),
('SafeStreets','Crowdsourced street-light + safety reporting.','Safety','completed','medium',array['safety','maps'],51,'11111111-1111-1111-1111-111111111111','{"demo": true}')
on conflict do nothing;

-- C) Tasks for first project ------------------------------------
do $$
declare pid uuid;
begin
  select id into pid from public.projects where title='Campus Navigator' limit 1;
  if pid is not null then
    insert into public.tasks (project_id, team_id, title, description, status, priority) values
    (pid,'11111111-1111-1111-1111-111111111111','Design landing page','Hero + features + CTA','done','high'),
    (pid,'11111111-1111-1111-1111-111111111111','Wire Supabase auth','Email + Google OAuth','doing','critical'),
    (pid,'11111111-1111-1111-1111-111111111111','Build map view','Leaflet + indoor polygons','todo','medium'),
    (pid,'11111111-1111-1111-1111-111111111111','Pitch deck','Problem → demo → impact, 5 slides','todo','high');
  end if;
end $$;

-- D) Posts + comments --------------------------------------------
do $$
declare pid uuid;
begin
  select id into pid from public.projects where title='MediQueue' limit 1;
  insert into public.posts (title, body, kind, project_id, upvotes) values
  ('Welcome to the hub 👋','Introduce your team and what you are building. Upvote the best ideas!','announcement', null, 12),
  ('How are we handling offline mode?','Clinics lose internet often. Should we add SMS fallback or local cache first?','question', pid, 8),
  ('Demo checklist','1. Seed data 2. Auth 3. Core flow 4. Pitch. Keep it shippable.','update', null, 5);
end $$;

-- After signup, claim demo data as yours (replace EMAIL):
--   update public.projects set owner_id = (select id from public.profiles where email='YOU@EMAIL.COM') where metadata->>'demo'='true';
--   insert into public.team_members (team_id, user_id, role)
--   select '11111111-1111-1111-1111-111111111111', id, 'owner' from public.profiles where email='YOU@EMAIL.COM'
--   on conflict do nothing;
