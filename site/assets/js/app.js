/* Humanitarian Programme Monitoring - static dashboard. No build step. */
(function () {
  'use strict';

  const COL = { on: '#0072B2', risk: '#E69F00', off: '#D55E00', na: '#9E9E9E', green: '#009E73', sky: '#56B4E9', pink: '#CC79A7', grey: '#4D4D4D' };
  const SERIES = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#CC79A7', '#56B4E9', '#F0E442', '#4D4D4D'];
  const D = {};                 // loaded data
  const charts = {};            // echarts instances
  const S = { start: 0, end: 0, sector: '', upazila: '', page: 'overview', sort: { k: 'pct', dir: -1 }, meals: 'No meals' };
  let map, mapLayer, tileLayer;

  /* ---------- helpers ---------- */
  const $ = (s, el = document) => el.querySelector(s);
  const fmtPct = (v, d = 1) => (v == null || !isFinite(v)) ? '–' : (v * 100).toFixed(d) + '%';
  const fmtInt = v => (v == null || !isFinite(v)) ? '–' : Math.round(v).toLocaleString('en-US');
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const status = p => p == null || !isFinite(p) ? 'na' : p >= 0.9 ? 'on' : p >= 0.7 ? 'risk' : 'off';
  const statusLabel = { on: 'On track', risk: 'At risk', off: 'Off track', na: 'No data' };
  const chip = p => { const s = status(p); return `<span class="chip ${s}">${statusLabel[s]}</span>`; };
  const isDark = () => {
    const t = document.documentElement.getAttribute('data-theme');
    return t ? t === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  };
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const monthLabel = m => { const [y, mm] = m.split('-'); return new Date(+y, +mm - 1, 1).toLocaleString('en-US', { month: 'short' }) + ' ' + y; };
  const monthEnd = m => { const [y, mm] = m.split('-').map(Number); return new Date(Date.UTC(y, mm, 0)); };

  /* ---------- filtering & measures ---------- */
  function campOk(c) { return !S.upazila || D.dims.camps[c].upazila === S.upazila; }
  function indOk(i) { return S.sector === '' || D.dims.indicators[i].sector === +S.sector; }
  function filtResults(opts = {}) {
    const lo = opts.allMonths ? 0 : S.start, hi = opts.allMonths ? D.dims.months.length - 1 : S.end;
    return D.results.rows.filter(r => r[0] >= lo && r[0] <= hi && campOk(r[1]) && (opts.allSectors || indOk(r[2])));
  }
  // Equal-weighted achievement over indicators
  function achievement(rows) {
    const t = new Map();
    for (const r of rows) { const a = t.get(r[2]) || [0, 0]; a[0] += r[4]; a[1] += r[5]; t.set(r[2], a); }
    let s = 0, n = 0;
    t.forEach(([tg, ac]) => { if (tg > 0) { s += ac / tg; n++; } });
    return n ? s / n : null;
  }
  function byKey(rows, keyFn) {
    const m = new Map();
    for (const r of rows) { const k = keyFn(r); if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
    return m;
  }
  function sums(rows) {
    const o = { n: 0, late: 0, lag: 0, mi: 0, ou: 0, inc: 0 };
    for (const r of rows) { o.n += r[7]; o.late += r[8]; o.lag += r[9]; o.mi += r[10]; o.ou += r[11]; o.inc += r[12]; }
    o.timely = o.n ? 1 - o.late / o.n : null;
    o.dq = o.n ? 1 - (o.mi + o.ou + o.inc) / o.n : null;
    return o;
  }
  function filtTpm(opts = {}) {
    const lo = opts.allMonths ? 0 : S.start, hi = opts.allMonths ? D.dims.months.length - 1 : S.end;
    return D.tpm.rows.filter(v => v[0] >= lo && v[0] <= hi && campOk(v[1]) && (S.sector === '' || v[3] === +S.sector));
  }
  function closure(visits) {
    const w = visits.filter(v => v[5] > 0);
    const closed = w.filter(v => !v[7]);
    const days = closed.filter(v => v[8] != null);
    return { visits: visits.length, withIssues: w.length, closed: closed.length, open: w.length - closed.length,
      rate: w.length ? closed.length / w.length : null,
      avgDays: days.length ? days.reduce((a, v) => a + v[8], 0) / days.length : null,
      avgRating: visits.length ? visits.reduce((a, v) => a + v[4], 0) / visits.length : null,
      issues: visits.reduce((a, v) => a + v[5], 0) };
  }
  function monthlySeries(fn, rows) {
    const g = byKey(rows, r => r[0]);
    const out = [];
    for (let m = S.start; m <= S.end; m++) out.push(g.has(m) ? fn(g.get(m)) : null);
    return out;
  }

  /* ---------- echarts base ---------- */
  function baseOpt() {
    const text = css('--text'), muted = css('--muted'), border = css('--border');
    return {
      textStyle: { fontFamily: 'Inter, system-ui, sans-serif', color: text },
      color: SERIES,
      animationDuration: 700,
      grid: { left: 8, right: 16, top: 28, bottom: 8, containLabel: true },
      tooltip: { trigger: 'axis', backgroundColor: css('--surface'), borderColor: border, textStyle: { color: text, fontSize: 12 }, confine: true },
      legend: { textStyle: { color: muted }, icon: 'roundRect', itemWidth: 12, itemHeight: 8, top: 0 },
      _axis: { axisLine: { lineStyle: { color: border } }, axisLabel: { color: muted, fontSize: 11 }, splitLine: { lineStyle: { color: border, type: 'dashed' } }, axisTick: { show: false } }
    };
  }
  function ax(extra) { const b = baseOpt()._axis; return Object.assign({}, b, extra); }
  function chart(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    if (!charts[id]) charts[id] = echarts.init(el, null, { renderer: 'svg' });
    return charts[id];
  }
  function setOpt(id, opt) {
    const c = chart(id); if (!c) return;
    const b = baseOpt(); delete b._axis;
    c.setOption(Object.assign(b, opt), true);
  }
  const pctAxis = (min) => ax({ type: 'value', min: min, axisLabel: { color: css('--muted'), fontSize: 11, formatter: v => Math.round(v * 100) + '%' } });

  /* ---------- KPI cards ---------- */
  function animateNumber(el, to, fmt) {
    const from = +el.dataset.v || 0; el.dataset.v = to;
    if (to == null || !isFinite(to) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = fmt(to); return; }
    const t0 = performance.now(), dur = 700;
    const step = t => { const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3); el.textContent = fmt(from + (to - from) * e); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }
  function renderKpis(containerId, items) {
    const box = document.getElementById(containerId);
    if (box.children.length !== items.length) {
      box.innerHTML = items.map((k, i) => `<div class="kpi" role="group" aria-label="${esc(k.label)}">
        <div class="kpi-l"><span>${esc(k.label)}</span><span class="kpi-chip"></span></div>
        <div class="kpi-v" data-v="0" aria-live="polite"></div><div class="kpi-s"></div>
        ${k.spark ? `<div class="spark" id="${containerId}-sp${i}" aria-hidden="true"></div>` : ''}</div>`).join('');
    }
    items.forEach((k, i) => {
      const card = box.children[i];
      const sc = k.status === undefined ? null : status(k.status);
      card.style.setProperty('--kc', sc ? (sc === 'on' ? COL.on : COL[sc]) : (k.real ? COL.green : css('--border')));
      card.querySelector('.kpi-chip').innerHTML = k.real ? '<span class="tag real">Real</span>' : (sc ? chip(k.status) : '');
      animateNumber(card.querySelector('.kpi-v'), k.value, k.fmt);
      card.querySelector('.kpi-s').textContent = k.sub || '';
      if (k.spark) {
        setOpt(`${containerId}-sp${i}`, {
          grid: { left: 0, right: 0, top: 4, bottom: 2 }, tooltip: { show: false }, legend: { show: false },
          xAxis: { type: 'category', show: false, data: k.spark.map((_, j) => j) },
          yAxis: { type: 'value', show: false, scale: true },
          series: [{ type: 'line', data: k.spark, smooth: true, symbol: 'none', lineStyle: { width: 2, color: k.sparkColor || COL.on },
            areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: (k.sparkColor || COL.on) + '55' }, { offset: 1, color: (k.sparkColor || COL.on) + '00' }] } } }]
        });
      }
    });
  }

  /* ---------- pages ---------- */
  function renderOverview() {
    const rows = filtResults();
    const ach = achievement(rows), q = sums(rows), t = closure(filtTpm());
    const achM = monthlySeries(achievement, rows);
    const qM = byKey(rows, r => r[0]);
    const tim = [], dq = [];
    for (let m = S.start; m <= S.end; m++) { const s = qM.has(m) ? sums(qM.get(m)) : {}; tim.push(s.timely ?? null); dq.push(s.dq ?? null); }
    const tpmM = monthlySeries(v => closure(v).rate, filtTpm());
    let pop = 0; D.dims.camps.forEach((c, i) => { if (campOk(i)) pop += c.pop; });
    const popAll = !S.upazila;
    renderKpis('kpis', [
      { label: 'Achievement', value: ach, fmt: fmtPct, status: ach, sub: 'Equal-weighted across indicators', spark: achM },
      { label: 'Reporting timeliness', value: q.timely, fmt: fmtPct, status: q.timely, sub: `${fmtInt(q.late)} late of ${fmtInt(q.n)} rows`, spark: tim, sparkColor: COL.sky },
      { label: 'Data quality score', value: q.dq, fmt: fmtPct, status: q.dq, sub: `${fmtInt(q.mi + q.ou + q.inc)} flagged rows`, spark: dq, sparkColor: COL.green },
      { label: 'TPM closure rate', value: t.rate, fmt: fmtPct, status: t.rate, sub: `${fmtInt(t.open)} open of ${fmtInt(t.withIssues)} with issues`, spark: tpmM, sparkColor: COL.risk },
      { label: popAll ? 'Registered population' : `Population (24 camps, ${S.upazila})`, value: popAll ? D.population.total : pop, fmt: fmtInt, real: true,
        sub: popAll ? `${fmtInt(D.population.families)} families · 30 Jun 2026` : 'Modelled camps only · 30 Jun 2026' }
    ]);

    const months = D.dims.months.slice(S.start, S.end + 1);
    const cutIdx = months.indexOf(D.meta.fundingCut);
    // count target vs achieved (count indicators only) as context bars
    const cnt = rows.filter(r => D.dims.indicators[r[2]].agg === 'sum');
    const g = byKey(cnt, r => r[0]);
    const tg = [], ac = [];
    for (let m = S.start; m <= S.end; m++) { const a = g.get(m) || []; tg.push(a.reduce((s, r) => s + r[4], 0)); ac.push(a.reduce((s, r) => s + r[5], 0)); }
    setOpt('c-trend', {
      legend: { data: ['Achievement %', 'Target (count)', 'Achieved (count)'], textStyle: { color: css('--muted') }, top: 0 },
      tooltip: { trigger: 'axis', backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text'), fontSize: 12 },
        valueFormatter: v => v == null ? '–' : (v <= 2 ? fmtPct(v) : fmtInt(v)) },
      grid: { left: 8, right: 8, top: 36, bottom: 8, containLabel: true },
      xAxis: ax({ type: 'category', data: months.map(monthLabel), splitLine: { show: false } }),
      yAxis: [pctAxis(v => Math.max(0, Math.floor(v.min * 10) / 10 - 0.05)), ax({ type: 'value', splitLine: { show: false }, axisLabel: { color: css('--muted'), fontSize: 11, formatter: v => (v / 1e6).toFixed(1) + 'M' } })],
      series: [
        { name: 'Target (count)', type: 'bar', yAxisIndex: 1, data: tg, itemStyle: { color: css('--border'), borderRadius: [3, 3, 0, 0] }, barGap: '-100%', barWidth: '55%' },
        { name: 'Achieved (count)', type: 'bar', yAxisIndex: 1, data: ac, itemStyle: { color: COL.sky + '88', borderRadius: [3, 3, 0, 0] }, barWidth: '55%' },
        { name: 'Achievement %', type: 'line', data: achM, smooth: true, symbolSize: 7, lineStyle: { width: 3, color: COL.on }, itemStyle: { color: COL.on }, z: 5,
          markLine: { symbol: 'none', silent: true, data: [
            { yAxis: 0.9, lineStyle: { color: COL.risk, type: 'dashed' }, label: { formatter: 'On-track 90%', color: COL.risk, position: 'insideEndTop' } },
            ...(cutIdx >= 0 ? [{ xAxis: cutIdx, lineStyle: { color: COL.off, type: 'solid', width: 1.5 }, label: { formatter: 'Funding cut (Jan 2026)', color: COL.off, position: 'insideEndTop' } }] : [])
          ] } }
      ]
    });

    const bySec = D.dims.sectors.map((name, s) => ({ name, v: achievement(rows.filter(r => D.dims.indicators[r[2]].sector === s)) })).filter(d => d.v != null).sort((a, b) => a.v - b.v);
    setOpt('c-sector', {
      tooltip: { trigger: 'item', formatter: p => `${esc(p.name)}<br>${fmtPct(p.value)} · ${statusLabel[status(p.value)]}` },
      grid: { left: 8, right: 112, top: 8, bottom: 8, containLabel: true },
      xAxis: pctAxis(0), yAxis: ax({ type: 'category', data: bySec.map(d => d.name), splitLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '55%', data: bySec.map(d => ({ value: d.v, itemStyle: { color: COL[status(d.v)], borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', color: css('--text'), formatter: p => `${fmtPct(p.value)}  ${statusLabel[status(p.value)]}` },
        markLine: { symbol: 'none', silent: true, data: [{ xAxis: 0.9 }], lineStyle: { color: COL.risk, type: 'dashed' }, label: { show: false } } }]
    });
  }

  function renderSectors() {
    const rows = filtResults();
    const prevRows = S.end > 0 ? D.results.rows.filter(r => r[0] === S.end - 1 && campOk(r[1]) && indOk(r[2])) : [];
    const lastRows = rows.filter(r => r[0] === S.end);
    const gi = byKey(rows, r => r[2]), gl = byKey(lastRows, r => r[2]), gp = byKey(prevRows, r => r[2]);
    const data = [];
    gi.forEach((rs, i) => {
      const ind = D.dims.indicators[i];
      const tgt = rs.reduce((a, r) => a + r[4], 0), ach = rs.reduce((a, r) => a + r[5], 0);
      const l = gl.has(i) ? achievement(gl.get(i)) : null, p = gp.has(i) ? achievement(gp.get(i)) : null;
      data.push({ sector: D.dims.sectors[ind.sector], name: ind.name, unit: ind.unit, agg: ind.agg, tgt, ach, pct: tgt ? ach / tgt : null, delta: l != null && p != null ? l - p : null });
    });
    const { k, dir } = S.sort;
    data.sort((a, b) => { const x = a[k], y = b[k]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * dir; });
    const tb = $('#t-ind tbody');
    tb.innerHTML = data.length ? data.map(d => {
      const isAvg = d.agg === 'avg';
      const w = Math.min(100, (d.pct || 0) * 100);
      const dl = d.delta == null ? '–' : `<span class="${d.delta >= 0 ? 'up' : 'down'}" aria-label="${d.delta >= 0 ? 'up' : 'down'} ${Math.abs(d.delta * 100).toFixed(1)} points">${d.delta >= 0 ? '▲' : '▼'} ${Math.abs(d.delta * 100).toFixed(1)} pt</span>`;
      return `<tr><td>${esc(d.sector)}</td><td>${esc(d.name)}</td><td>${esc(d.unit)}</td>
        <td class="num">${isAvg ? '–' : fmtInt(d.tgt)}</td><td class="num">${isAvg ? '–' : fmtInt(d.ach)}</td>
        <td class="num"><div class="bar-cell">${fmtPct(d.pct)}<div class="mini" aria-hidden="true"><span style="width:${w}%;background:${COL[status(d.pct)]}"></span></div></div></td>
        <td class="num">${dl}</td><td>${chip(d.pct)}</td></tr>`;
    }).join('') : '<tr><td colspan="8" class="empty">No data for this selection</td></tr>';
    document.querySelectorAll('#t-ind th[data-k]').forEach((th, idx) => {
      if (idx === 7) return;
      th.setAttribute('aria-sort', th.dataset.k === k ? (dir > 0 ? 'ascending' : 'descending') : 'none');
    });

    const byP = D.dims.partners.map((p, i) => ({ name: p.name, v: achievement(rows.filter(r => r[3] === i)) })).filter(d => d.v != null).sort((a, b) => a.v - b.v);
    setOpt('c-partner', {
      tooltip: { trigger: 'item', formatter: p => `${esc(p.name)}<br>${fmtPct(p.value)}` },
      grid: { left: 8, right: 50, top: 8, bottom: 8, containLabel: true },
      xAxis: pctAxis(0), yAxis: ax({ type: 'category', data: byP.map(d => d.name), splitLine: { show: false } }),
      series: [{ type: 'bar', barWidth: '60%', data: byP.map(d => ({ value: d.v, itemStyle: { color: COL[status(d.v)], borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', color: css('--text'), formatter: p => fmtPct(p.value) } }]
    });

    const months = D.dims.months.slice(S.start, S.end + 1);
    const secs = D.dims.sectors.map((n, s) => s).filter(s => S.sector === '' || s === +S.sector);
    const cutIdx = months.indexOf(D.meta.fundingCut);
    setOpt('c-sector-trend', {
      tooltip: { trigger: 'axis', backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text') }, valueFormatter: v => fmtPct(v) },
      grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
      xAxis: ax({ type: 'category', data: months.map(monthLabel), splitLine: { show: false } }),
      yAxis: pctAxis(v => Math.max(0, Math.floor(v.min * 10) / 10 - 0.05)),
      series: secs.map((s, j) => ({ name: D.dims.sectors[s], type: 'line', smooth: true, symbolSize: 5, color: SERIES[j],
        data: monthlySeries(achievement, rows.filter(r => D.dims.indicators[r[2]].sector === s)),
        markLine: j ? undefined : { symbol: 'none', silent: true, data: [{ yAxis: 0.9, lineStyle: { color: COL.risk, type: 'dashed' }, label: { formatter: '90%', color: COL.risk } },
          ...(cutIdx >= 0 ? [{ xAxis: cutIdx, lineStyle: { color: COL.off }, label: { formatter: 'Funding cut', color: COL.off } }] : [])] } }))
    });
  }

  function campMetrics() {
    const rows = filtResults();
    const nM = S.end - S.start + 1;
    const g = byKey(rows, r => r[1]);
    return D.dims.camps.map((c, i) => {
      if (!campOk(i)) return null;
      const rs = g.get(i) || [];
      const child = rs.filter(r => D.dims.indicators[r[2]].children);
      const ppl = rs.filter(r => D.dims.indicators[r[2]].agg === 'sum' && ['people', 'children'].includes(D.dims.indicators[r[2]].unit));
      const childPop = c.pop * c.childShare;
      const reachSum = child.reduce((a, r) => a + r[5], 0);
      const pa = ppl.reduce((a, r) => a + r[5], 0), pf = ppl.reduce((a, r) => a + r[6], 0);
      return { i, name: c.name, upazila: c.upazila, pop: c.pop, families: c.families, childPop, lat: c.lat, lon: c.lon,
        reach: child.length ? reachSum / nM / childPop * 1000 : null, female: pa ? pf / pa : null, ach: achievement(rs), q: sums(rs) };
    }).filter(Boolean);
  }

  // sequential ramp (light -> deep blue), colour-blind safe single hue
  function ramp(t) {
    const a = [222, 235, 247], b = [8, 69, 148];
    t = Math.max(0, Math.min(1, t));
    return `rgb(${a.map((x, k) => Math.round(x + (b[k] - x) * t)).join(',')})`;
  }

  function renderCamps() {
    const cm = campMetrics();
    const vals = cm.map(c => c.reach).filter(v => v != null);
    const lo = vals.length ? Math.min(...vals) : 0, hi = vals.length ? Math.max(...vals) : 1;
    const norm = v => v == null ? null : (hi > lo ? (v - lo) / (hi - lo) : 0.5);

    // map
    if (typeof L !== 'undefined') {
      if (!map) {
        map = L.map('map', { scrollWheelZoom: false, attributionControl: true }).setView([21.08, 92.15], 11);
        mapLayer = L.layerGroup().addTo(map);
      }
      const url = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
      if (!tileLayer || tileLayer._url !== url || tileLayer.options.className !== (isDark() ? 'map-tiles-dark' : '')) {
        if (tileLayer) map.removeLayer(tileLayer);
        tileLayer = L.tileLayer(url, { maxZoom: 19, className: isDark() ? 'map-tiles-dark' : '',
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
      }
      mapLayer.clearLayers();
      const maxPop = Math.max(...D.dims.camps.map(c => c.pop));
      const pts = [];
      cm.slice().sort((a, b) => b.pop - a.pop).forEach(c => {
        const t = norm(c.reach);
        const m = L.circleMarker([c.lat, c.lon], { radius: 5 + 16 * Math.sqrt(c.pop / maxPop), color: isDark() ? '#e2e8f0' : '#334155', weight: 1,
          fillColor: t == null ? COL.na : ramp(t), fillOpacity: 0.85, keyboard: true, title: c.name });
        m.bindTooltip(c.name, { direction: 'top' });
        m.bindPopup(`<h4>${esc(c.name)}</h4><div class="pop-grid">
          <span>Upazila</span><span>${esc(c.upazila)}</span>
          <span>Population (real)</span><span>${fmtInt(c.pop)}</span>
          <span>Families (real)</span><span>${fmtInt(c.families)}</span>
          <span>Child population</span><span>${fmtInt(c.childPop)}</span>
          <span>Reach / 1,000 children</span><span>${c.reach == null ? '–' : fmtInt(c.reach)}</span>
          <span>Achievement</span><span>${fmtPct(c.ach)} (${statusLabel[status(c.ach)]})</span>
          <span>Female share reached</span><span>${fmtPct(c.female)}</span>
          <span>Timeliness · DQ</span><span>${fmtPct(c.q.timely)} · ${fmtPct(c.q.dq)}</span></div>`);
        m.addTo(mapLayer); pts.push([c.lat, c.lon]);
      });
      if (pts.length) map.fitBounds(pts, { padding: [30, 30], maxZoom: 13 });
      setTimeout(() => map.invalidateSize(), 50);
      $('#map-legend').innerHTML = `<span>Reach / 1,000 children</span><span>${fmtInt(lo)}</span><span class="ramp" style="background:linear-gradient(90deg,${ramp(0)},${ramp(1)})"></span><span>${fmtInt(hi)}</span><span style="margin-left:12px">○ size = population</span>`;
    } else {
      $('#map').innerHTML = '<p class="empty">Map library failed to load.</p>';
    }

    const ranked = cm.filter(c => c.reach != null).sort((a, b) => a.reach - b.reach);
    const med = vals.length ? vals.slice().sort((a, b) => a - b)[Math.floor(vals.length / 2)] : null;
    setOpt('c-reach', {
      tooltip: { trigger: 'item', formatter: p => `${esc(p.name)}<br>${fmtInt(p.value)} per 1,000 children / month` },
      grid: { left: 8, right: 44, top: 22, bottom: 8, containLabel: true },
      xAxis: ax({ type: 'value' }), yAxis: ax({ type: 'category', data: ranked.map(c => c.name), splitLine: { show: false }, axisLabel: { color: css('--muted'), fontSize: 10, interval: 0 } }),
      series: [{ type: 'bar', barWidth: '65%', data: ranked.map(c => ({ value: c.reach, itemStyle: { color: ramp(norm(c.reach)), borderRadius: [0, 3, 3, 0] } })),
        label: { show: true, position: 'right', fontSize: 10, color: css('--muted'), formatter: p => fmtInt(p.value) },
        markLine: med == null ? undefined : { symbol: 'none', silent: true, data: [{ xAxis: med }], lineStyle: { color: COL.risk, type: 'dashed' }, label: { formatter: 'Median', color: COL.risk } } }],
      graphic: ranked.length ? [] : [{ type: 'text', left: 'center', top: 'middle', style: { text: 'No children indicators in this sector', fill: css('--muted') } }]
    });

    const ups = [...new Set(cm.map(c => c.upazila))];
    setOpt('c-female', {
      tooltip: { trigger: 'item', formatter: p => `${esc(p.data.name)}<br>Population ${fmtInt(p.data.value[0])}<br>Female share ${fmtPct(p.data.value[1])}` },
      legend: { data: ups, top: 0, textStyle: { color: css('--muted') } },
      grid: { left: 8, right: 24, top: 36, bottom: 24, containLabel: true },
      xAxis: ax({ type: 'value', name: 'Population', nameLocation: 'middle', nameGap: 26, nameTextStyle: { color: css('--muted') }, axisLabel: { color: css('--muted'), fontSize: 11, formatter: v => (v / 1000) + 'k' } }),
      yAxis: pctAxis(v => Math.max(0, Math.floor(v.min * 100 - 2) / 100)),
      series: ups.map((u, j) => ({ name: u, type: 'scatter', symbolSize: 12, color: [COL.on, COL.pink][j % 2],
        data: cm.filter(c => c.upazila === u && c.female != null).map(c => ({ name: c.name, value: [c.pop, c.female] })),
        markLine: j ? undefined : { symbol: 'none', silent: true, data: [{ yAxis: 0.515 }], lineStyle: { color: COL.risk, type: 'dashed' }, label: { formatter: '51.5%', color: COL.risk } } }))
    });

    const ag = D.population.ageGroups;
    setOpt('c-pyramid', {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text') }, valueFormatter: v => fmtInt(Math.abs(v)) },
      legend: { data: ['Female', 'Male'], top: 0, textStyle: { color: css('--muted') } },
      grid: { left: 8, right: 16, top: 30, bottom: 8, containLabel: true },
      xAxis: ax({ type: 'value', axisLabel: { color: css('--muted'), fontSize: 11, formatter: v => Math.abs(v / 1000) + 'k' } }),
      yAxis: ax({ type: 'category', data: ag, splitLine: { show: false } }),
      series: [
        { name: 'Female', type: 'bar', stack: 'p', data: D.population.ageSex.Female.map(v => -v), color: COL.pink, itemStyle: { borderRadius: [3, 0, 0, 3] } },
        { name: 'Male', type: 'bar', stack: 'p', data: D.population.ageSex.Male, color: COL.on, itemStyle: { borderRadius: [0, 3, 3, 0] } }
      ]
    });
  }

  function renderQuality() {
    const rows = filtResults();
    const q = sums(rows);
    renderKpis('kpis-q', [
      { label: 'Reporting timeliness', value: q.timely, fmt: fmtPct, status: q.timely },
      { label: 'Late rows', value: q.late, fmt: fmtInt },
      { label: 'Data quality score', value: q.dq, fmt: fmtPct, status: q.dq },
      { label: 'Data quality issues', value: q.mi + q.ou + q.inc, fmt: fmtInt, sub: `${fmtInt(q.mi)} missing · ${fmtInt(q.ou)} outlier · ${fmtInt(q.inc)} inconsistent` }
    ]);
    const months = D.dims.months.slice(S.start, S.end + 1);
    const heat = [];
    const gp = byKey(rows, r => r[3] * 100 + r[0]);
    D.dims.partners.forEach((p, pi) => {
      for (let m = S.start; m <= S.end; m++) { const rs = gp.get(pi * 100 + m); if (rs) heat.push([m - S.start, pi, +(sums(rs).timely * 100).toFixed(1)]); }
    });
    setOpt('c-heat', {
      tooltip: { trigger: 'item', formatter: p => `${esc(D.dims.partners[p.value[1]].name)} · ${monthLabel(months[p.value[0]])}<br>Timeliness ${p.value[2]}%` },
      grid: { left: 8, right: 16, top: 8, bottom: 56, containLabel: true },
      xAxis: ax({ type: 'category', data: months.map(monthLabel), splitLine: { show: false } }),
      yAxis: ax({ type: 'category', data: D.dims.partners.map(p => p.name), splitLine: { show: false } }),
      visualMap: { min: 70, max: 100, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 140, text: ['100%', '70%'],
        textStyle: { color: css('--muted') }, inRange: { color: [COL.off, COL.risk, '#f7f7f7', COL.sky, COL.on] } },
      series: [{ type: 'heatmap', data: heat, itemStyle: { borderColor: css('--surface'), borderWidth: 2, borderRadius: 3 },
        label: { show: months.length <= 9, fontSize: 9, color: '#111', formatter: p => Math.round(p.value[2]) } }]
    });
    const gm = byKey(rows, r => r[0]);
    const mk = idx => { const o = []; for (let m = S.start; m <= S.end; m++) o.push((gm.get(m) || []).reduce((a, r) => a + r[idx], 0)); return o; };
    setOpt('c-dq', {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text') } },
      legend: { data: ['Missing', 'Outlier', 'Inconsistent'], top: 0, textStyle: { color: css('--muted') } },
      grid: { left: 8, right: 8, top: 30, bottom: 8, containLabel: true },
      xAxis: ax({ type: 'category', data: months.map(monthLabel), splitLine: { show: false } }), yAxis: ax({ type: 'value' }),
      series: [['Missing', 10, COL.na], ['Outlier', 11, COL.risk], ['Inconsistent', 12, COL.off]].map(([n, i, c]) => ({ name: n, type: 'bar', stack: 'dq', data: mk(i), color: c, barWidth: '60%' }))
    });
    const tb = $('#t-partner tbody');
    const gpp = byKey(rows, r => r[3]);
    tb.innerHTML = D.dims.partners.map((p, i) => ({ p, s: sums(gpp.get(i) || []) })).filter(d => d.s.n).sort((a, b) => a.s.timely - b.s.timely).map(({ p, s }) =>
      `<tr><td>${esc(p.name)}</td><td>${esc(p.type)}</td>
       <td class="num"><div class="bar-cell">${fmtPct(s.timely)}<div class="mini" aria-hidden="true"><span style="width:${s.timely * 100}%;background:${COL[status(s.timely)]}"></span></div></div></td>
       <td class="num">${fmtInt(s.late)}</td><td class="num">${(s.lag / s.n).toFixed(1)}</td>
       <td class="num"><div class="bar-cell">${fmtPct(s.dq)}<div class="mini" aria-hidden="true"><span style="width:${s.dq * 100}%;background:${COL[status(s.dq)]}"></span></div></div></td>
       <td class="num">${fmtInt(s.mi)}</td><td class="num">${fmtInt(s.ou)}</td><td class="num">${fmtInt(s.inc)}</td></tr>`).join('') || '<tr><td colspan="9" class="empty">No data</td></tr>';
  }

  function renderTpm() {
    const v = filtTpm(), c = closure(v);
    renderKpis('kpis-t', [
      { label: 'TPM visits', value: c.visits, fmt: fmtInt },
      { label: 'Average rating (1–4)', value: c.avgRating, fmt: x => x == null ? '–' : x.toFixed(2) },
      { label: 'Issues flagged', value: c.issues, fmt: fmtInt },
      { label: 'Closure rate', value: c.rate, fmt: fmtPct, status: c.rate, sub: `${fmtInt(c.closed)} closed of ${fmtInt(c.withIssues)}` },
      { label: 'Avg days to close', value: c.avgDays, fmt: x => x == null ? '–' : x.toFixed(1) }
    ]);
    const cats = D.tpm.categories;
    const per = cats.map((n, k) => closure(v.filter(r => r[6] === k)));
    const order = cats.map((n, k) => k).sort((a, b) => (per[a].rate ?? 2) - (per[b].rate ?? 2));
    setOpt('c-tpm-cat', {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text') },
        formatter: ps => { const k = order[ps[0].dataIndex]; return `${esc(cats[k])}<br>Closed ${per[k].closed} · Open ${per[k].open}<br>Closure ${fmtPct(per[k].rate)}`; } },
      legend: { data: ['Closed', 'Open'], top: 0, textStyle: { color: css('--muted') } },
      grid: { left: 8, right: 60, top: 30, bottom: 8, containLabel: true },
      xAxis: ax({ type: 'value' }), yAxis: ax({ type: 'category', data: order.map(k => cats[k]), splitLine: { show: false } }),
      series: [
        { name: 'Closed', type: 'bar', stack: 't', data: order.map(k => per[k].closed), color: COL.on, barWidth: '55%' },
        { name: 'Open', type: 'bar', stack: 't', data: order.map(k => per[k].open), color: COL.off, barWidth: '55%',
          label: { show: true, position: 'right', color: css('--text'), formatter: p => fmtPct(per[order[p.dataIndex]].rate, 0) } }
      ]
    });
    const days = v.filter(r => r[5] > 0 && !r[7] && r[8] != null).map(r => r[8]);
    const bins = [[0, 7], [8, 14], [15, 30], [31, 60], [61, 90], [91, Infinity]];
    const lab = ['0–7', '8–14', '15–30', '31–60', '61–90', '90+'];
    setOpt('c-tpm-hist', {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text') } },
      grid: { left: 8, right: 8, top: 16, bottom: 24, containLabel: true },
      xAxis: ax({ type: 'category', data: lab, name: 'days', nameLocation: 'middle', nameGap: 24, nameTextStyle: { color: css('--muted') }, splitLine: { show: false } }),
      yAxis: ax({ type: 'value' }),
      series: [{ type: 'bar', name: 'Follow-ups', barWidth: '70%', data: bins.map(([a, b], j) => ({ value: days.filter(d => d >= a && d <= b).length, itemStyle: { color: j >= 3 ? COL.risk : COL.on, borderRadius: [4, 4, 0, 0] } })),
        label: { show: true, position: 'top', color: css('--muted') } }]
    });
    const end = monthEnd(D.dims.months[S.end]);
    const open = v.filter(r => r[5] > 0 && r[7]).map(r => ({ r, d: Math.round((end - new Date(r[10] + 'T00:00:00Z')) / 864e5) })).filter(o => o.d > 30).sort((a, b) => b.d - a.d);
    $('#open-note').textContent = `${open.length} item${open.length === 1 ? '' : 's'} · age measured at ${end.toISOString().slice(0, 10)}`;
    $('#t-open tbody').innerHTML = open.length ? open.map(({ r, d }) => `<tr><td>${esc(r[9])}</td><td>${esc(r[10])}</td><td>${esc(D.dims.camps[r[1]].name)}</td>
      <td>${esc(D.dims.sectors[r[3]])}</td><td>${esc(D.dims.partners[r[2]].name)}</td><td>${esc(cats[r[6]] || '–')}</td><td class="num">${r[5]}</td>
      <td class="num" style="color:${COL.off};font-weight:600">${d}</td></tr>`).join('') : '<tr><td colspan="8" class="empty">No open follow-ups older than 30 days</td></tr>';
  }

  function renderHost() {
    const W = D.wages, s = W.series[S.meals] || {};
    const defs = [["Cox's Bazar|Male", "Cox's Bazar, male", COL.on, 'solid'], ["Bangladesh (national median)|Male", 'National median, male', COL.on, 'dashed'],
      ["Cox's Bazar|Female", "Cox's Bazar, female", COL.off, 'solid'], ["Bangladesh (national median)|Female", 'National median, female', COL.off, 'dashed']];
    setOpt('c-wage', {
      tooltip: { trigger: 'axis', backgroundColor: css('--surface'), borderColor: css('--border'), textStyle: { color: css('--text') }, valueFormatter: v => v == null ? '–' : '৳' + fmtInt(v) },
      legend: { top: 0, textStyle: { color: css('--muted') } },
      grid: { left: 8, right: 16, top: 36, bottom: 40, containLabel: true },
      dataZoom: [{ type: 'slider', height: 18, bottom: 6, borderColor: css('--border'), textStyle: { color: css('--muted') } }, { type: 'inside' }],
      xAxis: ax({ type: 'category', data: W.months.map(monthLabel), splitLine: { show: false } }),
      yAxis: ax({ type: 'value', name: 'BDT / day (nominal)', nameTextStyle: { color: css('--muted') } }),
      series: defs.map(([k, n, c, t]) => ({ name: n, type: 'line', data: s[k] || [], connectNulls: false, symbol: 'none', color: c, lineStyle: { width: 2, type: t } }))
    });
    const last = k => { const a = s[k] || []; for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return a[i]; return null; };
    const cm = last("Cox's Bazar|Male"), nm = last("Bangladesh (national median)|Male"), cf = last("Cox's Bazar|Female"), nf = last("Bangladesh (national median)|Female");
    const prem = (a, b) => a != null && b ? (a / b - 1) : null;
    renderKpis('kpis-h', [
      { label: "Cox's Bazar male wage (latest)", value: cm, fmt: x => x == null ? '–' : '৳' + fmtInt(x), real: true, sub: `${S.meals} · ${W.months[W.months.length - 1]}` },
      { label: 'Male premium vs national', value: prem(cm, nm), fmt: x => x == null ? '–' : (x >= 0 ? '+' : '') + (x * 100).toFixed(0) + '%', real: true },
      { label: "Cox's Bazar female wage (latest)", value: cf, fmt: x => x == null ? '–' : '৳' + fmtInt(x), real: true, sub: S.meals },
      { label: 'Female premium vs national', value: prem(cf, nf), fmt: x => x == null ? '–' : (x >= 0 ? '+' : '') + (x * 100).toFixed(0) + '%', real: true }
    ]);
  }

  const RENDER = { overview: renderOverview, sectors: renderSectors, camps: renderCamps, quality: renderQuality, tpm: renderTpm, host: renderHost };
  function render() {
    const m = D.dims.months;
    $('#period-label').textContent = `· ${monthLabel(m[S.start])} – ${monthLabel(m[S.end])}`;
    document.querySelectorAll('.presets .chip-btn').forEach(b => {
      const p = b.dataset.preset, last = m.length - 1;
      const on = (p === 'all' && S.start === 0 && S.end === last) || (p === '2025' && m[S.start] === '2025-01' && m[S.end] === '2025-12') || (p === '2026' && m[S.start] === '2026-01' && S.end === last);
      b.setAttribute('aria-pressed', on);
    });
    RENDER[S.page]();
    requestAnimationFrame(() => Object.values(charts).forEach(c => c.getDom().offsetParent && c.resize()));
  }

  /* ---------- UI wiring ---------- */
  function setupTabs() {
    const tabs = [...document.querySelectorAll('[role="tab"]')];
    const select = (tab, focus) => {
      tabs.forEach(t => { const on = t === tab; t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1; document.getElementById(t.getAttribute('aria-controls')).hidden = !on; });
      S.page = tab.id.replace('tab-', '');
      if (focus) tab.focus();
      try { history.replaceState(null, '', '#' + S.page); } catch (e) {}
      render();
    };
    tabs.forEach((t, i) => {
      t.addEventListener('click', () => select(t));
      t.addEventListener('keydown', e => {
        let j = null;
        if (e.key === 'ArrowRight') j = (i + 1) % tabs.length; else if (e.key === 'ArrowLeft') j = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') j = 0; else if (e.key === 'End') j = tabs.length - 1;
        if (j != null) { e.preventDefault(); select(tabs[j], true); }
      });
    });
    const h = location.hash.slice(1), init = tabs.find(t => t.id === 'tab-' + h) || tabs[0];
    return () => select(init);
  }

  function setupFilters() {
    const m = D.dims.months, fs = $('#f-start'), fe = $('#f-end');
    m.forEach((x, i) => { fs.add(new Option(monthLabel(x), i)); fe.add(new Option(monthLabel(x), i)); });
    D.dims.sectors.forEach((n, i) => $('#f-sector').add(new Option(n, i)));
    D.dims.upazilas.forEach(u => $('#f-upazila').add(new Option(u, u)));
    D.wages.meals.forEach(x => $('#f-meals').add(new Option(x, x)));
    const sync = () => { fs.value = S.start; fe.value = S.end; $('#f-sector').value = S.sector; $('#f-upazila').value = S.upazila; $('#f-meals').value = S.meals; };
    S.start = 0; S.end = m.length - 1; sync();
    fs.addEventListener('change', () => { S.start = +fs.value; if (S.start > S.end) S.end = S.start; sync(); render(); });
    fe.addEventListener('change', () => { S.end = +fe.value; if (S.end < S.start) S.start = S.end; sync(); render(); });
    $('#f-sector').addEventListener('change', e => { S.sector = e.target.value; render(); });
    $('#f-upazila').addEventListener('change', e => { S.upazila = e.target.value; render(); });
    $('#f-meals').addEventListener('change', e => { S.meals = e.target.value; render(); });
    document.querySelectorAll('.presets .chip-btn').forEach(b => b.addEventListener('click', () => {
      const p = b.dataset.preset;
      if (p === 'all') { S.start = 0; S.end = m.length - 1; }
      if (p === '2025') { S.start = m.indexOf('2025-01'); S.end = m.indexOf('2025-12'); }
      if (p === '2026') { S.start = m.indexOf('2026-01'); S.end = m.length - 1; }
      sync(); render();
    }));
    $('#f-reset').addEventListener('click', () => { S.start = 0; S.end = m.length - 1; S.sector = ''; S.upazila = ''; sync(); render(); });
    document.querySelectorAll('#t-ind th[data-k] button').forEach(btn => btn.addEventListener('click', () => {
      const k = btn.parentElement.dataset.k;
      S.sort = { k, dir: S.sort.k === k ? -S.sort.dir : (['sector', 'name', 'unit'].includes(k) ? 1 : -1) };
      renderSectors();
    }));
  }

  function setupTheme() {
    $('#theme-btn').addEventListener('click', () => {
      const next = isDark() ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('hpm-theme', next); } catch (e) {}
      Object.values(charts).forEach(c => c.dispose()); for (const k in charts) delete charts[k];
      document.querySelectorAll('.kpis').forEach(k => { k.innerHTML = ''; });
      render();
    });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (!document.documentElement.getAttribute('data-theme')) { Object.values(charts).forEach(c => c.dispose()); for (const k in charts) delete charts[k]; render(); }
    });
  }

  function setupAbout() {
    const dlg = $('#about');
    $('#about-sources').innerHTML = D.meta.sources.map(s => `<li><strong>${esc(s.name)}</strong> — ${esc(s.publisher)}. ${esc(s.licence)}.${s.attribution ? ' <em>' + esc(s.attribution) + '</em>.' : ''} <a href="${esc(s.url)}" rel="noopener" target="_blank">Link</a></li>`).join('') +
      '<li>Programme results, partners and TPM visits: synthetic, generated for this portfolio (seed 2026).</li>';
    $('#about-gen').textContent = `Data built ${D.meta.generated}. Population as of ${D.meta.asOf.population}; wages to ${D.meta.asOf.wages}.`;
    $('#about-repo').href = $('#repo-link').href = D.meta.repo;
    $('#about-btn').addEventListener('click', () => (dlg.showModal ? dlg.showModal() : dlg.setAttribute('open', '')));
    $('#about-close').addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
  }

  async function load() {
    const names = ['metadata', 'dims', 'results', 'tpm', 'population', 'wages'];
    const got = await Promise.all(names.map(n => fetch(`data/${n}.json`).then(r => { if (!r.ok) throw new Error(n + ': ' + r.status); return r.json(); })));
    [D.meta, D.dims, D.results, D.tpm, D.population, D.wages] = got;
  }

  async function init() {
    try {
      await load();
    } catch (e) {
      $('#loading').textContent = 'Could not load data. If opening the file directly, serve the site folder over HTTP (e.g. python -m http.server).';
      console.error(e); return;
    }
    $('#loading').remove();
    if (typeof echarts === 'undefined') { $('#main').insertAdjacentHTML('afterbegin', '<p class="empty">Chart library failed to load.</p>'); return; }
    setupFilters(); setupTheme(); setupAbout();
    const start = setupTabs(); start();
    let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => Object.values(charts).forEach(c => c.getDom().offsetParent && c.resize()), 120); });
  }
  init();
})();
