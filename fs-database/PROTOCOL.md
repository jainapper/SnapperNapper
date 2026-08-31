# Judging whether a number is right

Written after the dashboard showed 750 orders for a week and Jai said that is not
what we shipped. He was right, and nothing in the system disagreed with the
number — which is the actual failure. A figure nobody can challenge is not a
strong figure, it is an unexamined one.

This is how a disputed number gets settled from now on, and what the system does
so that fewer of them need settling.

---

## The standing rule

**No number is presented as fact unless the system can say what it rests on.**

Every counted order now carries where its date came from, which account it
belongs to, and whether its line items have arrived. Anything the system cannot
vouch for is counted separately and shown — never quietly rolled into a total,
and never given an invented value so it looks complete.

Three things follow from that, and they are not negotiable:

1. **Nothing is fabricated to fill a gap.** An order with no ship date from
   Starshipit keeps no date. It does not get today's date so that it has one.
2. **An excluded record is reported, not dropped.** If 40 orders cannot be placed
   in the window, the dashboard says so next to the number they are missing from.
3. **A total that is known to be a floor is labelled as a floor.** Units sold is
   understated while line items are still arriving, and it says so.

---

## When a number looks wrong

**1. Say so immediately, and do not wait for proof.** Suspicion from someone who
knows the business is evidence. It is faster to check a figure than to discover
six weeks later that a decision was made on it.

**2. Read the Data check panel** at the bottom of the Dashboard. It lists every
way the current window is compromised, with a count and a share for each. If the
headline figure carries a **⚠**, the panel says why.

**3. Take the per-account split.** The panel breaks the window down by child
account. Comparing that against what each account shows in Starshipit itself
localises the problem in one step: every account off by a similar proportion
means the pipeline; one account wrong means that account's data or its key.

**4. Classify it.** There are only four kinds, and the fix differs for each:

| Kind | Looks like | Where the fault is |
|---|---|---|
| **Missing** | our number is lower than Starshipit's | orders not fetched, or discarded on the way in |
| **Inflated** | our number is higher | double counting, or records placed in the wrong window |
| **Misattributed** | totals right, split wrong | the account or client mapping |
| **Stale** | right, but for an earlier moment | the sync stopped running — check `sync_state` |

**5. Reproduce it in a test before fixing it.** Any real fault can be written as a
mock that fails. `scratchpad/mockss5.js` is the pattern: a Starshipit that behaves
badly on purpose. A fix without a failing test first is a guess.

**6. Record it below.** One line. The point is the pattern over time, not the
paperwork.

---

## What the system checks on its own

Run every sync, server-side, and stored under `app_settings.sync_state` so the
record exists whether or not anyone opens the app:

| Check | Why it matters |
|---|---|
| Orders with no ship date | they appear in no window, so every period figure is short by this many |
| Orders dated by `order_date` | an order date is a different event wearing a ship date's clothes |
| Orders with no line items | they contribute zero to units sold and to every SKU figure |
| One tracking number on two orders | a possible double count |
| One Starshipit order id under two accounts | normal, and the reason the account is part of the key |
| Delivered before shipped | impossible, and it poisons transit times |
| Ids stored before the account joined the key | these may already have overwritten each other |

The dashboard flags the headline figure when more than 2% of the window is
affected, or whenever a duplicate or a collision appears at all.

---

## Known faults, and what they cost

### 1. Order ids collided between child accounts — *fixed*

The key was `ss-<order_id>`. Every Starshipit child account numbers its own
orders from its own sequence, so account A's order 1052 and account B's order
1052 were the same record, and one overwrote the other on every sync.

Measured against a mock where two accounts share a numbering range: **40 orders
in, 20 stored.** Half of them, silently. With eleven accounts the overlap is
worse, not better.

The account is now part of the key. Existing rows stored under the old scheme are
counted and reported as `pre-fix ids` until they age out of the 95-day window.

### 2. Undated orders were stamped with the time of the sync — *fixed*

The date fell back to `new Date()` when Starshipit returned no date. Those orders
were then counted as having shipped at the moment we happened to look — landing
in the current 7-day window, and moving forward again on the next sync.

In the same mock, **8 of 40 orders were dated today** that had no date at all.
That inflates the current period and deflates every earlier one.

Undated orders now keep no date, are excluded from every window, and are
reported as excluded.

### 3. The scheduled sync was refused before it read anything — *fixed*

The first live run found all ten child accounts and fetched **zero orders**. It
fired roughly twenty requests at Starshipit in 1.6 seconds and nine of the ten
came back `HTTP 429`.

Two causes. The list fetch had no retry — the detail and tracking passes were
wrapped, the list that feeds them was not — so one refusal discarded a whole
account for that run. And nothing paced the requests: the rate limit is on the
subscription key, which every child account shares, so retrying a single request
only gets it refused again. The gap has to be global.

Reproduced against a Starshipit that refuses bursts (`scratchpad/mockss6.js`),
running the deployed code and the fix against the identical mock:

| | orders | accounts | refused by the API | lost |
|---|---|---|---|---|
| before | 80 | 2 of 3 | 43 | one account, entirely |
| after | 120 | 3 of 3 | 3 | none |

Accounts are now also taken in rotation from where the last run stopped, so a run
that cannot reach all ten does not reach the same ones every time — otherwise the
accounts at the end of the list would never sync at all.

Worth naming what this looked like from outside: `ok: true`, a green run, a fresh
`lastSync`, and no orders. The errors were recorded, which is the only reason it
was caught — but the run still called itself successful.

**A sync that fetches nothing from every account is a failure, not a quiet day.**
That is now enforced rather than left to whoever reads the row. A run that reached
accounts and came back with nothing marks itself `degraded`, answers `500` so the
scheduler records the failure too, and writes the reason into `sync_state`. The
app reads it: the Starshipit chip turns red and says **Server sync failing**
instead of showing a reassuring timestamp, and the Data check panel leads with the
fact that every figure below it is as old as the last run that worked.

### 3a. The same parcel was counted twice — *fixed in the reading*

Once the server started writing orders keyed by account, the build still live on
the teamaccess link carried on writing the same orders keyed by order id alone.
Starshipit ids are globally unique on this tenant, so those are the same parcel
under two keys, and every figure counted it twice.

The reading collapses them, keeping the account-keyed copy and reporting how many
were merged. Nothing is deleted while the old build can write them straight back;
`supabase/004_dedupe_legacy_orders.sql` clears them out once it cannot.

The check meant to catch this was itself wrong: it required `acctId` to be set,
but a row written before the account went into the key does not have one, so it
skipped precisely the rows it existed to find.

### 4. The scheduler called a function that did not exist — *fixed*

`run_starshipit_sync()` called `extensions.http_post`. `pg_net` always installs
into the `net` schema, whatever `create extension ... with schema` says, so the
function was never there. Because plpgsql resolves it at run time rather than at
create time, the migration applied cleanly and the schedule looked healthy while
every single run died on line 6.

Nothing surfaced this either. It was found by running the sync by hand instead of
trusting that a successful `create` meant a working call.

### 5. Nothing checked any of it — *fixed, and the reason for this document*

Neither fault would have been caught by the system. Both were found because
somebody who knew the real number looked at the screen and disagreed with it.

---

## Log

| Date | Number disputed | Verdict | Cause |
|---|---|---|---|
| 2026-08-19 | 750 orders shipped · 7d | wrong, both directions at once | id collisions losing orders; undated orders inflating the current window |
| 2026-08-31 | 0 orders from 10 accounts | wrong — refused, not empty | no pacing and no retry on the list fetch, against a shared rate limit |
| 2026-08-31 | schedule looked healthy | wrong — never ran | `extensions.http_post` does not exist; pg_net lives in `net` |
| 2026-08-31 | every order counted twice | wrong — inflated | two builds writing the same parcel under two key schemes |

---

## What this still does not do

Being straight about the edges, because a protocol that overstates its own
coverage is worse than none:

- **There is no independent source of truth.** Every check here compares the data
  against itself and against its own provenance. It can prove the pipeline is
  inconsistent; it cannot prove a consistent number is the true one. Only a count
  from Starshipit's own reporting, or from invoices, can do that.
- **The comparison against Starshipit is manual.** Step 3 asks a person to open
  Starshipit and compare. Pulling their own totals and reconciling automatically
  is the obvious next step and is not built.
- **Only the recent window is examined.** The sync reads the newest 500 shipped
  per account. Anything older is neither checked nor corrected.
