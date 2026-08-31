/* Scheduled Starshipit sync, run inside Supabase.
 *
 * The browser's 60-second tick only runs while someone has a tab open, so
 * overnight nothing happens and the first person in each morning lands on
 * yesterday's numbers. This runs on a schedule instead, whether or not anyone is
 * logged in, so the dashboard is already current when you open it.
 *
 * It lives here rather than on Vercel for two reasons: Supabase injects the
 * service key, so there is no password to store anywhere, and pg_cron can call
 * it as often as we like without a hosting plan getting in the way.
 *
 * The caller is checked against a secret held in the database, which pg_cron
 * reads from the same row — so the two agree without a secret existing in any
 * config file, environment variable or repository.
 *
 * Every run is bounded by a wall clock, not by finishing the job: it takes the
 * newest page per account, then spends what is left filling in line items and
 * delivery dates, always holding back a share for the delivery pass. Whatever a
 * run cannot reach, the next one picks up.
 */
const SB_URL   = Deno.env.get('SUPABASE_URL')!;
const SB_KEY   = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const SS_BASE  = Deno.env.get('FSDB_STARSHIPIT_URL') ?? 'https://api.starshipit.com';

const BUDGET_MS   = Number(Deno.env.get('FSDB_SYNC_BUDGET_MS') ?? 90000);
const LIST_PAGES  = Number(Deno.env.get('FSDB_SYNC_PAGES') ?? 2);
const KEEP_DAYS   = 95;
const CONCURRENCY = 2;                  /* Starshipit rate-limits bursts */

let t0 = 0;
const left = () => BUDGET_MS - (Date.now() - t0);
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

async function sb(path: string, opts: any = {}): Promise<any> {
  const r = await fetch(SB_URL + path, {
    method: opts.method ?? 'GET',
    headers: {
      apikey: SB_KEY, Authorization: 'Bearer ' + SB_KEY, 'Content-Type': 'application/json',
      ...(opts.headers ?? {})
    },
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body)
  });
  if(!r.ok) throw new Error('HTTP ' + r.status + ' ' + (await r.text().catch(() => '')).slice(0, 160));
  const t = await r.text();
  return t ? JSON.parse(t) : null;
}

/* ————— Starshipit: read every field tolerantly, shapes vary by plan ————— */
let subKey = '';

/* Starshipit rate-limits on the subscription key, and every child account shares
   one — so the pace has to be global rather than per account. The first live run
   fired roughly twenty requests in 1.6 seconds and was refused on nine of ten
   accounts. Each caller books the next slot before it leaves, which also spaces
   the two workers in the pool instead of letting them fire together. */
const MIN_GAP_MS = Number(Deno.env.get('FSDB_SS_GAP_MS') ?? 350);
let nextSlot = 0;
async function ssGate(){
  const now = Date.now();
  const wait = Math.max(0, nextSlot - now);
  nextSlot = Math.max(now, nextSlot) + MIN_GAP_MS;
  if(wait > 0) await sleep(wait);
}
async function ssFetch(path: string, apiKey: string): Promise<any> {
  await ssGate();
  const r = await fetch(SS_BASE + path, { headers: {
    'Content-Type': 'application/json',
    'StarShipIT-Api-Key': apiKey ?? '',
    'Ocp-Apim-Subscription-Key': subKey
  }});
  if(r.status === 429 || r.status === 503){
    /* Hold every caller off, not just this one — the limit is account-wide, so
       retrying only this request just spends the budget being refused again. */
    const ra = Number(r.headers.get('retry-after') ?? 0);
    nextSlot = Math.max(nextSlot, Date.now() + (ra > 0 ? Math.min(ra, 30) * 1000 : 2000));
    throw new Error('HTTP ' + r.status);
  }
  if(!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
function ssItems(o: any){
  const raw = o.items || o.order_items || o.products || o.lines || o.line_items || [];
  return (Array.isArray(raw) ? raw : []).map((i: any) => ({
    sku: String(i.sku || i.product_code || i.item_code || i.code || i.product_sku || '').trim(),
    name: String(i.description || i.name || i.product_name || '').trim(),
    qty: Number(i.quantity != null ? i.quantity : (i.qty != null ? i.qty : 1)) || 1
  })).filter((i: any) => i.sku || i.name || i.qty);
}
function ssDate(v: any){
  if(!v) return null;
  const t = new Date(v);
  return isNaN(t.getTime()) ? null : t.toISOString();
}
/* Delivery timestamps live on the order, on a tracking summary, or only inside
   the event list — and "out for delivery" is not delivery. */
function ssDelivered(o: any){
  if(!o) return null;
  const direct = o.delivery_date || o.delivered_date || o.date_delivered || o.actual_delivery_date ||
                 o.deliveredAt || o.delivered_at ||
                 (o.tracking_status && (o.tracking_status.delivered_date || o.tracking_status.delivery_date));
  const d = ssDate(direct);
  if(d) return d;
  const evs = o.events || o.tracking_events || o.trackingEvents || o.history ||
              (o.tracking_status && o.tracking_status.events) ||
              (o.tracking && o.tracking.events) || [];
  let best: string | null = null;
  if(Array.isArray(evs)) evs.forEach((e: any) => {
    const txt = String((e && (e.status || e.description || e.event || e.message || e.detail)) || '').toLowerCase();
    if(txt.indexOf('deliver') < 0 || txt.indexOf('out for deliver') >= 0 || txt.indexOf('attempted') >= 0) return;
    const when = ssDate(e.event_datetime || e.date || e.timestamp || e.occurred_at || e.datetime || e.event_date || e.time);
    if(when && (!best || when > best)) best = when;
  });
  return best;
}
function ssIsDelivered(o: any){
  const st = String(o.status || o.tracking_status_text || o.shipment_status ||
                    (o.tracking_status && (o.tracking_status.status || o.tracking_status.name)) || '').toLowerCase();
  return st.indexOf('deliver') >= 0;
}
const CARRIERS = ['auspost', 'dhl', 'nzpost', 'seko', 'parcelright'];
function carrierKey(raw: any){
  const s = String(raw || '').toLowerCase();
  return CARRIERS.find(k => s.indexOf(k === 'auspost' ? 'aus' : k === 'parcelright' ? 'parcel'
                                      : k === 'nzpost' ? 'nz' : k) >= 0) || '';
}
/* Which field a date came from decides how much it can be trusted, and nothing
   at all must stay nothing at all — stamping "now" on an undated order silently
   drops it into today's count. */
function ssWhen(o: any){
  for(const f of ['shipped_date', 'shipped_at', 'order_date', 'date']){
    const v = ssDate(o[f]);
    if(v) return { date: v, dateSource: f };
  }
  return { date: null, dateSource: null };
}
function mapOrder(o: any, shipped: boolean, accountLabel: string, acctId: string){
  const items = ssItems(o);
  const when = ssWhen(o);
  const deliveredTs = ssDelivered(o);
  const dest = o.destination || o.shipping_address || o.address || null;
  return {
    /* Every child account numbers its own orders from its own sequence, so two
       accounts routinely both have an order 1052. Without the account in the key
       one silently overwrites the other and the totals come out short. */
    id: 'ss-' + (acctId ? acctId + '-' : '') + (o.order_id || o.order_number),
    ssId: o.order_id != null ? String(o.order_id) : '',
    acctId: acctId || '',
    orderNo: String(o.order_number || o.name || o.reference || o.order_id || '—'),
    clientId: '',
    clientName: accountLabel || 'Starshipit',
    carrier: carrierKey(o.carrier_name || o.carrier || o.shipping_method || o.carrier_service),
    carrierLabel: o.carrier_name || o.carrier || o.shipping_method || '',
    dest: dest ? [dest.city, dest.state || dest.region, dest.country].filter(Boolean).join(' ') : '',
    tracking: o.tracking_number || o.tracking_code || '',
    trackingUrl: o.tracking_url || '',
    status: !shipped ? 'unshipped' : (deliveredTs || ssIsDelivered(o)) ? 'delivered' : 'transit',
    date: when.date,
    dateSource: when.dateSource,
    deliveredTs,
    items,
    value: o.declared_value || o.total_price || o.order_value || null
  };
}
async function ssPages(path: string, apiKey: string, maxPages: number){
  const out: any[] = [];
  for(let page = 1; page <= maxPages; page++){
    if(left() < 8000) break;
    /* Wrapped, because a single 429 here used to discard the whole account: the
       detail and tracking passes retried, the list that feeds them did not. */
    const r = await retry(() => ssFetch(path + '?limit=250&page=' + page, apiKey));
    const batch = r.orders || r.Orders || [];
    out.push(...batch);
    if(batch.length < 250) break;
  }
  return out;
}
/* '/api/orders/shipped?order_id=' is deliberately not a candidate: it ignores the
   filter and returns the whole list, whose first row passes for a detail response
   while carrying no line items. */
const DETAIL_PATHS = [
  (id: string) => '/api/orders?order_id=' + encodeURIComponent(id),
  (id: string) => '/api/orders/' + encodeURIComponent(id),
  (id: string) => '/api/orders/details?order_id=' + encodeURIComponent(id)
];
const TRACK_PATHS = [
  (t: string) => '/api/track?tracking_number=' + encodeURIComponent(t),
  (t: string) => '/api/track/' + encodeURIComponent(t),
  (t: string) => '/api/tracking?tracking_number=' + encodeURIComponent(t)
];
let detailPath: any = null, trackPath: any = null;
function unwrapOrder(r: any){
  if(!r) return null;
  const o = r.order || r.Order || r.data || r;
  if(Array.isArray(o)) return o[0] || null;
  if(Array.isArray(o.orders)) return o.orders[0] || null;
  return o;
}
/* Only this order's detail counts — otherwise a list endpoint's first row is
   mistaken for it and every lookup silently returns the same itemless record. */
const sameOrder = (o: any, id: string) => !!o && o.order_id != null && String(o.order_id) === String(id);

async function ssDetail(orderId: string, apiKey: string){
  if(detailPath){
    const o = unwrapOrder(await ssFetch(detailPath(orderId), apiKey));
    if(!sameOrder(o, orderId)) throw new Error('detail mismatch');
    return o;
  }
  let lastErr: any;
  for(const p of DETAIL_PATHS){
    try{
      const o = unwrapOrder(await ssFetch(p(orderId), apiKey));
      if(sameOrder(o, orderId)){ detailPath = p; return o; }
    }catch(e){ lastErr = e; }
  }
  throw lastErr ?? new Error('no working single-order endpoint');
}
function unwrapTrack(r: any){
  if(!r) return null;
  const t = r.results || r.result || r.tracking || r.track || r.shipment || r.data || r;
  return Array.isArray(t) ? (t[0] || null) : t;
}
async function ssTrack(tracking: string, apiKey: string){
  if(trackPath) return unwrapTrack(await ssFetch(trackPath(tracking), apiKey));
  let lastErr: any;
  for(const p of TRACK_PATHS){
    try{
      const t = unwrapTrack(await ssFetch(p(tracking), apiKey));
      if(t && typeof t === 'object'){ trackPath = p; return t; }
    }catch(e){ lastErr = e; }
  }
  throw lastErr ?? new Error('no tracking endpoint');
}
/* Rate limits are expected, not exceptional — back off rather than lose the order. */
async function retry<T>(fn: () => Promise<T>): Promise<T> {
  let lastErr: any;
  for(let attempt = 0; attempt < 5; attempt++){
    try{ return await fn(); }
    catch(e: any){
      lastErr = e;
      const limited = /HTTP (429|503)/.test(e.message ?? '');
      if(attempt === 4 || !limited || left() < 5000) throw e;
      await sleep(700 * (attempt + 1) * (attempt + 1));
    }
  }
  throw lastErr;
}
/* floor: stop while this much budget remains, so the pass after this one still
   gets a turn. Without it the first pass eats the whole run and delivery dates
   never get fetched — which is exactly how transit times stayed empty before. */
async function pool(items: string[], worker: (id: string) => Promise<void>, floorMs = 6000){
  let i = 0, done = 0, failed = 0;
  const run = async () => {
    while(i < items.length && left() > floorMs){
      const n = i++;
      try{ await worker(items[n]); done++; }
      catch(_e){ failed++; }
    }
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, run));
  return { done, failed, skipped: items.length - done - failed };
}

Deno.serve(async (req: Request) => {
  t0 = Date.now();

  /* The secret lives in a table only this function and pg_cron can read, so it
     exists in no config file, environment variable or repository. */
  const rows = await sb('/rest/v1/cron_auth?name=eq.starshipit-sync&select=secret').catch(() => null);
  const expected = rows && rows[0] && rows[0].secret;
  const given = req.headers.get('x-fsdb-cron') ?? '';
  if(!expected || given !== expected){
    return new Response(JSON.stringify({ error: 'unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' } });
  }

  const report: any = { ok: false, accounts: 0, fetched: 0, written: 0, enriched: 0, tracked: 0, errors: [] };
  try{
    const cfg = await sb('/rest/v1/app_settings?key=eq.starshipit&select=data');
    const ss = (cfg && cfg[0] && cfg[0].data) || {};
    subKey = ss.subKey || '';
    const accounts = (ss.accounts || []).filter((a: any) => a.apiKey);
    if(!subKey || !accounts.length){
      return new Response(JSON.stringify({ ...report, ok: true, note: 'no Starshipit keys stored yet' }),
        { headers: { 'Content-Type': 'application/json' } });
    }
    report.accounts = accounts.length;

    const existingRows = await sb('/rest/v1/ss_orders?select=id,data');
    const existing: Record<string, any> = {};
    (existingRows || []).forEach((r: any) => { existing[r.id] = r.data; });

    /* 1 — newest orders per account.
       Starting where the last run stopped, because a run that cannot reach every
       account would otherwise always reach the same ones: whoever sits at the end
       of the list would never sync at all, and their client would be missing from
       every figure with nothing to say why. */
    const prevState = await sb('/rest/v1/app_settings?key=eq.sync_state&select=data').catch(() => null);
    const startAt = Math.max(0, Number(prevState?.[0]?.data?.nextAccount ?? 0)) % accounts.length;
    const ordered = accounts.slice(startAt).concat(accounts.slice(0, startAt));

    const seen: Record<string, { m: any, key: string }> = {};
    let reached = 0;
    for(const a of ordered){
      if(left() < 10000) break;
      reached++;
      try{
        const shipped = await ssPages('/api/orders/shipped', a.apiKey, LIST_PAGES);
        shipped.forEach((o: any) => { const m = mapOrder(o, true, a.label, a.id); seen[m.id] = { m, key: a.apiKey }; });
        try{
          const un = await ssPages('/api/orders/unshipped', a.apiKey, 1);
          un.forEach((o: any) => { const m = mapOrder(o, false, a.label, a.id); seen[m.id] = { m, key: a.apiKey }; });
        }catch(_e){}
      }catch(e: any){ report.errors.push(a.label + ': ' + e.message); }
    }
    report.fetched = Object.keys(seen).length;
    report.accountsReached = reached;
    const nextAccount = (startAt + reached) % accounts.length;

    /* Carry forward what earlier runs filled in, so enrichment accumulates
       instead of starting over every time. */
    Object.keys(seen).forEach(id => {
      const prev = existing[id], m = seen[id].m;
      if(!prev) return;
      if(!(m.items ?? []).length && (prev.items ?? []).length) m.items = prev.items;
      if(!m.deliveredTs && prev.deliveredTs){ m.deliveredTs = prev.deliveredTs; m.status = 'delivered'; }
      if(!m.tracking && prev.tracking) m.tracking = prev.tracking;
    });

    const cutoff = Date.now() - KEEP_DAYS * 86400e3;
    const recent = (id: string) => {
      const t = seen[id].m.date ? new Date(seen[id].m.date).getTime() : NaN;
      return isNaN(t) || t >= cutoff;     /* undated still gets enriched — that is how it gets a date */
    };
    const newestFirst = (x: string, y: string) => +new Date(seen[y].m.date) - +new Date(seen[x].m.date);

    /* 2 — line items, keeping a share of the run for the delivery pass below */
    const trackReserve = Math.max(8000, Math.floor(BUDGET_MS * 0.35));
    const needItems = Object.keys(seen)
      .filter(id => recent(id) && seen[id].m.ssId && !(seen[id].m.items ?? []).length)
      .sort(newestFirst);
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
      .sort(newestFirst);
    const trackStats = await pool(needTrack, async id => {
      const { m, key } = seen[id];
      const t = await retry(() => ssTrack(m.tracking, key));
      const del = ssDelivered(t);
      if(del){ m.deliveredTs = del; m.status = 'delivered'; report.tracked++; }
      else if(t && ssIsDelivered(t)) m.status = 'delivered';
    });

    /* 4 — write back only what actually changed */
    const rowsOut = Object.keys(seen)
      .filter(id => !existing[id] || JSON.stringify(existing[id]) !== JSON.stringify(seen[id].m))
      .map(id => ({ id, data: seen[id].m, ord: 0 }));
    for(let i = 0; i < rowsOut.length; i += 200){
      await sb('/rest/v1/ss_orders', {
        method: 'POST', body: rowsOut.slice(i, i + 200),
        headers: { Prefer: 'resolution=merge-duplicates,return=minimal' }
      });
    }
    report.written = rowsOut.length;

    /* 5 — what this data can and cannot be trusted to say. Counted here rather
       than in the browser so it is the same answer for everyone, and so a bad
       run leaves a record even if nobody opens the app. */
    const mapped = Object.values(seen).map(v => v.m);
    const shippedOnly = mapped.filter((m: any) => m.status !== 'unshipped');
    const trackSeen: Record<string, number> = {};
    shippedOnly.forEach((m: any) => { if(m.tracking) trackSeen[m.tracking] = (trackSeen[m.tracking] ?? 0) + 1; });
    const ssIdAccts: Record<string, Set<string>> = {};
    shippedOnly.forEach((m: any) => {
      if(!m.ssId) return;
      (ssIdAccts[m.ssId] = ssIdAccts[m.ssId] ?? new Set()).add(m.acctId ?? '');
    });
    const check = {
      shipped: shippedOnly.length,
      undated: shippedOnly.filter((m: any) => !m.date).length,
      weakDate: shippedOnly.filter((m: any) => m.dateSource === 'order_date' || m.dateSource === 'date').length,
      noItems: shippedOnly.filter((m: any) => !(m.items ?? []).length).length,
      dupTracking: Object.values(trackSeen).filter(n => n > 1).length,
      sharedIds: Object.values(ssIdAccts).filter(s2 => s2.size > 1).length,
      impossible: shippedOnly.filter((m: any) => m.deliveredTs && m.date && new Date(m.deliveredTs) < new Date(m.date)).length,
      perAccount: accounts.map((a: any) => {
        const mine = shippedOnly.filter((m: any) => m.acctId === a.id);
        return { label: a.label, shipped: mine.length,
                 undated: mine.filter((m: any) => !m.date).length,
                 noItems: mine.filter((m: any) => !(m.items ?? []).length).length };
      })
    };
    report.check = check;

    /* 6 — leave a mark so the app can show when the server last looked */
    await sb('/rest/v1/app_settings', {
      method: 'POST',
      body: [{ key: 'sync_state', data: {
        lastSync: new Date().toISOString(),
        accounts: report.accounts, accountsReached: reached, nextAccount,
        fetched: report.fetched, written: report.written,
        enriched: report.enriched, tracked: report.tracked,
        check,
        outstandingItems: itemStats.skipped + itemStats.failed,
        outstandingTracking: trackStats.skipped + trackStats.failed,
        errors: report.errors.slice(0, 6),
        ms: Date.now() - t0
      }}],
      headers: { Prefer: 'resolution=merge-duplicates,return=minimal' }
    });

    report.ok = true;
    report.itemLookups = itemStats;
    report.trackLookups = trackStats;
    report.ms = Date.now() - t0;
    return new Response(JSON.stringify(report), { headers: { 'Content-Type': 'application/json' } });
  }catch(e: any){
    report.errors.push(String(e?.message ?? e));
    report.ms = Date.now() - t0;
    console.error('starshipit sync failed', report);
    return new Response(JSON.stringify(report), { status: 500, headers: { 'Content-Type': 'application/json' } });
  }
});
