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

It ships **seeded demo data** so every screen is alive on first open — demo records
are marked, and *Settings → Reset demo data / Erase everything* clears them when
you're ready to run it for real.

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

Everything stays **in the browser** — records in `localStorage`, uploaded files in
IndexedDB. Nothing is sent to any server, so the app can be hosted publicly while
the data stays with whoever uses it.

That also means data is **per browser, per device**. To move or share it:
**Export** (sidebar or Settings) downloads one JSON backup including uploaded
files; **Import backup** restores it elsewhere. Export regularly — clearing
browser data clears the database.

## Connecting Starshipit (live dashboard, all child accounts)

The Starshipit web login (app2.starshipit.com) can't be read directly — the
supported route is their API, and **every child account has its own API key**:

1. In Starshipit, open each child account → *Settings → API* — copy that
   account's **API key** (the **subscription key** is shared across the login).
2. FS Database → *Settings → Starshipit API* — paste the subscription key, add a
   row per child account (name + API key), **Connect & sync all accounts**.

Every synced order is tagged with its child account as the client, so the
dashboard splits by client automatically. On the live Vercel link the built-in
`/api/ss` proxy handles the browser-side CORS problem with zero setup; anywhere
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

Keys are stored only in the browser. If you'd rather lock a proxy down,
hard-code the keys server-side and keep its URL private.

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
