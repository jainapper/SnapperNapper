# Supabase — project `fofghcaqgwgixjshmubt`

Region `ap-southeast-2` (Sydney), deliberately separate from the Klip project so
FS ops data and Klip's acquirer/KYC data never share a database.

## Already applied

| Migration | What it did |
|---|---|
| `fs_database_core_schema` | The twelve document tables, `profiles`, `app_settings`, the `fs-files` storage bucket, and the row-level security behind all of them |
| `fs_database_requests_and_team` | `requests` and `team_users`, plus the trigger that stamps `updated_at` / `updated_by` |
| `fs_database_row_order` | The `ord` column, so a collection round-trips in the order the UI arranged it |
| `fs_database_harden_functions` | Pinned `search_path` on the trigger function; revoked `is_admin()` from `anon` |

## Not yet applied

`001_public_intake.sql` — the public write path for the website's quote form and
onboarding questionnaire. **Both forms fail until this runs.** They fail visibly,
with their own error messages, so nothing is lost quietly in the meantime.

`002_scheduled_sync.sql` — the `sync@fullstackfs.com.au` account the scheduled
Starshipit sync signs in as. **Set a password in the file before running it**, and
use the same value for the Vercel environment variable `FSDB_SYNC_PASSWORD`.
Until this runs, the dashboard is only as fresh as the last time someone had a tab
open.

Run them in the SQL editor, or approve the migration tool calls.

## Still open

**Leaked-password protection is off** in Supabase Auth. Turning it on checks new
passwords against HaveIBeenPwned. Worth doing — and worth rotating any account
still on a common dictionary password first, since that check would reject it on
the way in.
