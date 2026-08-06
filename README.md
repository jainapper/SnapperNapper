# FYBRE — fybrelab.com

Brand and website for **FYBRE**, the 24-hour hair growth system —
performance hair science for professionals, athletes and high-achievers.
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
│   └── og-image.png        social sharing card
├── email-signature/        signature.html + install guide
└── scripts/generate_brand.py   regenerates every brand asset + web fonts
```

## Identity

- **Mark** — the growth bars: three ascending strands, rounded at the tip,
  planted on a shared baseline. Hair fibre × bar chart × signal meter —
  *growth you can measure*. The bars are the brand's atomic element, reused
  across the site as bullets, dividers and data punctuation.
- **Palette** — carbon `#0A0A0B` · bone `#F2F0EA` · volt `#C8FF2E`
  (olive `#55700A` is volt's readable twin on light backgrounds)
- **Type** — Archivo Expanded Black (display) · Archivo (body) ·
  Space Mono (data labels)
- **Voice** — sports science, not cosmetics: protocols, numbers, guarantees.

The signature move on the site: **the 24-hour theatre**. Scrolling through
"The System" runs a clock from 06:00 to 06:00 while the stage crossfades
from day (bone) to night (carbon) — day activation hands over to night
recovery, exactly like the product line (FYBRE White → FYBRE Black).

To tweak the logo system or regenerate fonts, edit
`scripts/generate_brand.py` and run:

```bash
pip install fonttools brotli pillow
python3 scripts/generate_brand.py
```

| File | Use |
|---|---|
| `assets/brand/mark.svg` / `mark-dark.svg` / `mark-volt.svg` | bars for light / dark / accent use |
| `assets/brand/logo-light.svg` / `logo-dark.svg` | full lockup (wordmark is vector paths — no font needed) |
| `assets/brand/favicon.svg` + `favicon.ico` | browser icons |
| `assets/brand/apple-touch-icon.png` | iOS / avatar-sized tile |
| `assets/og-image.png` | link previews (WhatsApp, Instagram, LinkedIn, X…) |

## Content checklist before going live

- [ ] **Instagram handle** — the site links to
      `https://www.instagram.com/fybrelab/`; confirm that's the real handle
      (three places in `index.html`, one in `email-signature/signature.html`)
- [ ] **Contact email** — waitlist submissions and the signature use
      `hello@fybrelab.com`; swap if the inbox differs (`js/main.js`,
      `email-signature/signature.html`)
- [ ] **Signature placeholders** — name, title, mobile in
      `email-signature/signature.html`
- [ ] **Legal line** — add a registered legal name / company number to the
      footer if required
- [ ] **Waitlist delivery** — the form opens the visitor's email app (no
      backend). To collect signups silently instead, point both forms at
      [Formspree](https://formspree.io) or a list tool (Mailchimp, Loops):
      set `action="https://formspree.io/f/<id>" method="POST"` on the two
      `<form>` elements in `index.html` and remove the mailto handler in
      `js/main.js`.
- [ ] **Claims review** — the copy carries the brand's own claims (90-day
      follicular-density guarantee, science-backed); confirm wording with
      whoever signs off on product claims before launch.

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
