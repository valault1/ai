# infra — Shared Pipeline Infrastructure

Shared backend and frontend for running multi-step AI pipelines across projects.
Currently hosts the stocks analysis pipeline; designed to grow as new projects are added.

## Architecture

```
infra/
├── pipeline.py      # Base classes: Pipeline, ScriptStep, LLMStep
├── runner.py        # Async execution engine; manages run state + SSE events
├── server.py        # FastAPI app: API endpoints + static file serving
├── runs/            # Runtime state (gitignored) — one directory per run
└── ui/              # Frontend: index.html + app.js + styles.css
```

Each project defines its pipeline in a `pipeline.py` file in its own subdirectory
(e.g. `stocks/pipeline.py`), then registers it in `infra/server.py`.

## Core concepts

### Pipeline
A named sequence of steps triggered with a dict of params (e.g. `{"ticker": "AAPL"}`).

```python
Pipeline(
    id="stocks/analyze",
    name="Stock Analysis",
    params=["ticker"],
    steps=[QuantScreen(), SecFetch(), ValuationFetch(), QualitativeAnalysis(), FinalVerdict()],
)
```

### ScriptStep
A deterministic step that runs Python/shell logic. Subclass and implement `run()`:

```python
class QuantScreen(ScriptStep):
    id = "quant"
    name = "Quantitative Screen"

    def run(self, params: dict, context: dict) -> dict:
        # context holds outputs of all prior steps keyed by step id
        result = subprocess.run(...)
        return json.loads(output_file.read_text())
```

### LLMStep
A step that calls the Claude API. Subclass and implement `build_messages()`:

```python
class QualitativeAnalysis(LLMStep):
    id = "qualitative"
    name = "Qualitative Analysis"
    output_schema = QUALITATIVE_SCHEMA   # JSON Schema → uses tool_use for structured output

    def build_messages(self, params: dict, context: dict) -> list[dict]:
        # Build and return an Anthropic messages array
        return [{"role": "user", "content": f"Analyze {params['ticker']}..."}]

    def post_run(self, params, context, output):
        # Optional: called after runner saves step output; write canonical files here
        Path(f"reports/{params['ticker']}_qualitative.json").write_text(json.dumps(output))
```

Additional hooks (all optional):
- `should_skip(params, context) -> bool` — return True to skip the step
- `on_skip(params, context)` — called when skipped; use for fallback file writes
- `post_run(params, context, output)` — called after a successful LLM step

### Run state
Each run gets a unique ID (`YYYYMMDD-HHMMSS-xxxxxx`) and a directory under `infra/runs/`:

```
infra/runs/{run_id}/
    state.json            # run metadata + per-step status
    {step_id}/
        output.json       # step output dict
```

Step statuses: `pending` → `running` → `done` / `failed` / `skipped`

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pipelines` | List registered pipelines |
| POST | `/api/runs` | Start a run: `{"pipeline_id": "...", "params": {...}}` → `{"run_id": "..."}` |
| GET | `/api/runs` | List all runs (newest first) |
| GET | `/api/runs/{id}` | Get run state |
| GET | `/api/runs/{id}/stream` | SSE stream of step updates |
| GET | `/api/runs/{id}/steps/{step_id}` | Get step output JSON |
| GET | `/api/stocks/reports` | Stocks-specific: all ticker report data |

## Running the server

**Dependencies** (install once from the repo root):
```bash
pip install -r stocks/requirements.txt
```

**Development:**
```bash
cd /home/val/ai
PYTHONPATH=/home/val/ai python3 infra/server.py
```

**Production (systemd):**
```bash
mkdir -p ~/.config/systemd/user
cp infra/systemd/infra-server.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now infra-server
```

After any changes to `infra/server.py` or Python files:
```bash
systemctl --user restart infra-server
```

After any changes to `infra/ui/` (HTML/JS/CSS):
- Just refresh the browser — static files are read from disk on each request.

Check logs:
```bash
journalctl --user -u infra-server -f
```

Get the Tailscale URL:
```bash
python3 -c "
import subprocess, json
r = subprocess.run(['tailscale','status','--json'], capture_output=True, text=True)
d = json.loads(r.stdout)
h = d.get('Self',{}).get('DNSName','').rstrip('.')
print(f'http://{h}:7842' if h else 'http://localhost:7842')
"
```

## Adding a new project

1. Create `newproject/pipeline.py` with a `PIPELINE = Pipeline(...)` definition
2. In `infra/server.py`, add one import and add it to `_ALL_PIPELINES`:
   ```python
   from newproject.pipeline import PIPELINE as NEWPROJECT_PIPELINE
   _ALL_PIPELINES = [STOCKS_PIPELINE, NEWPROJECT_PIPELINE]
   ```
3. Restart the server.

The UI auto-discovers all registered pipelines — no frontend changes needed.

## Migrated from

`stocks/scripts/server.py` — the old single-file FastAPI server with embedded HTML.
That file is kept for reference but is no longer the active server.
The old systemd service (`stocks-dashboard.service`) is replaced by `infra-server.service`.
