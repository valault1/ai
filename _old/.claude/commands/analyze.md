Run the full analysis pipeline for: **$ARGUMENTS**

**If `$ARGUMENTS` is blank or missing**, stop immediately and tell the user: "Please provide a ticker symbol, e.g. `/analyze AAPL`"

The ticker is `$ARGUMENTS` (uppercase it if lowercase was given). All bash commands run from `/home/val/ai/stocks`. Do not skip any steps.

---

## Setup

```bash
mkdir -p /home/val/ai/stocks/reports/$ARGUMENTS
```

Write the initial progress file (atomic write via rename):

```bash
python3 - << 'EOF'
import json, os, datetime
data = {
  "ticker": "$ARGUMENTS",
  "started_at": datetime.datetime.now().isoformat(timespec='seconds'),
  "steps": [
    {"id": "quant",     "label": "Quantitative screen",   "status": "pending"},
    {"id": "circle",    "label": "Circle of competence",  "status": "pending"},
    {"id": "moat",      "label": "Moat assessment",        "status": "pending"},
    {"id": "risks",     "label": "Risk assessment",        "status": "pending"},
    {"id": "valuation", "label": "Valuation context",      "status": "pending"},
    {"id": "verdict",   "label": "Final verdict",          "status": "pending"}
  ]
}
with open("/home/val/ai/stocks/reports/.progress.json.tmp", "w") as f:
    json.dump(data, f)
os.rename("/home/val/ai/stocks/reports/.progress.json.tmp", "/home/val/ai/stocks/reports/.progress.json")
EOF
```

---

## How to update the progress file

At each step transition, run a snippet like this (replacing STEP_ID and STATUS):

```bash
python3 - << 'EOF'
import json, os, datetime
with open("/home/val/ai/stocks/reports/.progress.json") as f:
    data = json.load(f)
for s in data["steps"]:
    if s["id"] == "STEP_ID":
        s["status"] = "STATUS"   # "running", "done", or "skipped"
        s["ts"] = datetime.datetime.now().strftime("%H:%M:%S")
with open("/home/val/ai/stocks/reports/.progress.json.tmp", "w") as f:
    json.dump(data, f)
os.rename("/home/val/ai/stocks/reports/.progress.json.tmp", "/home/val/ai/stocks/reports/.progress.json")
EOF
```

---

## Step 1 — Quantitative Screen

Mark `quant` as `"running"`, then:

```bash
cd /home/val/ai/stocks && python3 scripts/quant_screen.py $ARGUMENTS --output-dir reports/$ARGUMENTS/
```

Read `stocks/reports/$ARGUMENTS/$ARGUMENTS_quant.json`. Mark `quant` as `"done"`.

**If `quant_gate` is `"HALT"`:**
- Mark all remaining steps `"skipped"` in the progress file
- Write a minimal `/home/val/ai/stocks/reports/$ARGUMENTS/$ARGUMENTS_final.json` using the HALT template from `stocks/processes/03-final-verdict.md`
- Tell the user the stock failed the quant screen, then skip to the **Completion** section

---

## Step 2 — Circle of Competence

Mark `circle` as `"running"`, then:

```bash
cd /home/val/ai/stocks && python3 scripts/sec_fetcher.py $ARGUMENTS --section 1 --output-dir reports/$ARGUMENTS/
```

Follow sub-step 2.1 from `stocks/processes/02-qualitative-analysis.md`. Mark `circle` as `"done"`.

---

## Step 3 — Moat Assessment

Mark `moat` as `"running"`, then:

```bash
cd /home/val/ai/stocks && python3 scripts/sec_fetcher.py $ARGUMENTS --section 7 --output-dir reports/$ARGUMENTS/
```

Follow sub-step 2.2 from `stocks/processes/02-qualitative-analysis.md`. Mark `moat` as `"done"`.

---

## Step 4 — Risk Assessment

Mark `risks` as `"running"`, then:

```bash
cd /home/val/ai/stocks && python3 scripts/sec_fetcher.py $ARGUMENTS --section 1A --output-dir reports/$ARGUMENTS/
```

Follow sub-step 2.3 from `stocks/processes/02-qualitative-analysis.md`. Mark `risks` as `"done"`.

---

## Step 5 — Valuation Context

Mark `valuation` as `"running"`, then:

```bash
cd /home/val/ai/stocks && python3 scripts/valuation.py $ARGUMENTS
```

Follow sub-step 2.4 from `stocks/processes/02-qualitative-analysis.md`.

Write the complete qualitative output:
- `/home/val/ai/stocks/reports/$ARGUMENTS/$ARGUMENTS_qualitative.json`
- `/home/val/ai/stocks/reports/$ARGUMENTS/$ARGUMENTS_qualitative.md`

Mark `valuation` as `"done"`.

---

## Step 6 — Final Verdict

Mark `verdict` as `"running"`.

Follow `stocks/processes/03-final-verdict.md` to synthesize the verdict. Write:
- `/home/val/ai/stocks/reports/$ARGUMENTS/$ARGUMENTS_final.json`
- `/home/val/ai/stocks/reports/$ARGUMENTS/$ARGUMENTS_final.md`

Mark `verdict` as `"done"`.

---

## Completion

Open the live dashboard:

```bash
python3 -c "
import subprocess, json
r = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True)
d = json.loads(r.stdout)
h = d.get('Self', {}).get('DNSName', '').rstrip('.')
url = f'http://{h}:7842' if h else 'http://localhost:7842'
print(url)
import webbrowser; webbrowser.open(url)
"
```

Present a final summary to the user:
- Verdict (🟢 STRONG BUY / 🟡 WATCHLIST / 🔴 PASS / 🔵 MORE RESEARCH)
- Overall score
- Elevator pitch
- Path to full report: `stocks/reports/$ARGUMENTS/$ARGUMENTS_final.md`
