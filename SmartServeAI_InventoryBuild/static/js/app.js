// ---------------------------------------------------------------
// SmartServe AI - Dashboard interactions
// ---------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initDefaultDates();
  initForecastTab();
  initWeekTab();
  initWhatIfTab();
  initAnalyticsTab();
  initDailyAnalysisTab();
  initPlannerTab();
  initOptimizationTab();
  initControlTowerTab();
  initContextTab();
  initQuickCommands();
  loadOverview();
  checkDbStatus();
});


function initQuickCommands() {
  document.querySelectorAll("[data-tab-jump]").forEach((el) => {
    el.addEventListener("click", () => {
      const target = document.querySelector(`.tab-btn[data-tab="${el.dataset.tabJump}"]`);
      if (target) target.click();
      window.scrollTo({ top: document.querySelector(".tabs").offsetTop - 8, behavior: "smooth" });
    });
  });
}

async function loadOverview() {
  try {
    const res = await fetch("/api/analytics");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("ov-demand").textContent = Number(data.total_demand || 0).toLocaleString();
    document.getElementById("ov-prepared").textContent = Number(data.total_prepared || 0).toLocaleString();
    document.getElementById("ov-waste").textContent = Number(data.estimated_waste || 0).toLocaleString();
    document.getElementById("ov-waste-rate").textContent = `${data.waste_rate || 0}% waste rate`;
  } catch (e) {
    // Overview remains usable when analytics is unavailable.
  }
}

function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");

      if (btn.dataset.tab === "analytics") {
        loadAnalytics();
      }
      if (btn.dataset.tab === "daily") {
        loadDailyAnalysis();
      }
      if (btn.dataset.tab === "insights") {
        loadInsights();
      }
      if (btn.dataset.tab === "planner") {
        const d = document.getElementById("p-date");
        if (d && !d.value) d.value = new Date().toISOString().split("T")[0];
      }
    });
  });
}

function initDefaultDates() {
  const today = new Date().toISOString().split("T")[0];
  ["f-date", "w-date", "wi-date", "p-date", "k-date"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = today;
  });
}

function riskClass(risk) {
  return `risk-${risk}`;
}


function escapeHtmlSafe(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatNumberSafe(value) {
  const num = Number(value);

  if (!Number.isFinite(num)) {
    return "0";
  }

  return num.toLocaleString(undefined, {
    maximumFractionDigits: 2
  });
}

function weatherEmojiForCategory(weather) {
  const category = String(weather || "").toLowerCase();

  if (category === "rainy") return "🌧️";
  if (category === "hot") return "☀️";
  if (category === "cold") return "❄️";

  return "🌤️";
}
// ---------------------- Tab 1: Forecast ----------------------
function initForecastTab() {
  document.getElementById("f-generate").addEventListener("click", async () => {
    const btn = document.getElementById("f-generate");
    btn.disabled = true;
    btn.textContent = "Generating...";

    const payload = {
      date: document.getElementById("f-date").value,
      item: document.getElementById("f-item").value,
      weather: document.getElementById("f-weather").value,
      event: document.getElementById("f-event").value,
      holiday: document.getElementById("f-holiday").checked,
    };

    try {
      const res = await fetch("/api/forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      document.getElementById("f-demand").textContent = data.predicted_demand;
      document.getElementById("f-production").textContent = data.recommended_production;
      document.getElementById("f-surplus").textContent = data.expected_surplus;

      const riskEl = document.getElementById("f-risk");
      riskEl.textContent = data.waste_risk;
      riskEl.className = `value ${riskClass(data.waste_risk)}`;

      document.getElementById("f-results").style.display = "grid";
      document.getElementById("f-decision").style.display = "grid";
      document.getElementById("f-summary").textContent = data.summary || "Review the forecast and adjust production according to kitchen capacity.";
      document.getElementById("f-drivers").innerHTML = (data.drivers || []).map(d => `<div class="driver"><span>${d.label}</span><b class="driver-${d.type}">${d.impact}</b></div>`).join("");
      const b = data.balance || {};
      document.getElementById("f-balance").innerHTML = `<span>Waste pressure <b>${b.waste_risk_pct || 0}%</b></span><span>Stockout pressure <b>${b.stockout_risk_pct || 0}%</b></span><span>Balance score <b>${b.score || 0}/100</b></span>`;
    } catch (err) {
      alert("Forecast failed: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Generate Forecast";
    }
  });
}

// ---------------------- Tab 2: 7-Day Forecast ----------------------
function initWeekTab() {
  document.getElementById("w-generate").addEventListener("click", async () => {
    const btn = document.getElementById("w-generate");
    btn.disabled = true;
    btn.textContent = "Generating...";

    const payload = {
      date: document.getElementById("w-date").value,
      item: document.getElementById("w-item").value,
      weather: document.getElementById("w-weather").value,
    };

    try {
      const res = await fetch("/api/forecast-week", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      const tbody = document.getElementById("w-table-body");
      tbody.innerHTML = "";
      data.days.forEach((day) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${day.date}</td>
          <td>${day.day}</td>
          <td>${day.predicted_demand}</td>
          <td>${day.recommended_production}</td>
          <td>${day.expected_surplus}</td>
          <td><span class="badge ${riskClass(day.waste_risk)}">${day.waste_risk}</span></td>
        `;
        tbody.appendChild(tr);
      });

      document.getElementById("w-table-wrap").style.display = "block";
      document.getElementById("w-empty").style.display = "none";
    } catch (err) {
      alert("7-day forecast failed: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Generate 7-Day Forecast";
    }
  });
}

// ---------------------- Tab 3: What-If Lab ----------------------
function initWhatIfTab() {
  document.getElementById("wi-run").addEventListener("click", async () => {
    const btn = document.getElementById("wi-run");
    btn.disabled = true;
    btn.textContent = "Running...";

    const payload = {
      date: document.getElementById("wi-date").value,
      item: document.getElementById("wi-item").value,
      weather: document.getElementById("wi-weather").value,
      event: document.getElementById("wi-event").value,
      demand_change_pct: parseFloat(document.getElementById("wi-change").value || 0),
      delay_hours: parseFloat(document.getElementById("wi-delay").value || 0),
    };

    try {
      const res = await fetch("/api/what-if", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      document.getElementById("wi-baseline").textContent = data.baseline_demand;
      document.getElementById("wi-scenario").textContent = data.scenario_demand;
      document.getElementById("wi-production").textContent = data.recommended_production;
      document.getElementById("wi-surplus").textContent = data.expected_surplus;

      const riskEl = document.getElementById("wi-risk");
      riskEl.textContent = data.waste_risk;
      riskEl.className = `value ${riskClass(data.waste_risk)}`;

      const hint = document.getElementById("wi-hint");
      hint.style.display = "block";
      hint.textContent = `Scenario: demand ${data.demand_change_pct >= 0 ? "+" : ""}${data.demand_change_pct}%, ${data.delay_hours}h operational delay.`;

      document.getElementById("wi-results").style.display = "flex";
    } catch (err) {
      alert("Scenario failed: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Run Scenario";
    }
  });
}

// ---------------------- Tab 4: Analytics ----------------------
function initAnalyticsTab() {
  // Loaded lazily when the tab is first opened.
}

let analyticsLoaded = false;

function setupCanvas(canvas) {
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width || canvas.parentElement.clientWidth || 640));
  const height = Math.max(220, Math.floor(parseFloat(getComputedStyle(canvas).height) || canvas.parentElement.clientHeight || 260));
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width, height };
}

function chartTheme() {
  const styles = getComputedStyle(document.documentElement);
  return {
    text: styles.getPropertyValue("--text").trim() || "#172033",
    muted: styles.getPropertyValue("--muted").trim() || "#7a8499",
    border: styles.getPropertyValue("--border").trim() || "#e6ebf2",
    primary: styles.getPropertyValue("--primary").trim() || "#1769aa",
    success: styles.getPropertyValue("--success").trim() || "#22a06b",
    warning: styles.getPropertyValue("--warning").trim() || "#f2a93b",
    danger: styles.getPropertyValue("--danger").trim() || "#e45757",
    purple: styles.getPropertyValue("--purple").trim() || "#7656d6"
  };
}

function drawLineChart(canvasId, labels, series, options = {}) {
  const canvas = document.getElementById(canvasId);
  const setup = setupCanvas(canvas);
  if (!setup) return;
  const { ctx, width, height } = setup;
  const t = chartTheme();
  const pad = { l: 48, r: 18, t: 28, b: 42 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const values = series.flatMap(s => s.values).map(Number).filter(Number.isFinite);
  const max = Math.max(...values, 1) * 1.12;
  const min = Math.min(0, ...values);
  const x = i => pad.l + (labels.length <= 1 ? plotW / 2 : i * plotW / (labels.length - 1));
  const y = v => pad.t + plotH - ((v - min) / Math.max(1, max - min)) * plotH;

  ctx.clearRect(0, 0, width, height);
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.fillStyle = t.muted;
  ctx.strokeStyle = t.border;
  ctx.lineWidth = 1;
  for (let g = 0; g <= 4; g++) {
    const gy = pad.t + plotH * g / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(width - pad.r, gy); ctx.stroke();
    const value = Math.round(max - (max - min) * g / 4);
    ctx.fillText(value.toLocaleString(), 5, gy + 4);
  }
  labels.forEach((label, i) => {
    if (labels.length > 9 && i % 2 !== 0 && i !== labels.length - 1) return;
    ctx.fillStyle = t.muted;
    ctx.textAlign = "center";
    ctx.fillText(label, x(i), height - 14);
  });

  const colors = [t.primary, t.success, t.warning, t.purple];
  series.forEach((s, si) => {
    ctx.strokeStyle = colors[si % colors.length];
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    s.values.forEach((v, i) => {
      const px = x(i), py = y(Number(v));
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.stroke();
    s.values.forEach((v, i) => {
      ctx.fillStyle = colors[si % colors.length];
      ctx.beginPath(); ctx.arc(x(i), y(Number(v)), 3.5, 0, Math.PI * 2); ctx.fill();
    });
  });

  let lx = pad.l;
  series.forEach((s, si) => {
    const color = colors[si % colors.length];
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(lx + 4, 13, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = t.text; ctx.textAlign = "left"; ctx.fillText(s.label, lx + 12, 17);
    lx += ctx.measureText(s.label).width + 38;
  });
}

function drawBarChart(canvasId, labels, series, options = {}) {
  const canvas = document.getElementById(canvasId);
  const setup = setupCanvas(canvas);
  if (!setup) return;
  const { ctx, width, height } = setup;
  const t = chartTheme();
  const pad = { l: options.horizontal ? 105 : 42, r: 16, t: 28, b: options.horizontal ? 24 : 58 };
  const colors = [t.primary, t.success, t.warning, t.purple];
  const all = series.flatMap(s => s.values).map(Number);
  const max = Math.max(...all, 1) * 1.12;
  ctx.clearRect(0, 0, width, height);
  ctx.font = "10px Inter, system-ui, sans-serif";

  if (options.horizontal) {
    const rowH = (height - pad.t - pad.b) / labels.length;
    labels.forEach((label, i) => {
      const y = pad.t + i * rowH + rowH / 2;
      ctx.fillStyle = t.text; ctx.textAlign = "right"; ctx.fillText(label, pad.l - 10, y + 4);
      series.forEach((s, si) => {
        const barH = Math.min(12, rowH / (series.length + 1));
        const offset = (si - (series.length - 1) / 2) * (barH + 3);
        const w = ((Number(s.values[i]) || 0) / max) * (width - pad.l - pad.r);
        ctx.fillStyle = colors[si % colors.length];
        ctx.beginPath(); ctx.roundRect(pad.l, y + offset - barH / 2, Math.max(1, w), barH, 4); ctx.fill();
      });
    });
  } else {
    const groupW = (width - pad.l - pad.r) / labels.length;
    const barW = Math.min(30, (groupW * 0.72) / Math.max(series.length, 1));
    for (let g = 0; g <= 4; g++) {
      const gy = pad.t + (height - pad.t - pad.b) * g / 4;
      ctx.strokeStyle = t.border; ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(width - pad.r, gy); ctx.stroke();
      ctx.fillStyle = t.muted; ctx.textAlign = "right"; ctx.fillText(Math.round(max * (1 - g / 4)).toLocaleString(), pad.l - 7, gy + 3);
    }
    labels.forEach((label, i) => {
      const baseX = pad.l + i * groupW + groupW / 2;
      ctx.fillStyle = t.muted; ctx.textAlign = "center";
      ctx.fillText(label.length > 12 ? label.slice(0, 11) + "…" : label, baseX, height - 24);
      series.forEach((s, si) => {
        const value = Number(s.values[i]) || 0;
        const barH = ((value / max) * (height - pad.t - pad.b));
        const xPos = baseX - (series.length * barW) / 2 + si * barW;
        ctx.fillStyle = colors[si % colors.length];
        ctx.beginPath(); ctx.roundRect(xPos, height - pad.b - barH, Math.max(3, barW - 4), barH, 4); ctx.fill();
      });
    });
  }

  let lx = pad.l;
  series.forEach((s, si) => {
    const color = colors[si % colors.length];
    ctx.fillStyle = color; ctx.fillRect(lx, 8, 9, 9);
    ctx.fillStyle = t.text; ctx.textAlign = "left"; ctx.fillText(s.label, lx + 14, 17);
    lx += ctx.measureText(s.label).width + 34;
  });
}

function drawDonutChart(canvasId, labels, values) {
  const canvas = document.getElementById(canvasId);
  const setup = setupCanvas(canvas);
  if (!setup) return;
  const { ctx, width, height } = setup;
  const t = chartTheme();
  const colors = [t.primary, t.success, t.warning, t.purple, t.danger, "#55a8d6"];
  const total = values.reduce((a, b) => a + (Number(b) || 0), 0);
  ctx.clearRect(0, 0, width, height);
  const cx = Math.min(width * .34, 145), cy = height / 2, r = Math.min(82, height * .30);
  if (!total) { ctx.fillStyle=t.muted; ctx.textAlign="center"; ctx.fillText("No waste recorded",cx,cy); return; }
  let angle = -Math.PI / 2;
  values.forEach((value, i) => {
    const slice = (Number(value) / total) * Math.PI * 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r, angle, angle + slice); ctx.closePath();
    ctx.fillStyle = colors[i % colors.length]; ctx.fill(); angle += slice;
  });
  ctx.beginPath(); ctx.arc(cx, cy, r * .56, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill();
  ctx.fillStyle = t.text; ctx.textAlign = "center"; ctx.font = "700 16px Inter, system-ui, sans-serif"; ctx.fillText(total.toLocaleString(), cx, cy + 4);
  ctx.font = "10px Inter, system-ui, sans-serif"; ctx.fillStyle = t.muted; ctx.fillText("waste units", cx, cy + 20);
  labels.forEach((label, i) => {
    const y = 25 + i * 27;
    ctx.fillStyle = colors[i % colors.length]; ctx.fillRect(width - 150, y - 8, 9, 9);
    ctx.fillStyle = t.text; ctx.textAlign = "left"; ctx.font = "10px Inter, system-ui, sans-serif";
    ctx.fillText(label.length > 20 ? label.slice(0, 19) + "…" : label, width - 135, y);
    ctx.fillStyle = t.muted; ctx.textAlign = "right"; ctx.fillText(String(values[i]), width - 12, y);
  });
}

async function loadAnalytics() {
  if (analyticsLoaded) return;
  analyticsLoaded = true;
  try {
    const res = await fetch("/api/analytics");
    if (!res.ok) throw new Error("No analytics data available yet");
    const data = await res.json();
    const kpis = document.getElementById("a-kpis");
    kpis.innerHTML = `
      <div class="kpi-card blue"><div class="label">Historical Demand</div><div class="value">${formatNumberSafe(data.total_demand)}</div><div class="unit">units</div></div>
      <div class="kpi-card green"><div class="label">Prepared</div><div class="value">${formatNumberSafe(data.total_prepared)}</div><div class="unit">units</div></div>
      <div class="kpi-card amber"><div class="label">Estimated Waste</div><div class="value">${formatNumberSafe(data.estimated_waste)}</div><div class="unit">units</div></div>
      <div class="kpi-card purple"><div class="label">Waste Rate</div><div class="value">${data.waste_rate}%</div><div class="unit">of prepared</div></div>`;

    const trend = data.weekly_trend || [];
    drawLineChart("a-weekly-chart", trend.map(x => x.week.slice(5)), [
      { label: "Demand", values: trend.map(x => x.demand) },
      { label: "Prepared", values: trend.map(x => x.prepared) }
    ]);

    const waste = data.top_waste_items || [];
    drawBarChart("a-waste-chart", waste.map(x => x.item), [{ label: "Waste", values: waste.map(x => x.waste_units) }], { horizontal: true });

    const dvp = data.demand_vs_production || [];
    drawBarChart("a-dvp-chart", dvp.map(x => x.item), [
      { label: "Demand", values: dvp.map(x => x.demand) },
      { label: "Prepared", values: dvp.map(x => x.production) }
    ]);

    document.getElementById("a-weekly-table").innerHTML = trend.map(w => `
      <tr><td>${escapeHtmlSafe(w.week)}</td><td>${formatNumberSafe(w.demand)}</td><td>${formatNumberSafe(w.prepared)}</td><td>${formatNumberSafe(w.prepared - w.demand)}</td></tr>`).join("");

    if (data.model_metrics && Object.keys(data.model_metrics).length > 0) {
      const m = data.model_metrics;
      document.getElementById("a-model-metrics-panel").style.display = "block";
      document.getElementById("a-model-metrics").innerHTML = `
        <div class="kpi-card"><div class="label">MAE</div><div class="value">${m.mae}</div><div class="unit">units</div></div>
        <div class="kpi-card"><div class="label">MAPE</div><div class="value">${m.mape}%</div></div>
        <div class="kpi-card"><div class="label">R²</div><div class="value">${m.r2}</div></div>`;
    }
  } catch (err) {
    document.querySelector("#tab-analytics").insertAdjacentHTML("beforeend", `<div class="empty-state">${escapeHtmlSafe(err.message)}</div>`);
  }
}

// ---------------------- Daily Analysis ----------------------
let dailyAnalysisLoaded = false;

function initDailyAnalysisTab() {
  const date = document.getElementById("d-date");
  if (date && !date.value) date.value = new Date().toISOString().split("T")[0];
  const btn = document.getElementById("d-run");
  if (btn) btn.addEventListener("click", () => loadDailyAnalysis(true));
}

async function loadDailyAnalysis(force = false) {
  const dateEl = document.getElementById("d-date");
  if (!dateEl) return;
  if (dailyAnalysisLoaded && !force) return;
  dailyAnalysisLoaded = true;
  const date = dateEl.value || new Date().toISOString().split("T")[0];
  try {
    const res = await fetch(`/api/daily-analysis?date=${encodeURIComponent(date)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "No daily analysis available");

    const context = data.context || {};
    document.getElementById("d-context").innerHTML = `
      <span>📅 ${escapeHtmlSafe(data.day_name)}, ${escapeHtmlSafe(data.date)}</span>
      <span>🌦️ ${escapeHtmlSafe(context.weather || "Historical weather not recorded")}</span>
      <span>🎉 ${escapeHtmlSafe(context.event || "None")}</span>
      <span>🏷️ Holiday: ${context.holiday ? "Yes" : "No"}</span>`;

    document.getElementById("d-kpis").innerHTML = `
      <div class="kpi-card blue"><div class="label">Demand</div><div class="value">${formatNumberSafe(data.total_demand)}</div><div class="unit">units</div></div>
      <div class="kpi-card green"><div class="label">Prepared</div><div class="value">${formatNumberSafe(data.total_prepared)}</div><div class="unit">units</div></div>
      <div class="kpi-card purple"><div class="label">Sold</div><div class="value">${formatNumberSafe(data.total_sold)}</div><div class="unit">units</div></div>
      <div class="kpi-card amber"><div class="label">Waste</div><div class="value">${formatNumberSafe(data.waste_units)}</div><div class="unit">${data.waste_rate}% waste rate</div></div>
      <div class="kpi-card blue"><div class="label">Sell-through</div><div class="value">${data.sell_through}%</div><div class="unit">prepared sold</div></div>
      <div class="kpi-card green"><div class="label">Top Demand Item</div><div class="value small-value">${escapeHtmlSafe(data.top_demand_item)}</div><div class="unit">${formatNumberSafe(data.top_demand_units)} units</div></div>`;

    const trend = data.daily_trend || [];
    drawLineChart("d-trend-chart", trend.map(x => x.label), [
      { label: "Demand", values: trend.map(x => x.demand) },
      { label: "Prepared", values: trend.map(x => x.prepared) },
      { label: "Sold", values: trend.map(x => x.sold) }
    ]);

    const items = data.item_breakdown || [];
    drawBarChart("d-item-chart", items.map(x => x.item), [{ label: "Demand", values: items.map(x => x.demand) }], { horizontal: true });
    drawDonutChart("d-waste-chart", items.map(x => x.item), items.map(x => x.waste));

    document.getElementById("d-table-body").innerHTML = items.map(x => `
      <tr><td><strong>${escapeHtmlSafe(x.item)}</strong></td><td>${formatNumberSafe(x.demand)}</td><td>${formatNumberSafe(x.prepared)}</td><td>${formatNumberSafe(x.sold)}</td><td>${formatNumberSafe(x.waste)}</td><td>${x.waste_rate}%</td><td class="${x.gap > 0 ? "gap-positive" : x.gap < 0 ? "gap-negative" : ""}">${x.gap > 0 ? "+" : ""}${formatNumberSafe(x.gap)}</td></tr>`).join("");

    document.getElementById("d-callouts").innerHTML = `
      <div class="daily-callout"><span>🔥</span><div><small>Highest demand</small><strong>${escapeHtmlSafe(data.top_demand_item)}</strong><p>${formatNumberSafe(data.top_demand_units)} units demanded on this day.</p></div></div>
      <div class="daily-callout"><span>♻️</span><div><small>Highest estimated waste</small><strong>${escapeHtmlSafe(data.top_waste_item)}</strong><p>${formatNumberSafe(data.top_waste_units)} units of estimated waste.</p></div></div>
      <div class="daily-callout"><span>⚖️</span><div><small>Production balance</small><strong>${data.overproduction_items} over / ${data.underproduction_items} under</strong><p>Items where prepared quantity differed from historical demand.</p></div></div>`;
  } catch (err) {
    dailyAnalysisLoaded = false;
    document.getElementById("d-callouts").innerHTML = `<div class="empty-state">${escapeHtmlSafe(err.message)}</div>`;
  }
}

// ---------------------- AI Insights + Alerts ----------------------
let insightsLoaded = false;
async function loadInsights() {
  if (insightsLoaded) return;
  insightsLoaded = true;
  try {
    const [ir, ar] = await Promise.all([fetch("/api/insights"), fetch("/api/alerts")]);
    const insights = await ir.json();
    const alerts = await ar.json();
    document.getElementById("insight-summary").textContent = insights.summary || "No operational intelligence available.";
    document.getElementById("alerts-list").innerHTML = (alerts.alerts || []).map(a => `<div class="alert-card alert-${a.severity.toLowerCase()}"><b>${a.title}</b><span>${a.message}</span></div>`).join("");
    document.getElementById("intel-body").innerHTML = (insights.items || []).map(i => `<tr><td><b>${i.item}</b></td><td>${i.demand.toLocaleString()}</td><td>${i.waste.toLocaleString()}</td><td><span class="trend-${i.trend.toLowerCase()}">${i.trend} ${i.trend_pct > 0 ? "↑" : i.trend_pct < 0 ? "↓" : "→"}</span></td></tr>`).join("");
  } catch (e) {
    document.getElementById("insight-summary").textContent = "Unable to load AI insights.";
  }
}

// ---------------------- System status pill ----------------------
async function checkDbStatus() {
  try {
    const res = await fetch("/api/db-status");
    const data = await res.json();
    const pill = document.getElementById("statusPill");
    if (data.ai_model && data.dataset) {
      pill.innerHTML = `<span class="dot"></span> AI Engine Active`;
    } else {
      pill.innerHTML = `<span class="dot"></span> AI Engine Limited`;
      pill.style.color = "var(--medium)";
    }
  } catch (err) {
    // silently ignore — status pill is cosmetic
  }
}


// ---------------------- Production Planner ----------------------
function initPlannerTab() {
  const generate = document.getElementById("p-generate");
  const exportBtn = document.getElementById("p-export");
  if (!generate) return;

  generate.addEventListener("click", async () => {
    generate.disabled = true;
    generate.textContent = "Building...";
    const payload = {
      date: document.getElementById("p-date").value,
      weather: document.getElementById("p-weather").value,
      event: document.getElementById("p-event").value,
      holiday: document.getElementById("p-holiday").checked
    };
    try {
      const res = await fetch("/api/production-plan", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Production plan request failed");
      if (!Array.isArray(data.items) || data.items.length === 0) throw new Error("No menu-item forecasts were returned.");
      document.getElementById("p-demand").textContent = Number(data.total_demand || 0).toLocaleString();
      document.getElementById("p-production").textContent = Number(data.total_production || 0).toLocaleString();
      document.getElementById("p-surplus").textContent = Number(data.total_surplus || 0).toLocaleString();
      document.getElementById("p-risk").textContent = data.high_risk_items || 0;
      const body = document.getElementById("p-table-body");
      body.innerHTML = (data.items || []).map(r => {
        const c = r.confidence || {};
        return `<tr class="plan-row"><td><strong>${r.item}</strong></td><td>${r.predicted_demand}</td><td><strong>${r.recommended_production}</strong></td><td>${r.expected_surplus}</td><td><span class="badge ${riskClass(r.waste_risk)}">${r.waste_risk}</span></td><td>${c.low ?? "-"} – ${c.high ?? "-"} <small class="confidence-pill">${c.confidence_pct ?? "-"}%</small></td></tr>`;
      }).join("");
      document.getElementById("p-summary").style.display = "grid";
      document.getElementById("p-table-wrap").style.display = "block";
      document.getElementById("p-empty").style.display = "none";
      exportBtn.disabled = false;
      exportBtn.dataset.payload = JSON.stringify(payload);
      document.getElementById("p-summary").classList.remove("reveal-pop");
      void document.getElementById("p-summary").offsetWidth;
      document.getElementById("p-summary").classList.add("reveal-pop");
    } catch (e) {
      alert("Unable to build the production plan. Please check that the Flask server is running.");
    } finally {
      generate.disabled = false;
      generate.textContent = "Build Production Plan";
    }
  });

  exportBtn.addEventListener("click", async () => {
    if (exportBtn.disabled) return;
    const payload = JSON.parse(exportBtn.dataset.payload || "{}");
    const res = await fetch("/api/export-plan", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href=url; a.download=`smartserve_production_plan_${payload.date}.csv`; a.click();
    URL.revokeObjectURL(url);
  });
}


// ---------------------- Inventory + Waste Optimization ----------------------
function initOptimizationTab() {
  const btn=document.getElementById("o-run");
  if(!btn) return;
  const today=new Date().toISOString().split("T")[0];
  const date=document.getElementById("o-date"); if(date && !date.value) date.value=today;
  btn.addEventListener("click", async ()=>{
    btn.disabled=true; btn.textContent="Optimizing...";
    const payload={date:date.value,weather:document.getElementById("o-weather").value,event:document.getElementById("o-event").value,holiday:document.getElementById("o-holiday").checked};
    try{
      const res=await fetch("/api/optimization",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      if(!res.ok) throw new Error("Optimization request failed");
      const d=await res.json();
      document.getElementById("o-waste-saved").textContent=Number(d.waste_reduction_units||0).toLocaleString();
      document.getElementById("o-savings").textContent=`₹${Number(d.estimated_savings||0).toLocaleString()}`;
      document.getElementById("o-stockout").textContent=d.high_stockout_items||0;
      document.getElementById("o-revenue").textContent=`₹${Number(d.revenue_at_risk||0).toLocaleString()}`;
      document.getElementById("o-message").textContent=d.recommendation||"Review the plan and monitor service demand.";
      document.getElementById("o-note").textContent=d.prototype_note||"";
      document.getElementById("o-table-body").innerHTML=(d.items||[]).map(r=>`<tr class="plan-row"><td><strong>${r.item}</strong></td><td>${r.predicted_demand}</td><td>${r.current_stock}</td><td><strong>${r.production_needed}</strong></td><td>${r.stock_coverage_pct}%</td><td><span class="badge ${riskClass(r.stockout_risk)}">${r.stockout_risk}</span></td><td>${r.waste_avoided_units}</td></tr>`).join("");
      document.getElementById("o-kpis").style.display="grid"; document.getElementById("o-recommendation").style.display="block"; document.getElementById("o-table-panel").style.display="block";
      ["o-kpis","o-recommendation","o-table-panel"].forEach(id=>{const el=document.getElementById(id);el.classList.remove("reveal-pop");void el.offsetWidth;el.classList.add("reveal-pop");});
    }catch(e){alert("Unable to run optimization. Please check that the Flask server is running.");}
    finally{btn.disabled=false;btn.textContent="Run AI Optimization";}
  });
}



// ---------------------- Kitchen Control Tower ----------------------
function initControlTowerTab() {
  const btn = document.getElementById("k-build");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Building...";
    const payload = {
      date: document.getElementById("k-date").value,
      city: document.getElementById("k-city").value || "Pune",
      event: document.getElementById("k-event").value,
      holiday: document.getElementById("k-holiday").checked ? 1 : 0
    };
    try {
      const res = await fetch("/api/kitchen-control-tower", {
        method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload)
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || "Control Tower request failed");

      const totalProduction = Object.values(d.menu_totals || {}).reduce((a, v) => a + Number(v || 0), 0);
      document.getElementById("k-production").textContent = totalProduction.toLocaleString();
      document.getElementById("k-alerts").textContent = Number(d.procurement_alerts || 0).toLocaleString();
      document.getElementById("k-cost").textContent = `₹${Number(d.estimated_procurement_cost || 0).toLocaleString()}`;
      document.getElementById("k-source").textContent = String(d.weather_source || "—").replace("Open-Meteo live forecast", "Live weather").replace("Fallback: live weather unavailable", "Fallback");

      const actionHost = document.getElementById("k-actions");
      actionHost.innerHTML = (d.top_actions || []).map(a => `
        <div class="control-action ${String(a.type || '').toLowerCase()}">
          <div class="control-action-icon">${a.type === "PROCURE" ? "🛒" : a.type === "WATCH" ? "👀" : "✅"}</div>
          <div><b>${escapeHtmlSafe(a.title)}</b><span>${escapeHtmlSafe(a.message)}</span></div>
        </div>`).join("");

      document.getElementById("k-ingredient-body").innerHTML = (d.ingredient_requirements || []).map(r => `
        <tr><td><strong>${escapeHtmlSafe(r.ingredient)}</strong></td>
        <td>${formatNumberSafe(r.required)} ${escapeHtmlSafe(r.unit)}</td>
        <td>${formatNumberSafe(r.available)} ${escapeHtmlSafe(r.unit)}</td>
        <td>${r.shortage > 0 ? formatNumberSafe(r.shortage) + " " + escapeHtmlSafe(r.unit) : "—"}</td>
        <td><strong>${r.recommended_order > 0 ? formatNumberSafe(r.recommended_order) + " " + escapeHtmlSafe(r.unit) : "No order"}</strong></td>
        <td><span class="control-status ${String(r.risk).toLowerCase()}">${escapeHtmlSafe(r.risk)}</span></td></tr>`).join("");

      const today = d.today_action || {};
      document.getElementById("k-today-date").textContent = `${today.day || "Today"} · ${today.date || payload.date}`;
      document.getElementById("k-today-weather").textContent = today.weather ? `🌦️ ${today.weather}` : "";
      const menuIcons = {"Veg Thali":"🍱","Paneer Rice":"🧀","Biryani":"🍗","Sandwich":"🥪","Idli":"🥣","Masala Dosa":"🥞"};
      document.getElementById("k-today-menu").innerHTML = (today.items || []).map(r => `
        <div class="control-menu-card"><span>${menuIcons[r.item] || "🍽️"} ${escapeHtmlSafe(r.item)}</span><div><b>${formatNumberSafe(r.production)}</b><small>produce</small></div><small>Forecast ${formatNumberSafe(r.demand)}</small></div>`).join("");

      document.getElementById("k-day-grid").innerHTML = (d.days || []).map(day => `
        <div class="control-day-card"><div><b>${escapeHtmlSafe(day.day)}</b><small>${escapeHtmlSafe(day.date)}</small></div><span>${escapeHtmlSafe(day.weather)}</span><strong>${(day.items || []).reduce((a,r)=>a+Number(r.production||0),0).toLocaleString()}</strong><small>portions</small></div>`).join("");
      document.getElementById("k-note").textContent = d.prototype_note || "";
      document.getElementById("k-results").style.display = "block";
      const el = document.getElementById("k-results"); el.classList.remove("reveal-pop"); void el.offsetWidth; el.classList.add("reveal-pop");
    } catch (e) {
      alert("Unable to build the Kitchen Control Tower. " + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Build Control Tower";
    }
  });
}

// ---------------------- Tab 7: Context Intelligence ----------------------
function initContextTab() {
  const btn = document.getElementById("c-run");
  const liveBtn = document.getElementById("c-live-weather");
  const liveCard = document.getElementById("c-live-card");
  if (!btn) return;
  const date = document.getElementById("c-date");
  const city = document.getElementById("c-city");
  if (date && !date.value) date.value = new Date().toISOString().split("T")[0];

  if (liveBtn) liveBtn.addEventListener("click", async () => {
    liveBtn.disabled = true; liveBtn.textContent = "Fetching...";
    try {
      const res = await fetch("/api/realtime-weather", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({city: city.value || "Pune", date: date.value})});
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || "Weather service unavailable");
      document.getElementById("c-weather").value = d.category;
      document.getElementById("c-live-condition").textContent = `${d.condition} · ${d.category}`;
      document.getElementById("c-live-location").textContent = `${d.city}${d.country ? ", " + d.country : ""} · ${d.date}`;
      document.getElementById("c-live-max").textContent = `${Math.round(d.temp_max_c)}°C`;
      document.getElementById("c-live-rain").textContent = `${Math.round(d.rain_probability_pct || 0)}%`;
      document.getElementById("c-live-mm").textContent = `${Number(d.rain_mm || 0).toFixed(1)} mm`;
      document.getElementById("c-live-status").textContent = `Live from ${d.source} · weather category set to ${d.category}`;
      const icon = d.category === "Rainy" ? "🌧️" : d.category === "Hot" ? "☀️" : d.category === "Cold" ? "❄️" : "🌤️";
      document.getElementById("c-weather-icon").textContent = icon;
      liveCard.style.display = "grid"; liveCard.classList.remove("reveal-pop"); void liveCard.offsetWidth; liveCard.classList.add("reveal-pop");
    } catch (e) {
      document.getElementById("c-live-status").textContent = `Live weather unavailable: ${e.message}`;
      liveCard.style.display = "grid";
    } finally { liveBtn.disabled = false; liveBtn.textContent = "🌦️ Fetch Live Weather"; }
  });

  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Analyzing...";
    const payload = {
      date: date.value,
      weather: document.getElementById("c-weather").value,
      event: document.getElementById("c-event").value,
      holiday: document.getElementById("c-holiday").checked
    };
    try {
      const res = await fetch("/api/context-intelligence", {
        method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Context analysis failed");
      const d = await res.json();
      const up = d.largest_increase || {};
      const down = d.largest_decrease || {};
      document.getElementById("c-up").textContent = up.item ? `${up.context_delta_pct >= 0 ? "+" : ""}${up.context_delta_pct}%` : "—";
      document.getElementById("c-up-meta").textContent = up.item ? `${up.item} · ${up.context_demand} units` : "—";
      document.getElementById("c-down").textContent = down.item ? `${down.context_delta_pct >= 0 ? "+" : ""}${down.context_delta_pct}%` : "—";
      document.getElementById("c-down-meta").textContent = down.item ? `${down.item} · ${down.context_demand} units` : "—";
      document.getElementById("c-actions").textContent = (d.actions || []).length;
      document.getElementById("c-anomalies").textContent = (d.items || []).filter(r => r.anomaly && r.anomaly.status === "HIGH").length;
      document.getElementById("c-summary").textContent = d.summary || "No summary available.";
      document.getElementById("c-action-list").innerHTML = (d.actions || []).map(r => `<div class="context-action context-${r.action.toLowerCase()}"><b>${r.action}</b><span>${r.action_text}</span></div>`).join("");
      document.getElementById("c-table-body").innerHTML = (d.items || []).map(r => `<tr class="plan-row"><td><strong>${r.item}</strong></td><td>${r.baseline_demand}</td><td>${r.context_demand}</td><td><span class="context-impact ${r.context_delta_pct >= 0 ? "positive" : "negative"}">${r.context_delta_pct >= 0 ? "+" : ""}${r.context_delta_pct}%</span></td><td><span class="badge ${r.anomaly.status === "HIGH" ? "risk-HIGH" : r.anomaly.status === "WATCH" ? "risk-MEDIUM" : "risk-LOW"}">${r.anomaly.status}</span></td><td><b>${r.action}</b></td></tr>`).join("");
      document.getElementById("c-alerts").innerHTML = (d.alerts || []).map(a => `<div class="alert-card alert-${String(a.severity).toLowerCase()}"><b>${a.title}</b><span>${a.message}</span></div>`).join("");
      document.getElementById("c-note").textContent = d.method_note || "";
      document.getElementById("c-results").style.display = "block";
      const el=document.getElementById("c-results"); el.classList.remove("reveal-pop"); void el.offsetWidth; el.classList.add("reveal-pop");
    } catch (e) { alert("Unable to analyze context. Please check that the Flask server is running."); }
    finally { btn.disabled = false; btn.textContent = "Analyze Context"; }
  });
}


async function generateFull7DayProductionPlan() {
  const cityEl = document.getElementById("c-city");
  const eventEl = document.getElementById("c-event");
  const holidayEl = document.getElementById("c-holiday");
  const output = document.getElementById("full-seven-day-plan-output");
  if (!output) return;

  const city = cityEl && cityEl.value ? cityEl.value.trim() : "Pune";
  const event = eventEl ? eventEl.value : "None";
  const holiday = holidayEl ? Number(holidayEl.value || 0) : 0;

  output.innerHTML = '<div class="empty-state">Building 7-day × 6-item production intelligence…</div>';

  try {
    const res = await fetch("/api/7day-production-plan", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({city, event, holiday})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Production plan failed.");

    window.smartServeFullPlan = data;
    const totals = data.days.reduce((a, d) => ({
      demand: a.demand + Number(d.total_demand || 0),
      production: a.production + Number(d.total_production || 0),
      surplus: a.surplus + Number(d.expected_surplus || 0),
      risk: a.risk + Number(d.high_risk_items || 0)
    }), {demand:0, production:0, surplus:0, risk:0});

    output.innerHTML = `
      <div class="full-plan-kpis">
        <div><span>7-Day Demand</span><strong>${formatNumberSafe(totals.demand)}</strong></div>
        <div><span>Recommended Production</span><strong>${formatNumberSafe(totals.production)}</strong></div>
        <div><span>Expected Surplus</span><strong>${formatNumberSafe(totals.surplus)}</strong></div>
        <div><span>High-Risk Flags</span><strong>${formatNumberSafe(totals.risk)}</strong></div>
      </div>
      <div class="full-plan-days">
        ${data.days.map((d, idx) => `
          <div class="full-plan-day">
            <div class="full-plan-day-head">
              <div>
                <strong>${d.day}</strong> <span class="muted">${d.date}</span>
                <div class="muted">${weatherEmojiForCategory(d.weather)} ${escapeHtmlSafe(d.weather)} · ${escapeHtmlSafe(d.condition)}</div>
              </div>
              <div class="day-weather-number">${formatNumberSafe(d.temp_max_c)}°C · 🌧 ${formatNumberSafe(d.rain_probability_pct)}%</div>
            </div>
            <div class="table-scroll">
              <table class="data-table compact-table">
                <thead><tr>
                  <th>Food Item</th><th>Demand</th><th>Produce</th><th>Surplus</th><th>Risk</th>
                </tr></thead>
                <tbody>
                  ${d.items.map(r => `<tr>
                    <td><strong>${escapeHtmlSafe(r.item)}</strong></td>
                    <td>${formatNumberSafe(r.predicted_demand)}</td>
                    <td>${formatNumberSafe(r.recommended_production)}</td>
                    <td>${formatNumberSafe(r.expected_surplus)}</td>
                    <td><span class="risk-badge ${String(r.waste_risk).toLowerCase()}">${escapeHtmlSafe(r.waste_risk)}</span></td>
                  </tr>`).join("")}
                </tbody>
              </table>
            </div>
          </div>`).join("")}
      </div>
      <p class="muted full-plan-note">Prototype planning output: live weather changes by day; event and holiday are held constant for this scenario. Production uses the SmartServe AI lean-buffer heuristic.</p>
    `;
  } catch (err) {
    output.innerHTML = `<div class="empty-state">Could not build the full plan: ${escapeHtmlSafe(err.message)}</div>`;
  }
}


window.addEventListener("resize", () => {
  if (document.getElementById("tab-analytics")?.classList.contains("active")) {
    analyticsLoaded = false; loadAnalytics();
  }
  if (document.getElementById("tab-daily")?.classList.contains("active")) {
    dailyAnalysisLoaded = false; loadDailyAnalysis();
  }
});

