/* Intake for the onboarding questionnaire on fullstackfs.com.au.
 *
 * The site walks a new client through the same questions the Onboarding tab
 * holds, so this maps the answers onto the same keys and files the record as
 * in_progress, ready to be worked. It appears in the app on the next sync.
 *
 * As with the quote intake, the database only lets an anonymous caller INSERT
 * an onboarding record — never read, change or delete one.
 */
const SB_URL  = process.env.FSDB_SUPABASE_URL || 'https://fofghcaqgwgixjshmubt.supabase.co';
const SB_ANON = process.env.FSDB_SUPABASE_KEY || 'sb_publishable_exBeewUiYhoyw21kYB5guQ_OKUIiCDp';

const ORIGINS = [
  'https://fullstackfs.com.au',
  'https://www.fullstackfs.com.au',
  'https://fullstack-fulfillment.vercel.app'
];

/* Every key the Onboarding tab reads. Anything the site sends that is not on
   this list is dropped, so a stranger cannot invent fields. */
const KEYS = [
  'company_name', 'company_address', 'city_state_post', 'company_phone', 'company_email',
  'primary_contact', 'primary_email', 'invalid_addr_emails', 'stock_report_emails', 'returns_emails',
  'billing_company', 'billing_address', 'billing_email',
  'products_desc', 'active_skus', 'dangerous_goods', 'sku_list_ok', 'sku_list_file',
  'weekly_under_500g', 'weekly_500g_1kg', 'weekly_over_1kg', 'golive_date',
  'packaging_type', 'ships_intl',
  'ecom_platform', 'it_contact', 'it_email', 'wms_erp'
];

const str = (v, max) => String(v == null ? '' : v).trim().slice(0, max || 400);

module.exports = async (req, res) => {
  const origin = req.headers.origin || '';
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
  if(str(b.company_website_url)){ res.status(200).json({ ok: true }); return; }   /* honeypot */

  const src = (b.answers && typeof b.answers === 'object') ? b.answers : b;
  const answers = {};
  KEYS.forEach(k => { const v = str(src[k], 1200); if(v) answers[k] = v; });

  if(!answers.company_name || !(answers.company_email || answers.primary_email)){
    res.status(400).json({ error: 'Company name and an email address are required' });
    return;
  }

  const rec = {
    id: 'web-ob-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    clientName: answers.company_name,
    acct: '',
    started: new Date().toISOString(),
    status: 'in_progress',
    source: 'website',
    answers: answers,
    files: {}, kyc: {}, agreements: {}, extras: [],
    notes: 'Submitted through the website questionnaire.'
  };
  rec.id = rec.id.slice(0, 48);

  try{
    const r = await fetch(SB_URL + '/rest/v1/onboarding', {
      method: 'POST',
      headers: {
        apikey: SB_ANON,
        Authorization: 'Bearer ' + SB_ANON,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      body: JSON.stringify([{ id: rec.id, data: rec, ord: -1 }])
    });
    if(!r.ok){
      const detail = await r.text().catch(() => '');
      console.error('onboarding intake rejected', r.status, detail.slice(0, 300));
      res.status(502).json({ error: 'Could not record the questionnaire' });
      return;
    }
    res.status(200).json({ ok: true, id: rec.id });
  }catch(e){
    console.error('onboarding intake failed', String(e));
    res.status(502).json({ error: 'Could not record the questionnaire' });
  }
};
