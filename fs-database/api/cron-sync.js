/* Scheduled Starshipit sync.
 *
 * The browser's 60-second tick only runs while someone has a tab open, so
 * overnight nothing happens and the first person in each morning lands on
 * yesterday's numbers. This runs on a schedule instead, whether or not anyone
 * is logged in, so the dashboard is already current when you open it.
 *
 * It signs in as a dedicated sync account rather than carrying a service-role
 * key, so row-level security still applies to everything it does.
 *
 * Every run is bounded by a wall clock, not by finishing the job: it takes the
 * newest page per account, then spends whatever time is left filling in line
 * items and delivery dates for orders still missing them. Work not done this
 * run is picked up by the next one, so the backlog drains without any single
 * run risking the function timeout.
 */
const SB_URL  = process.env.FSDB_SUPABASE_URL || 'https://fofghcaqgwgixjshmubt.supabase.co';
const SB_ANON = process.env.FSDB_SUPABASE_KEY || 'sb_publishable_exBeewUiYhoyw21kYB5guQ_OKUIiCDp';
const SS_BASE = process.env.FSDB_STARSHIPIT_URL || 'https://api.starshipit.com';

const BUDGET_MS   = Number(process.env.FSDB_SYNC_BUDGET_MS || 45000);
const LIST_PAGES  = Number(process.env.FSDB_SYNC_PAGES || 2);
const KEEP_DAYS   = 95;
const CONCURRENCY = 2;                 /* Starshipit rate-limits bursts */

const started = () => Date.now();
let t0 = 0;
const left = () => BUDGET_MS - (Date.now() - t0);
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* ————— Supabase ————— */
async function sbSignIn(){
  const email = process.env.FSDB_SYNC_EMAIL;
  const password = process.env.FSDB_SYNC_PASSWORD;
  if(!email || !password) throw new Error('FSDB_SYNC_EMAIL / FSDB_SYNC_PASSWORD are not set');
  const r = await fetch(SB_URL + '/auth/v1/token?grant_type=password', {
    method: 'POST',
    headers: { apikey: SB_ANON, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.toLowerCase().trim(), password })
  });
  const j = await r.json().catch(() => ({}));
  if(!r.ok) throw new Error('sync sign-in failed: ' + (j.error_description || j.msg || r.status));
  return j.access_token;
}
async function sb(token, path, opts){
  opts = opts || {};
  const r = await fetch(SB_URL + path, {
    method: opts.method || 'GET',
    headers: Object.assign({
      apikey: SB_ANON, Authorization: 'Bearer ' + token, 'Content-Type': 'application/json'
    }, opts.headers || {}),
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body)
  });
  if(!r.ok) throw new Error('HTTP ' + r.status + ' ' + (await r.text().catch(() => '')).slice(0, 160));
  const t = await r.text();
  return t ? JSON.parse(t) : null;
}

/* ————— Starshipit — the same tolerant reading the app uses ————— */
let subKey = '';
async function ssFetch(path, apiKey){
  const r = await fetch(SS_BASE + path, { headers: {
    'Content-Type': 'application/json',
    'StarShipIT-Api-Key': apiKey || '',
    'Ocp-Apim-Subscription-Key': subKey
  }});
  if(!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
function ssItems(o){
  const raw = o.items || o.order_items || o.products || o.lines || o.line_items || [];
  return (Array.isArray(raw) ? raw : []).map(i => ({
    sku: String(i.sku || i.product_code || i.item_code || i.code || i.product_sku || '').trim(),
    name: String(i.description || i.name || i.product_name || '').trim(),
    qty: Number(i.quantity != null ? i.quantity : (i.qty != null ? i.qty : 1)) || 1
  })).filter(i => i.sku || i.name || i.qty);
}
function ssDate(v){
  if(!v) return null;
  const t = new Date(v);
  return isNaN(t.getTime()) ? null : t.toISOString();
}
/* Delivery timestamps live on the order, on a tracking summary, or only inside
   the event list — and "out for delivery" is not delivery. */
function ssDelivered(o){
  if(!o) return null;
  const direct = o.delivery_date || o.delivered_date || o.date_delivered || o.actual_delivery_date ||
                 o.deliveredAt || o.delivered_at ||
                 (o.tracking_status && (o.tracking_status.delivered_date || o.tracking_status.delivery_date));
  const d = ssDate(direct);
  if(d) return d;
  const evs = o.events || o.tracking_events || o.trackingEvents || o.history ||
              (o.tracking_status && o.tracking_status.events) ||
              (o.tracking && o.tracking.events) || [];
  let best = null;
  if(Array.isArray(evs)) evs.forEach(e => {
    const txt = String((e && (e.status || e.description || e.event || e.message || e.detail)) || '').toLowerCase();
    if(txt.indexOf('deliver') < 0 || txt.indexOf('out for deliver') >= 0 || txt.indexOf('attempted') >= 0) return;
    const when = ssDate(e.event_datetime || e.date || e.timestamp || e.occurred_at || e.datetime || e.event_date || e.time);
    if(when && (!best || when > best)) best = when;
  });
  return best;
}
function ssIsDelivered(o){
  const st = String(o.status || o.tracking_status_text || o.shipment_status ||
                    (o.tracking_status && (o.tracking_status.status || o.tracking_status.name)) || '').toLowerCase();
  return st.indexOf('deliver') >= 0;
}
const CARRIERS = ['auspost', 'dhl', 'nzpost', 'seko', 'parcelright'];
function carrierKey(raw){
  const s = String(raw || '').toLowerCase();
  return CARRIERS.find(k => s.indexOf(k === 'auspost' ? 'aus' : k === 'parcelright' ? 'parcel'
                                     : k === 'nzpost' ? 'nz' : k) >= 0) || '';
}
function mapOrder(o, shipped, accountLabel){
  const items = ssItems(o);
  const deliveredTs = ssDelivered(o);
  const dest = o.destination || o.shipping_address || o.address || null;
  return {
    id: 'ss-' + (o.order_id || o.order_number),
    ssId: o.order_id != null ? String(o.order_id) : '',
    orderNo: String(o.order_number || o.name || o.reference || o.order_id || '—'),
    clientId: '',
    clientName: accountLabel || 'Starshipit',
    carrier: carrierKey(o.carrier_name || o.carrier || o.shipping_method || o.carrier_service),
    carrierLabel: o.carrier_name || o.carrier || o.shipping_method || '',
    dest: dest ? [dest.city, dest.state || dest.region, dest.country].filter(Boolean).join(' ') : '',
    tracking: o.tracking_number || o.tracking_code || '',
    trackingUrl: o.tracking_url || '',
    status: !shipped ? 'unshipped' : (deliveredTs || ssIsDelivered(o)) ? 'delivered' : 'transit',
    date: o.shipped_date || o.shipped_at || o.order_date || o.date || new Date().toISOString(),
    deliveredTs,
    items,
    value: o.declared_value || o.total_price || o.order_value || null
  };
}
async function ssPages(path, apiKey, maxPages){
  const out = [];
  for(let page = 1; page <= maxPages; page++){
    if(left() < 6000) break;
    const r = await ssFetch(path + '?limit=250&page=' + page, apiKey);
    const batch = r.orders || r.Orders || [];
    out.push.apply(out, batch);
    if(batch.length < 250) break;
  }
  return out;
}
/* '/api/orders/shipped?order_id=' is deliberately not a candidate: it ignores the
   filter and returns the whole list, whose first row passes for a detail response
   while carrying no line items. */
const DETAIL_PATHS = [
  id => '/api/orders?order_id=' + encodeURIComponent(id),
  id => '/api/orders/' + encodeURIComponent(id),
  id => '/api/orders/details?order_id=' + encodeURIComponent(id)
];
const TRACK_PATHS = [
  t => '/api/track?tracking_number=' + encodeURIComponent(t),
  t => '/api/track/' + encodeURIComponent(t),
  t => '/api/tracking?tracking_number=' + encodeURIComponent(t)
];
let detailPath = null, trackPath = null;
function unwrapOrder(r){
  if(!r) return null;
  const o = r.order || r.Order || r.data || r;
  if(Array.isArray(o)) return o[0] || null;
  if(Array.isArray(o.orders)) return o.orders[0] || null;
  return o;
}
/* Only this order's detail counts — otherwise a list endpoint's first row is
   mistaken for it and every lookup silently returns the same itemless record. */
const sameOrder = (o, id) => !!o && o.order_id != null && String(o.order_id) === String(id);

async function ssDetail(orderId, apiKey){
  if(detailPath){
    const o = unwrapOrder(await ssFetch(detailPath(orderId), apiKey));
    if(!sameOrder(o, orderId)) throw new Error('detail mismatch');
    return o;
  }
  let lastErr;
  for(const p of DETAIL_PATHS){
    try{
      const o = unwrapOrder(await ssFetch(p(orderId), apiKey));
      if(sameOrder(o, orderId)){ detailPath = p; return o; }
    }catch(e){ lastErr = e; }
  }
  throw lastErr || new Error('no working single-order endpoint');
}
function unwrapTrack(r){
  if(!r) return null;
  const t = r.results || r.result || r.tracking || r.track || r.shipment || r.data || r;
  return Array.isArray(t) ? (t[0] || null) : t;
}
async function ssTrack(tracking, apiKey){
  if(trackPath) return unwrapTrack(await ssFetch(trackPath(tracking), apiKey));
  let lastErr;
  for(const p of TRACK_PATHS){
    try{
      const t = unwrapTrack(await ssFetch(p(tracking), apiKey));
      if(t && typeof t === 'object'){ trackPath = p; return t; }
    }catch(e){ lastErr = e; }
  }
  throw lastErr || new Error('no tracking endpoint');
}
/* Rate limits are expected, not exceptional — back off rather than lose the order. */
async function retry(fn){
  for(let attempt = 0; attempt < 5; attempt++){
    try{ return await fn(); }
    catch(e){
      const limited = /HTTP (429|503)/.test(e.message);
      if(attempt === 4 || !limited || left() < 4000) throw e;
      await sleep(700 * (attempt + 1) * (attempt + 1));
    }
  }
}
/* floor: stop when less than this much of the budget remains, so a later pass
   still gets a turn. Without it the first pass eats the whole run and the second
   never happens — which is exactly how delivery dates stayed empty before. */
async function pool(items, worker, floorMs){
  let i = 0, done = 0, failed = 0;
  const stop = floorMs || 5000;
  const run = async () => {
    while(i < items.length && left() > stop){
      const n = i++;
      try{ await worker(items[n]); done++; }
      catch(e){ failed++; }
    }
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, run));
  return { done, failed, skipped: items.length - done - failed };
}

/* ————— the run ————— */
module.exports = async (req, res) => {
  t0 = started();

  /* Only Vercel's scheduler, or someone holding the secret, may start a run. */
  const secret = process.env.CRON_SECRET;
  const auth = req.headers.authorization || '';
  const given = auth.replace(/^Bearer /, '') || (req.query && req.query.key) || '';
  if(secret && given !== secret){ res.status(401).json({ error: 'unauthorized' }); return; }

  const report = { ok: false, accounts: 0, fetched: 0, written: 0, enriched: 0, tracked: 0, errors: [] };
  try{
    const token = await sbSignIn();

    const cfg = await sb(token, '/rest/v1/app_settings?key=eq.starshipit&select=data');
    const ss = (cfg && cfg[0] && cfg[0].data) || {};
    subKey = ss.subKey || '';
    const accounts = (ss.accounts || []).filter(a => a.apiKey);
    if(!subKey || !accounts.length){
      res.status(200).json(Object.assign(report, { ok: true, note: 'no Starshipit keys stored yet' }));
      return;
    }
    report.accounts = accounts.length;

    /* what we already hold, so only genuine changes are written back */
    const existingRows = await sb(token, '/rest/v1/ss_orders?select=id,data');
    const existing = {};
    (existingRows || []).forEach(r => { existing[r.id] = r.data; });

    /* 1 — newest orders per account */
    const seen = {};
    for(const a of accounts){
      if(left() < 8000) break;
      try{
        const shipped = await ssPages('/api/orders/shipped', a.apiKey, LIST_PAGES);
        shipped.forEach(o => { const m = mapOrder(o, true, a.label); seen[m.id] = { m, key: a.apiKey }; });
        try{
          const un = await ssPages('/api/orders/unshipped', a.apiKey, 1);
          un.forEach(o => { const m = mapOrder(o, false, a.label); seen[m.id] = { m, key: a.apiKey }; });
        }catch(e){}
      }catch(e){
        report.errors.push(a.label + ': ' + e.message);
      }
    }
    report.fetched = Object.keys(seen).length;

    /* Carry forward what earlier runs already filled in, so enrichment accumulates
       instead of starting over every time. */
    Object.keys(seen).forEach(id => {
      const prev = existing[id];
      const m = seen[id].m;
      if(!prev) return;
      if((!m.items || !m.items.length) && prev.items && prev.items.length) m.items = prev.items;
      if(!m.deliveredTs && prev.deliveredTs){ m.deliveredTs = prev.deliveredTs; m.status = 'delivered'; }
      if(!m.tracking && prev.tracking) m.tracking = prev.tracking;
    });

    /* 2 — fill in line items for orders still missing them */
    const cutoff = Date.now() - KEEP_DAYS * 86400e3;
    const recent = id => { const t = new Date(seen[id].m.date).getTime(); return isNaN(t) || t >= cutoff; };
    const needItems = Object.keys(seen)
      .filter(id => recent(id) && seen[id].m.ssId && !(seen[id].m.items || []).length)
      .sort((x, y) => new Date(seen[y].m.date) - new Date(seen[x].m.date));
    /* Leave a share of the run for the tracking pass below. */
    const trackReserve = Math.max(6000, Math.floor(BUDGET_MS * 0.35));
    const itemStats = await pool(needItems, async id => {
      const { m, key } = seen[id];
      const d = await retry(() => ssDetail(m.ssId, key));
      if(!d) return;
      const items = ssItems(d);
      if(items.length){ m.items = items; report.enriched++; }
      if(!m.tracking) m.tracking = d.tracking_number || d.tracking_code || '';
      const del = ssDelivered(d);
      if(del){ m.deliveredTs = del; m.status = 'delivered'; }
    }, trackReserve);

    /* 3 — delivery dates, which live on the tracking record rather than the order */
    const needTrack = Object.keys(seen)
      .filter(id => recent(id) && seen[id].m.tracking && !seen[id].m.deliveredTs && seen[id].m.status !== 'unshipped')
      .sort((x, y) => new Date(seen[y].m.date) - new Date(seen[x].m.date));
    const trackStats = await pool(needTrack, async id => {
      const { m, key } = seen[id];
      const t = await retry(() => ssTrack(m.tracking, key));
      const del = ssDelivered(t);
      if(del){ m.deliveredTs = del; m.status = 'delivered'; report.tracked++; }
      else if(t && ssIsDelivered(t)) m.status = 'delivered';
    });
    report.itemLookups = itemStats;
    report.trackLookups = trackStats;

    /* 4 — write back only what actually changed */
    const rows = [];
    Object.keys(seen).forEach(id => {
      const m = seen[id];
      const body = JSON.stringify(m.m);
      if(existing[id] && JSON.stringify(existing[id]) === body) return;
      rows.push({ id, data: m.m, ord: 0 });
    });
    for(let i = 0; i < rows.length; i += 200){
      await sb(token, '/rest/v1/ss_orders', {
        method: 'POST',
        body: rows.slice(i, i + 200),
        headers: { Prefer: 'resolution=merge-duplicates,return=minimal' }
      });
    }
    report.written = rows.length;

    /* 5 — leave a mark so the app can show when the server last looked */
    await sb(token, '/rest/v1/app_settings', {
      method: 'POST',
      body: [{ key: 'sync_state', data: {
        lastSync: new Date().toISOString(),
        accounts: report.accounts, fetched: report.fetched, written: report.written,
        enriched: report.enriched, tracked: report.tracked,
        outstandingItems: itemStats.skipped + itemStats.failed,
        outstandingTracking: trackStats.skipped + trackStats.failed,
        errors: report.errors.slice(0, 6),
        ms: Date.now() - t0
      }}],
      headers: { Prefer: 'resolution=merge-duplicates,return=minimal' }
    });

    report.ok = true;
    report.ms = Date.now() - t0;
    res.status(200).json(report);
  }catch(e){
    report.errors.push(String(e && e.message || e));
    report.ms = Date.now() - t0;
    console.error('cron sync failed', report);
    res.status(500).json(report);
  }
};
