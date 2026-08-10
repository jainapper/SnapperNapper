# fullstackfs.com.au — quote form fix

`index.html` here is the live Fullstack marketing site with two corrections
applied. It was taken from the deployed page, because the site's own source is
not in this repository. **If you have that source, apply the two changes below to
it instead and treat this copy as a reference** — it will drift the moment
anything else on the site changes.

The site is deployed as the Vercel project `fullstack-fulfillment`. This folder
is not part of the FS Database build and is not served from
`fs-database.vercel.app`.

## 1. The form fields overlapped

The stylesheet has no `box-sizing: border-box`. Every field is `width: 100%`
with `padding: 13px 16px` and a 1px border, so each one renders 34px wider than
its grid column. In the two-column rows that is 18px more than the 16px gap, so
First Name ran into Last Name, Email into Phone, and Company into ABN — they read
as one merged bar with a seam through it.

```css
/* added immediately before the .f-input,.f-select rule */
.f-input,.f-select,.f-textarea,textarea.f-input{box-sizing:border-box}
```

One line. Verified at 1440, 1280 and 390 wide: no pair of fields overlaps.

## 2. The form never sent anything

The submit handler validated the fields, hid the form and showed the
"Quote request received" panel. It made no request. Every quote submitted since
the site went live was validated, thanked, and discarded.

It now posts to the FS Database intake and only claims success once that
succeeds:

- `POST https://fs-database.vercel.app/api/lead` with the form as JSON
- on failure it re-enables the button, shows an error naming
  `info@fullstackfs.com.au`, and leaves everything typed in place
- a hidden `company_website_url` field is a honeypot; anything that fills it in
  gets a polite 200 and is dropped

The lead appears in the FS Database Leads tab within a minute — the app pulls
every 60 seconds.

## Still to do

The **onboarding questionnaire** on the same site has the same problem: it
collects answers and does not submit them anywhere. It needs the same treatment,
posting into the `onboarding` table.
