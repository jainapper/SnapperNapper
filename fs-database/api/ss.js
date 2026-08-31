// Same-origin proxy to the Starshipit API.
// Browsers cannot call api.starshipit.com directly (no CORS headers), so the
// app calls /api/ss?p=/api/orders/shipped&... and this function forwards it,
// passing the per-account API key and subscription key headers through.
// (A fixed path is used because multi-segment catch-alls are not routed for
// plain Vercel functions.)
module.exports = async (req, res) => {
  const q = Object.assign({}, req.query);
  const p = String(q.p || '');
  delete q.p;
  if (p.indexOf('/api/') !== 0) {
    res.status(400).json({ error: 'bad path' });
    return;
  }
  const qs = new URLSearchParams(q).toString();
  const url = 'https://api.starshipit.com' + p + (qs ? '?' + qs : '');
  try {
    const r = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        'StarShipIT-Api-Key': req.headers['starshipit-api-key'] || '',
        'Ocp-Apim-Subscription-Key': req.headers['ocp-apim-subscription-key'] || ''
      }
    });
    const body = await r.text();
    res.status(r.status).setHeader('Content-Type', 'application/json');
    res.send(body);
  } catch (e) {
    res.status(502).json({ error: String(e) });
  }
};
