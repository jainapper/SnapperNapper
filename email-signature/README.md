# VC Limited — email signature

`signature.html` is a table-based, image-free signature that renders reliably
in Outlook (Windows, Mac, Web), Gmail, and Apple Mail. The monogram tile is
built from a coloured table cell, so nothing breaks when a client blocks
remote images.

## Personalise

Open `signature.html` in a text editor and replace:

| Placeholder | Example |
|---|---|
| `{{FULL NAME}}` | Jai Napper |
| `{{JOB TITLE}}` | Managing Director |
| `{{+971 50 000 0000}}` | your mobile number (also update the `tel:` link) |
| `{{name}}@vcltd.co` | your email address (both display text and `mailto:` link) |

The office line `+971 4 000 0000` and the confidentiality note are
placeholders too — edit or delete as needed.

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
<img src="https://vcltd.co/assets/brand/apple-touch-icon.png" width="48" height="48"
     alt="VC" style="display:block; border-radius:10px;">
```

Keep the text-tile version if you want the signature to survive image
blocking, which many corporate mail servers still apply.
