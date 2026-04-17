Run the full analysis pipeline for: **$ARGUMENTS**

The ticker is `$ARGUMENTS`. Follow every step in order. Do not skip steps.

---

## Setup

```bash
mkdir -p reports/$ARGUMENTS
```

Write the initial progress file. Run this bash command (atomic write via rename):

```bash
python3 - << 'EOF'
import json, os
data = {
  "ticker": "$ARGUMENTS",
  "started_at": __import__('datetime').datetime.now().isoformat(timespec='seconds'),
  "steps": [
    {"id": "quant",     "label": "Quantitative screen",   "status": "pending"},
    {"id": "circle",    "label": "Circle of competence",  "status": "pending"},
    {"id": "moat",      "label": "Moat assessment",        "status": "pending"},
    {"id": "risks",     "label": "Risk assessment",        "status": "pending"},
    {"id": "valuation", "label": "Valuation context",      "status": "pending"},
    {"id": "verdict",   "label": "Final verdict",          "status": "pending"}
  ]
}
with open("reports/.progress.json.tmp", "w") as f:
    json.dump(data, f)
os.rename("reports/.progress.json.tmp", "reports/.progress.json")
EOF
```

---

## Step 1 — Quantitative Screen

Mark `quant` as running (update progress file: set `quant` status to `"running"`).

```bash
python3 scripts/quant_screen.py $ARGUMENTS --output-dir reports/$ARGUMENTS/
```

Read `reports/$ARGUMENTS/$ARGUMENTS_quant.json`. Mark `quant` as `"done"` with current time in `ts` field.

**If `quant_gate` is `"HALT"`:**
- Mark all remaining steps `"skipped"` in the progress file
- Write a minimal `reports/$ARGUMENTS/$ARGUMENTS_final.json` using the HALT template from `processes/03-final-verdict.md`
- Tell the user the stock failed the quant screen and skip to the **Completion** section

---

## Step 2 — Circle of Competence

Mark `circle` as `"running"` in the progress file.

```bash
python3 scripts/sec_fetcher.py $ARGUMENTS --section 1 --output-dir reports/$ARGUMENTS/
```

Follow sub-step 2.1 from `processes/02-qualitative-analysis.md`. Mark `circle` as `"done"`.

---

## Step 3 — Moat Assessment

Mark `moat` as `"running"` in the progress file.

```bash
python3 scripts/sec_fetcher.py $ARGUMENTS --section 7 --output-dir reports/$ARGUMENTS/
```

Follow sub-step 2.2 from `processes/02-qualitative-analysis.md`. Mark `moat` as `"done"`.

---

## Step 4 — Risk Assessment

Mark `risks` as `"running"` in the progress file.

```bash
python3 scripts/sec_fetcher.py $ARGUMENTS --section 1A --output-dir reports/$ARGUMENTS/
```

Follow sub-step 2.3 from `processes/02-qualitative-analysis.md`. Mark `risks` as `"done"`.

---

## Step 5 — Valuation Context

Mark `valuation` as `"running"` in the progress file.

```bash
python3 scripts/valuation.py $ARGUMENTS
```

Follow sub-step 2.4 from `processes/02-qualitative-analysis.md`.

Now write the complete qualitative output files:
- `reports/$ARGUMENTS/$ARGUMENTS_qualitative.json` (full schema from process 02)
- `reports/$ARGUMENTS/$ARGUMENTS_qualitative.md`

Mark `valuation` as `"done"`.

---

## Step 6 — Final Verdict

Mark `verdict` as `"running"` in the progress file.

Follow `processes/03-final-verdict.md` to synthesize the verdict. Write:
- `reports/$ARGUMENTS/$ARGUMENTS_final.json`
- `reports/$ARGUMENTS/$ARGUMENTS_final.md`

Mark `verdict` as `"done"`.

---

## How to update the progress file

At each step transition, run a bash command like this (replace the JSON content as needed):

```bash
python3 - << 'PYEOF'
import json, os
with open("reports/.progress.json") as f:
    data = json.load(f)
# Update the step you just completed or started:
for s in data["steps"]:
    if s["id"] == "STEP_ID":
        s["status"] = "done"   # or "running" or "skipped"
        s["ts"] = __import__('datetime').datetime.now().strftime("%H:%M:%S")
with open("reports/.progress.json.tmp", "w") as f:
    json.dump(data, f)
os.rename("reports/.progress.json.tmp", "reports/.progress.json")
PYEOF
```

---

## Completion

Get the Tailscale dashboard URL:

```bash
python3 -c "
import subprocess, json
r = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True)
d = json.loads(r.stdout)
h = d.get('Self', {}).get('DNSName', '').rstrip('.')
print(f'http://{h}:7842' if h else 'http://localhost:7842')
"
```

Open the URL in the browser:
```bash
xdg-open <URL from above>
```

Present a final summary to the user:
- Verdict (with emoji: 🟢 STRONG BUY, 🟡 WATCHLIST, 🔴 PASS, 🔵 MORE RESEARCH)
- Overall score
- Elevator pitch
- Path to the final report: `reports/$ARGUMENTS/$ARGUMENTS_final.md`
