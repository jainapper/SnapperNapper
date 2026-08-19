# Supabase — project `fofghcaqgwgixjshmubt`

Region `ap-southeast-2` (Sydney), deliberately separate from the Klip project so
FS ops data and Klip's acquirer/KYC data never share a database.

## Everything outstanding, in two steps

**1. Deploy the edge function.** `functions/starshipit-sync/` — the scheduled
Starshipit sync. Either paste it into Supabase → Edge Functions → Deploy a new
function named `starshipit-sync`, or from a terminal:

```
supabase functions deploy starshipit-sync --project-ref fofghcaqgwgixjshmubt --no-verify-jwt
```

`--no-verify-jwt` is deliberate: the function does its own check against a secret
held in the database, which is what lets the scheduler call it without a key
existing in any config file.

**2. Run `003_setup_everything.sql`** in the SQL editor. Nothing to fill in — it
generates the secret itself. It grants the website's two forms permission to file
a lead or a questionnaire, creates that secret, and schedules the sync every five
minutes.

Order does not matter. If the SQL runs first, the schedule simply starts working
the moment the function is deployed.

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

## Still open

**Leaked-password protection is off** in Supabase Auth. Turning it on checks new
passwords against HaveIBeenPwned. Worth doing — and worth rotating any account
still on a common dictionary password first, since that check would reject it on
the way in.
