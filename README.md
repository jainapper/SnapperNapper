# FYBRE — fybrelab.com

Brand implementation and website for **FYBRE™** — *Engineered for Growth®*.
Not a beauty brand: a performance system for hair, skin, and body, launching
with the 24-hour hair growth system. Built to the **FYBRE Brand DNA** guide
(Noize Agency): the F glyph, the extended FYBRE™ wordmark, the volt
gradient, and the official product line and copy.

A fast, dependency-free static site plus a full logo system and a matching
email signature.

```
├── index.html              the site (single page)
├── 404.html                branded not-found page
├── css/styles.css          all styling (design tokens at the top)
├── js/main.js              nav, reveals, waitlist forms, day→night theatre
├── assets/
│   ├── brand/              logo system (SVG + PNG + ICO)
│   ├── fonts/              self-hosted Archivo + Space Mono (SIL OFL)
│   ├── products/           product illustrations (hand-drawn SVG)
│   └── og-image.png        social sharing card (volt gradient lockup)
├── email-signature/        signature.html + install guide
└── scripts/generate_brand.py   regenerates every brand asset + web fonts
```

## Identity (per the Brand DNA)

- **Mark** — the F glyph: four fibre-blades with 45° cuts and wind-swept
  tips, stacked into a forward-leaning F. Reconstructed as vector from the
  brand guide and reused across the site as watermark, favicon and label.
- **Lockup** — glyph + `FYBRE™` in extended grotesk caps, with the tagline
  `ENGINEERED FOR GROWTH` tracked out and width-matched beneath.
- **Palette** — carbon `#0A0A0B` · paper `#F5F5F2` · volt `#D8F231`, with
  the volt gradient (`#F1F3E2 → #E0EC8C → #E5FA46`) for feature moments
  (olive `#57660A` is volt's readable twin on light backgrounds)
- **Type** — Archivo (variable width/weight; extended caps for display) ·
  Space Mono for data labels
- **Voice** — sports science, not cosmetics: protocols, modes, numbers,
  guarantees. Product taglines from the guide: *Night mode. Growth mode.* ·
  *Unstoppable growth — all day long.* · *Bold hair. Bold moves.* ·
  *Brush. Boost. Breakthrough.*

The signature move on the site: **the 24-hour theatre**. Scrolling through
"The System" runs a clock from 06:00 to 06:00 while the stage crossfades
from day (paper) to night (carbon) — day mode hands over to night mode,
exactly like the product pair (FYBRE White → FYBRE Black).

To tweak the logo system or regenerate fonts, edit
`scripts/generate_brand.py` and run:

```bash
pip install fonttools brotli pillow
python3 scripts/generate_brand.py
```

| File | Use |
|---|---|
| `assets/brand/mark.svg` / `mark-dark.svg` / `mark-volt.svg` | F glyph for light / dark / accent use |
| `assets/brand/logo-light.svg` / `logo-dark.svg` | glyph + FYBRE™ lockup (vector paths — no font needed) |
| `assets/brand/logo-tagline-light.svg` / `logo-tagline-dark.svg` | full lockup with ENGINEERED FOR GROWTH |
| `assets/brand/favicon.svg` + `favicon.ico` | browser icons |
| `assets/brand/apple-touch-icon.png` | iOS / avatar-sized tile |
| `assets/og-image.png` | link previews (WhatsApp, Instagram, LinkedIn, X…) |

## Content checklist before going live

- [ ] **Instagram handle** — the site links to
      `https://www.instagram.com/fybrehair/` (packaging in the brand guide
      prints FYBREHAIR.COM); confirm the real handle (three places in
      `index.html`, one in `email-signature/signature.html`)
- [ ] **Domain strategy** — this repo deploys to `fybrelab.com` (FYBRE Lab
      is the research division per the guide); packaging references
      `fybrehair.com`. If both domains exist, point one at the other.
- [ ] **Contact email** — waitlist submissions and the signature use
      `hello@fybrelab.com`; swap if the inbox differs (`js/main.js`,
      `email-signature/signature.html`)
- [ ] **Signature placeholders** — name, title, mobile in
      `email-signature/signature.html`
- [ ] **Legal line** — add a registered legal name / company number to the
      footer if required; the guide marks the tagline as
      *Engineered for Growth®* — keep the ® consistent once registered
- [ ] **Ordering** — the site runs in live posture with no commerce backend:
      "Get the Growth Kit" opens a prefilled order-enquiry email. Wire up a
      real checkout (Shopify buy button, Stripe payment link) when ready by
      swapping the two mailto CTAs in `index.html`.
- [ ] **Ingestible placeholders** — six placeholder cards (four gummies, two
      capsules) sit under Products with redacted names. When artwork and
      pricing land: replace `assets/products/gummies-tba.svg` /
      `capsules-tba.svg`, the `.tba-name` blocks and the "pricing to come"
      copy in `index.html`.
- [ ] **Claims review** — the copy carries the brand's own claims from the
      guide and live site (90-day follicular-density guarantee,
      science-backed); confirm wording with whoever signs off on product
      claims before launch.
- [ ] **Photography** — the brand guide's packaging renders and lifestyle
      photography aren't in this repo; the product SVGs are placeholders in
      the same art direction. Swap in the real packshots when available
      (`assets/products/*.svg`, referenced from `index.html`).

## Preview locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

(Any static server works; the site is plain HTML/CSS/JS with zero build step.)

## Deploy

The site is static — host it anywhere. For GitHub Pages:

1. Repo → **Settings → Pages** → Source: *Deploy from a branch* → `main` / root.
2. Add the custom domain `fybrelab.com`, then at your DNS provider create:
   - `A` records for `fybrelab.com` → `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`
   - `CNAME` for `www` → `<your-github-username>.github.io`
3. Tick **Enforce HTTPS** once the certificate is issued.

Netlify/Vercel/Cloudflare Pages: point them at the repo root, no build command.

(The domain currently points at Wix — switching the DNS records above cuts
it over to this site. Keep the Wix email capture list; export it before
closing that account.)

## Email signature

See [`email-signature/README.md`](email-signature/README.md) — personalise
three placeholders, copy, paste into Gmail/Outlook/Apple Mail.
