# FS Database — Fullstack Fulfillment

The internal ops database for **Fullstack Fulfillment** (fullstackfs.com.au), in the
same Night Freight brand as the website. One static page, zero dependencies, works
anywhere — open `index.html` or drop this folder on any static host.

```
fs-database/
├── index.html      the whole app (styles + views + logic)
├── manifest.json   PWA manifest — lets phones install it like an app
├── assets/         brand + carrier logos + home-screen icons
└── README.md       this file
```

It ships **seeded demo data** so every screen is alive on first open — demo records
are marked, and *Settings → Reset demo data / Erase everything* clears them when
you're ready to run it for real.

## The tabs

| Tab | What it does |
|---|---|
| **Dashboard** | Orders shipped, products sold, SKU counts, active clients and open orders — with per-day chart, carrier mix, units by client, top SKUs, and a live shipments feed where every tracking number links to the carrier's tracking page. **Transit times** show collection → delivered per order: average door-to-door days, a distribution histogram, per-carrier averages, and a door-to-door stamp on every delivered order in the feed (filter chips: Delivered / In transit / Packed / Awaiting). Filter everything by 7 / 14 / 30 / 90 days. Runs on demo data until Starshipit is connected. |
| **New Client Leads** | Website "Get a Quote" inquiries, laid out as readable cards with the same fields as the site form (integrations, volume, SKUs, needs, timeline). Pipeline: New → Contacted → Quoted → Won / Lost, plus notes, search, and one-click **Convert to onboarding**. |
| **New Client Onboarding** | One record per new client: the **website questionnaire** (same sections and questions as fullstackfs.com.au/#/onboarding, each with its title), a **KYC checklist** (ASIC extract, director ID, ABN check, proof of address, bank/DDR, insurance, DG declaration) with an upload slot per item, and the four **agreements** (Services Agreement, NDA, Performance Guarantee, Rate Card) tracked Not sent → Sent → Signed and attached from the library or uploaded signed. Progress bar rolls all three up. |
| **Client Documents** | The shared library — NDAs, agreements, guarantee docs, rate cards, and carrier freight-charge explainers. Categorised, searchable, taggable to a client, downloadable, and shareable (opens a pre-written email; attach the downloaded file). |
| **Carriers** | A card per carrier — Australia Post, DHL Express, NZ Post, SEKO, Parcel Right — with account #, rep, phone, email, portal link, tracking-URL template, attached agreement / rate card / surcharge explainer, and notes. Starshipit and Extensiv sit below as platforms. |
| **Client Go Live** | The default pre-launch gate, per client. Three checks pull **automatically from onboarding** (questionnaire complete, KYC complete, all agreements signed) and eight ops checks are ticked by hand (stock received, SKUs in Extensiv, Starshipit connected, test order dispatched, shipping rules, billing, returns, date confirmed) — each with a note and done-date. The **Mark client LIVE** button only appears when every box is ticked, and clicking it promotes the client onto the dashboard as Live. |
| **Fullstack Catalog** | The internal FS catalog — packaging and consumables supplied by Eagle AU — with SKU, spec, unit cost, pack/MOQ, lead time, stock on hand (edit inline) and **live usage from sales data** (use-per-order × current orders/day → days of cover, flagged when cover drops under lead time + 14 days). Also holds **new product requests to Eagle AU**: drafted, submitted, then tracked Quoted → Approved → added to the catalog. |
| **Fullstack PO** | What to order from Eagle AU, driven by the sales data: a reorder-suggestions table turns the catalog flags into a purchase order in one click. **Admin-only** — every PO action sits behind the admin PIN — and every PO needs a **second signature from a different person** before it can be sent. Flow: Draft → Awaiting 2nd signature → Approved → Sent (pre-written email + downloadable PO document, GST totals included). |
| **Team** | Add users (admin or member) and toggle **exactly which tabs each person sees**. Everyone picks themselves in the sidebar switcher and their menu shows only their tabs; direct links to hidden tabs bounce back to the dashboard. Dashboard is always on, admins always keep Team, the last admin can't be demoted or deleted. This is a device-level switcher (not a login) — it keeps screens tidy and fingers out of admin areas; real per-person logins arrive with the backend phase, and the PO admin PIN stays as the hard gate meanwhile. |

## Where the data lives

Everything stays **in the browser** — records in `localStorage`, uploaded files in
IndexedDB. Nothing is sent to any server, so the app can be hosted publicly while
the data stays with whoever uses it.

That also means data is **per browser, per device**. To move or share it:
**Export** (sidebar or Settings) downloads one JSON backup including uploaded
files; **Import backup** restores it elsewhere. Export regularly — clearing
browser data clears the database.

## Connecting Starshipit (live dashboard)

1. Starshipit → *Settings → API* — copy the **API key** and **subscription key**.
2. FS Database → *Settings → Starshipit API* — paste both, **Connect & sync**.

One catch: the Starshipit API is built for server-to-server use, so browsers
usually block direct calls (CORS). The fix is a tiny proxy that forwards requests
and adds the CORS header — free on Cloudflare Workers:

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

Once connected, the dashboard reads shipped + unshipped orders from the account,
uses each order's own tracking link, and matches orders to clients by SKU prefix
(e.g. `APN-…` → Alpine Peak Nutrition). Keys are stored only in the browser.
If you'd rather lock the proxy down, hard-code the keys in the Worker and keep
its URL private instead of passing keys through.

## Eagle AU

Product requests and purchase orders go to Eagle AU. **Where these should land on
Eagle's side is still being confirmed** — so for now the app logs everything
internally and opens a pre-written email to the contact set in
*Settings → Eagle AU* (the PO document also downloads so it can be attached).
Once their process is known — an inbox, a portal, an API — only the send step
needs re-pointing; every request and PO is already structured data.

## Admin PIN & the two-signature rule

Creating, countersigning and sending POs is gated behind a shared **admin PIN** —
first unlock on the PO tab sets it (change or lock it in Settings). Every PO must
be signed by the person who prepared it and **countersigned by a different
person** (different name, same PIN) before Send unlocks. Honest caveat: this is a
client-side workflow control that keeps day-to-day fingers off the order button —
it is not real security or a legally robust audit trail. When the app grows a
backend, this is the first thing to upgrade to real accounts.

## On phones

The whole app is responsive, and it installs like a native app: open it on a
phone → browser menu → **Add to Home Screen**. It launches full-screen in the
Night Freight theme with its own icon. (For iPhones the app must be served over
HTTPS — any of the hosts below do that out of the box.)

## Wiring the website forms in

The website's quote form and onboarding questionnaire are front-end prototypes —
they don't submit anywhere yet. Until they're pointed at a form backend
(Formspree, Zoho, a webhook…), add inquiries with **+ Add lead** (same fields as
the form, ~30 seconds). When the site forms go live, the clean path is: form
backend → email/CSV → paste into a lead. The Leads and Onboarding data models
here already match the site fields one-to-one, so nothing needs remapping later.

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
- Add a password in front (Netlify password protection, Cloudflare Access) if it
  should be team-only — the app itself has no auth.
