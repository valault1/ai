"""FastAPI router for stocks-specific dashboard endpoints.

Mounted at /api/stocks by infra/server.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

REPORTS_DIR = Path(__file__).parent / "reports"

router = APIRouter()


def _discover_tickers() -> list[str]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(
        d.name for d in REPORTS_DIR.iterdir()
        if d.is_dir() and (d / f"{d.name}_quant.json").exists()
    )


def _load_ticker(ticker: str) -> dict:
    base = REPORTS_DIR / ticker

    def _load(path: Path):
        try:
            return json.loads(path.read_text()) if path.exists() else None
        except Exception:
            return None

    quant = _load(base / f"{ticker}_quant.json")
    qualitative = _load(base / f"{ticker}_qualitative.json")
    final = _load(base / f"{ticker}_final.json")

    return {
        "ticker": ticker,
        "quant": quant,
        "qualitative": qualitative,
        "final": final,
        "has_quant": quant is not None,
        "has_qualitative": qualitative is not None,
        "has_final": final is not None,
    }


@router.get("/reports")
def reports():
    tickers = _discover_tickers()
    data = [_load_ticker(t) for t in tickers]
    return JSONResponse({"tickers": data, "count": len(data)})
