# VC Limited — vcltd.co

Brand and website for **VC Limited**, a logistics & supply chain consultancy
operating at the intersection of logistics and manufacturing (Business Bay,
Dubai). A fast, dependency-free static site plus a full logo system and a
matching email signature.

```
├── index.html              the site (single page)
├── 404.html                branded not-found page
├── css/styles.css          all styling (design tokens at the top)
├── js/main.js              nav, scroll reveals, contact form
├── assets/
│   ├── brand/              logo system (SVG + PNG + ICO)
│   ├── fonts/              self-hosted Space Grotesk, Archivo, IBM Plex Mono (SIL OFL)
│   └── og-image.png        social sharing card
├── email-signature/        signature.html + install guide
└── scripts/generate_brand.py   regenerates every brand asset
```

## Identity

- **Mark** — "VC." — the full stop. Space Grotesk letterforms closed by an
  orange square period: *we identify. we implement. we deliver.* The orange
  square is the brand's atomic element, reused across the site as heading
  punctuation, list bullets and separators.
- **Palette** — black `#0B0B0C` · white `#FFFFFF` · orange `#FF4D00`
  (soft `#FF7A3D`, deep `#D63F00`)
- **Type** — Space Grotesk (display) · Archivo (body) · IBM Plex Mono (labels)

To tweak the logo system, edit `scripts/generate_brand.py` and run:

```bash
pip install fonttools brotli pillow
python3 scripts/generate_brand.py
```

| File | Use |
|---|---|
| `assets/brand/mark.svg` / `mark-dark.svg` | mark for light / dark backgrounds |
| `assets/brand/logo-light.svg` / `logo-dark.svg` | full lockup (wordmark is vector paths — no font needed) |
| `assets/brand/favicon.svg` + `favicon.ico` | browser icons |
| `assets/brand/apple-touch-icon.png` | iOS / avatar-sized tile |
| `assets/og-image.png` | link previews (WhatsApp, LinkedIn, X…) |

## Content checklist before going live

- [ ] **Signature placeholders** — name, title, mobile in `email-signature/signature.html`
- [ ] **Legal line** — add a registered legal name / licence number to the footer if required
- [ ] **Phone number** — the site currently lists email + address only; add a
      phone line to the contact section if you want one
- [ ] **Form delivery** — the form opens the visitor's email app (no backend).
      To receive submissions silently instead, point the form at
      [Formspree](https://formspree.io) or similar: set
      `action="https://formspree.io/f/<id>" method="POST"` in `index.html`
      and remove the mailto handler in `js/main.js`.

## Preview locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

(Any static server works; the site is plain HTML/CSS/JS with zero build step.)

## Deploy

The site is static — host it anywhere. For GitHub Pages:

1. Repo → **Settings → Pages** → Source: *Deploy from a branch* → `main` / root.
2. Add the custom domain `vcltd.co`, then at your DNS provider create:
   - `A` records for `vcltd.co` → `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`
   - `CNAME` for `www` → `<your-github-username>.github.io`
3. Tick **Enforce HTTPS** once the certificate is issued.

Netlify/Vercel/Cloudflare Pages: point them at the repo root, no build command.

## Letterhead

`letterhead/` holds the company stationery, both regenerable:

- **`VC-Letterhead-A4.docx`** — the everyday Word template: open, replace the
  `[bracketed]` placeholders, write the letter. Brand art is embedded as an
  image and body text is Arial, so it renders identically on any machine.
  Rebuild with `node scripts/generate_letterhead_docx.js`.
- **`VC-Letterhead-A4.pdf`** — blank print-ready stationery (real brand
  fonts embedded). Rebuilt from `letterhead/letterhead.html` via
  `chrome --headless --no-pdf-header-footer --print-to-pdf=letterhead/VC-Letterhead-A4.pdf letterhead/letterhead.html`.

## Email signature

See [`email-signature/README.md`](email-signature/README.md) — personalise
three placeholders, copy, paste into Gmail/Outlook/Apple Mail.
