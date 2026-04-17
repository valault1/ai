# Stock Analysis System — Implementation Plan

## Overview

The system has four layers: (1) Python scripts for data fetching and computation, (2) process docs that serve as agent instructions, (3) Claude Code slash commands as user entry points, and (4) a persistent live dashboard server accessible over Tailscale.

---

## Directory Structure

```
stocks/
  implementation_plan.md       # This file
  CLAUDE.md                    # Project philosophy, overview, and server instructions
  requirements.txt             # Python dependencies
  scripts/
    quant_screen.py            # Quantitative analysis engine
    sec_fetcher.py             # SEC EDGAR 10-K section fetcher
    valuation.py               # Historical P/E comparison (Phase 3)
    server.py                  # Live dashboard web server (Phase 4)
  systemd/
    stocks-dashboard.service   # systemd user service unit file
  processes/
    01-quantitative-screen.md  # Agent instructions: quant screen
    02-qualitative-analysis.md # Agent instructions: qualitative deep-dive
    03-final-verdict.md        # Agent instructions: final verdict synthesis
  .claude/
    commands/
      screen.md                # /screen {TICKER} — quick quant screen
      analyze.md               # /analyze {TICKER} — full pipeline + open dashboard
      deep-dive.md             # /deep-dive {TICKER} — qualitative only
      compare.md               # /compare AAPL MSFT ... — side-by-side
      dashboard.md             # /dashboard — open live dashboard URL
  reports/
    .progress.json             # Live progress state written during /analyze runs
    {TICKER}/
      {TICKER}_quant.json      # Machine-readable quant results
      {TICKER}_quant.md        # Human-readable quant table
      {TICKER}_qualitative.json # Machine-readable qualitative results (Phase 4)
      {TICKER}_qualitative.md  # Human-readable qualitative assessment
      {TICKER}_final.json      # Machine-readable final verdict (Phase 4)
      {TICKER}_final.md        # Human-readable combined verdict
```

---

## Build Sequence

### Phase 1 — Quant Core (build first; immediate value, minimal deps)

1. `requirements.txt` — write and install deps
2. `scripts/quant_screen.py` — core quantitative engine
3. `processes/01-quantitative-screen.md` — agent instructions for quant
4. `.claude/commands/screen.md` — `/screen AAPL` working end-to-end

**Test with:** `/screen AAPL`, `/screen MSFT`, `/screen BRK-B`

### Phase 2 — SEC Fetcher + Qualitative Framework

5. `scripts/sec_fetcher.py` — 10-K section fetcher from SEC EDGAR
6. `processes/02-qualitative-analysis.md` — agent instructions for qualitative
7. `processes/03-final-verdict.md` — verdict synthesis instructions
8. `.claude/commands/deep-dive.md`

**Test with:** `/deep-dive AAPL`

### Phase 3 — Full Pipeline + Polish

9. `.claude/commands/analyze.md` — orchestrates Phases 1+2 end-to-end
10. `.claude/commands/compare.md` — multi-ticker side-by-side comparison
11. `scripts/valuation.py` — historical P/E comparison (nice-to-have)
12. Update `CLAUDE.md` with full system documentation

**End-to-end test:** `/analyze COST` (Costco is a classic Buffett-style stock)

### Phase 4 — Live Dashboard Server

13. Update `scripts/quant_screen.py` to output the finalized schema (add `company_name`, `sector`, `current_price`, `quant_gate`, `display_value` fields)
14. Update `processes/02-qualitative-analysis.md` to instruct agent to also output `_qualitative.json` and write progress steps to `reports/.progress.json`
15. Update `processes/03-final-verdict.md` to instruct agent to also output `_final.json` and write final progress step
16. `scripts/server.py` — FastAPI app serving the dashboard UI + JSON API + SSE progress stream
17. `systemd/stocks-dashboard.service` — user service unit; install and enable
18. `.claude/commands/analyze.md` — updated to write `.progress.json` at each step; final step opens Tailscale URL
19. `.claude/commands/dashboard.md` — opens the Tailscale dashboard URL in browser

**End-to-end test:** `systemctl --user start stocks-dashboard`, then `/analyze COST` → browser opens live dashboard, steps update in real time

---

## Python Scripts

### `scripts/quant_screen.py`

**Interface:**
```
python3 scripts/quant_screen.py AAPL [--output-dir reports/AAPL/]
```

**Exit codes:** 0 = passed screen, 1 = rejected (>2 Big 4 failures), 2 = error

**Output:** JSON (machine-readable) + markdown table (human-readable)

**Function structure:**
```python
import yfinance as yf
import json, sys, argparse
from datetime import datetime

def fetch_data(ticker: str) -> dict:
    """Fetch info, balance_sheet, financials, cashflow from yfinance."""

def calc_big4(info: dict) -> list[dict]:
    """Calculate ROE, D/E, FCF Yield, P/E.
    Returns list of dicts: {metric, value, threshold, pass_fail}"""

def calc_supporting(info: dict, balance_sheet) -> list[dict]:
    """Calculate Current Ratio, Operating Margin, Shares Outstanding Trend.
    For shares trend: compare most recent 4 columns of balance_sheet."""

def generate_report(ticker, big4, supporting, info) -> dict:
    """Assemble full results with verdict (PASS/FAIL/BORDERLINE).
    Verdict logic: >2 Big 4 fails = FAIL, 0 fails = PASS, else BORDERLINE."""

def format_markdown(report: dict) -> str:
    """Render the report dict as a markdown table + verdict summary."""
```

**Big 4 Metrics:**

| Metric | yfinance source | Threshold | Notes |
|--------|----------------|-----------|-------|
| ROE | `info.get('returnOnEquity')` | >= 0.15 | |
| D/E Ratio | `info.get('debtToEquity') / 100` | < 0.50 | yfinance returns e.g. 150 meaning 1.5x — divide by 100 |
| FCF Yield | `info.get('freeCashflow') / info.get('marketCap')` | >= 0.05 | |
| P/E Ratio | `info.get('trailingPE')` | < 20 | |

**Supporting Metrics:**

| Metric | yfinance source | Threshold |
|--------|----------------|-----------|
| Current Ratio | `info.get('currentRatio')` | > 1.5 |
| Operating Margin | `info.get('operatingMargins')` | > 0.10 |
| Shares Outstanding Trend | `balance_sheet.loc['Ordinary Shares Number']` last 4 cols | Flat or decreasing |

**Decision gate:** If >2 Big 4 metrics fail → verdict = FAIL, halt further analysis.

---

### `scripts/sec_fetcher.py`

**Interface:**
```
python3 scripts/sec_fetcher.py AAPL --section 1 [--section 1A] [--section 7]
```

**Output:** Extracted 10-K section text to stdout or `{TICKER}_10k_section{N}.txt`

**Function structure:**
```python
import requests, re, argparse
from html import unescape

SEC_HEADERS = {
    "User-Agent": "StockAnalysis valault1@gmail.com",
    "Accept-Encoding": "gzip, deflate"
}

def get_cik(ticker: str) -> str:
    """Lookup CIK from ticker using SEC company tickers JSON."""

def get_latest_10k_url(cik: str) -> str:
    """Get URL of most recent 10-K filing from submissions endpoint."""

def fetch_filing_html(url: str) -> str:
    """Download the 10-K HTML document."""

def extract_section(html: str, section: str) -> str:
    """Extract text between Item N header and the next Item header.
    Truncate to ~15000 chars to keep agent context manageable."""
```

**SEC EDGAR endpoints used:**
- CIK lookup: `https://www.sec.gov/files/company_tickers.json`
- Submissions: `https://data.sec.gov/submissions/CIK{cik_padded}.json`
- Section extraction via regex on stripped HTML

---

### `scripts/valuation.py` (Phase 3)

**Purpose:** Compute 5-year historical P/E by combining quarterly EPS from `financials` with 5-year price history from `yf.Ticker.history(period="5y")`.

**Output:** Current P/E, 5-year avg P/E, premium/discount percentage.

---

### `requirements.txt`

```
yfinance>=0.2.36
requests>=2.31.0
beautifulsoup4>=4.12.0
```

---

## Process Docs

### `processes/01-quantitative-screen.md`

Agent instructions for running the quant screen, reading output JSON, applying the decision gate (FAIL = stop, PASS/BORDERLINE = proceed to process 02), and presenting results.

### `processes/02-qualitative-analysis.md`

Agent instructions for all four qualitative steps:

- **2.1 Circle of Competence:** Fetch 10-K Item 1 via `sec_fetcher.py`, summarize revenue model in one sentence, flag "Complex" if >3 steps needed.
- **2.2 Moat Assessment:** Fetch Item 7 (MD&A), classify moat as Brand Power / Switching Costs / Cost Advantage / Network Effect / None, find one pricing power quote.
- **2.3 Risk Assessment:** Fetch Item 1A, identify top 2 material risks, calculate Years to Payoff = Total Debt / avg(FCF 3yr), flag >4 years as High Risk.
- **2.4 Valuation Context:** Compare current P/E to 5-year avg, determine premium/discount, if heavy discount use web search to find why.

**Qualitative report output format:**
```
- Company: {Name} ({TICKER})
- Revenue Model: {one sentence}
- Complexity: Simple / Complex
- Moat Type: {classification}
- Pricing Power Evidence: "{quote}"
- Top Risks: 1. ... 2. ...
- Debt Payoff: {N} years — Low/High Risk
- Valuation: Premium/Discount to historical ({current} vs {avg} P/E)
- Overall Assessment: {2-3 sentences}
```

### `processes/03-final-verdict.md`

Agent instructions for synthesizing a final verdict:

| Verdict | Criteria |
|---------|---------|
| STRONG BUY | All Big 4 pass + clear moat + discount to historical valuation |
| WATCHLIST | Mostly passes but one concern |
| PASS | Failed quant screen OR no moat OR high risk |
| MORE RESEARCH | Borderline on multiple dimensions |

Includes writing a 1-paragraph "elevator pitch" and saving to `{TICKER}_final.md`.

---

## Slash Commands

All files go in `/home/val/ai/stocks/.claude/commands/`.

| Command | File | What it does |
|---------|------|-------------|
| `/screen {TICKER}` | `screen.md` | Runs quant screen only, presents table + 2-sentence assessment |
| `/analyze {TICKER}` | `analyze.md` | Full pipeline: quant → qualitative → verdict → opens live dashboard |
| `/deep-dive {TICKER}` | `deep-dive.md` | Qualitative only (assumes quant already done) |
| `/compare {T1} {T2} ...` | `compare.md` | Side-by-side quant comparison, ranked by quality |
| `/dashboard` | `dashboard.md` | Opens the live Tailscale dashboard URL in browser |

### `/analyze` pipeline (end-to-end)

1. `mkdir -p reports/{TICKER}/`
2. Write initial `.progress.json` (all steps `"pending"`, ticker set)
3. Mark `quant` step `"running"` → run `quant_screen.py` → save `_quant.json` + `_quant.md` → mark `"done"`
4. Check `quant_gate`: if `"HALT"` → mark remaining steps `"skipped"`, write minimal `_final.json` with verdict `"PASS"`, skip to step 9
5. Mark `circle` step `"running"` → run circle-of-competence analysis → mark `"done"`
6. Mark `moat` step `"running"` → run moat assessment → mark `"done"`
7. Mark `risks` step `"running"` → run risk assessment → mark `"done"`
8. Mark `valuation` step `"running"` → run valuation context → save `_qualitative.json` + `_qualitative.md` → mark `"done"`
9. Mark `verdict` step `"running"` → run final verdict per `03-final-verdict.md` → save `_final.json` + `_final.md` → mark `"done"`
10. Open `http://[tailscale-hostname]:7842/` in browser
11. Present summary to user: verdict, score, elevator pitch, file paths

Each `.progress.json` write must be atomic: write to `.progress.json.tmp`, then `os.rename`.

### `/dashboard` command

Opens `http://[tailscale-hostname]:7842/` in the browser. The live server always reflects current state — no regeneration step needed. If the server is not running, tell the user to run `systemctl --user start stocks-dashboard`.

---

## JSON Artifact Schemas

### `{TICKER}_quant.json`

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "analysis_date": "2026-04-15",
  "analysis_type": "quantitative",
  "market_cap": 2850000000000,
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "current_price": 198.50,
  "verdict": "PASS",
  "big4": [
    {
      "metric": "ROE",
      "label": "Return on Equity",
      "value": 0.1712,
      "display_value": "17.1%",
      "threshold": 0.15,
      "threshold_label": ">= 15%",
      "direction": "higher_is_better",
      "pass_fail": "PASS"
    }
    // ...repeat for DE, FCF_YIELD, PE
  ],
  "supporting": [
    {
      "metric": "CURRENT_RATIO",
      "label": "Current Ratio",
      "value": 1.07,
      "display_value": "1.07x",
      "threshold": 1.5,
      "threshold_label": "> 1.5x",
      "pass_fail": "FAIL"
    },
    {
      "metric": "SHARES_TREND",
      "label": "Shares Outstanding",
      "value": null,
      "display_value": "Decreasing",
      "threshold": null,
      "threshold_label": "Flat or decreasing",
      "pass_fail": "PASS",
      "shares_history": [16400000000, 15900000000, 15550000000, 15200000000]
    }
    // ...operating margin
  ],
  "big4_pass_count": 3,
  "big4_fail_count": 1,
  "quant_gate": "PROCEED"
}
```

Notes:
- `pass_fail` is always `"PASS"`, `"FAIL"`, or `"NA"` (when data unavailable — never counts as failure)
- `verdict` is `"PASS"`, `"FAIL"`, or `"BORDERLINE"`
- `quant_gate` is `"PROCEED"` or `"HALT"` — the actionable pipeline decision
- `direction` tells the dashboard whether green = high or green = low

### `{TICKER}_qualitative.json`

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "analysis_date": "2026-04-15",
  "analysis_type": "qualitative",
  "circle_of_competence": {
    "revenue_model": "Sells premium consumer electronics and high-margin services.",
    "complexity": "Simple",
    "complexity_reasoning": "Revenue model can be explained in one step."
  },
  "moat": {
    "type": "Brand Power",
    "strength": "Wide",
    "pricing_power_quote": "We believe our customers choose our products for their superior value.",
    "pricing_power_source": "10-K Item 7, FY2025",
    "moat_evidence": "Apple consistently raises iPhone ASPs while maintaining unit sales."
  },
  "risks": {
    "top_risks": [
      { "rank": 1, "title": "Regulatory & Antitrust", "description": "...", "severity": "Medium" },
      { "rank": 2, "title": "China Supply Chain", "description": "...", "severity": "Medium" }
    ],
    "years_to_payoff": 0.8,
    "years_to_payoff_display": "0.8 years",
    "debt_risk_level": "Low",
    "total_debt": 98000000000,
    "avg_fcf_3yr": 115000000000
  },
  "valuation": {
    "current_pe": 28.5,
    "historical_avg_pe": 25.2,
    "pe_period": "5-year",
    "premium_discount_pct": 13.1,
    "premium_discount_label": "Premium",
    "valuation_context": "Trading at a 13% premium to 5-year average."
  },
  "overall_assessment": "Apple has a wide moat..."
}
```

Notes:
- `moat.type` must be one of: `"Brand Power"`, `"Switching Costs"`, `"Cost Advantage"`, `"Network Effect"`, `"None"`, `"Multiple"`
- `moat.strength` must be one of: `"Wide"`, `"Narrow"`, `"None"`
- `risks.severity` must be one of: `"Low"`, `"Medium"`, `"High"`
- `valuation.premium_discount_label` must be `"Premium"` or `"Discount"`

### `{TICKER}_final.json`

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "analysis_date": "2026-04-15",
  "analysis_type": "final_verdict",
  "verdict": "WATCHLIST",
  "verdict_reasoning": "All Big 4 pass except P/E. Wide moat but trades at 13% premium to historical.",
  "elevator_pitch": "Apple is a wide-moat cash machine. At current prices, it's fairly valued — wait for a pullback.",
  "target_entry_note": "Would revisit below P/E of 22x (~$170 at current earnings).",
  "scores": {
    "business_quality": 9,
    "financial_strength": 8,
    "moat_durability": 9,
    "valuation_attractiveness": 4,
    "overall": 7
  },
  "summary": {
    "quant_verdict": "PASS",
    "big4_pass_count": 3,
    "big4_fail_count": 1,
    "moat_type": "Brand Power",
    "moat_strength": "Wide",
    "debt_risk": "Low",
    "valuation_stance": "Premium",
    "top_risk": "Regulatory & Antitrust"
  }
}
```

Notes:
- `verdict` must be exactly one of: `"STRONG BUY"`, `"WATCHLIST"`, `"PASS"`, `"MORE RESEARCH"`
- `scores` are integers 1–10; `overall` is the leaderboard sort key
- `summary` is a flattened view — the dashboard leaderboard reads this directly without cross-referencing other files

---

## Live Dashboard Server (`scripts/server.py`)

### Overview

A persistent FastAPI app that runs as a systemd user service. The browser connects to it over Tailscale for live updates during analysis and static browsing of completed reports.

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Serves the dashboard single-page app (inline HTML/CSS/JS) |
| `GET /api/reports` | Returns all JSON artifacts from `reports/` — scans subdirs for `*_quant.json`, `*_qualitative.json`, `*_final.json` |
| `GET /api/progress` | Server-Sent Events stream; watches `reports/.progress.json` for changes and pushes updates |

### Function signatures
```python
def discover_tickers(reports_dir: Path) -> list[str]
def load_ticker_data(ticker: str, reports_dir: Path) -> dict
    # Returns: {ticker, quant, qualitative, final, has_quant, has_qualitative, has_final}
def reports_endpoint() -> JSONResponse          # GET /api/reports
async def progress_endpoint() -> EventSourceResponse  # GET /api/progress (SSE)
def index_endpoint() -> HTMLResponse           # GET /
```

### Server-Sent Events protocol

The `/api/progress` endpoint polls `reports/.progress.json` every 500ms. When the file changes (checked via `mtime`), it pushes the new content as a JSON SSE event:

```
data: {"ticker":"AAPL","steps":[{"id":"quant","status":"done"},{"id":"moat","status":"running"},...]}\n\n
```

The browser uses `new EventSource('/api/progress')` and re-renders the progress panel on each event.

### `reports/.progress.json` format

Written atomically (write to `.progress.json.tmp`, then `os.rename`) by slash commands at each step:

```json
{
  "ticker": "AAPL",
  "started_at": "2026-04-15T14:32:00",
  "steps": [
    {"id": "quant",     "label": "Quantitative screen",   "status": "done",    "ts": "14:32:04"},
    {"id": "circle",    "label": "Circle of competence",  "status": "done",    "ts": "14:32:18"},
    {"id": "moat",      "label": "Moat assessment",        "status": "running", "ts": "14:32:31"},
    {"id": "risks",     "label": "Risk assessment",        "status": "pending"},
    {"id": "valuation", "label": "Valuation context",      "status": "pending"},
    {"id": "verdict",   "label": "Final verdict",          "status": "pending"}
  ]
}
```

`status` is one of `"done"`, `"running"`, `"pending"`, `"skipped"` (used when quant gate halts).

### systemd user service (`systemd/stocks-dashboard.service`)

```ini
[Unit]
Description=Stocks Dashboard Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/val/ai/stocks
ExecStart=/usr/bin/python3 scripts/server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

**Install once:**
```bash
mkdir -p ~/.config/systemd/user
cp systemd/stocks-dashboard.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now stocks-dashboard
```

**After any UI changes to `server.py`:**
```bash
systemctl --user restart stocks-dashboard
```

### Port and access

- Server listens on `0.0.0.0:7842`
- Accessible via Tailscale at `http://[tailscale-hostname]:7842/`
- The `/dashboard` slash command opens this URL in the browser

### Visual Design

**Theme:** Dark mode, Bloomberg-terminal inspired. Self-contained HTML — no server, just `file://` in browser.

**Color palette:**
```
Page background:   #0a0e17
Card background:   #131a2b
Border:            #1e2a45
Text primary:      #e1e4ea
Text secondary:    #8892a5
Accent blue:       #4a90d9
```

**Verdict badge colors:**
```
STRONG BUY:    bg #0d3320, text #34d399, border #16a34a
WATCHLIST:     bg #332b0d, text #fbbf24, border #d97706
PASS:          bg #330d0d, text #f87171, border #dc2626
MORE RESEARCH: bg #1a1a33, text #a78bfa, border #7c3aed
```

**Metric card colors:**
```
PASS: bg #0d2e1f, text #34d399, left-border #16a34a
FAIL: bg #2e0d0d, text #f87171, left-border #dc2626
NA:   bg #1a1a22, text #8892a5, left-border #5a6478
```

**Fonts:** Monospace (`SF Mono`, `Cascadia Code`, `Fira Code`, `Consolas`) for data values; system sans-serif for headings and prose.

### Dashboard layout (per ticker card)

1. **Card header** — ticker symbol (large, blue, monospace), company name, analysis date, verdict badge, overall score
2. **Elevator pitch** — italic quote block with left accent border
3. **Big 4 grid** — 4 metric cards in a row (color-coded pass/fail)
4. **Supporting metrics grid** — 3 metric cards
5. **Qualitative section** — moat badge + strength, revenue model, complexity, pricing power blockquote
6. **Risk section** — Years to Payoff (large number) + top 2 risks with severity badges
7. **Valuation section** — current P/E, 5yr avg P/E, premium/discount (green if discount, red if premium)

### Multi-ticker leaderboard

When 2+ tickers are present, a summary table appears at the top with columns:
`#` | `Ticker` | `Company` | `Verdict` | `Score` | `Big 4` | `Moat` | `Valuation` | `Debt Risk`

Rows link down to the individual ticker cards. Sorted by `overall` score descending.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| yfinance fields returning `None` | Handle every field gracefully — display N/A, do not count as failure |
| `debtToEquity` scale issue | Always divide by 100 before comparing to threshold |
| `Ordinary Shares Number` label may vary | Try multiple label variants, fall back gracefully |
| SEC 10-K HTML inconsistency | Regex extraction works for ~80% of filings; agent falls back to WebFetch for the rest |
| yfinance rate limiting on compare | Add 1-second delay between fetches in `/compare` |
| SEC EDGAR User-Agent requirement | All requests must include `User-Agent: StockAnalysis valault1@gmail.com` |
| Corrupt `.progress.json` mid-write | Always write atomically: write to `.progress.json.tmp`, then `os.rename` |
| Dashboard server not running | `/dashboard` command checks and tells user to run `systemctl --user start stocks-dashboard` if unreachable |
