(() => {
  const box = document.querySelector('.rate');
  if (!box) return;
  const { api } = TI;
  const id = box.dataset.id;
  const stars = [...box.querySelectorAll('.star-input button')];
  const msg = document.getElementById('rate-msg');
  const paint = n => stars.forEach((b, i) => b.classList.toggle('on', i < n));
  paint(Number(box.dataset.mine));

  stars.forEach(b => {
    b.addEventListener('mouseenter', () => paint(Number(b.dataset.v)));
    b.addEventListener('mouseleave', () => paint(Number(box.dataset.mine)));
    b.addEventListener('click', async () => {
      try {
        const r = await api(`/api/destinations/${id}/rate`, 'POST', { rating: Number(b.dataset.v) });
        box.dataset.mine = r.mine; paint(r.mine);
        document.getElementById('avg-rating').textContent = '★ ' + r.rating.toFixed(2);
        document.getElementById('rating-count').textContent = r.user_ratings;
        msg.textContent = 'Thanks! Your rating now shapes your recommendations.';
      } catch (e) { msg.textContent = 'Could not save rating: ' + e.message; }
    });
  });

  const save = document.getElementById('save-btn');
  save.addEventListener('click', async () => {
    try {
      const r = await api(`/api/destinations/${id}/save`, 'POST');
      save.textContent = r.saved ? 'Saved ✓' : 'Save for later';
    } catch (e) { msg.textContent = 'Could not update: ' + e.message; }
  });
})();
