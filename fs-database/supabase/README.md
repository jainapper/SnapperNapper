# Supabase — project `fofghcaqgwgixjshmubt`

Region `ap-southeast-2` (Sydney), deliberately separate from the Klip project so
FS ops data and Klip's acquirer/KYC data never share a database.

## Outstanding: one line of SQL

Everything else is done. The edge function is deployed and active, the secret
exists, `run_starshipit_sync()` exists, and the website's two forms can file a
lead and a questionnaire. What is missing is the timer that calls the function.

Supabase → SQL Editor → paste this → Run:

```sql
select cron.schedule('fs-starshipit-sync', '*/5 * * * *', 'select public.run_starshipit_sync()');
```

That is the whole remaining step. It returns a job id — any number means it
worked. Re-running it a second time creates a duplicate job rather than failing,
so if you are unsure whether it already ran, check first:

```sql
select jobid, schedule, active from cron.job where jobname = 'fs-starshipit-sync';
```

Pasting the whole of `003_setup_everything.sql` also works and is safe to repeat;
every other statement in it is written to no-op if it has already been applied.

### Checking it worked

```sql
select data->>'lastSync', data->>'fetched', data->>'written', data->>'errors'
from public.app_settings where key = 'sync_state';
```

A timestamp within the last five minutes means it is running. To trigger a run
immediately rather than waiting: `select public.run_starshipit_sync();`

## Why it is built this way

The sync needs privileged database access, which normally means a password or a
service key stored somewhere. An edge function is handed the service key by
Supabase itself, so there is nothing to store — which is why this lives here
rather than on Vercel. It also means `pg_cron` drives the schedule, so the
frequency is not limited by a hosting plan.

The one secret involved — proving to the function that a caller is really the
scheduler — is generated inside the database and read from there by both sides.
It exists in no environment variable, no config file, and no repository.

## Already applied

| Migration | What it did |
|---|---|
| `fs_database_core_schema` | The twelve document tables, `profiles`, `app_settings`, the `fs-files` storage bucket, and the row-level security behind all of them |
| `fs_database_requests_and_team` | `requests` and `team_users`, plus the trigger that stamps `updated_at` / `updated_by` |
| `fs_database_row_order` | The `ord` column, so a collection round-trips in the order the UI arranged it |
| `fs_database_harden_functions` | Pinned `search_path` on the trigger function; revoked `is_admin()` from `anon` |
| `fs_database_public_intake_and_schedule` | The website's lead and questionnaire intake policies, the `cron_auth` secret, `pg_cron` / `pg_net`, and `run_starshipit_sync()` |

The `starshipit-sync` edge function is deployed and active, with JWT verification
off — deliberate, because it checks the caller against the database secret
itself, which is what lets the scheduler reach it without a key existing in any
config file.

## Still open

**Leaked-password protection is off** in Supabase Auth. Turning it on checks new
passwords against HaveIBeenPwned. Worth doing — and worth rotating any account
still on a common dictionary password first, since that check would reject it on
the way in.
