/* Intake for the "Get a Quote" form on fullstackfs.com.au.
 *
 * The form posts here, this turns it into the same record shape the Leads tab
 * uses, and writes it straight to the shared database. It appears in the app on
 * the next sync — within a minute.
 *
 * The database only lets an anonymous caller INSERT a lead, never read, change
 * or delete one, so nothing here holds a secret worth stealing.
 */
/* Overridable so the intake can be pointed at a test database. */
const SB_URL  = process.env.FSDB_SUPABASE_URL || 'https://fofghcaqgwgixjshmubt.supabase.co';
const SB_ANON = process.env.FSDB_SUPABASE_KEY || 'sb_publishable_exBeewUiYhoyw21kYB5guQ_OKUIiCDp';

const ORIGINS = [
  'https://fullstackfs.com.au',
  'https://www.fullstackfs.com.au',
  'https://fullstack-fulfillment.vercel.app'
];

/* The form posts slugs; the app stores the labels people read. */
const INTEGRATIONS = {
  shopify: 'Shopify', woocommerce: 'WooCommerce', bigcommerce: 'BigCommerce',
  squarespace: 'Squarespace', wix: 'Wix', wix_studio: 'Wix Studio',
  netsuite: 'NetSuite', cin7: 'Cin7', dear: 'DEAR', zapier: 'Zapier',
  starshipit: 'Starshipit', australia_post: 'Australia Post', other: 'Other'
};
const NEEDS = {
  satchels: 'Satchels', cartons: 'Cartons', branded_inserts: 'Branded Inserts',
  gift_boxes: 'Gift Boxes', seasonal_promo: 'Seasonal/Promo Packs',
  returns: 'Returns Processing', fragile: 'Fragile Handling', kitting: 'Kitting/Assembly'
};
const VOLUMES   = ['under_100', '100_500', '500_2000', '2000_10000', '10000_plus'];
const SKUBANDS  = ['under_50', '50_200', '200_1000', '1000_plus'];
const TIMELINES = ['asap', '1_3_months', '3_6_months', '6_plus_months', 'exploring'];

const str = (v, max) => String(v == null ? '' : v).trim().slice(0, max || 200);
const pick = (v, allowed) => (allowed.indexOf(String(v)) >= 0 ? String(v) : '');
function labels(v, map){
  if(!Array.isArray(v)) v = v == null ? [] : [v];
  const out = [];
  v.slice(0, 30).forEach(x => { const l = map[String(x)]; if(l && out.indexOf(l) < 0) out.push(l); });
  return out;
}

module.exports = async (req, res) => {
  const origin = req.headers.origin || '';
  /* Only the Fullstack sites may post from a browser. Anything else still gets a
     CORS answer, just not permission to read the reply. A local origin is allowed
     only when the intake is deliberately pointed at a test database. */
  const local = process.env.FSDB_SUPABASE_URL && /^http:\/\/localhost(:\d+)?$/.test(origin);
  res.setHeader('Access-Control-Allow-Origin', (ORIGINS.indexOf(origin) >= 0 || local) ? origin : ORIGINS[0]);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Vary', 'Origin');
  if(req.method === 'OPTIONS'){ res.status(204).end(); return; }
  if(req.method !== 'POST'){ res.status(405).json({ error: 'POST only' }); return; }

  let b = req.body;
  if(typeof b === 'string'){ try{ b = JSON.parse(b); }catch(e){ b = null; } }
  if(!b || typeof b !== 'object'){ res.status(400).json({ error: 'Expected a JSON body' }); return; }

  /* A hidden field no person ever fills in. Answer politely so a bot learns nothing. */
  if(str(b.company_website_url)){ res.status(200).json({ ok: true }); return; }

  const first   = str(b.first_name, 80);
  const email   = str(b.email, 160);
  const company = str(b.company_name, 160);
  if(!first || !email || !company || email.indexOf('@') < 1){
    res.status(400).json({ error: 'First name, email and company are required' });
    return;
  }

  const lead = {
    id: 'web-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    ts: new Date().toISOString(),
    first: first,
    last: str(b.last_name, 80),
    email: email,
    phone: str(b.phone, 40),
    company: company,
    abn: str(b.abn_account_number, 60),
    website: str(b.website, 200),
    integrations: labels(b['integrations[]'] || b.integrations, INTEGRATIONS),
    volume: pick(b.monthly_volume, VOLUMES),
    skus: pick(b.active_sku, SKUBANDS),
    dims: str(b.item_dimensions_weight, 300),
    needs: labels(b['additional_needs[]'] || b.additional_needs, NEEDS),
    timeline: pick(b.start_timeline, TIMELINES),
    status: 'new',
    source: 'website',
    notes: ''
  };
  lead.id = lead.id.slice(0, 40);

  try{
    const r = await fetch(SB_URL + '/rest/v1/leads', {
      method: 'POST',
      headers: {
        apikey: SB_ANON,
        Authorization: 'Bearer ' + SB_ANON,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      /* ord -1 puts it above the existing leads until the app renumbers them */
      body: JSON.stringify([{ id: lead.id, data: lead, ord: -1 }])
    });
    if(!r.ok){
      const detail = await r.text().catch(() => '');
      console.error('lead intake rejected', r.status, detail.slice(0, 300));
      res.status(502).json({ error: 'Could not record the inquiry' });
      return;
    }
    res.status(200).json({ ok: true, id: lead.id });
  }catch(e){
    console.error('lead intake failed', String(e));
    res.status(502).json({ error: 'Could not record the inquiry' });
  }
};
