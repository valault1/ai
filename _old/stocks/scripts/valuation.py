#!/usr/bin/env python3
"""Historical P/E comparison for valuation context.

Computes current trailing P/E vs a 5-year average P/E derived from
quarterly earnings and price history. Falls back gracefully when data
is insufficient.

Usage:
    python3 scripts/valuation.py AAPL
"""

import argparse
import json
import sys

import yfinance as yf


def _safe(value, default=None):
    if value is None:
        return default
    if isinstance(value, float) and value != value:
        return default
    return value


def calc_historical_pe(ticker: str) -> dict:
    """Compute current P/E vs 5-year average P/E."""
    t = yf.Ticker(ticker.upper())
    info = t.info

    current_pe = _safe(info.get("trailingPE"))
    if current_pe is None:
        return {
            "ticker": ticker.upper(),
            "current_pe": None,
            "historical_avg_pe": None,
            "pe_period": "5-year",
            "premium_discount_pct": None,
            "premium_discount_label": None,
            "valuation_context": "P/E data not available for this ticker.",
        }

    # Attempt to build a 5-year P/E series from quarterly EPS + price history
    pe_values = []
    try:
        hist = t.history(period="5y", interval="3mo")
        financials = t.quarterly_financials

        if financials is not None and not financials.empty:
            # Try to find net income and share count rows
            ni_row = next(
                (r for r in financials.index if "Net Income" in str(r) and "Common" not in str(r)),
                None,
            )
            sh_row = next(
                (r for r in financials.index if "Diluted" in str(r) and "Share" in str(r)),
                None,
            )
            if ni_row and sh_row:
                net_income = financials.loc[ni_row]
                shares = financials.loc[sh_row]
                for col in net_income.index:
                    ni = _safe(net_income.get(col))
                    sh = _safe(shares.get(col))
                    if ni and sh and sh > 0:
                        eps_annual = (ni / sh) * 4  # annualize quarterly
                        if eps_annual > 0:
                            # Find the closest price in history
                            price_candidates = hist[hist.index >= col]["Close"] if len(hist) else []
                            if len(price_candidates):
                                price = float(price_candidates.iloc[0])
                                pe_values.append(price / eps_annual)
    except Exception:
        pass

    current_pe = round(float(current_pe), 1)

    if len(pe_values) >= 4:
        historical_avg_pe = round(sum(pe_values) / len(pe_values), 1)
    else:
        # Insufficient history — report current P/E only
        return {
            "ticker": ticker.upper(),
            "current_pe": current_pe,
            "historical_avg_pe": None,
            "pe_period": "5-year",
            "premium_discount_pct": None,
            "premium_discount_label": None,
            "valuation_context": (
                f"Current P/E is {current_pe}x. "
                "Insufficient historical EPS data to compute 5-year average P/E."
            ),
        }

    pct = round((current_pe - historical_avg_pe) / historical_avg_pe * 100, 1)
    label = "Premium" if pct > 0 else "Discount"

    return {
        "ticker": ticker.upper(),
        "current_pe": current_pe,
        "historical_avg_pe": historical_avg_pe,
        "pe_period": "5-year",
        "premium_discount_pct": round(abs(pct), 1),
        "premium_discount_label": label,
        "valuation_context": (
            f"Trading at {abs(pct):.1f}% {label.lower()} to 5-year average P/E "
            f"({current_pe}x vs {historical_avg_pe}x avg)."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Historical P/E comparison")
    parser.add_argument("ticker", help="Stock ticker symbol")
    args = parser.parse_args()

    result = calc_historical_pe(args.ticker)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
