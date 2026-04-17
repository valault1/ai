"""Infra pipeline server.

Serves the UI and exposes the run management API. All projects register
their pipelines here. Runs on port 7842, accessible over Tailscale.

After any changes:
    systemctl --user restart infra-server
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from infra import runner
from stocks.dashboard import router as stocks_router
from stocks.pipeline import PIPELINE as STOCKS_PIPELINE

# ── Pipeline registry ─────────────────────────────────────────────────────────
# To add a new project: import its PIPELINE and add it to this list.

_ALL_PIPELINES = [STOCKS_PIPELINE]
REGISTRY: dict[str, object] = {p.id: p for p in _ALL_PIPELINES}

# ── App setup ─────────────────────────────────────────────────────────────────

UI_DIR = Path(__file__).parent / "ui"
PORT = 7842

app = FastAPI(title="AI Pipelines")
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")
app.include_router(stocks_router, prefix="/api/stocks")


# ── Pipeline endpoints ────────────────────────────────────────────────────────

@app.get("/api/pipelines")
def list_pipelines():
    return JSONResponse([
        {"id": p.id, "name": p.name, "params": p.params}
        for p in REGISTRY.values()
    ])


# ── Run endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/runs")
async def create_run(body: dict):
    pipeline_id = body.get("pipeline_id")
    params = body.get("params", {})
    if pipeline_id not in REGISTRY:
        raise HTTPException(404, f"Pipeline {pipeline_id!r} not found")
    run_id = await runner.start_run(REGISTRY[pipeline_id], params)
    return {"run_id": run_id}


@app.get("/api/runs")
def list_runs():
    return JSONResponse(runner.list_runs())


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    try:
        return JSONResponse(runner.read_state(run_id))
    except runner.RunNotFound:
        raise HTTPException(404)


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    try:
        runner.read_state(run_id)
    except runner.RunNotFound:
        raise HTTPException(404)

    async def generate():
        q = runner.subscribe(run_id)
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event["type"] in ("run_complete", "run_failed"):
                        break
                except asyncio.TimeoutError:
                    yield 'data: {"type":"ping"}\n\n'
        finally:
            runner.unsubscribe(run_id, q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/runs/{run_id}/steps/{step_id}")
def get_step_output(run_id: str, step_id: str):
    out = runner.RUNS_DIR / run_id / step_id / "output.json"
    if not out.exists():
        raise HTTPException(404)
    return JSONResponse(json.loads(out.read_text()))


# ── UI ────────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return HTMLResponse((UI_DIR / "index.html").read_text())


if __name__ == "__main__":
    runner.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
