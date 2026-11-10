(() => {
  const { api, el, debounce, inr } = TI;
  const $ = s => document.querySelector(s);
  const form = $('#pref-form');
  const budget = $('#budget'), budgetAny = $('#budget-any');
  const ICONS = { 'Heritage': '🏰', 'Spiritual': '🛕', 'Beach': '🏖️', 'Nature': '🌿', 'Hill Station': '⛰️', 'Adventure': '🧗', 'Wildlife': '🐅', 'City': '🏙️' };
  const COLORS = { 'Heritage': '#c2410c', 'Spiritual': '#a16207', 'Beach': '#0891b2', 'Nature': '#15803d', 'Hill Station': '#4f46e5', 'Adventure': '#dc2626', 'Wildlife': '#65a30d', 'City': '#475569' };

  const checked = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(i => i.value);
  const prefs = () => ({
    interests: checked('interests'), activities: checked('activities'),
    budget: budgetAny.checked ? null : Number(budget.value),
    min_rating: Number($('#min_rating').value), trip_days: Number($('#trip_days').value) || 5,
    keywords: $('#keywords').value.trim(), top_n: 12,
  });

  function syncLabels() {
    $('#budget-out').textContent = budgetAny.checked ? 'any' : inr(budget.value);
    budget.disabled = budgetAny.checked;
    $('#rating-out').textContent = Number($('#min_rating').value).toFixed(1);
  }

  function card(r) {
    const c = COLORS[r.category] || '#0e7c86';
    return el('a', { class: 'card dest-card rec-card', href: `/destination/${r.id}` },
      el('div', { class: 'dest-banner', style: `--c:${c}` },
        el('span', { class: 'dest-icon' }, ICONS[r.category] || '📍'),
        el('span', { class: 'chip chip-onc' }, r.category)),
      el('div', { class: 'dest-body' },
        el('div', { class: 'row between' }, el('h3', {}, r.name), el('span', { class: 'match' }, `${r.match}%`)),
        el('div', { class: 'bar' }, el('i', { style: `width:${Math.min(r.match, 100)}%` })),
        el('div', { class: 'muted small' }, `${r.state} · ${r.best_season}`),
        el('div', { class: 'row between mt-s' },
          el('span', { class: 'stars' }, `★ ${r.rating.toFixed(1)}`),
          el('span', { class: 'small' }, `${inr(r.budget_per_day)}/day`)),
        r.within_budget ? null : el('div', { class: 'over' }, 'Slightly above your budget'),
        el('div', { class: 'why mt-s' }, `Cosine similarity ${r.similarity.toFixed(2)}`,
          r.matched_on.length ? ` · matched on: ${r.matched_on.join(', ')}` : '')));
  }

  let seq = 0;
  const run = async () => {
    const mine = ++seq;
    $('#rec-status').textContent = 'Updating…';
    try {
      const out = await api('/api/recommend', 'POST', prefs());
      if (mine !== seq) return;            // a newer request superseded this one
      const box = $('#results');
      box.replaceChildren(...out.results.map(card));
      $('#rec-status').textContent = out.results.length
        ? (out.cold_start ? 'Pick interests or activities to personalise — showing top-rated places.'
          : `${out.results.length} matches${out.personalised_with_history ? ' · personalised with your ratings & saves' : ''}`)
        : 'No destinations match — try raising the budget or lowering the minimum rating.';
      const seg = $('#segment-box');
      if (out.segment) {
        seg.classList.remove('hidden');
        seg.replaceChildren(el('div', { class: 'small muted' }, 'Your visitor segment (K-Means)'),
          el('div', { class: 'big' }, out.segment.label));
      } else seg.classList.add('hidden');
    } catch (e) { $('#rec-status').textContent = 'Could not load recommendations. Please retry.'; }
  };
  const runSoon = debounce(run, 250);

  form.addEventListener('input', () => { syncLabels(); runSoon(); });
  $('#reset').addEventListener('click', () => {
    form.reset(); form.querySelectorAll('input[type=checkbox]').forEach(i => { i.checked = i.id === 'budget-any'; });
    $('#min_rating').value = 0; $('#keywords').value = ''; $('#trip_days').value = 5; syncLabels(); run();
  });
  const saveBtn = $('#save-prefs');
  if (saveBtn) saveBtn.addEventListener('click', async () => {
    const msg = $('#save-msg');
    try { await api('/api/preferences', 'POST', prefs()); msg.textContent = 'Preferences saved ✓'; }
    catch (e) { msg.textContent = 'Could not save: ' + e.message; }
  });
  syncLabels(); run();
})();
