-- FS Database — everything still outstanding, in one paste.
--
-- Run this once in the Supabase SQL editor (project fofghcaqgwgixjshmubt).
-- Nothing to fill in: no password to invent, no key to copy anywhere. The one
-- secret it needs it generates itself and keeps in a table only the scheduler
-- and the sync function can read.
--
-- It does three things:
--   1. lets the website's two forms file a lead / questionnaire without a login
--   2. creates the shared secret the scheduled sync authenticates with
--   3. schedules that sync every 5 minutes
--
-- Deploy the edge function first (supabase/functions/starshipit-sync), or run
-- this first and the schedule will simply start working once it is deployed.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. The website's quote form and onboarding questionnaire
-- ─────────────────────────────────────────────────────────────────────────────
-- Insert only: a visitor can drop a new inquiry in and can never read, change or
-- delete anything, so the worst a stranger can do is add noise an admin deletes.

grant insert on public.leads, public.onboarding to anon;

drop policy if exists leads_public_insert on public.leads;
create policy leads_public_insert on public.leads
  for insert to anon
  with check (
    id like 'web-%'                   -- cannot collide with or impersonate a record made in the app
    and data->>'status' = 'new'       -- always arrives at the top of the pipeline
    and data->>'source' = 'website'   -- and is labelled as having come from outside
    and length(data::text) < 8000     -- a form submission, not a payload
    and ord = -1                      -- sorts above existing leads until the app renumbers
  );

drop policy if exists onboarding_public_insert on public.onboarding;
create policy onboarding_public_insert on public.onboarding
  for insert to anon
  with check (
    id like 'web-ob-%'
    and data->>'status' = 'in_progress'
    and data->>'source' = 'website'
    and length(data::text) < 20000    -- 28 answers, some of them long
    and ord = -1
  );

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. The secret the scheduled sync authenticates with
-- ─────────────────────────────────────────────────────────────────────────────
-- Row-level security is on and there are no policies, so no signed-in user can
-- read this — not even an admin through the API. Only the scheduler (which runs
-- as the database owner) and the edge function (which holds the service key)
-- ever see it, which is why the secret needs to exist nowhere else.

create table if not exists public.cron_auth (
  name   text primary key,
  secret text not null,
  created_at timestamptz not null default now()
);
alter table public.cron_auth enable row level security;
revoke all on public.cron_auth from anon, authenticated;

insert into public.cron_auth (name, secret)
values ('starshipit-sync', encode(extensions.gen_random_bytes(32), 'hex'))
on conflict (name) do nothing;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Run the sync every 5 minutes
-- ─────────────────────────────────────────────────────────────────────────────
create extension if not exists pg_cron  with schema extensions;
create extension if not exists pg_net   with schema extensions;

-- Reading the secret at call time means it is never written into the schedule.
create or replace function public.run_starshipit_sync()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare v_secret text;
begin
  select secret into v_secret from public.cron_auth where name = 'starshipit-sync';
  if v_secret is null then return; end if;
  perform extensions.http_post(
    url     := 'https://fofghcaqgwgixjshmubt.supabase.co/functions/v1/starshipit-sync',
    headers := jsonb_build_object('Content-Type', 'application/json', 'x-fsdb-cron', v_secret),
    body    := '{}'::jsonb
  );
end $$;
revoke all on function public.run_starshipit_sync() from anon, authenticated;

select cron.unschedule('fs-starshipit-sync')
where exists (select 1 from cron.job where jobname = 'fs-starshipit-sync');

select cron.schedule('fs-starshipit-sync', '*/5 * * * *', 'select public.run_starshipit_sync()');

-- ─────────────────────────────────────────────────────────────────────────────
-- Check it took
-- ─────────────────────────────────────────────────────────────────────────────
select jobname, schedule, active from cron.job where jobname = 'fs-starshipit-sync';

-- After five minutes or so, this should show a recent timestamp:
--   select data->>'lastSync', data->>'fetched', data->>'written'
--   from public.app_settings where key = 'sync_state';
--
-- To run it immediately rather than waiting:
--   select public.run_starshipit_sync();
--
-- To stop it:
--   select cron.unschedule('fs-starshipit-sync');
