# FS Database — Fullstack Fulfillment

The internal ops database for **Fullstack Fulfillment** (fullstackfs.com.au), in the
same Night Freight brand as the website. One static page, zero dependencies, works
anywhere — open `index.html` or drop this folder on any static host.

**Live build:** https://fs-database.vercel.app — deployed from this branch via a
Vercel build step that clones the repo (redeploy after pushing changes; it is not
auto-linked to git yet).

```
fs-database/
├── index.html      the whole app (styles + views + logic)
├── manifest.json   PWA manifest — lets phones install it like an app
├── assets/         brand + carrier logos + home-screen icons
└── README.md       this file
```

**Beta mode:** the app starts **empty** — no demo clients, orders, leads, documents,
products or POs. Only the real logins and the carrier reference cards are there.
Existing browsers are cleaned automatically the first time they load this build
(uploaded files that belong to carriers or the catalog PDF are kept; orphaned demo
uploads are pruned). Want the sample dataset back to explore a screen? *Settings →
**Load demo data*** — and *Erase everything* wipes the lot.

## The tabs

| Tab | What it does |
|---|---|
| **Dashboard** | Orders shipped, products sold, SKU counts, active clients and open orders — with per-day chart, carrier mix, units by client, top SKUs, and a live shipments feed where every tracking number links to the carrier's tracking page. **Transit times** show collection → delivered per order: average door-to-door days, a distribution histogram, per-carrier averages, and a door-to-door stamp on every delivered order in the feed (filter chips: Delivered / In transit / Packed / Awaiting). Filter everything by 7 / 14 / 30 / 90 days. Runs on demo data until Starshipit is connected. |
| **New Client Leads** | A **summary table** up top (name, company, volume, timeline, received, status), then the inquiries as readable cards with the same fields as the site form. Pipeline: New → Contacted → Quoted → Won / Lost, plus notes, search, and one-click **Convert to onboarding**. |
| **New Client Onboarding** | One record per new client: the **website questionnaire** (same sections and questions as fullstackfs.com.au/#/onboarding, each with its title), a **KYC checklist** (ASIC extract, director ID, ABN check, proof of address, bank/DDR, insurance, DG declaration) with an upload slot per item, and the four **agreements** (Services Agreement, NDA, Performance Guarantee, Rate Card) tracked Not sent → Sent → Signed and attached from the library or uploaded signed. Progress bar rolls all three up. Questions can be **tailored per client** — add new points, rename or remove any of them (hover a row for the ✎ / ✕ tools). |
| **Client Documents** | The shared library — NDAs, agreements, guarantee docs, rate cards, and carrier freight-charge explainers. Adding one is two fields: **pick the type, upload the file** (the title comes from the file name). Searchable, downloadable, shareable. |
| **Carriers** | A card per carrier — Australia Post, DHL Express, NZ Post, SEKO, Parcel Right — with account #, rep, phone, email, portal link, tracking-URL template, attached agreement / rate card / surcharge explainer with an **expiry date** each (countdown pills warn at 30 days and flag expired), and a clear **notes** box for corrections. Starshipit and Extensiv sit below as platforms. |
| **Client Go Live** | The default pre-launch gate, per client. Three checks pull **automatically from onboarding** (questionnaire complete, KYC complete, all agreements signed) and eight ops checks are ticked by hand (stock received, SKUs in Extensiv, Starshipit connected, test order dispatched, shipping rules, billing, returns, date confirmed) — each with a note and done-date. The **Mark client LIVE** button only appears when every box is ticked, and clicking it promotes the client onto the dashboard as Live. |
| **Fullstack Catalog** | Simple on purpose: the **Eagle AU catalog PDF** lives up top, and below it the product list — name, SKU, **type (gummy / capsule / powder)**, flavour, mold or capsule size, and each product's **label template** (upload slot per product). **+ Add new product** asks exactly those fields. Every product added here appears in the Fullstack PO dropdown. |
| **Fullstack PO** | Orders to Eagle AU built straight from the catalog: pick products from the **dropdown**, set the **amount required** and the **required-by date** — name and SKU come along automatically. Still admin-only with the **two-signature rule** before Send (pre-written email + downloadable PO document). |
| **Team** | Deliberately simple: add a user with **full name, mobile and email**, then a **toggle zone** for every tab — with **All / None** one-tap buttons. Each person picks themselves in the sidebar and sees only their tabs. Optional per-user passwords (Set/Reset on the card) stored as salted hashes only. |

## Where the data lives

**Sign in and it is shared; don't and it is not.** The lock screen takes your
Fullstack email password. That signs you in to the shared database (Supabase,
Sydney region), and from then on records and uploaded documents live on the
server: the same data on your phone, your laptop and everyone else's. The
sidebar pill reads **Synced**.

Without a sign-in — or with no signal — the app still runs the same way on the
copy held in this browser (`localStorage` for records, IndexedDB for files), and
the pill says **This device only**. Nothing is sent anywhere in that state.

How the two stay in step:

- The browser copy is always the read path, so every screen renders instantly
  and works offline.
- A local edit is pushed within a second. Every 60 seconds (and whenever you
  come back to the tab) the device pushes what it owes and pulls what changed.
- An edit made with no signal is queued and pushed when the connection returns —
  the queue survives a reload.
- Conflicts are last-write-wins **per record**, so two people working in
  different rows never overwrite each other.
- Deletions made while offline don't propagate — a record deleted on a
  disconnected device comes back on the next pull. Delete it again once
  reconnected.

Who can see what is enforced by the database, not just the UI:

| | Admin (Jai) | Member (Darlene) |
|---|---|---|
| Leads, onboarding, go-live, documents, carriers, catalog, orders | read + write | read + write |
| Purchase orders | read + write | invisible |
| Starshipit API keys | read + write | invisible |
| Team roster | read + write | read only |

**Export backup** (sidebar or Settings) still downloads the whole database as one
JSON file, uploaded documents included. **Erase everything** now asks which one
you mean: erase for the whole team, or erase this device only and leave the
shared copy alone (signing back in restores it).

### Adding someone new

Adding a user in the Team tab puts them on the shared roster. Giving them a
**sign-in** is a separate step — it needs an account created in Supabase Auth
(Authentication → Users → Add user, email + password, "Auto Confirm"), then a
row in `public.profiles` with their `id`, `role` and `tabs`. Until that exists
they can use the app on their own device but won't sync.

## Keeping the dashboard current

Starshipit is synced **on a schedule by the server**, not by whoever has a tab
open — so the numbers are already right when you log in, including first thing in
the morning when nobody has been in since yesterday.

`supabase/functions/starshipit-sync/` runs every 5 minutes, scheduled by
`pg_cron` inside the database. It lives in Supabase rather than on Vercel because
Supabase hands an edge function its own service key: there is no password or API
key to store in a config file, an environment variable or this repository, and
the schedule is not limited by a hosting plan.

Each run is bounded by a **wall clock rather than by finishing the job**: it takes
the newest page per account, then spends what is left filling in line items and
delivery dates for orders still missing them, always holding back about a third of
the budget for the delivery-date pass. (Without that reserve the first pass eats
the whole run and delivery dates never get fetched — which is exactly how transit
times stayed empty before.) Whatever a run does not reach, the next one picks up,
so the backlog drains without any single run risking a timeout. Only records that
actually changed are written back.

The browser keeps its own 60-second tick as a fallback, but stands down whenever
the server has synced in the last 10 minutes, so the two never both hammer a
rate-limited API. Order history is upsert-only from a browser: the server keeps
more of it than any one device does, and a device trimming its local copy must
never take the server's with it.

The dashboard shows whichever sync ran most recently, marked *on the server* when
that is the newer one.

Setup is two steps, both in `supabase/` — deploy the function, run one SQL file.
There is nothing to fill in.

## Connecting Starshipit (live dashboard, all child accounts)

The Starshipit web login (app2.starshipit.com) can't be read directly — the
supported route is their API, and **every child account has its own API key**:

1. In Starshipit, open each child account → *Settings → API* — copy that
   account's **API key** (the **subscription key** is shared across the login).
2. FS Database → *Settings → Starshipit API* — paste the subscription key, add a
   row per child account (name + API key), **Connect & sync all accounts**.

Both keys sit on the same Starshipit page — the **subscription key** is shared
across the login, the **API key** is per child account. Connect refuses early with
a plain message if the subscription key is blank (the most common cause of a 404
or 403 from their API).

Every synced order is tagged with its child account as the client, so the
dashboard splits by client automatically. On the live Vercel link the built-in
proxy (`api/ss.js`, called as `/api/ss?p=/api/orders/shipped`) handles the
browser-side CORS problem with zero setup — note it is a *fixed* function path,
because plain Vercel functions do not route multi-segment catch-alls. Anywhere
else, set a proxy URL (a 20-line Cloudflare Worker does it):

```js
// Cloudflare Worker — deploy at workers.cloudflare.com, then paste its URL
// into Settings → "Proxy base URL"
export default {
  async fetch(req) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: cors() });
    const upstream = await fetch("https://api.starshipit.com" + url.pathname + url.search, {
      headers: {
        "Content-Type": "application/json",
        "StarShipIT-Api-Key": req.headers.get("StarShipIT-Api-Key") || "",
        "Ocp-Apim-Subscription-Key": req.headers.get("Ocp-Apim-Subscription-Key") || "",
      },
    });
    return new Response(upstream.body, { status: upstream.status, headers: cors() });
  },
};
const cors = () => ({
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type, StarShipIT-Api-Key, Ocp-Apim-Subscription-Key",
});
```

Keys entered while signed in are stored on the server under an **admin-only** row,
so they follow you to your other devices and stay invisible to members. Signed
out, they stay in that browser alone. If you'd rather lock a proxy down,
hard-code the keys server-side and keep its URL private.

Order history is capped at **95 days / 4,000 records** in the browser copy. That
cap exists because a browser gives roughly 5 MB and an uncapped history filled
it, taking the stored API keys down with it. Settings are now written before bulk
data, a failed write raises a banner instead of a toast, and neither an empty
sync nor an unrendered form can blank what is stored.

## The website quote form

`fullstackfs.com.au` → **Get a Quote** posts straight into this database.

`api/lead.js` is the intake. It takes the form as JSON, maps it to the same
record shape the Leads tab uses (the checkbox slugs become the labels the app
shows; the volume, SKU and timeline values already match), and writes it as a new
lead. It shows up in the app on the next sync — within a minute.

The database lets an anonymous caller **INSERT a lead and nothing else** — never
read, change or delete one — and the policy additionally requires the row to be
marked `source: website`, status `new`, under 8 KB, with a `web-` id it cannot
use to overwrite anything. So the worst a stranger can do is add noise to the
leads list. On top of that the intake validates the fields, requires a real
email, and carries a honeypot.

Two changes were needed on the website itself; both are in `website/` with the
reasoning. The short version: its submit handler showed "Quote request received"
without sending anything, and a missing `box-sizing: border-box` made every
two-column field overlap the one beside it by 18px.

## The website onboarding questionnaire

The same site's questionnaire posts to `api/onboarding.js`, which maps its 28
answers onto the keys the Onboarding tab already uses and files the record as
`in_progress`, ready to be worked. Same anonymous-insert-only rules as the quote
intake.

Because someone has just spent ten minutes on it, a failure there never shows a
thank-you: it says it did not send, keeps every answer in the page, and offers
**Try again** and **Copy my answers**.

## Brand & charts

Design tokens are lifted straight from the website (`--ground #0d0c0a`,
`--raise #151310`, `--accent #f55d2f`, Inter + mono labels). Chart colors are a
**validated palette** — checked for colour-blind separation (protan/deutan ΔE ≥ 8
adjacent), lightness band, and ≥ 3:1 contrast against the panel surface:

| Slot | Hex | Assigned to |
|---|---|---|
| 1 | `#f0561f` | Australia Post + all single-series charts |
| 2 | `#3987e5` | DHL Express |
| 3 | `#199e70` | NZ Post |
| 4 | `#c98500` | SEKO Logistics |
| 5 | `#d55181` | Parcel Right |

Carrier colours are fixed to the carrier (never re-assigned by rank), every chart
has a hover tooltip and a **⊞ table** twin, and status pills always carry a label.

## Deploy

Any static host, no build step:

- **Netlify / Vercel** — drag the `fs-database` folder in, done.
- **GitHub Pages** — serve this folder from a branch.

The page is safe to host publicly: it ships only the Supabase project URL and the
**publishable** key, both of which are designed to be public. Everything a signed-in
person can read or write is decided by row-level security in the database, and a
visitor who never signs in sees an empty local app.

The Starshipit proxy (`api/ss.js`) needs a host that runs functions — on Vercel it
is included; on GitHub Pages set a proxy URL in Settings instead.

### The backend

Supabase project `fofghcaqgwgixjshmubt` (region `ap-southeast-2`, Sydney) —
deliberately separate from the Klip project, so FS ops data and Klip's
acquirer/KYC data never share a database.

| Piece | What is there |
|---|---|
| Tables | `clients`, `shipments`, `ss_orders`, `leads`, `onboarding`, `docs`, `carriers`, `catalog`, `go_live`, `pos`, `requests`, `team_users` — each `id text` / `data jsonb` / `ord int`, so a collection round-trips in the order the UI arranged it |
| `profiles` | one row per sign-in: name, email, `role`, and the per-tab `tabs` map |
| `app_settings` | single documents — the `starshipit` row is admin-only |
| Storage | bucket `fs-files`, private, signed-in access only |
| Policies | team-wide read/write, except purchase orders and the Starshipit keys (admin only) and the roster (admin writes, everyone reads) |

Still open: **leaked-password protection** is off in Supabase Auth. Turning it on
checks new passwords against HaveIBeenPwned. Worth doing — and worth rotating any
account still on a common dictionary password first, since that check would
reject it on the way in.
