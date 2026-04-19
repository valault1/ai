'use strict';

// ── State ─────────────────────────────────────────────────────────────────────

let pipelines = [];
let runs = [];
let activeRunId = null;
let activeSSE = null;
let currentTab = 'runs';

// ── Utilities ─────────────────────────────────────────────────────────────────

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtTime(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleTimeString(); } catch { return iso; }
}

function fmtElapsed(state) {
  if (!state.started_at) return '';
  const end = state.finished_at ? new Date(state.finished_at) : new Date();
  const sec = Math.round((end - new Date(state.started_at)) / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

function paramsLabel(params) {
  return Object.values(params || {}).join(' · ') || '—';
}

// ── Status indicators ─────────────────────────────────────────────────────────

function statusDotClass(status) {
  return { running: 's-running', done: 's-done', failed: 's-failed' }[status] || 's-pending';
}

function stepIcon(status) {
  if (status === 'done')    return '<span style="color:var(--green)">✓</span>';
  if (status === 'running') return '<span class="spin"></span>';
  if (status === 'failed')  return '<span style="color:var(--red)">✗</span>';
  if (status === 'skipped') return '<span style="color:var(--muted)">—</span>';
  return '<span style="color:var(--muted)">·</span>';
}

// ── Tab switching ─────────────────────────────────────────────────────────────

function showTab(tab) {
  currentTab = tab;
  document.getElementById('view-runs').style.display   = tab === 'runs'   ? 'flex' : 'none';
  document.getElementById('view-stocks').style.display = tab === 'stocks' ? 'flex' : 'none';
  document.getElementById('tab-runs').classList.toggle('active', tab === 'runs');
  document.getElementById('tab-stocks').classList.toggle('active', tab === 'stocks');
  if (tab === 'stocks') loadStocksDashboard();
}

// ── Run list ──────────────────────────────────────────────────────────────────

function renderRunList() {
  const el = document.getElementById('run-list');
  if (!runs.length) {
    el.innerHTML = '<div style="padding:24px 14px;text-align:center;color:var(--muted);font-size:13px">No runs yet.<br>Click <strong>+ New Run</strong> to start.</div>';
    return;
  }
  el.innerHTML = runs.map(r => `
    <div class="run-item ${r.run_id === activeRunId ? 'active' : ''}"
         onclick="openRun('${esc(r.run_id)}')">
      <div class="run-pip">${esc(r.pipeline_name || r.pipeline_id)}</div>
      <div class="run-params">${esc(paramsLabel(r.params))}</div>
      <div class="run-meta">
        <span class="status-dot ${statusDotClass(r.status)}"></span>
        <span class="run-time">${fmtTime(r.started_at)}</span>
      </div>
    </div>
  `).join('');
}

// ── Run detail ────────────────────────────────────────────────────────────────

function openRun(runId) {
  activeRunId = runId;
  renderRunList();
  loadRunDetail(runId);
}

async function loadRunDetail(runId) {
  const emptyEl = document.getElementById('detail-empty');
  const contentEl = document.getElementById('detail-content');
  emptyEl.style.display = 'none';
  contentEl.style.display = 'block';
  contentEl.innerHTML = '<div style="color:var(--muted);padding:20px">Loading…</div>';

  try {
    const state = await fetch(`/api/runs/${runId}`).then(r => r.json());
    renderRunDetail(state);
    if (state.status === 'running') subscribeToRun(runId);
  } catch (e) {
    contentEl.innerHTML = `<div style="color:var(--red);padding:20px">Failed to load run: ${esc(String(e))}</div>`;
  }
}

function renderRunDetail(state) {
  const contentEl = document.getElementById('detail-content');
  const stepsHtml = (state.steps || []).map(s => renderStep(state.run_id, s)).join('');

  contentEl.innerHTML = `
    <div class="detail-header">
      <div class="detail-pip">${esc(state.pipeline_name || state.pipeline_id)}</div>
      <div class="detail-params">${esc(paramsLabel(state.params))}</div>
      <div class="detail-meta">
        ${esc(state.status)} · started ${fmtTime(state.started_at)}
        ${state.finished_at ? ` · ${fmtElapsed(state)} elapsed` : ''}
      </div>
    </div>
    <div class="steps" id="steps-${esc(state.run_id)}">${stepsHtml}</div>
    ${state.error ? `<div style="color:var(--red);font-size:13px;margin-top:8px">Error: ${esc(state.error)}</div>` : ''}
  `;
}

function renderStep(runId, step) {
  const canExpand = step.status === 'done' || step.status === 'failed';
  const ts = step.finished_at ? fmtTime(step.finished_at) : (step.started_at ? fmtTime(step.started_at) : '');
  return `
    <div class="step ${esc(step.status)}" id="step-${esc(runId)}-${esc(step.id)}">
      <div class="step-header" ${canExpand ? `onclick="toggleStep('${esc(runId)}','${esc(step.id)}')"` : ''}>
        <div class="step-icon">${stepIcon(step.status)}</div>
        <div class="step-name">${esc(step.name)}</div>
        <div class="step-ts">${esc(ts)}</div>
        ${canExpand ? '<div class="step-expand">▾</div>' : ''}
      </div>
      <div class="step-output" id="out-${esc(runId)}-${esc(step.id)}"></div>
    </div>
  `;
}

function updateStep(runId, stepUpdate) {
  const stepEl = document.getElementById(`step-${runId}-${stepUpdate.step_id}`);
  if (!stepEl) return;
  // Re-fetch full state and re-render — simpler than partial DOM surgery
  loadRunDetail(runId);
}

async function toggleStep(runId, stepId) {
  const outEl = document.getElementById(`out-${runId}-${stepId}`);
  if (!outEl) return;
  if (outEl.classList.contains('open')) {
    outEl.classList.remove('open');
    return;
  }
  outEl.classList.add('open');
  if (outEl.dataset.loaded) return;
  outEl.innerHTML = '<div class="loading">Loading…</div>';
  try {
    const data = await fetch(`/api/runs/${runId}/steps/${stepId}`).then(r => r.json());
    outEl.innerHTML = `<pre>${esc(JSON.stringify(data, null, 2))}</pre>`;
    outEl.dataset.loaded = '1';
  } catch (e) {
    outEl.innerHTML = `<div style="color:var(--red)">Failed to load output</div>`;
  }
}

// ── SSE subscription ──────────────────────────────────────────────────────────

function subscribeToRun(runId) {
  if (activeSSE) { activeSSE.close(); activeSSE = null; }
  const es = new EventSource(`/api/runs/${runId}/stream`);
  activeSSE = es;

  es.onmessage = (e) => {
    const event = JSON.parse(e.data);
    if (event.type === 'connected' || event.type === 'ping') return;

    if (event.type === 'step_update') {
      if (runId === activeRunId) updateStep(runId, event);
      // Update run status dot in sidebar
      const run = runs.find(r => r.run_id === runId);
      if (run) {
        if (event.status === 'failed') run.status = 'failed';
      }
      renderRunList();
    }

    if (event.type === 'run_complete' || event.type === 'run_failed') {
      es.close();
      activeSSE = null;
      loadRuns().then(() => {
        if (runId === activeRunId) loadRunDetail(runId);
      });
    }
  };

  es.onerror = () => { es.close(); activeSSE = null; };
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal() {
  document.getElementById('modal').classList.add('open');
  if (pipelines.length) renderPipelineFields();
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
}

function onPipelineChange() {
  renderPipelineFields();
}

function renderPipelineFields() {
  const sel = document.getElementById('pipeline-select');
  const pipeline = pipelines.find(p => p.id === sel.value);
  const container = document.getElementById('params-fields');
  if (!pipeline) { container.innerHTML = ''; return; }
  container.innerHTML = pipeline.params.map(param => `
    <div class="field">
      <label>${esc(param.toUpperCase())}</label>
      <input type="text" id="param-${esc(param)}" placeholder="${esc(param)}" autocomplete="off">
    </div>
  `).join('');
  // Focus first field
  const first = container.querySelector('input');
  if (first) first.focus();
}

async function submitRun() {
  const sel = document.getElementById('pipeline-select');
  const pipeline = pipelines.find(p => p.id === sel.value);
  if (!pipeline) return;

  const params = {};
  for (const param of pipeline.params) {
    const val = document.getElementById(`param-${param}`)?.value?.trim();
    if (!val) { alert(`Please enter a value for ${param}`); return; }
    params[param] = val;
  }

  const btn = document.getElementById('btn-submit');
  btn.disabled = true;
  btn.textContent = 'Starting…';

  try {
    const res = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pipeline_id: pipeline.id, params }),
    });
    const data = await res.json();
    closeModal();
    await loadRuns();
    openRun(data.run_id);
    showTab('runs');
  } catch (e) {
    alert('Failed to start run: ' + e);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Start Run';
  }
}

// Allow Enter key in modal inputs to submit
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.getElementById('modal').classList.contains('open')) {
    submitRun();
  }
  if (e.key === 'Escape') closeModal();
});

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadPipelines() {
  try {
    pipelines = await fetch('/api/pipelines').then(r => r.json());
    const sel = document.getElementById('pipeline-select');
    sel.innerHTML = pipelines.map(p =>
      `<option value="${esc(p.id)}">${esc(p.name)}</option>`
    ).join('');
  } catch (e) {
    console.error('loadPipelines:', e);
  }
}

async function loadRuns() {
  try {
    runs = await fetch('/api/runs').then(r => r.json());
    renderRunList();
  } catch (e) {
    console.error('loadRuns:', e);
  }
}

// ── Stocks dashboard ──────────────────────────────────────────────────────────

async function loadStocksDashboard() {
  try {
    const data = await fetch('/api/stocks/reports').then(r => r.json());
    renderStocksDashboard(data);
  } catch (e) {
    document.getElementById('stocks-loading').textContent = 'Failed to load stocks data.';
  }
}

function badge(v) {
  if (!v) return '';
  return `<span class="badge v-${esc(v.trim().replace(/\s+/g, '-').toUpperCase())}">${esc(v)}</span>`;
}

function mc(m) {
  const cls = m.pass_fail === 'PASS' ? 'pass' : m.pass_fail === 'FAIL' ? 'fail' : 'na';
  return `<div class="mc ${cls}"><div class="mc-lbl">${esc(m.label)}</div><div class="mc-val">${esc(m.display_value)}</div><div class="mc-thr">${esc(m.threshold_label)}</div></div>`;
}

function renderStocksDashboard(data) {
  document.getElementById('stocks-loading').style.display = 'none';
  const tickers = data.tickers || [];

  // Leaderboard
  const lbEl = document.getElementById('stocks-lb');
  const withFinal = tickers.filter(t => t.final);
  if (withFinal.length >= 2) {
    const rows = [...withFinal].sort((a, b) => (b.final.scores?.overall || 0) - (a.final.scores?.overall || 0));
    lbEl.style.display = 'block';
    lbEl.innerHTML = `<div class="sec-ttl">Leaderboard</div>
    <table class="lb"><thead><tr>
      <th>#</th><th>Ticker</th><th>Company</th><th>Verdict</th>
      <th>Score</th><th>Big 4</th><th>Moat</th><th>Valuation</th><th>Debt</th>
    </tr></thead><tbody>${rows.map((t, i) => {
      const f = t.final, s = f.summary || {};
      return `<tr>
        <td class="lb-rank">${i + 1}</td>
        <td><a href="#t-${esc(t.ticker)}" class="lb-ticker">${esc(t.ticker)}</a></td>
        <td style="color:var(--muted);font-size:13px">${esc(f.company_name || '')}</td>
        <td>${badge(f.verdict)}</td>
        <td style="font-family:var(--mono);font-weight:700">${f.scores?.overall ?? '—'}</td>
        <td style="font-family:var(--mono)">${s.big4_pass_count ?? '—'}/4</td>
        <td>${s.moat_type ? `<span class="moat-b">${esc(s.moat_type)}</span>` : '—'}</td>
        <td>${s.valuation_stance || '—'}</td>
        <td>${s.debt_risk ? `<span class="sev sev-${esc(s.debt_risk)}">${esc(s.debt_risk)}</span>` : '—'}</td>
      </tr>`;
    }).join('')}</tbody></table>`;
  } else {
    lbEl.style.display = 'none';
  }

  // Ticker cards
  document.getElementById('stocks-tickers').innerHTML = tickers.map(renderTickerCard).join('');
}

function renderTickerCard(t) {
  const q = t.quant || {}, qual = t.qualitative || {}, f = t.final || {};
  const verdict = f.verdict || q.verdict || null;
  const score = f.scores?.overall;
  const company = f.company_name || q.company_name || t.ticker;
  const price = q.current_price ? ` · $${q.current_price}` : '';

  let h = `<div class="tcard" id="t-${esc(t.ticker)}">
    <div class="card-hdr">
      <div>
        <div class="card-sym">${esc(t.ticker)}</div>
        <div class="card-name">${esc(company)}</div>
        <div class="card-meta">${esc(q.sector || '')}${esc(price)} · ${esc(q.analysis_date || f.analysis_date || '')}</div>
      </div>
      <div class="card-rhs">
        ${score != null ? `<div class="card-score">${score}<span style="font-size:14px;color:var(--muted)">/10</span></div><div class="card-score-lbl">Score</div>` : ''}
        ${verdict ? badge(verdict) : ''}
      </div>
    </div>`;

  if (f.elevator_pitch) h += `<div class="pitch">${esc(f.elevator_pitch)}</div>`;

  if (q.big4?.length) h += `<div class="slbl">Big 4 Metrics</div><div class="g4">${q.big4.map(mc).join('')}</div>`;
  if (q.supporting?.length) h += `<div class="slbl">Supporting Metrics</div><div class="g3">${q.supporting.map(mc).join('')}</div>`;

  if (t.has_qualitative && qual.moat) {
    const coc = qual.circle_of_competence || {}, moat = qual.moat || {};
    h += `<div class="csec">
      <div class="slbl">Qualitative Analysis</div>
      <div class="qgrid">
        <div class="qi"><label>Revenue Model</label><div class="val">${esc(coc.revenue_model || '')}</div></div>
        <div class="qi"><label>Complexity</label><div class="val">${esc(coc.complexity || '')}</div></div>
        <div class="qi"><label>Moat</label><div class="val"><span class="moat-b">${esc(moat.type || '')}</span>${moat.strength ? ` <span style="color:var(--muted);font-size:12px">${esc(moat.strength)}</span>` : ''}</div></div>
        <div class="qi"><label>Assessment</label><div class="val" style="font-size:12px;color:var(--muted)">${esc(qual.overall_assessment || '')}</div></div>
      </div>
      ${moat.pricing_power_quote ? `<div class="pq">"${esc(moat.pricing_power_quote)}"<span style="font-size:11px"> — ${esc(moat.pricing_power_source || '')}</span></div>` : ''}
    </div>`;
  }

  if (t.has_qualitative && qual.risks) {
    const r = qual.risks || {}, lvl = r.debt_risk_level || 'Low';
    h += `<div class="csec">
      <div class="slbl">Risk Assessment</div>
      <div class="risk-row">
        <div class="ytp">
          <div class="ytp-num ${lvl === 'High' ? 'high' : 'low'}">${r.years_to_payoff ?? '—'}</div>
          <div class="ytp-lbl">Years to<br>Payoff</div>
          <div style="margin-top:6px"><span class="sev sev-${esc(lvl)}">${esc(lvl)} Risk</span></div>
        </div>
        <div class="risk-items">${(r.top_risks || []).map(ri => `
          <div class="ri">
            <div class="ri-title">${esc(ri.title)}<span class="sev sev-${esc(ri.severity)}">${esc(ri.severity)}</span></div>
            <div class="ri-desc">${esc(ri.description || '')}</div>
          </div>`).join('')}
        </div>
      </div>
    </div>`;
  }

  if (t.has_qualitative && qual.valuation) {
    const v = qual.valuation, disc = v.premium_discount_label === 'Discount';
    h += `<div class="csec">
      <div class="slbl">Valuation</div>
      <div class="vgrid">
        <div class="vi"><div class="vi-lbl">Current P/E</div><div class="vi-num">${v.current_pe != null ? v.current_pe + 'x' : 'N/A'}</div></div>
        <div class="vi"><div class="vi-lbl">5-Year Avg P/E</div><div class="vi-num">${v.historical_avg_pe != null ? v.historical_avg_pe + 'x' : 'N/A'}</div></div>
        <div class="vi"><div class="vi-lbl">${esc(v.premium_discount_label || '')}</div><div class="vi-num ${disc ? 'disc' : 'prem'}">${v.premium_discount_pct != null ? v.premium_discount_pct + '%' : 'N/A'}</div></div>
      </div>
      ${v.valuation_context ? `<div style="font-size:12px;color:var(--muted);margin-top:9px">${esc(v.valuation_context)}</div>` : ''}
    </div>`;
  }

  if (f.verdict_reasoning) {
    h += `<div class="csec">
      <div class="slbl">Verdict</div>
      <div style="font-size:13px;color:var(--muted);margin-bottom:7px">${esc(f.verdict_reasoning)}</div>
      ${f.target_entry_note ? `<div style="font-size:12px;color:var(--blue)">${esc(f.target_entry_note)}</div>` : ''}
    </div>`;
  }

  return h + '</div>';
}

// ── Server connectivity indicator ─────────────────────────────────────────────

function setConnected(ok) {
  const dot = document.getElementById('dot');
  const lbl = document.getElementById('conn-lbl');
  dot.className = 'dot ' + (ok ? 'live' : 'err');
  lbl.textContent = ok ? 'Live' : 'Disconnected';
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

async function init() {
  await loadPipelines();
  await loadRuns();

  // Select most recent run automatically if there is one
  if (runs.length) openRun(runs[0].run_id);

  setConnected(true);

  // Poll for run list updates every 10 seconds
  setInterval(loadRuns, 10000);
}

init().catch(e => { console.error(e); setConnected(false); });
