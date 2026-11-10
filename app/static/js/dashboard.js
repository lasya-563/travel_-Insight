(() => {
  const { api, el } = TI;
  const $ = id => document.getElementById(id);
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  const txt = dark ? '#eaf0f3' : '#10222e', grid = dark ? '#243a46' : '#e4ded2';
  const PALETTE = ['#0e7c86', '#e4572e', '#d99a1c', '#4f46e5', '#15803d', '#a855f7', '#0891b2', '#64748b'];
  const base = (extra = {}) => ({
    margin: { t: 10, r: 10, b: 40, l: 50 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: txt, family: 'system-ui, sans-serif', size: 12 },
    xaxis: { gridcolor: grid, zerolinecolor: grid }, yaxis: { gridcolor: grid, zerolinecolor: grid },
    ...extra,
  });
  const cfg = { displayModeBar: false, responsive: true };
  const draw = (id, data, layout) => Plotly.react(id, data, layout, cfg);

  function render(d) {
    const k = d.kpis;
    $('data-note').textContent = d.data_note;
    $('kpis').replaceChildren(...[
      ['Destinations', k.destinations], ['Visitor records', k.visitors], ['Registered users', k.registered_users],
      ['Traveller ratings', k.user_ratings], ['Avg rating', k.avg_rating], ['Events (24 h)', k.events_24h],
    ].map(([label, v]) => el('div', { class: 'kpi' }, el('b', {}, String(v)), el('span', {}, label))));

    const cats = d.categories;
    draw('ch-category', [{ type: 'bar', x: cats.map(c => c.category), y: cats.map(c => c.count), marker: { color: cats.map(c => c.color) } }],
      base({ yaxis: { title: 'Destinations', gridcolor: grid } }));
    const top = [...d.top_destinations].reverse();
    draw('ch-popular', [{ type: 'bar', orientation: 'h', x: top.map(t => t.popularity), y: top.map(t => t.name),
      marker: { color: top.map(t => d.category_colors[t.category]) } }], base({ margin: { t: 10, r: 10, b: 30, l: 110 } }));
    draw('ch-rating', [{ type: 'bar', x: cats.map(c => c.category), y: cats.map(c => c.avg_rating), marker: { color: cats.map(c => c.color) },
      text: cats.map(c => c.avg_rating.toFixed(2)), textposition: 'outside' }],
      base({ yaxis: { range: [3.5, 5], title: 'Average rating', gridcolor: grid } }));
    draw('ch-budget', [{ type: 'pie', hole: .5, labels: d.budget_bands.map(b => b.band), values: d.budget_bands.map(b => b.count),
      marker: { colors: ['#0e7c86', '#d99a1c', '#e4572e'] } }], base({ margin: { t: 10, r: 10, b: 10, l: 10 } }));
    draw('ch-trend', [
      { type: 'scatter', mode: 'lines+markers', name: 'Views', x: d.trend.map(t => t.date), y: d.trend.map(t => t.views), line: { color: '#0e7c86' } },
      { type: 'scatter', mode: 'lines+markers', name: 'Ratings', x: d.trend.map(t => t.date), y: d.trend.map(t => t.ratings), line: { color: '#e4572e' } },
      { type: 'scatter', mode: 'lines+markers', name: 'Saves', x: d.trend.map(t => t.date), y: d.trend.map(t => t.saves), line: { color: '#d99a1c' } },
    ], base({ legend: { orientation: 'h', y: 1.12 } }));
    $('feed').replaceChildren(...d.feed.map(f => el('li', {}, f.text, el('span', { class: 'muted small' }, '  ' + f.at.slice(5, 16)))));

    const s = d.segmentation;
    if (!s.ready) { $('seg-meta').textContent = s.reason || 'Segmentation not available.'; return; }
    $('seg-meta').textContent = `K = ${s.k} clusters from ${s.records} visitor records · silhouette ${s.silhouette} · trained ${s.trained_at}. ` +
      `Segment names are generated from each cluster's dominant interests and budget; review them before using them in reports.`;
    const color = c => PALETTE[c % PALETTE.length];
    const traces = s.clusters.map(c => {
      const pts = s.scatter.filter(p => p.cluster === c.cluster);
      return { type: 'scattergl', mode: 'markers', name: c.label, x: pts.map(p => p.x), y: pts.map(p => p.y), marker: { size: 6, color: color(c.cluster), opacity: .75 } };
    });
    draw('ch-scatter', traces, base({ xaxis: { title: `PC1 (${s.pca_explained[0]}%)`, gridcolor: grid }, yaxis: { title: `PC2 (${s.pca_explained[1]}%)`, gridcolor: grid }, legend: { orientation: 'h', y: -0.25 } }));
    draw('ch-seg-size', [{ type: 'pie', hole: .45, labels: s.clusters.map(c => c.label), values: s.clusters.map(c => c.size), marker: { colors: s.clusters.map(c => color(c.cluster)) } }],
      base({ margin: { t: 10, r: 10, b: 10, l: 10 }, showlegend: false }));
    const names = Object.keys(s.clusters[0].interests);
    draw('ch-heat', [{ type: 'heatmap', x: names, y: s.clusters.map(c => c.label), z: s.clusters.map(c => names.map(n => c.interests[n])),
      colorscale: 'YlGnBu', zmin: 0, zmax: 5, hovertemplate: '%{y}<br>%{x}: %{z}<extra></extra>' }],
      base({ margin: { t: 10, r: 10, b: 50, l: 200 } }));
    $('seg-table').replaceChildren(...s.clusters.map(c => el('div', { class: 'card seg-card', style: `border-left-color:${color(c.cluster)}` },
      el('h4', {}, c.label),
      el('div', { class: 'small' }, `${c.size} visitors (${c.share}%) · avg ₹${c.avg_budget.toLocaleString('en-IN')}/day · ${c.avg_trip_days} days`),
      el('div', { class: 'tags mt-s' }, c.top_interests.map(t => el('span', { class: 'tag' }, t))))));
  }

  async function refresh() {
    try { render(await api('/api/analytics')); $('live-label').textContent = 'Live · updated ' + new Date().toLocaleTimeString(); }
    catch (e) { $('live-label').textContent = 'Reconnecting…'; }
  }
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, 10000);
})();
