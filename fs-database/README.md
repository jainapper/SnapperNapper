# FS Database — Fullstack Fulfillment

The internal ops database for **Fullstack Fulfillment** (fullstackfs.com.au), in the
same Night Freight brand as the website. One static page, zero dependencies, works
anywhere — open `index.html` or drop this folder on any static host.

```
fs-database/
├── index.html      the whole app (styles + views + logic)
├── assets/         brand + carrier logos (copied from the website)
└── README.md       this file
```

It ships **seeded demo data** so every screen is alive on first open — demo records
are marked, and *Settings → Reset demo data / Erase everything* clears them when
you're ready to run it for real.

## The tabs

| Tab | What it does |
|---|---|
| **Dashboard** | Orders shipped, products sold, SKU counts, active clients and open orders — with per-day chart, carrier mix, units by client, top SKUs, and a live shipments feed where every tracking number links to the carrier's tracking page. Filter everything by 7 / 14 / 30 / 90 days. Runs on demo data until Starshipit is connected. |
| **New Client Leads** | Website "Get a Quote" inquiries, laid out as readable cards with the same fields as the site form (integrations, volume, SKUs, needs, timeline). Pipeline: New → Contacted → Quoted → Won / Lost, plus notes, search, and one-click **Convert to onboarding**. |
| **New Client Onboarding** | One record per new client: the **website questionnaire** (same sections and questions as fullstackfs.com.au/#/onboarding, each with its title), a **KYC checklist** (ASIC extract, director ID, ABN check, proof of address, bank/DDR, insurance, DG declaration) with an upload slot per item, and the four **agreements** (Services Agreement, NDA, Performance Guarantee, Rate Card) tracked Not sent → Sent → Signed and attached from the library or uploaded signed. Progress bar rolls all three up. |
| **Client Documents** | The shared library — NDAs, agreements, guarantee docs, rate cards, and carrier freight-charge explainers. Categorised, searchable, taggable to a client, downloadable, and shareable (opens a pre-written email; attach the downloaded file). |
| **Carriers** | A card per carrier — Australia Post, DHL Express, NZ Post, SEKO, Parcel Right — with account #, rep, phone, email, portal link, tracking-URL template, attached agreement / rate card / surcharge explainer, and notes. Starshipit and Extensiv sit below as platforms. |

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
