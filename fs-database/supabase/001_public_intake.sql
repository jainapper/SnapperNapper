-- FS Database — public intake for the website forms
--
-- NOT YET APPLIED. Run this in the Supabase SQL editor for project
-- fofghcaqgwgixjshmubt, or approve the migration tool call.
--
-- Until it runs, the quote form and the onboarding questionnaire will fail —
-- visibly, with their error messages, not silently. Everything else keeps
-- working: this only adds a public write path, it changes nothing existing.
--
-- What it grants: an anonymous visitor may INSERT a new lead or a new onboarding
-- record and nothing else. No select, no update, no delete. The checks stop a
-- stranger impersonating a record made inside the app, overwriting one, or
-- posting something huge. The worst they can do is add noise that an admin then
-- deletes.

grant insert on public.leads, public.onboarding to anon;

drop policy if exists leads_public_insert on public.leads;
create policy leads_public_insert on public.leads
  for insert to anon
  with check (
    id like 'web-%'                   -- cannot collide with, or impersonate, a record made in the app
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

-- Check it did what it should: this must fail with 42501, because reading is
-- never granted.
--
--   set local role authenticated;  -- then, as anon:
--   set local role anon;
--   select count(*) from public.leads;        -- expect: permission denied
--   insert into public.leads (id, data, ord)  -- expect: succeeds
--     values ('web-test-1', '{"status":"new","source":"website"}'::jsonb, -1);
--   insert into public.leads (id, data, ord)  -- expect: violates policy
--     values ('app-test-1', '{"status":"new","source":"website"}'::jsonb, -1);
--   reset role;
--   delete from public.leads where id = 'web-test-1';
