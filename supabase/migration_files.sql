-- =============================================================
-- VAULTLENS file tables (PS3) — run AFTER schema.sql
-- Paste into Supabase SQL Editor → Run.
-- PRIVACY CONTRACT: these tables store REDACTED metadata only.
-- Raw filenames/paths/contents NEVER leave the device (see app
-- Privacy page for the exact payload). No raw PII columns exist.
-- Works with anonymous demo use: user_id is nullable.
-- =============================================================

create table if not exists public.scan_sessions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references public.profiles(id) on delete set null,
  device_label text default 'this device',
  source text default 'demo',              -- 'demo' | folder name picked
  file_count int default 0,
  total_bytes bigint default 0,
  pii_hits int default 0,
  dup_waste_bytes bigint default 0,
  created_at timestamptz default now()
);

create table if not exists public.file_records (
  id uuid primary key default uuid_generate_v4(),
  session_id uuid not null references public.scan_sessions(id) on delete cascade,
  path_hash text not null,                 -- SHA-256 of path (matchable, unreadable)
  redacted_name text not null,             -- PII-scrubbed display name
  kind text default 'other',               -- image|video|audio|document|archive|code|app|other|temp
  ext text default '',
  size_bytes bigint default 0,
  modified_at timestamptz,
  pii_types text[] default '{}',           -- e.g. {email,aadhaar} — types only, no values
  content_hash text,                       -- duplicate matching without content
  created_at timestamptz default now()
);
create index if not exists idx_files_session on public.file_records(session_id);
create index if not exists idx_files_content on public.file_records(content_hash);

create table if not exists public.suggestions (
  id uuid primary key default uuid_generate_v4(),
  session_id uuid references public.scan_sessions(id) on delete cascade,
  kind text default 'organize',            -- organize|cleanup|privacy|space
  title text not null,
  detail text,
  impact_bytes bigint default 0,
  status text default 'open' check (status in ('open','accepted','dismissed')),
  upvotes int default 0,
  created_at timestamptz default now()
);
create index if not exists idx_sugg_session on public.suggestions(session_id, status);

alter table public.scan_sessions enable row level security;
alter table public.file_records  enable row level security;
alter table public.suggestions   enable row level security;

do $$ declare r record; begin
  for r in (select policyname, tablename from pg_policies where schemaname='public'
            and tablename in ('scan_sessions','file_records','suggestions')) loop
    execute format('drop policy if exists %I on public.%I', r.policyname, r.tablename);
  end loop;
end $$;

-- Hackathon-demo policies: public read, anyone can contribute.
-- Tighten to auth.uid() ownership after the event.
create policy "public read" on public.scan_sessions for select using (true);
create policy "open insert" on public.scan_sessions for insert with check (true);
create policy "public read" on public.file_records  for select using (true);
create policy "open insert" on public.file_records  for insert with check (true);
create policy "public read" on public.suggestions   for select using (true);
create policy "open insert" on public.suggestions   for insert with check (true);
create policy "open update" on public.suggestions   for update using (true);
