Run a side-by-side quantitative comparison for: **$ARGUMENTS**

The tickers are: `$ARGUMENTS` (space-separated list).

## Steps

For each ticker in the list:
1. Run:
   ```bash
   python3 scripts/quant_screen.py {TICKER} --output-dir reports/{TICKER}/
   sleep 1
   ```
   (The 1-second delay avoids yfinance rate limiting.)

2. Read each `reports/{TICKER}/{TICKER}_quant.json`.

## Output

Present a ranked side-by-side comparison table:

| Rank | Ticker | Company | ROE | D/E | FCF Yield | P/E | Big 4 | Verdict |
|------|--------|---------|-----|-----|-----------|-----|-------|---------|
| 1 | ... | ... | ... | ... | ... | ... | 4/4 | PASS |
| 2 | ... | ... | ... | ... | ... | ... | 2/4 | BORDERLINE |

Sort by:
1. Big 4 pass count (descending)
2. Among ties: FCF Yield (descending)

After the table, provide a 2-sentence assessment of the best-looking ticker and why it stands out.

Recommend running `/analyze {best_ticker}` for a full qualitative deep-dive on the winner.
