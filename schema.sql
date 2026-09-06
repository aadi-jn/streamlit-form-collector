-- Form Collector — database schema.
-- Run this in the Supabase SQL editor (Dashboard → SQL Editor → New query).
-- Safe to re-run: drops and recreates the policy, leaves existing rows untouched.

-- gen_random_uuid() lives in pgcrypto. Supabase usually has it enabled already;
-- this is a no-op if so.
create extension if not exists pgcrypto;

create table if not exists public.submissions (
    id           uuid primary key default gen_random_uuid(),
    submitted_at timestamptz not null default now(),
    form_id      text not null,
    data         jsonb not null,
    user_agent   text
);

create index if not exists submissions_submitted_at_idx
    on public.submissions (submitted_at desc);

create index if not exists submissions_form_id_idx
    on public.submissions (form_id);

-- Row Level Security -------------------------------------------------------
-- RLS is ENABLED. The public app uses the anon key and may only INSERT.
-- There is deliberately NO select/update/delete policy for anon, so the
-- anon key cannot read submissions back.
-- The admin page reads with the service_role key, which bypasses RLS.

alter table public.submissions enable row level security;

drop policy if exists "anon can insert submissions" on public.submissions;
create policy "anon can insert submissions"
    on public.submissions
    for insert
    to anon
    with check (true);
