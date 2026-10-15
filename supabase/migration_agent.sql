-- =============================================================
-- AGENT MEMORY (optional upgrade, run AFTER schema.sql)
-- Paste into Supabase SQL Editor → Run.
-- Gives Nova Agent persistent chat history per user.
-- The app works WITHOUT this too (in-memory fallback).
-- =============================================================

create table if not exists public.agent_threads (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text default 'Workspace chat',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
drop trigger if exists trg_threads_updated on public.agent_threads;
create trigger trg_threads_updated before update on public.agent_threads
  for each row execute function public.handle_updated_at();

create table if not exists public.agent_messages (
  id uuid primary key default uuid_generate_v4(),
  thread_id uuid not null references public.agent_threads(id) on delete cascade,
  role text not null check (role in ('user','assistant','system')),
  content text not null,
  created_at timestamptz default now()
);
create index if not exists idx_agent_msg_thread on public.agent_messages(thread_id, created_at);

alter table public.agent_threads enable row level security;
alter table public.agent_messages enable row level security;

do $$ declare r record; begin
  for r in (select policyname, tablename from pg_policies where schemaname='public'
            and tablename in ('agent_threads','agent_messages')) loop
    execute format('drop policy if exists %I on public.%I', r.policyname, r.tablename);
  end loop;
end $$;

-- Own threads only
create policy "own threads" on public.agent_threads
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Messages visible iff you own the parent thread
create policy "own thread messages read" on public.agent_messages
  for select using (exists (
    select 1 from public.agent_threads t
    where t.id = thread_id and t.user_id = auth.uid()));
create policy "own thread messages write" on public.agent_messages
  for insert with check (exists (
    select 1 from public.agent_threads t
    where t.id = thread_id and t.user_id = auth.uid()));
