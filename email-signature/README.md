# FYBRE — email signature

`signature.html` is a table-based, image-free signature that renders reliably
in Outlook (Windows, Mac, Web), Gmail, and Apple Mail. The growth-bars tile
is built from coloured table cells, so nothing breaks when a client blocks
remote images.

## Personalise

Open `signature.html` in a text editor and replace:

| Placeholder | Notes |
|---|---|
| `{{FULL NAME}}` | your name |
| `{{JOB TITLE}}` | your role |
| `{{+61 400 000 000}}` | your mobile (also update the `tel:` link beside it) |

The email is set to `hello@fybrelab.com` — swap in a personal address if you
use one. The confidentiality note at the bottom is optional; delete that
table row if you don't want it.

## Install

First: open the edited `signature.html` in a browser, press `Ctrl/Cmd-A` then
`Ctrl/Cmd-C` to copy the rendered signature.

**Gmail** — Settings → *See all settings* → *General* → *Signature* →
*Create new* → paste → Save changes.

**Outlook (new / web)** — Settings → *Account* → *Signatures* → paste into a
new signature → set as default for new messages and replies.

**Outlook (classic Windows)** — File → Options → Mail → *Signatures…* →
*New* → paste → OK.

**Apple Mail** — Settings → *Signatures* → add a signature, paste, and untick
*"Always match my default message font"*.

## Optional: use the real logo image

Once the site is live, you can swap the text tile for the actual mark: replace
the tile `<td>` with

```html
<img src="https://fybrelab.com/assets/brand/apple-touch-icon.png" width="48" height="48"
     alt="FYBRE" style="display:block; border-radius:10px;">
```

Keep the cell-built version if you want the signature to survive image
blocking, which many corporate mail servers still apply.
