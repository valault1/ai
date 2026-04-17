#!/usr/bin/env python3
"""Live dashboard web server for the Buffett-style stock analysis system.

Runs as a systemd user service on port 7842. Accessible over Tailscale.

After any UI changes to this file:
    systemctl --user restart stocks-dashboard
"""

import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

REPORTS_DIR = Path(__file__).parent.parent / "reports"
PORT = 7842

app = FastAPI(title="Stocks Dashboard")


# ─── Data helpers ─────────────────────────────────────────────────────────────

def discover_tickers() -> list[str]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(
        d.name for d in REPORTS_DIR.iterdir()
        if d.is_dir() and (d / f"{d.name}_quant.json").exists()
    )


def load_ticker_data(ticker: str) -> dict:
    base = REPORTS_DIR / ticker

    def load_json(path: Path):
        try:
            return json.loads(path.read_text()) if path.exists() else None
        except Exception:
            return None

    quant = load_json(base / f"{ticker}_quant.json")
    qualitative = load_json(base / f"{ticker}_qualitative.json")
    final = load_json(base / f"{ticker}_final.json")

    return {
        "ticker": ticker,
        "quant": quant,
        "qualitative": qualitative,
        "final": final,
        "has_quant": quant is not None,
        "has_qualitative": qualitative is not None,
        "has_final": final is not None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/reports")
def reports_endpoint():
    tickers = discover_tickers()
    data = [load_ticker_data(t) for t in tickers]
    return JSONResponse({"tickers": data, "count": len(data)})


@app.get("/api/progress")
async def progress_endpoint():
    async def generate():
        last_mtime = None
        yield 'data: {"type":"connected"}\n\n'
        while True:
            progress_file = REPORTS_DIR / ".progress.json"
            try:
                if progress_file.exists():
                    mtime = progress_file.stat().st_mtime
                    if mtime != last_mtime:
                        last_mtime = mtime
                        content = progress_file.read_text()
                        yield f"data: {content}\n\n"
            except Exception:
                pass
            await asyncio.sleep(0.5)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/")
def index_endpoint():
    return HTMLResponse(DASHBOARD_HTML)


# ─── Embedded dashboard HTML ──────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stocks Dashboard</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0e17;--card:#131a2b;--border:#1e2a45;
  --text:#e1e4ea;--muted:#8892a5;--blue:#4a90d9;
  --green:#34d399;--green-bg:#0d2e1f;--green-bd:#16a34a;
  --red:#f87171;--red-bg:#2e0d0d;--red-bd:#dc2626;
  --yellow:#fbbf24;--yellow-bg:#332b0d;--yellow-bd:#d97706;
  --purple:#a78bfa;--purple-bg:#1a1a33;--purple-bd:#7c3aed;
  --na-bg:#1a1a22;--na-bd:#5a6478;
  --mono:'SF Mono','Cascadia Code','Fira Code','Consolas',monospace;
  --sans:system-ui,-apple-system,sans-serif;
}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:14px;line-height:1.5}

/* Header */
header{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:100}
.h-title{font-family:var(--mono);font-size:16px;color:var(--blue);letter-spacing:3px;font-weight:700}
.h-meta{display:flex;align-items:center;gap:16px;font-size:12px;color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block;margin-right:6px;transition:background .3s}
.dot.live{background:var(--green);box-shadow:0 0 6px var(--green)}
.dot.err{background:var(--red)}

/* Layout */
main{max-width:1200px;margin:0 auto;padding:24px}

/* Progress panel */
#prog{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:20px 24px;margin-bottom:24px}
.prog-hdr{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.prog-ticker{font-family:var(--mono);font-size:20px;color:var(--blue);font-weight:700}
.prog-lbl{color:var(--muted);font-size:13px}
.steps{display:flex;flex-direction:column;gap:6px}
.step{display:flex;align-items:center;gap:12px;padding:8px 12px;border-radius:6px;background:rgba(255,255,255,.02)}
.step.running{background:rgba(74,144,217,.08)}
.step.pending,.step.skipped{opacity:.45}
.step-ico{width:20px;text-align:center;font-size:13px;flex-shrink:0}
.step-lbl{flex:1;font-size:13px}
.step-ts{font-family:var(--mono);font-size:11px;color:var(--muted)}
@keyframes spin{to{transform:rotate(360deg)}}
.spin{display:inline-block;width:13px;height:13px;border:2px solid var(--blue);border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}

/* Empty */
.empty{text-align:center;padding:80px 24px;color:var(--muted)}
.empty h2{color:var(--text);font-size:20px;margin-bottom:8px}
.empty code{background:var(--card);padding:2px 8px;border-radius:4px;font-family:var(--mono);color:var(--blue)}

/* Leaderboard */
#lb{margin-bottom:32px}
.sec-ttl{font-family:var(--mono);font-size:11px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px}
table.lb{width:100%;border-collapse:collapse;font-size:13px}
table.lb th{text-align:left;padding:7px 10px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
table.lb td{padding:9px 10px;border-bottom:1px solid rgba(30,42,69,.5)}
table.lb tr:hover td{background:rgba(255,255,255,.02)}
.lb-ticker{font-family:var(--mono);font-weight:700;color:var(--blue)}
.lb-rank{font-family:var(--mono);color:var(--muted);font-size:12px}

/* Verdict badges */
.badge{display:inline-block;padding:2px 9px;border-radius:4px;font-size:11px;font-weight:700;font-family:var(--mono);letter-spacing:.5px;border:1px solid;white-space:nowrap}
.v-STRONG-BUY,.v-STRONG_BUY{background:#0d3320;color:var(--green);border-color:var(--green-bd)}
.v-WATCHLIST{background:var(--yellow-bg);color:var(--yellow);border-color:var(--yellow-bd)}
.v-PASS{background:var(--red-bg);color:var(--red);border-color:var(--red-bd)}
.v-MORE-RESEARCH,.v-MORE_RESEARCH{background:var(--purple-bg);color:var(--purple);border-color:var(--purple-bd)}
.v-BORDERLINE{background:var(--yellow-bg);color:var(--yellow);border-color:var(--yellow-bd)}
.v-FAIL{background:var(--red-bg);color:var(--red);border-color:var(--red-bd)}

/* Ticker cards */
.tcard{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:24px;margin-bottom:24px;scroll-margin-top:64px}
.card-hdr{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px}
.card-sym{font-family:var(--mono);font-size:30px;color:var(--blue);font-weight:700}
.card-name{font-size:15px;color:var(--text);margin-top:2px}
.card-meta{color:var(--muted);font-size:12px;margin-top:3px}
.card-rhs{display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.card-score{font-family:var(--mono);font-size:26px;font-weight:700}
.card-score-lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}

/* Elevator pitch */
.pitch{border-left:3px solid var(--blue);padding:10px 14px;background:rgba(74,144,217,.06);border-radius:0 6px 6px 0;margin-bottom:18px;font-style:italic;font-size:14px}

/* Metric grids */
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:8px}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:18px}
.slbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;font-family:var(--mono)}
.mc{padding:11px 13px;border-radius:6px;border:1px solid;border-left-width:3px}
.mc.pass{background:var(--green-bg);border-color:rgba(22,163,74,.3);border-left-color:var(--green-bd)}
.mc.fail{background:var(--red-bg);border-color:rgba(220,38,38,.3);border-left-color:var(--red-bd)}
.mc.na{background:var(--na-bg);border-color:rgba(90,100,120,.3);border-left-color:var(--na-bd)}
.mc-lbl{font-size:11px;color:var(--muted);margin-bottom:3px}
.mc-val{font-family:var(--mono);font-size:17px;font-weight:700}
.mc.pass .mc-val{color:var(--green)}
.mc.fail .mc-val{color:var(--red)}
.mc.na .mc-val{color:var(--muted)}
.mc-thr{font-size:10px;color:var(--muted);margin-top:2px}

/* Card sections */
.csec{margin-bottom:18px;padding-top:14px;border-top:1px solid var(--border)}
.qgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.qi label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:3px}
.qi .val{font-size:13px;color:var(--text)}
.moat-b{display:inline-block;padding:2px 9px;border-radius:4px;font-size:12px;font-weight:600;background:rgba(74,144,217,.1);color:var(--blue);border:1px solid rgba(74,144,217,.3)}
.pq{border-left:2px solid var(--na-bd);padding:7px 11px;background:rgba(255,255,255,.02);border-radius:0 4px 4px 0;font-style:italic;font-size:13px;color:var(--muted);margin-top:8px}

/* Risk */
.risk-row{display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start}
.ytp{text-align:center;min-width:90px}
.ytp-num{font-family:var(--mono);font-size:34px;font-weight:700}
.ytp-num.low{color:var(--green)}
.ytp-num.high{color:var(--red)}
.ytp-lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;line-height:1.3}
.risk-items{display:flex;flex-direction:column;gap:7px}
.ri{padding:9px 13px;background:rgba(255,255,255,.02);border-radius:6px;border:1px solid var(--border)}
.ri-title{font-size:13px;font-weight:600;color:var(--text)}
.ri-desc{font-size:12px;color:var(--muted);margin-top:2px}
.sev{display:inline-block;padding:1px 7px;border-radius:3px;font-size:10px;font-weight:600;margin-left:7px;font-family:var(--mono)}
.sev-Low{background:var(--green-bg);color:var(--green);border:1px solid var(--green-bd)}
.sev-Medium{background:var(--yellow-bg);color:var(--yellow);border:1px solid var(--yellow-bd)}
.sev-High{background:var(--red-bg);color:var(--red);border:1px solid var(--red-bd)}

/* Valuation */
.vgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:11px}
.vi{text-align:center;padding:13px;background:rgba(255,255,255,.02);border-radius:6px;border:1px solid var(--border)}
.vi-lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.vi-num{font-family:var(--mono);font-size:20px;font-weight:700;color:var(--text)}
.vi-num.prem{color:var(--red)}
.vi-num.disc{color:var(--green)}

@media(max-width:680px){
  .g4{grid-template-columns:repeat(2,1fr)}
  .qgrid,.vgrid{grid-template-columns:1fr}
  .risk-row{grid-template-columns:1fr}
}
</style>
</head>
<body>
<header>
  <div class="h-title">STOCKS DASHBOARD</div>
  <div class="h-meta">
    <span><span class="dot" id="dot"></span><span id="conn">Connecting...</span></span>
    <span id="updated"></span>
  </div>
</header>
<main>
  <div id="prog" style="display:none"></div>
  <div id="lb" style="display:none"></div>
  <div id="tickers"></div>
</main>
<script>
'use strict';

function esc(s){
  if(s==null)return'';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function verdictCls(v){
  return v?'badge v-'+v.trim().replace(/\s+/g,'-').toUpperCase():'badge';
}

function badge(v){
  if(!v)return'';
  return`<span class="${verdictCls(v)}">${esc(v)}</span>`;
}

function mc(m){
  const cls=m.pass_fail==='PASS'?'pass':m.pass_fail==='FAIL'?'fail':'na';
  return`<div class="mc ${cls}"><div class="mc-lbl">${esc(m.label)}</div><div class="mc-val">${esc(m.display_value)}</div><div class="mc-thr">${esc(m.threshold_label)}</div></div>`;
}

// ── Progress ──────────────────────────────────────────────────────────────

function renderProgress(data){
  const el=document.getElementById('prog');
  if(!data||!data.steps){el.style.display='none';return;}
  const allDone=data.steps.every(s=>s.status==='done'||s.status==='skipped');
  if(allDone){el.style.display='none';return;}
  el.style.display='block';
  const stepsHtml=data.steps.map(s=>{
    let ico;
    if(s.status==='done')     ico=`<span style="color:var(--green)">✓</span>`;
    else if(s.status==='running') ico=`<span class="spin"></span>`;
    else if(s.status==='skipped') ico=`<span style="color:var(--muted)">—</span>`;
    else                          ico=`<span style="color:var(--muted)">·</span>`;
    return`<div class="step ${s.status}"><div class="step-ico">${ico}</div><div class="step-lbl">${esc(s.label)}</div>${s.ts?`<div class="step-ts">${esc(s.ts)}</div>`:''}</div>`;
  }).join('');
  el.innerHTML=`<div class="prog-hdr"><div class="prog-ticker">${esc(data.ticker)}</div><div class="prog-lbl">Analysis in progress…</div></div><div class="steps">${stepsHtml}</div>`;
}

// ── Leaderboard ───────────────────────────────────────────────────────────

function renderLeaderboard(tickers){
  const el=document.getElementById('lb');
  const withFinal=tickers.filter(t=>t.final);
  if(withFinal.length<2){el.style.display='none';return;}
  const rows=[...withFinal].sort((a,b)=>(b.final.scores?.overall||0)-(a.final.scores?.overall||0));
  el.style.display='block';
  el.innerHTML=`<div class="sec-ttl">Leaderboard</div>
  <table class="lb"><thead><tr>
    <th>#</th><th>Ticker</th><th>Company</th><th>Verdict</th>
    <th>Score</th><th>Big 4</th><th>Moat</th><th>Valuation</th><th>Debt</th>
  </tr></thead><tbody>${rows.map((t,i)=>{
    const f=t.final,s=f.summary||{};
    return`<tr>
      <td class="lb-rank">${i+1}</td>
      <td><a href="#t-${esc(t.ticker)}" class="lb-ticker">${esc(t.ticker)}</a></td>
      <td style="color:var(--muted);font-size:13px">${esc(f.company_name||'')}</td>
      <td>${badge(f.verdict)}</td>
      <td style="font-family:var(--mono);font-weight:700">${f.scores?.overall??'—'}</td>
      <td style="font-family:var(--mono)">${s.big4_pass_count??'—'}/4</td>
      <td>${s.moat_type?`<span class="moat-b">${esc(s.moat_type)}</span>`:'—'}</td>
      <td>${s.valuation_stance||'—'}</td>
      <td>${s.debt_risk?`<span class="sev sev-${esc(s.debt_risk)}">${esc(s.debt_risk)}</span>`:'—'}</td>
    </tr>`;
  }).join('')}</tbody></table>`;
}

// ── Ticker cards ──────────────────────────────────────────────────────────

function renderCard(t){
  const q=t.quant||{},qual=t.qualitative||{},f=t.final||{};
  const verdict=f.verdict||q.verdict||null;
  const score=f.scores?.overall;
  const company=f.company_name||q.company_name||t.ticker;
  const price=q.current_price?` · $${q.current_price}`:'';

  let h=`<div class="tcard" id="t-${esc(t.ticker)}">
    <div class="card-hdr">
      <div>
        <div class="card-sym">${esc(t.ticker)}</div>
        <div class="card-name">${esc(company)}</div>
        <div class="card-meta">${esc(q.sector||'')}${price} · ${esc(q.analysis_date||f.analysis_date||'')}</div>
      </div>
      <div class="card-rhs">
        ${score!=null?`<div class="card-score">${score}<span style="font-size:14px;color:var(--muted)">/10</span></div><div class="card-score-lbl">Score</div>`:''}
        ${verdict?badge(verdict):''}
      </div>
    </div>`;

  if(f.elevator_pitch)
    h+=`<div class="pitch">${esc(f.elevator_pitch)}</div>`;

  if(q.big4?.length){
    h+=`<div class="slbl">Big 4 Metrics</div><div class="g4">${q.big4.map(mc).join('')}</div>`;
  }
  if(q.supporting?.length){
    h+=`<div class="slbl">Supporting Metrics</div><div class="g3">${q.supporting.map(mc).join('')}</div>`;
  }

  if(t.has_qualitative&&qual.moat){
    const coc=qual.circle_of_competence||{},moat=qual.moat||{};
    h+=`<div class="csec">
      <div class="slbl">Qualitative Analysis</div>
      <div class="qgrid">
        <div class="qi"><label>Revenue Model</label><div class="val">${esc(coc.revenue_model||'')}</div></div>
        <div class="qi"><label>Complexity</label><div class="val">${esc(coc.complexity||'')}</div></div>
        <div class="qi"><label>Moat</label><div class="val"><span class="moat-b">${esc(moat.type||'')}</span>${moat.strength?` <span style="color:var(--muted);font-size:12px">${esc(moat.strength)}</span>`:''}</div></div>
        <div class="qi"><label>Assessment</label><div class="val" style="font-size:12px;color:var(--muted)">${esc(qual.overall_assessment||'')}</div></div>
      </div>
      ${moat.pricing_power_quote?`<div class="pq">"${esc(moat.pricing_power_quote)}"<span style="font-size:11px"> — ${esc(moat.pricing_power_source||'')}</span></div>`:''}
    </div>`;
  }

  if(t.has_qualitative&&qual.risks){
    const r=qual.risks||{},lvl=r.debt_risk_level||'Low';
    h+=`<div class="csec">
      <div class="slbl">Risk Assessment</div>
      <div class="risk-row">
        <div class="ytp">
          <div class="ytp-num ${lvl==='High'?'high':'low'}">${r.years_to_payoff??'—'}</div>
          <div class="ytp-lbl">Years to<br>Payoff</div>
          <div style="margin-top:6px"><span class="sev sev-${esc(lvl)}">${esc(lvl)} Risk</span></div>
        </div>
        <div class="risk-items">${(r.top_risks||[]).map(ri=>`
          <div class="ri">
            <div class="ri-title">${esc(ri.title)}<span class="sev sev-${esc(ri.severity)}">${esc(ri.severity)}</span></div>
            <div class="ri-desc">${esc(ri.description||'')}</div>
          </div>`).join('')}
        </div>
      </div>
    </div>`;
  }

  if(t.has_qualitative&&qual.valuation){
    const v=qual.valuation,disc=v.premium_discount_label==='Discount';
    h+=`<div class="csec">
      <div class="slbl">Valuation</div>
      <div class="vgrid">
        <div class="vi"><div class="vi-lbl">Current P/E</div><div class="vi-num">${v.current_pe!=null?v.current_pe+'x':'N/A'}</div></div>
        <div class="vi"><div class="vi-lbl">5-Year Avg P/E</div><div class="vi-num">${v.historical_avg_pe!=null?v.historical_avg_pe+'x':'N/A'}</div></div>
        <div class="vi"><div class="vi-lbl">${esc(v.premium_discount_label||'')}</div><div class="vi-num ${disc?'disc':'prem'}">${v.premium_discount_pct!=null?v.premium_discount_pct+'%':'N/A'}</div></div>
      </div>
      ${v.valuation_context?`<div style="font-size:12px;color:var(--muted);margin-top:9px">${esc(v.valuation_context)}</div>`:''}
    </div>`;
  }

  if(f.verdict_reasoning){
    h+=`<div class="csec">
      <div class="slbl">Verdict</div>
      <div style="font-size:13px;color:var(--muted);margin-bottom:7px">${esc(f.verdict_reasoning)}</div>
      ${f.target_entry_note?`<div style="font-size:12px;color:var(--blue)">${esc(f.target_entry_note)}</div>`:''}
    </div>`;
  }

  return h+'</div>';
}

// ── Dashboard ─────────────────────────────────────────────────────────────

function renderDashboard(data){
  const tickers=data.tickers||[];
  const el=document.getElementById('tickers');
  if(!tickers.length){
    el.innerHTML=`<div class="empty"><h2>No analyses yet</h2><p style="margin-top:8px">Run <code>/analyze AAPL</code> in Claude Code to get started.</p></div>`;
    document.getElementById('lb').style.display='none';
    return;
  }
  renderLeaderboard(tickers);
  el.innerHTML=tickers.map(renderCard).join('');
}

function setUpdated(){
  document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────

async function loadReports(){
  try{
    const r=await fetch('/api/reports');
    const d=await r.json();
    renderDashboard(d);
    setUpdated();
  }catch(e){console.error('load reports:',e);}
}

function connectSSE(){
  const dot=document.getElementById('dot'),conn=document.getElementById('conn');
  const es=new EventSource('/api/progress');
  es.onopen=()=>{dot.className='dot live';conn.textContent='Live';};
  es.onmessage=(e)=>{
    const d=JSON.parse(e.data);
    if(d.type==='connected')return;
    renderProgress(d);
    const done=(d.steps||[]).every(s=>s.status==='done'||s.status==='skipped');
    if(done)setTimeout(loadReports,1000);
  };
  es.onerror=()=>{
    dot.className='dot err';conn.textContent='Reconnecting…';
    es.close();setTimeout(connectSSE,3000);
  };
}

document.addEventListener('DOMContentLoaded',()=>{
  loadReports();
  connectSSE();
  setInterval(loadReports,60000);
});
</script>
</body>
</html>"""


if __name__ == "__main__":
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
