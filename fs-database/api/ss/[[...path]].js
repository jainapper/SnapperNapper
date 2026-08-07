// Same-origin proxy to the Starshipit API.
// Browsers cannot call api.starshipit.com directly (no CORS headers), so the
// app talks to /api/ss/... on its own origin and this function forwards the
// request, passing the per-account API key and subscription key through.
module.exports = async (req, res) => {
  const segs = [].concat(req.query.path || []);
  const q = Object.assign({}, req.query);
  delete q.path;
  const qs = new URLSearchParams(q).toString();
  const url = 'https://api.starshipit.com/' + segs.join('/') + (qs ? '?' + qs : '');
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
