#!/usr/bin/env python3
"""Quantitative screening engine for Buffett-style value investing analysis.

Usage:
    python3 scripts/quant_screen.py AAPL [--output-dir reports/AAPL/]

Exit codes:
    0 = quant_gate PROCEED (0-2 Big 4 failures)
    1 = quant_gate HALT (>2 Big 4 failures)
    2 = error (bad ticker, no data)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yfinance as yf


def fetch_data(ticker: str) -> dict:
    """Fetch info, balance_sheet, financials, cashflow from yfinance."""
    t = yf.Ticker(ticker)
    return {
        "info": t.info,
        "balance_sheet": t.balance_sheet,
        "financials": t.financials,
        "cashflow": t.cashflow,
    }


def _safe(value, default=None):
    """Return value if it is a real number, else default."""
    if value is None:
        return default
    if isinstance(value, float) and value != value:  # NaN
        return default
    return value


def calc_big4(info: dict) -> list:
    """Calculate Big 4 metrics: ROE, D/E, FCF Yield, P/E."""
    results = []

    # ROE
    roe = _safe(info.get("returnOnEquity"))
    results.append({
        "metric": "ROE",
        "label": "Return on Equity",
        "value": roe,
        "display_value": f"{roe:.1%}" if roe is not None else "N/A",
        "threshold": 0.15,
        "threshold_label": ">= 15%",
        "direction": "higher_is_better",
        "pass_fail": "PASS" if roe is not None and roe >= 0.15
                     else ("FAIL" if roe is not None else "NA"),
    })

    # D/E — yfinance returns e.g. 150 meaning 1.5x; divide by 100
    de_raw = _safe(info.get("debtToEquity"))
    de = de_raw / 100 if de_raw is not None else None
    results.append({
        "metric": "DE",
        "label": "Debt / Equity",
        "value": de,
        "display_value": f"{de:.2f}x" if de is not None else "N/A",
        "threshold": 0.50,
        "threshold_label": "< 0.50x",
        "direction": "lower_is_better",
        "pass_fail": "PASS" if de is not None and de < 0.50
                     else ("FAIL" if de is not None else "NA"),
    })

    # FCF Yield
    fcf = _safe(info.get("freeCashflow"))
    mktcap = _safe(info.get("marketCap"))
    if fcf is not None and mktcap is not None and mktcap > 0:
        fcf_yield = fcf / mktcap
    else:
        fcf_yield = None
    results.append({
        "metric": "FCF_YIELD",
        "label": "FCF Yield",
        "value": fcf_yield,
        "display_value": f"{fcf_yield:.1%}" if fcf_yield is not None else "N/A",
        "threshold": 0.05,
        "threshold_label": ">= 5%",
        "direction": "higher_is_better",
        "pass_fail": "PASS" if fcf_yield is not None and fcf_yield >= 0.05
                     else ("FAIL" if fcf_yield is not None else "NA"),
    })

    # P/E
    pe = _safe(info.get("trailingPE"))
    results.append({
        "metric": "PE",
        "label": "P/E Ratio",
        "value": pe,
        "display_value": f"{pe:.1f}x" if pe is not None else "N/A",
        "threshold": 20,
        "threshold_label": "< 20x",
        "direction": "lower_is_better",
        "pass_fail": "PASS" if pe is not None and pe < 20
                     else ("FAIL" if pe is not None else "NA"),
    })

    return results


def calc_supporting(info: dict, balance_sheet) -> list:
    """Calculate Current Ratio, Operating Margin, Shares Outstanding Trend."""
    results = []

    # Current Ratio
    cr = _safe(info.get("currentRatio"))
    results.append({
        "metric": "CURRENT_RATIO",
        "label": "Current Ratio",
        "value": cr,
        "display_value": f"{cr:.2f}x" if cr is not None else "N/A",
        "threshold": 1.5,
        "threshold_label": "> 1.5x",
        "direction": "higher_is_better",
        "pass_fail": "PASS" if cr is not None and cr > 1.5
                     else ("FAIL" if cr is not None else "NA"),
    })

    # Operating Margin
    om = _safe(info.get("operatingMargins"))
    results.append({
        "metric": "OP_MARGIN",
        "label": "Operating Margin",
        "value": om,
        "display_value": f"{om:.1%}" if om is not None else "N/A",
        "threshold": 0.10,
        "threshold_label": "> 10%",
        "direction": "higher_is_better",
        "pass_fail": "PASS" if om is not None and om > 0.10
                     else ("FAIL" if om is not None else "NA"),
    })

    # Shares Outstanding Trend — most recent 4 annual columns
    shares_history = None
    shares_pass_fail = "NA"
    shares_display = "N/A"
    if balance_sheet is not None and not balance_sheet.empty:
        for label in ["Ordinary Shares Number", "Share Issued", "Common Stock Equity"]:
            try:
                if label in balance_sheet.index:
                    row = balance_sheet.loc[label].dropna()
                    if len(row) >= 2:
                        vals = [int(v) for v in row.iloc[:4]]  # most recent first
                        shares_history = vals
                        if vals[0] <= vals[-1]:
                            shares_pass_fail = "PASS"
                            shares_display = "Decreasing"
                        else:
                            shares_pass_fail = "FAIL"
                            shares_display = "Increasing"
                        break
            except Exception:
                continue

    results.append({
        "metric": "SHARES_TREND",
        "label": "Shares Outstanding",
        "value": None,
        "display_value": shares_display,
        "threshold": None,
        "threshold_label": "Flat or decreasing",
        "direction": None,
        "pass_fail": shares_pass_fail,
        "shares_history": shares_history,
    })

    return results


def generate_report(ticker: str, big4: list, supporting: list, info: dict) -> dict:
    """Assemble full results with verdict and quant_gate."""
    fail_count = sum(1 for m in big4 if m["pass_fail"] == "FAIL")
    pass_count = sum(1 for m in big4 if m["pass_fail"] == "PASS")

    if fail_count > 2:
        verdict = "FAIL"
        quant_gate = "HALT"
    elif fail_count == 0:
        verdict = "PASS"
        quant_gate = "PROCEED"
    else:
        verdict = "BORDERLINE"
        quant_gate = "PROCEED"

    price = _safe(info.get("currentPrice")) or _safe(info.get("regularMarketPrice"))

    return {
        "ticker": ticker.upper(),
        "company_name": _safe(info.get("longName"), ticker.upper()),
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "analysis_type": "quantitative",
        "market_cap": _safe(info.get("marketCap")),
        "sector": _safe(info.get("sector"), "Unknown"),
        "industry": _safe(info.get("industry"), "Unknown"),
        "current_price": price,
        "verdict": verdict,
        "big4": big4,
        "supporting": supporting,
        "big4_pass_count": pass_count,
        "big4_fail_count": fail_count,
        "quant_gate": quant_gate,
    }


def format_markdown(report: dict) -> str:
    """Render the report dict as a markdown table + verdict summary."""
    price_str = f"${report['current_price']}" if report["current_price"] else "N/A"
    lines = [
        f"# Quantitative Screen — {report['company_name']} ({report['ticker']})",
        f"**Date:** {report['analysis_date']}  |  **Sector:** {report['sector']}  |  **Price:** {price_str}",
        "",
        "## Big 4 Metrics",
        "",
        "| Metric | Value | Threshold | Result |",
        "|--------|-------|-----------|--------|",
    ]
    for m in report["big4"]:
        icon = "PASS" if m["pass_fail"] == "PASS" else ("FAIL" if m["pass_fail"] == "FAIL" else "N/A")
        lines.append(f"| {m['label']} | {m['display_value']} | {m['threshold_label']} | {icon} |")

    lines += [
        "",
        "## Supporting Metrics",
        "",
        "| Metric | Value | Threshold | Result |",
        "|--------|-------|-----------|--------|",
    ]
    for m in report["supporting"]:
        icon = "PASS" if m["pass_fail"] == "PASS" else ("FAIL" if m["pass_fail"] == "FAIL" else "N/A")
        lines.append(f"| {m['label']} | {m['display_value']} | {m['threshold_label']} | {icon} |")

    lines += [
        "",
        "## Verdict",
        "",
        f"**{report['verdict']}** — {report['big4_pass_count']}/4 Big 4 metrics pass, {report['big4_fail_count']} fail.",
        f"**Decision gate:** {report['quant_gate']}",
    ]
    if report["quant_gate"] == "HALT":
        lines.append(
            "\n> More than 2 Big 4 failures. Halting pipeline — does not meet minimum quality threshold."
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Quantitative stock screen")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--output-dir", help="Directory to save JSON and markdown output")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    try:
        data = fetch_data(ticker)
    except Exception as e:
        print(f"ERROR: Failed to fetch data for {ticker}: {e}", file=sys.stderr)
        sys.exit(2)

    info = data["info"]
    if not info or (
        info.get("regularMarketPrice") is None
        and info.get("currentPrice") is None
        and info.get("marketCap") is None
    ):
        print(f"ERROR: No market data found for {ticker}. Check the ticker symbol.", file=sys.stderr)
        sys.exit(2)

    big4 = calc_big4(info)
    supporting = calc_supporting(info, data["balance_sheet"])
    report = generate_report(ticker, big4, supporting, info)
    md = format_markdown(report)

    print(md)
    print()
    print(json.dumps(report, indent=2))

    if args.output_dir:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{ticker}_quant.json").write_text(json.dumps(report, indent=2))
        (out / f"{ticker}_quant.md").write_text(md)
        print(f"\nSaved to {out}/", file=sys.stderr)

    sys.exit(0 if report["quant_gate"] == "PROCEED" else 1)


if __name__ == "__main__":
    main()
