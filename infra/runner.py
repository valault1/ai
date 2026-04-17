from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

import anthropic

from infra.pipeline import LLMStep, ScriptStep

RUNS_DIR = Path(__file__).parent / "runs"

_anthropic_client: anthropic.Anthropic | None = None


def _client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


# ── SSE event bus ─────────────────────────────────────────────────────────────

_subscribers: dict[str, list[asyncio.Queue]] = {}


def subscribe(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(run_id, []).append(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(run_id, [])
    if q in subs:
        subs.remove(q)


def _broadcast(run_id: str, event: dict) -> None:
    for q in list(_subscribers.get(run_id, [])):
        q.put_nowait(event)


# ── State helpers ─────────────────────────────────────────────────────────────

class RunNotFound(Exception):
    pass


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def read_state(run_id: str) -> dict:
    p = _run_dir(run_id) / "state.json"
    if not p.exists():
        raise RunNotFound(run_id)
    return json.loads(p.read_text())


def _write_state(run_id: str, state: dict) -> None:
    p = _run_dir(run_id) / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.rename(p)


def _update_step(run_id: str, step_id: str, **kwargs) -> None:
    state = read_state(run_id)
    for s in state["steps"]:
        if s["id"] == step_id:
            s.update(kwargs)
            break
    _write_state(run_id, state)
    _broadcast(run_id, {"type": "step_update", "step_id": step_id, **kwargs})


def _write_step_output(run_id: str, step_id: str, output: dict) -> None:
    out_dir = _run_dir(run_id) / step_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "output.json").write_text(json.dumps(output, indent=2, default=str))


def list_runs() -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    runs = []
    for d in sorted(RUNS_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        sf = d / "state.json"
        if sf.exists():
            try:
                runs.append(json.loads(sf.read_text()))
            except Exception:
                pass
    return runs


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_claude_sync(step: LLMStep, messages: list[dict]) -> dict:
    if step.output_schema:
        tools = [{
            "name": "structured_output",
            "description": "Output the result in the required structured form.",
            "input_schema": step.output_schema,
        }]
        response = _client().messages.create(
            model=step.model,
            max_tokens=4096,
            tools=tools,
            tool_choice={"type": "tool", "name": "structured_output"},
            messages=messages,
        )
        for block in response.content:
            if hasattr(block, "input"):
                return block.input
        raise RuntimeError("LLM did not return structured_output tool use")
    else:
        response = _client().messages.create(
            model=step.model,
            max_tokens=4096,
            messages=messages,
        )
        return {"content": response.content[0].text}


# ── Pipeline execution ────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


async def start_run(pipeline, params: dict) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{ts}-{uuid.uuid4().hex[:6]}"

    state = {
        "run_id": run_id,
        "pipeline_id": pipeline.id,
        "pipeline_name": pipeline.name,
        "params": params,
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "steps": [
            {
                "id": s.id,
                "name": s.name,
                "status": "pending",
                "started_at": None,
                "finished_at": None,
            }
            for s in pipeline.steps
        ],
    }
    _write_state(run_id, state)
    asyncio.create_task(_execute_run(run_id, pipeline, params))
    return run_id


async def _execute_run(run_id: str, pipeline, params: dict) -> None:
    context: dict = {}

    for step in pipeline.steps:
        if step.should_skip(params, context):
            _update_step(run_id, step.id, status="skipped")
            try:
                step.on_skip(params, context)
            except Exception:
                pass
            continue

        _update_step(run_id, step.id, status="running", started_at=_now())

        try:
            if isinstance(step, ScriptStep):
                output = await asyncio.to_thread(step.run, params, context)
            else:
                messages = step.build_messages(params, context)
                output = await asyncio.to_thread(_call_claude_sync, step, messages)
                try:
                    step.post_run(params, context, output)
                except Exception:
                    pass
        except Exception as exc:
            _update_step(run_id, step.id,
                         status="failed", finished_at=_now(), error=str(exc))
            state = read_state(run_id)
            _write_state(run_id, {**state, "status": "failed", "finished_at": _now()})
            _broadcast(run_id, {"type": "run_failed", "error": str(exc)})
            return

        context[step.id] = output
        _write_step_output(run_id, step.id, output)
        _update_step(run_id, step.id, status="done", finished_at=_now())

    state = read_state(run_id)
    _write_state(run_id, {**state, "status": "done", "finished_at": _now()})
    _broadcast(run_id, {"type": "run_complete"})
