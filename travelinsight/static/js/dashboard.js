// ---------------- Tab switching ----------------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel-section").forEach(s => s.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

// ---------------- Interest chip selection ----------------
const selectedTags = new Set();
document.querySelectorAll("#interest-chips .chip").forEach(chip => {
  chip.addEventListener("click", () => {
    chip.classList.toggle("selected");
    const tag = chip.dataset.tag;
    selectedTags.has(tag) ? selectedTags.delete(tag) : selectedTags.add(tag);
  });
});

const GOLD = "#C8963E";
const TEAL = "#4C9C8F";
const BRICK = "#C06B54";
const PAPER_DIM = "#B9C2CE";
const HAIRLINE = "#2C4568";

const chartDefaults = {
  color: PAPER_DIM,
  scale: {
    grid: { color: HAIRLINE },
    ticks: { color: PAPER_DIM },
  },
};

// ---------------- Load dashboard stats ----------------
async function loadStats() {
  const res = await fetch("/api/stats");
  const data = await res.json();

  document.getElementById("kpi-visitors").textContent =
    data.trend_values.reduce((a, b) => a + b, 0).toLocaleString();
  document.getElementById("kpi-reviews").textContent = data.total_reviews;
  document.getElementById("kpi-rating").textContent = data.avg_rating + " / 5";

  new Chart(document.getElementById("trendChart"), {
    type: "line",
    data: {
      labels: data.trend_labels,
      datasets: [{
        label: "Visitors",
        data: data.trend_values,
        borderColor: GOLD,
        backgroundColor: "rgba(200,150,62,0.12)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      }],
    },
    options: baseOptions(false),
  });

  const sentLabels = Object.keys(data.sentiment_distribution);
  const sentValues = Object.values(data.sentiment_distribution);
  const sentColors = sentLabels.map(l =>
    l === "Positive" ? TEAL : l === "Negative" ? BRICK : PAPER_DIM
  );
  new Chart(document.getElementById("sentimentChart"), {
    type: "doughnut",
    data: {
      labels: sentLabels,
      datasets: [{ data: sentValues, backgroundColor: sentColors, borderWidth: 0 }],
    },
    options: {
      plugins: { legend: { labels: { color: PAPER_DIM } } },
    },
  });

  new Chart(document.getElementById("topChart"), {
    type: "bar",
    data: {
      labels: data.top_labels,
      datasets: [{ label: "Total visitors", data: data.top_values, backgroundColor: TEAL }],
    },
    options: baseOptions(true),
  });

  const wLabels = Object.keys(data.weather_impact);
  const wValues = Object.values(data.weather_impact);
  new Chart(document.getElementById("weatherChart"), {
    type: "bar",
    data: {
      labels: wLabels,
      datasets: [{ label: "Avg. visitors/day", data: wValues, backgroundColor: GOLD }],
    },
    options: baseOptions(false),
  });
}

function baseOptions(indexAxisY) {
  return {
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: HAIRLINE }, ticks: { color: PAPER_DIM } },
      y: { grid: { color: HAIRLINE }, ticks: { color: PAPER_DIM } },
    },
  };
}

// ---------------- Predict footfall ----------------
async function runPredict() {
  const spot_id = document.getElementById("p-spot").value;
  const date = document.getElementById("p-date").value;
  const weather = document.getElementById("p-weather").value;
  if (!date) { alert("Pick a date first."); return; }

  const res = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spot_id, date, weather }),
  });
  const data = await res.json();

  document.getElementById("predict-number").textContent =
    `~${data.predicted_visitors.toLocaleString()} visitors`;
  document.getElementById("predict-meta").textContent =
    `${data.spot_name} · ${data.weekday}, ${data.date} · ${data.season} · ${data.weather}` +
    (data.is_holiday ? " · Public holiday" : "");
  document.getElementById("predict-result").classList.add("show");
}

// ---------------- Recommend ----------------
async function runRecommend() {
  const res = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interests: Array.from(selectedTags) }),
  });
  const data = await res.json();

  const container = document.getElementById("rec-results");
  container.innerHTML = data.map(spot => `
    <div class="rec-card">
      <div class="name">${spot.name}</div>
      <div class="meta">${spot.category} · ${spot.city} · ${spot.avg_rating}★ · ${spot.tags}</div>
    </div>
  `).join("");
}

// ---------------- Sentiment ----------------
async function runSentiment() {
  const text = document.getElementById("review-text").value;
  if (!text.trim()) { alert("Write a review first."); return; }

  const res = await fetch("/api/sentiment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const data = await res.json();

  const tag = document.getElementById("sentiment-tag");
  tag.textContent = data.label;
  tag.className = "sentiment-tag sentiment-" + data.label;
  document.getElementById("sentiment-meta").textContent =
    `Positive cues: ${data.positive_hits} · Negative cues: ${data.negative_hits} · Confidence: ${data.confidence}`;
  document.getElementById("sentiment-result").classList.add("show");
}

loadStats();
