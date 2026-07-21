# VC Limited — vcltd.co

Brand and website for **VC Limited**, a general trading company in the UAE.
A fast, dependency-free static site plus a full logo system and a matching
email signature.

```
├── index.html              the site (single page)
├── 404.html                branded not-found page
├── css/styles.css          all styling (design tokens at the top)
├── js/main.js              nav, scroll reveals, counters, contact form
├── assets/
│   ├── brand/              logo system (SVG + PNG + ICO)
│   ├── fonts/              self-hosted Archivo + IBM Plex Mono (SIL OFL)
│   └── og-image.png        social sharing card
├── email-signature/        signature.html + install guide
└── scripts/generate_brand.py   regenerates every brand asset
```

## Before going live — content checklist

The copy is written to be real, but a few facts are placeholders. Search
`TODO(owner)` in `index.html` and update:

- [ ] **Stats bar** — markets served / product lines figures
- [ ] **Phone number** — `+971 4 000 0000` (hero contact + signature)
- [ ] **Office address** — currently just "Dubai, United Arab Emirates"
- [ ] **Legal line in the footer** — add your registered name + licence number
- [ ] **Email** — assumed `info@vcltd.co` (index.html + js/main.js + signature)
- [ ] Division names/descriptions if your trade mix differs

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
   - `A` records for `vcltd.co` → `185.199.108.153`, `.109.`, `.110.`, `.111.153`
   - `CNAME` for `www` → `<your-github-username>.github.io`
3. Tick **Enforce HTTPS** once the certificate is issued.

Netlify/Vercel/Cloudflare Pages: point them at the repo root, no build command.

## Brand assets

| File | Use |
|---|---|
| `assets/brand/mark.svg` / `mark-dark.svg` | monogram for light / dark backgrounds |
| `assets/brand/logo-light.svg` / `logo-dark.svg` | full lockup (wordmark is vector paths — no font needed) |
| `assets/brand/favicon.svg` + `favicon.ico` | browser icons |
| `assets/brand/apple-touch-icon.png` | iOS / avatar-sized tile |
| `assets/og-image.png` | link previews (WhatsApp, LinkedIn, X…) |

Palette: ink `#0A0E17` · paper `#F6F4EF` · gold `#C9A227` (soft `#E8C766`,
deep `#8C6D12`). Type: Archivo (display/body) + IBM Plex Mono (labels), both
self-hosted under the SIL Open Font License.

To tweak the logo, edit `scripts/generate_brand.py` and run:

```bash
pip install fonttools brotli pillow
python3 scripts/generate_brand.py
```

## Email signature

See [`email-signature/README.md`](email-signature/README.md) — personalise
four placeholders, copy, paste into Gmail/Outlook/Apple Mail.
