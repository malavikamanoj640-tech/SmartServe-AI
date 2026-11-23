(() => {
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  const fmt = n => Number(n || 0).toLocaleString('en-IN');
  const pct = n => `${Number(n || 0).toFixed(1)}%`;
  const maxOf = arr => Math.max(...arr.map(x => Number(x.demand ?? x.avg_demand ?? 0)), 1);
  const setToday = () => {
    const d = new Date();
    const iso = new Date(d.getTime() - d.getTimezoneOffset()*60000).toISOString().slice(0,10);
    ['i-date'].forEach(id => { if ($(id) && !$(id).value) $(id).value = iso; });
  };

  function barChart(target, rows, labelKey, valueKey, formatter = fmt) {
    if (!rows?.length) { $(target).innerHTML = '<div class="empty-state">No data available.</div>'; return; }
    const max = Math.max(...rows.map(r => Number(r[valueKey] || 0)), 1);
    $(target).innerHTML = rows.map(r => {
      const value = Number(r[valueKey] || 0);
      return `<div class="bar-row"><div class="bar-label"><span>${esc(r[labelKey])}</span><strong>${formatter(value)}</strong></div><div class="bar-track"><i style="width:${Math.max(4, value/max*100)}%"></i></div></div>`;
    }).join('');
  }

  function renderMatrix(data) {
    const weather = data.weather_profile.map(x => x.weather);
    const days = data.day_profile;
    const cells = [];
    const baseDate = new Date(data.date + 'T12:00:00');
    for (let d=0; d<7; d++) {
      const date = new Date(baseDate); date.setDate(baseDate.getDate() + ((d - baseDate.getDay() + 7) % 7));
      const row = { day: ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][d], values: [] };
      weather.forEach(wx => {
        const x = new Date(data.date + 'T12:00:00');
        const targetDow = (d + 6) % 7;
        x.setDate(x.getDate() + ((targetDow - x.getDay() + 7) % 7));
        // The backend's day profile already captures weekday. Use a deterministic
        // relative adjustment from the weather profile so the matrix remains transparent.
        const dayVal = Number(days.find(v => v.index === targetDow)?.demand || data.baseline_demand);
        const wxVal = Number(data.weather_profile.find(v => v.weather === wx)?.demand || data.baseline_demand);
        const normal = Number(data.weather_profile.find(v => v.weather === 'Normal')?.demand || data.baseline_demand);
        const value = normal ? dayVal * (wxVal / normal) : dayVal;
        row.values.push(Math.round(value));
      });
      cells.push(row);
    }
    const flat = cells.flatMap(r=>r.values); const mx = Math.max(...flat,1);
    $("i-matrix").innerHTML = `<div class="matrix-table"><div class="matrix-row matrix-head"><b>Day</b>${weather.map(w=>`<b>${esc(w)}</b>`).join('')}</div>${cells.map(r=>`<div class="matrix-row"><strong>${r.day}</strong>${r.values.map(v=>`<span style="--cell:${Math.max(0.12,v/mx)}">${v}</span>`).join('')}</div>`).join('')}</div>`;
  }

  function renderDrivers(data) {
    const max = Math.max(...data.components.map(x => Math.abs(Number(x.impact_pct))), 1);
    $("i-drivers").innerHTML = data.components.map(x => {
      const n = Number(x.impact_pct); const cls = n >= 0 ? 'positive' : 'negative';
      return `<div class="impact-row"><div><strong>${esc(x.label)}</strong><span>${n >= 0 ? '+' : ''}${n.toFixed(1)}%</span></div><div class="impact-track"><i class="${cls}" style="width:${Math.max(8,Math.abs(n)/max*100)}%"></i></div></div>`;
    }).join('');
  }

  function renderSeven(data) {
    const mx = Math.max(...data.seven_day.map(x=>x.demand),1);
    $("i-seven").innerHTML = data.seven_day.map(x => `<div class="timeline-day"><span>${esc(x.day)}</span><i style="height:${Math.max(12,x.demand/mx*70)}px"></i><strong>${fmt(x.demand)}</strong></div>`).join('');
  }

  function renderModel(m) {
    const cards = [
      ['R²', m.r2 ?? '—', 'higher is better'],
      ['MAE', m.mae ?? '—', 'units'],
      ['MAPE', m.mape != null ? `${m.mape}%` : '—', 'error'],
      ['Train Rows', fmt(m.n_train), 'observations'],
      ['Test Rows', fmt(m.n_test), 'holdout']
    ];
    $("i-model").innerHTML = cards.map(c=>`<div class="model-card"><small>${c[0]}</small><strong>${c[1]}</strong><span>${c[2]}</span></div>`).join('');
  }

  async function loadIntelligence() {
    const btn = $('i-run'); if (!btn) return;
    btn.disabled = true; btn.textContent = 'Analyzing…';
    try {
      const body = {
        date: $('i-date').value,
        item: $('i-item').value,
        weather: $('i-weather').value,
        event: $('i-event').value,
        holiday: $('i-holiday').checked
      };
      const res = await fetch('/api/intelligence', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      const data = await res.json(); if (!res.ok) throw new Error(data.error || 'Unable to analyze');
      const impact = Number(data.total_context_impact_pct || 0);
      $('i-impact').textContent = `${impact >= 0 ? '+' : ''}${impact.toFixed(1)}%`;
      $('i-summary-title').textContent = `${data.item} • ${data.day_name} • ${data.weather}`;
      $('i-summary').textContent = `${fmt(data.context_demand)} units are predicted versus ${fmt(data.baseline_demand)} units under a normal baseline. ${impact >= 0 ? 'Demand is expected to rise.' : 'Demand is expected to fall.'} Use the scenario as a planning signal, not causal proof.`;
      $('i-production').textContent = fmt(data.recommended_production);
      $('i-risk').textContent = `Waste risk: ${data.waste_risk}`;
      barChart('i-day-chart', data.day_profile, 'short', 'demand');
      barChart('i-weather-chart', data.weather_profile, 'weather', 'demand');
      renderDrivers(data); renderSeven(data); renderMatrix(data);
      barChart('i-history-day', data.historical_weekday, 'day', 'avg_demand', x=>Number(x).toFixed(1));
      barChart('i-season', data.seasonal, 'month', 'avg_demand', x=>Number(x).toFixed(1));
      renderModel(data.model_metrics || {});
      $('i-note').textContent = data.prototype_note || '';
    } catch (e) {
      $('i-summary').textContent = e.message;
    } finally { btn.disabled = false; btn.textContent = 'Analyze Intelligence →'; }
  }

  document.addEventListener('DOMContentLoaded', () => {
    setToday();
    $('i-run')?.addEventListener('click', loadIntelligence);
    ['i-date','i-item','i-weather','i-event','i-holiday'].forEach(id => $(id)?.addEventListener('change', () => {
      if (document.getElementById('tab-intelligence')?.classList.contains('active')) loadIntelligence();
    }));
    document.querySelectorAll('.tab-btn[data-tab="intelligence"]').forEach(b => b.addEventListener('click', () => setTimeout(loadIntelligence, 80)));
  });
})();
