# Supplement Brand Database — Elite Supps · Nutrition Warehouse · ASN

`supplement-brands-database.xlsx` — a deduplicated database of every brand stocked by the
three Australian supplement retailers, built for bulk import into a CRM or emailing tool.

## What's in the workbook

| Sheet | Contents |
|---|---|
| **CRM Import** | One row per brand — the import sheet. Entity name, ABN, country, website, email, phone, address, product formats, category mix, which retailers stock it, SKU counts, example products. |
| **Format Matrix** | SKU counts per brand broken down by format (powder / capsules / tablets / gummies / liquid / RTD / bars / topical / accessories). |
| **Product List** | Every product listing captured (5,104 rows) with its retailer, brand, name, retailer category and derived format — the evidence behind the brand rows. |
| **Summary** | Coverage and composition counts. |

## How it was built

1. **Catalogue capture** — full product catalogues pulled from each retailer's public Shopify
   JSON endpoints (`/products.json`), paginated to exhaustion:
   * Elite Supps — 985 products
   * Australian Sports Nutrition (ASN) — 1,089 products
   * Nutrition Warehouse — 3,111 products
2. **Brand normalisation** — 368 raw vendor strings collapsed to 299 canonical brands via a
   curated alias map (e.g. `Krupt` / `KRUPT` / `Krupt Supps`; `BSC ( Body Science )` /
   `BSc Supplements` / `Body Science`). Non-brand vendors (gift cards, promos, clearance
   buckets) were excluded. The original strings are kept in the *Retailer Vendor Names* column.
3. **Format classification** — each product classified from, in priority order: the retailer's
   own `form:` tag, the product title, then the retailer category.
4. **Contact and entity research** — per-brand web research for official website, contact email,
   phone and postal address; Australian legal entity names and ABNs from ABN Lookup
   (abr.business.gov.au).

## Coverage — read before importing

Contact fields were only filled where a source was actually found. Nothing is inferred or
generated, so blanks are genuine gaps rather than placeholders.

| Field | Brands populated (of 299) |
|---|---|
| Website | 250 |
| Email | 191 |
| Phone | 136 |
| Legal entity name | 164 |
| ABN | 31 |

The 47 brands marked *"Not researched — retailer listing only"* in the **Record Status** column
each carry six SKUs or fewer; they have retailer, SKU and format data but no contact research. Filter that column before a send.

Emails are role addresses published on the brands' own sites (support@, info@, sales@) — general
business contacts, not personal addresses. A handful are the founder's or a named manager's
address where that is the only contact the brand publishes.

## Caveats

* SKU counts are what each retailer had published on the capture date, and include bundles,
  apparel and accessories where the brand sells them.
* ABNs are only recorded where the ABN Lookup match was unambiguous (exact entity-name match
  with a consistent location). Ambiguous matches were left blank rather than guessed.
* Some brands are house or exclusive labels of the retailers themselves — for example
  *Anabolix Nutrition* shares Nutrition Warehouse's ABN (17 128 438 755), and *AlphaBreed*
  routes its customer service to ASN. These are flagged in the entity column.
* Overseas brands (US, UK, EU) list the global brand's contact details; their Australian
  distributor may be the more useful outreach target.

All derived cells (total SKUs, retailer counts, the Summary tallies) are stored as computed
values rather than live formulas, so the file imports cleanly into tools that read cell values
only. Every figure is derived from the Product List sheet in the same workbook.

**Captured:** 31 August 2026.
