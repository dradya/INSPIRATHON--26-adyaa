-- =============================================================
-- INSPIRATHON '26 — Universal Hackathon Backend
-- Copy-paste this ENTIRE file into: Supabase Dashboard
--   → SQL Editor → New Query → Paste → Run
-- =============================================================
-- What this gives you (works for ANY problem statement):
--  • profiles        → users (auto-created on signup)
--  • teams + team_members → group / org / class / department
--  • projects        → GENERIC entity. Rename in UI to:
--      Ideas / Complaints / Patients / Inventory / Cases /
--      Reports / Startups / Events / Anything.
--  • tasks           → Kanban (todo / doing / done)
--  • posts + comments + votes → community feed / discussions /
--      issue tracker / Q&A / feedback board
--  • notifications   → activity bell
--  • Storage buckets → avatars, project-images, attachments
--  • RLS + Realtime + Search + Auto-updated_at + Upvote fn
-- -------------------------------------------------------------
-- HACKATHON MODE: RLS is permissive (public read, auth write)
-- so your demo never breaks. Lock down after winning. See
-- Section 9 comments for strict version.
-- =============================================================

-- 0) EXTENSIONS ------------------------------------------------
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- 1) HELPER FUNCTIONS ------------------------------------------
create or replace function public.handle_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- Auto-create profile row when a user signs up via Supabase Auth
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end $$;

-- Upvote / like counter (call via RPC from frontend)
create or replace function public.toggle_vote(
  p_target_type text, p_target_id uuid, p_value int default 1
)
returns void language plpgsql security definer set search_path = public as $$
begin
  insert into public.votes (user_id, target_type, target_id, value)
  values (auth.uid(), p_target_type, p_target_id, p_value)
  on conflict (user_id, target_type, target_id)
  do update set value = excluded.value, created_at = now();

  if p_target_type = 'project' then
    update public.projects p set upvotes =
      (select coalesce(sum(value),0) from public.votes
        where target_type='project' and target_id = p_target_id)
    where id = p_target_id;
  elsif p_target_type = 'post' then
    update public.posts p set upvotes =
      (select coalesce(sum(value),0) from public.votes
        where target_type='post' and target_id = p_target_id)
    where id = p_target_id;
  end if;
end $$;

-- 2) PROFILES ---------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  role text default 'member' check (role in ('admin','member','viewer')),
  bio text,
  metadata jsonb default '{}'::jsonb, -- ← put ANY extra fields here, no migration needed
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
drop trigger if exists trg_profiles_updated on public.profiles;
create trigger trg_profiles_updated before update on public.profiles
  for each row execute function public.handle_updated_at();

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 3) TEAMS -------------------------------------------------------
create table if not exists public.teams (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  description text,
  avatar_url text,
  invite_code text unique default substr(md5(random()::text),1,8),
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
drop trigger if exists trg_teams_updated on public.teams;
create trigger trg_teams_updated before update on public.teams
  for each row execute function public.handle_updated_at();

create table if not exists public.team_members (
  id uuid primary key default uuid_generate_v4(),
  team_id uuid not null references public.teams(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text default 'member' check (role in ('owner','admin','member')),
  joined_at timestamptz default now(),
  unique(team_id, user_id)
);

-- 4) PROJECTS (the generic ⭐ entity) -----------------------------
-- Rename "Project" in the UI to whatever your statement needs.
create table if not exists public.projects (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  description text,
  category text default 'General',        -- e.g. Health / Edu / Civic / Fintech
  status text default 'active' check (status in ('draft','active','in_review','completed','archived')),
  priority text default 'medium' check (priority in ('low','medium','high','critical')),
  tags text[] default '{}',
  image_url text,
  metadata jsonb default '{}'::jsonb,     -- ← flexible: put statement-specific fields here
  upvotes int default 0,
  view_count int default 0,
  owner_id uuid references public.profiles(id) on delete set null,
  team_id uuid references public.teams(id) on delete set null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
drop trigger if exists trg_projects_updated on public.projects;
create trigger trg_projects_updated before update on public.projects
  for each row execute function public.handle_updated_at();

create index if not exists idx_projects_status on public.projects(status);
create index if not exists idx_projects_category on public.projects(category);
create index if not exists idx_projects_owner on public.projects(owner_id);
create index if not exists idx_projects_search
  on public.projects using gin (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'')));

-- 5) TASKS (Kanban) ----------------------------------------------
create table if not exists public.tasks (
  id uuid primary key default uuid_generate_v4(),
  project_id uuid references public.projects(id) on delete cascade,
  team_id uuid references public.teams(id) on delete set null,
  title text not null,
  description text,
  status text default 'todo' check (status in ('todo','doing','done')),
  priority text default 'medium' check (priority in ('low','medium','high','critical')),
  due_date date,
  assignee_id uuid references public.profiles(id) on delete set null,
  created_by uuid references public.profiles(id) on delete set null,
  position int default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
drop trigger if exists trg_tasks_updated on public.tasks;
create trigger trg_tasks_updated before update on public.tasks
  for each row execute function public.handle_updated_at();
create index if not exists idx_tasks_project on public.tasks(project_id);
create index if not exists idx_tasks_status on public.tasks(status);
create index if not exists idx_tasks_assignee on public.tasks(assignee_id);

-- 6) POSTS / FEED (discussions, issues, announcements) ------------
create table if not exists public.posts (
  id uuid primary key default uuid_generate_v4(),
  author_id uuid references public.profiles(id) on delete set null,
  team_id uuid references public.teams(id) on delete set null,
  project_id uuid references public.projects(id) on delete cascade, -- nullable: standalone post or linked
  title text,
  body text not null,
  kind text default 'discussion' check (kind in ('discussion','question','announcement','issue','feedback','update')),
  image_url text,
  upvotes int default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
drop trigger if exists trg_posts_updated on public.posts;
create trigger trg_posts_updated before update on public.posts
  for each row execute function public.handle_updated_at();
create index if not exists idx_posts_kind on public.posts(kind);
create index if not exists idx_posts_project on public.posts(project_id);

-- 7) COMMENTS -----------------------------------------------------
create table if not exists public.comments (
  id uuid primary key default uuid_generate_v4(),
  author_id uuid references public.profiles(id) on delete set null,
  post_id uuid references public.posts(id) on delete cascade,
  project_id uuid references public.projects(id) on delete cascade,
  body text not null,
  created_at timestamptz default now(),
  -- exactly one parent must be set:
  check (num_nonnulls(post_id, project_id) = 1)
);
create index if not exists idx_comments_post on public.comments(post_id);
create index if not exists idx_comments_project on public.comments(project_id);

-- 8) VOTES ----------------------------------------------------------
create table if not exists public.votes (
  user_id uuid not null references public.profiles(id) on delete cascade,
  target_type text not null check (target_type in ('project','post')),
  target_id uuid not null,
  value int default 1 check (value in (-1,1)),
  created_at timestamptz default now(),
  primary key (user_id, target_type, target_id)
);

-- 9) NOTIFICATIONS ---------------------------------------------------
create table if not exists public.notifications (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  body text,
  link text,
  is_read boolean default false,
  created_at timestamptz default now()
);
create index if not exists idx_notif_user on public.notifications(user_id, is_read);

-- 10) ROW LEVEL SECURITY (hackathon-friendly) -------------------------
alter table public.profiles       enable row level security;
alter table public.teams          enable row level security;
alter table public.team_members   enable row level security;
alter table public.projects       enable row level security;
alter table public.tasks          enable row level security;
alter table public.posts          enable row level security;
alter table public.comments       enable row level security;
alter table public.votes          enable row level security;
alter table public.notifications  enable row level security;

-- Drop old policies (re-runnable)
do $$ declare r record; begin
  for r in (select policyname, tablename from pg_policies where schemaname='public') loop
    execute format('drop policy if exists %I on public.%I', r.policyname, r.tablename);
  end loop;
end $$;

-- Public read for demo (judges can browse without login)
create policy "public read"  on public.profiles      for select using (true);
create policy "public read"  on public.teams         for select using (true);
create policy "public read"  on public.team_members  for select using (true);
create policy "public read"  on public.projects      for select using (true);
create policy "public read"  on public.tasks         for select using (true);
create policy "public read"  on public.posts         for select using (true);
create policy "public read"  on public.comments      for select using (true);
create policy "public read"  on public.votes         for select using (true);

-- Authenticated users can insert/update/delete (demo-safe)
create policy "auth insert" on public.profiles      for insert with check (auth.uid() = id);
create policy "auth update" on public.profiles      for update using (auth.uid() = id);
create policy "auth all teams"   on public.teams        for all using (auth.role() = 'authenticated');
create policy "auth all members" on public.team_members for all using (auth.role() = 'authenticated');
create policy "auth all projects"on public.projects     for all using (auth.role() = 'authenticated');
create policy "auth all tasks"   on public.tasks        for all using (auth.role() = 'authenticated');
create policy "auth all posts"   on public.posts        for all using (auth.role() = 'authenticated');
create policy "auth all comments"on public.comments     for all using (auth.role() = 'authenticated');
create policy "auth all votes"   on public.votes        for all using (auth.uid() = user_id);

-- Notifications: only own
create policy "own notif read"   on public.notifications for select using (auth.uid() = user_id);
create policy "auth insert notif"on public.notifications for insert with check (auth.role()='authenticated');
create policy "own notif update" on public.notifications for update using (auth.uid() = user_id);

-- STRICT VERSION (use after hackathon): replace "auth all X" with e.g.
--   create policy "owner update" on public.projects for update using (auth.uid() = owner_id);

-- 11) STORAGE ----------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('avatars','avatars', true),
       ('project-images','project-images', true),
       ('attachments','attachments', false)
on conflict (id) do nothing;

do $$ declare r record; begin
  for r in (select policyname from pg_policies where schemaname='storage' and tablename='objects'
            and policyname like 'hack_%') loop
    execute format('drop policy if exists %I on storage.objects', r.policyname);
  end loop;
end $$;

create policy "hack_public_read"
  on storage.objects for select using (bucket_id in ('avatars','project-images'));
create policy "hack_auth_upload"
  on storage.objects for insert with check (auth.role()='authenticated' and bucket_id in ('avatars','project-images','attachments'));
create policy "hack_auth_update"
  on storage.objects for update using (auth.role()='authenticated');
create policy "hack_auth_delete"
  on storage.objects for delete using (auth.role()='authenticated');

-- 12) REALTIME -----------------------------------------------------------
-- After running this, go to Database → Replication and enable
-- the tables you want live (projects, tasks, posts, comments, notifications).
-- Or run: alter publication supabase_realtime add table public.projects, public.tasks, public.posts, public.comments, public.notifications;
-- (commented because publication membership can error on fresh projects)
-- alter publication supabase_realtime add table public.projects;
-- alter publication supabase_realtime add table public.tasks;
-- alter publication supabase_realtime add table public.posts;
-- alter publication supabase_realtime add table public.comments;
-- alter publication supabase_realtime add table public.notifications;

-- 13) STATS VIEW (dashboard numbers in one query) --------------------------
create or replace view public.dashboard_stats as
select
  (select count(*) from public.projects where status='active') as active_projects,
  (select count(*) from public.tasks where status != 'done') as open_tasks,
  (select count(*) from public.tasks where status = 'done') as done_tasks,
  (select count(*) from public.posts) as total_posts,
  (select count(*) from public.profiles) as total_users,
  (select count(*) from public.teams) as total_teams;

-- DONE ✅ — Now run seed.sql (optional demo data), then:
--  1. Authentication → Providers → enable Email + Google
--  2. Authentication → URL Configuration → add http://localhost:5173
--  3. Database → Replication → enable realtime for the 5 tables
--  4. Copy Project URL + anon key into frontend .env
