-- FS Database — the account the scheduled Starshipit sync signs in as
--
-- NOT YET APPLIED.
--
-- The sync runs on a schedule whether or not anyone is logged in, so it needs an
-- identity of its own. It gets a normal admin account rather than a service-role
-- key, so row-level security still applies to everything it does and it can be
-- disabled by disabling one login.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- BEFORE RUNNING: replace CHANGE-ME below with a long random password (40+
-- characters — nobody types this one). Use the SAME value for the Vercel
-- environment variable FSDB_SYNC_PASSWORD.
--
-- Generate one with:  openssl rand -base64 32
-- ─────────────────────────────────────────────────────────────────────────────

do $$
declare
  v_password text := 'CHANGE-ME';
  v_id uuid;
begin
  if v_password = 'CHANGE-ME' then
    raise exception 'Set a real password first — see the note above.';
  end if;

  select id into v_id from auth.users where email = 'sync@fullstackfs.com.au';

  if v_id is null then
    v_id := gen_random_uuid();
    insert into auth.users (
      instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
      created_at, updated_at, raw_app_meta_data, raw_user_meta_data,
      confirmation_token, recovery_token, email_change_token_new, email_change
    ) values (
      '00000000-0000-0000-0000-000000000000', v_id, 'authenticated', 'authenticated',
      'sync@fullstackfs.com.au', extensions.crypt(v_password, extensions.gen_salt('bf')),
      now(), now(), now(),
      '{"provider":"email","providers":["email"]}'::jsonb,
      '{"name":"Scheduled sync"}'::jsonb, '', '', '', ''
    );
    insert into auth.identities (provider_id, user_id, identity_data, provider,
                                 last_sign_in_at, created_at, updated_at)
    values (v_id::text, v_id,
      jsonb_build_object('sub', v_id::text, 'email', 'sync@fullstackfs.com.au',
                         'email_verified', true, 'phone_verified', false),
      'email', now(), now(), now());
  else
    update auth.users
       set encrypted_password = extensions.crypt(v_password, extensions.gen_salt('bf')),
           updated_at = now()
     where id = v_id;
  end if;

  -- Admin, because it has to read the Starshipit keys. No tabs: this account is
  -- never meant to be used by a person, and the app shows it nothing.
  insert into public.profiles (id, name, email, role, tabs)
  values (v_id, 'Scheduled sync', 'sync@fullstackfs.com.au', 'admin', '{}'::jsonb)
  on conflict (id) do update set role = 'admin', tabs = '{}'::jsonb;
end $$;

-- The sync leaves a mark under app_settings key 'sync_state' so the dashboard can
-- show when the server last looked. Readable by the whole team; the existing
-- policies already allow that for any key other than 'starshipit'.

select p.name, p.email, p.role, u.email_confirmed_at is not null as confirmed
from public.profiles p join auth.users u on u.id = p.id
where p.email = 'sync@fullstackfs.com.au';
