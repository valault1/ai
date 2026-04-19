"""Stocks analysis pipeline.

Defines five steps:
  quant       — runs quant_screen.py (ScriptStep)
  sec_fetch   — runs sec_fetcher.py for sections 1, 1A, 7 (ScriptStep)
  valuation   — runs valuation.py (ScriptStep)
  qualitative — LLM qualitative analysis (LLMStep)
  verdict     — LLM final verdict (LLMStep)
"""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

from infra.pipeline import LLMStep, Pipeline, ScriptStep

STOCKS_DIR = Path(__file__).parent
REPORTS_DIR = STOCKS_DIR / "reports"
PROCESSES_DIR = STOCKS_DIR / "processes"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_halt(context: dict) -> bool:
    return context.get("quant", {}).get("quant_gate") == "HALT"


def _read_process(filename: str) -> str:
    return (PROCESSES_DIR / filename).read_text()


# ── Script steps ──────────────────────────────────────────────────────────────

class QuantScreen(ScriptStep):
    id = "quant"
    name = "Quantitative Screen"

    def run(self, params: dict, context: dict) -> dict:
        ticker = params["ticker"].upper()
        out_dir = REPORTS_DIR / ticker
        out_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["python3", str(STOCKS_DIR / "scripts/quant_screen.py"), ticker,
             "--output-dir", str(out_dir)],
            capture_output=True, text=True, cwd=str(STOCKS_DIR),
        )
        # exit 0 = PROCEED, 1 = HALT, 2 = error
        if result.returncode == 2:
            raise RuntimeError(result.stderr.strip() or "quant_screen.py error")
        output_file = out_dir / f"{ticker}_quant.json"
        if not output_file.exists():
            raise RuntimeError(f"quant_screen.py did not produce {output_file.name}")
        return json.loads(output_file.read_text())


class SecFetch(ScriptStep):
    id = "sec_fetch"
    name = "Fetch SEC Filings"

    def should_skip(self, params: dict, context: dict) -> bool:
        return _is_halt(context)

    def run(self, params: dict, context: dict) -> dict:
        ticker = params["ticker"].upper()
        out_dir = REPORTS_DIR / ticker
        result = subprocess.run(
            ["python3", str(STOCKS_DIR / "scripts/sec_fetcher.py"), ticker,
             "--section", "1", "--section", "1A", "--section", "7",
             "--output-dir", str(out_dir)],
            capture_output=True, text=True, cwd=str(STOCKS_DIR),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "sec_fetcher.py error")
        return {
            "section1":  str(out_dir / f"{ticker}_10k_section1.txt"),
            "section1a": str(out_dir / f"{ticker}_10k_section1A.txt"),
            "section7":  str(out_dir / f"{ticker}_10k_section7.txt"),
        }


class ValuationFetch(ScriptStep):
    id = "valuation"
    name = "Valuation Context"

    def should_skip(self, params: dict, context: dict) -> bool:
        return _is_halt(context)

    def run(self, params: dict, context: dict) -> dict:
        ticker = params["ticker"].upper()
        result = subprocess.run(
            ["python3", str(STOCKS_DIR / "scripts/valuation.py"), ticker],
            capture_output=True, text=True, cwd=str(STOCKS_DIR),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "valuation.py error")
        return json.loads(result.stdout)


# ── JSON schemas ──────────────────────────────────────────────────────────────

_RISK_ITEM = {
    "type": "object",
    "properties": {
        "rank":        {"type": "integer"},
        "title":       {"type": "string"},
        "description": {"type": "string"},
        "severity":    {"type": "string", "enum": ["Low", "Medium", "High"]},
    },
    "required": ["rank", "title", "description", "severity"],
}

QUALITATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker":       {"type": "string"},
        "company_name": {"type": "string"},
        "analysis_date": {"type": "string"},
        "analysis_type": {"type": "string"},
        "circle_of_competence": {
            "type": "object",
            "properties": {
                "revenue_model":        {"type": "string"},
                "complexity":           {"type": "string", "enum": ["Simple", "Complex"]},
                "complexity_reasoning": {"type": "string"},
            },
            "required": ["revenue_model", "complexity", "complexity_reasoning"],
        },
        "moat": {
            "type": "object",
            "properties": {
                "type":                  {"type": "string", "enum": ["Brand Power", "Switching Costs", "Cost Advantage", "Network Effect", "Multiple", "None"]},
                "strength":              {"type": "string", "enum": ["Wide", "Narrow", "None"]},
                "pricing_power_quote":   {"type": "string"},
                "pricing_power_source":  {"type": "string"},
                "moat_evidence":         {"type": "string"},
            },
            "required": ["type", "strength"],
        },
        "risks": {
            "type": "object",
            "properties": {
                "top_risks":              {"type": "array", "items": _RISK_ITEM},
                "years_to_payoff":        {"type": ["number", "null"]},
                "years_to_payoff_display":{"type": "string"},
                "debt_risk_level":        {"type": "string", "enum": ["Low", "High"]},
                "total_debt":             {"type": ["number", "null"]},
                "avg_fcf_3yr":            {"type": ["number", "null"]},
            },
            "required": ["top_risks", "debt_risk_level"],
        },
        "valuation": {
            "type": "object",
            "properties": {
                "current_pe":              {"type": ["number", "null"]},
                "historical_avg_pe":       {"type": ["number", "null"]},
                "pe_period":               {"type": "string"},
                "premium_discount_pct":    {"type": ["number", "null"]},
                "premium_discount_label":  {"type": ["string", "null"], "enum": ["Premium", "Discount", None]},
                "valuation_context":       {"type": "string"},
            },
            "required": ["valuation_context"],
        },
        "overall_assessment": {"type": "string"},
    },
    "required": [
        "ticker", "company_name", "analysis_date", "circle_of_competence",
        "moat", "risks", "valuation", "overall_assessment",
    ],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "ticker":            {"type": "string"},
        "company_name":      {"type": "string"},
        "analysis_date":     {"type": "string"},
        "analysis_type":     {"type": "string"},
        "verdict":           {"type": "string", "enum": ["STRONG BUY", "WATCHLIST", "MORE RESEARCH", "PASS"]},
        "verdict_reasoning": {"type": "string"},
        "elevator_pitch":    {"type": ["string", "null"]},
        "target_entry_note": {"type": ["string", "null"]},
        "scores": {
            "type": ["object", "null"],
            "properties": {
                "business_quality":       {"type": "integer", "minimum": 1, "maximum": 10},
                "financial_strength":     {"type": "integer", "minimum": 1, "maximum": 10},
                "moat_durability":        {"type": "integer", "minimum": 1, "maximum": 10},
                "valuation_attractiveness":{"type": "integer", "minimum": 1, "maximum": 10},
                "overall":                {"type": "integer", "minimum": 1, "maximum": 10},
            },
        },
        "summary": {
            "type": "object",
            "properties": {
                "quant_verdict":    {"type": "string"},
                "big4_pass_count":  {"type": "integer"},
                "big4_fail_count":  {"type": "integer"},
                "moat_type":        {"type": ["string", "null"]},
                "moat_strength":    {"type": ["string", "null"]},
                "debt_risk":        {"type": ["string", "null"]},
                "valuation_stance": {"type": ["string", "null"]},
                "top_risk":         {"type": ["string", "null"]},
            },
            "required": ["quant_verdict", "big4_pass_count", "big4_fail_count"],
        },
    },
    "required": ["ticker", "company_name", "analysis_date", "verdict",
                 "verdict_reasoning", "summary"],
}


# ── LLM steps ─────────────────────────────────────────────────────────────────

class QualitativeAnalysis(LLMStep):
    id = "qualitative"
    name = "Qualitative Analysis"
    output_schema = QUALITATIVE_SCHEMA

    def should_skip(self, params: dict, context: dict) -> bool:
        return _is_halt(context)

    def build_messages(self, params: dict, context: dict) -> list[dict]:
        ticker = params["ticker"].upper()
        quant = context["quant"]
        sec = context["sec_fetch"]
        valuation = context["valuation"]

        section1  = Path(sec["section1"]).read_text(errors="replace")
        section1a = Path(sec["section1a"]).read_text(errors="replace")
        section7  = Path(sec["section7"]).read_text(errors="replace")

        process_doc = _read_process("02-qualitative-analysis.md")

        user = f"""Perform a full qualitative analysis for {ticker}. Today's date is {date.today()}.

## Process instructions
{process_doc}

## Quantitative screen results
```json
{json.dumps(quant, indent=2)}
```

## Valuation data
```json
{json.dumps(valuation, indent=2)}
```

## 10-K Item 1 — Business Description
{section1[:15000]}

## 10-K Item 1A — Risk Factors
{section1a[:15000]}

## 10-K Item 7 — MD&A
{section7[:15000]}

Use the structured_output tool to return your complete analysis. \
Set analysis_date to today's date ({date.today()}) and analysis_type to "qualitative"."""

        return [{"role": "user", "content": user}]

    def post_run(self, params: dict, context: dict, output: dict) -> None:
        ticker = params["ticker"].upper()
        out = REPORTS_DIR / ticker / f"{ticker}_qualitative.json"
        out.write_text(json.dumps(output, indent=2))


class FinalVerdict(LLMStep):
    id = "verdict"
    name = "Final Verdict"
    output_schema = VERDICT_SCHEMA

    def should_skip(self, params: dict, context: dict) -> bool:
        return _is_halt(context)

    def on_skip(self, params: dict, context: dict) -> None:
        """Write a minimal HALT final.json when quant screen failed."""
        ticker = params["ticker"].upper()
        quant = context.get("quant", {})
        big4 = quant.get("big4", [])
        fail_count = sum(1 for m in big4 if m.get("pass_fail") == "FAIL")
        pass_count = len(big4) - fail_count
        minimal = {
            "ticker": ticker,
            "company_name": quant.get("company_name", ticker),
            "analysis_date": str(date.today()),
            "analysis_type": "final_verdict",
            "verdict": "PASS",
            "verdict_reasoning": f"Failed quantitative screen: {fail_count} of 4 Big 4 metrics fail.",
            "elevator_pitch": None,
            "target_entry_note": None,
            "scores": None,
            "summary": {
                "quant_verdict": "FAIL",
                "big4_pass_count": pass_count,
                "big4_fail_count": fail_count,
                "moat_type": None,
                "moat_strength": None,
                "debt_risk": None,
                "valuation_stance": None,
                "top_risk": None,
            },
        }
        out = REPORTS_DIR / ticker / f"{ticker}_final.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(minimal, indent=2))

    def build_messages(self, params: dict, context: dict) -> list[dict]:
        ticker = params["ticker"].upper()
        quant = context["quant"]
        qualitative = context.get("qualitative", {})

        process_doc = _read_process("03-final-verdict.md")

        user = f"""Synthesize the final investment verdict for {ticker}. Today's date is {date.today()}.

## Process instructions
{process_doc}

## Quantitative screen results
```json
{json.dumps(quant, indent=2)}
```

## Qualitative analysis
```json
{json.dumps(qualitative, indent=2)}
```

Use the structured_output tool to return your verdict. \
Set analysis_date to today's date ({date.today()}) and analysis_type to "final_verdict"."""

        return [{"role": "user", "content": user}]

    def post_run(self, params: dict, context: dict, output: dict) -> None:
        ticker = params["ticker"].upper()
        out = REPORTS_DIR / ticker / f"{ticker}_final.json"
        out.write_text(json.dumps(output, indent=2))


# ── Pipeline definition ───────────────────────────────────────────────────────

PIPELINE = Pipeline(
    id="stocks/analyze",
    name="Stock Analysis",
    params=["ticker"],
    steps=[
        QuantScreen(),
        SecFetch(),
        ValuationFetch(),
        QualitativeAnalysis(),
        FinalVerdict(),
    ],
)
