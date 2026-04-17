Run a side-by-side quantitative comparison for: **$ARGUMENTS**

The tickers are: `$ARGUMENTS` (space-separated list). All commands run from `/home/val/ai/stocks`.

## Steps

For each ticker in the list:
1. Run:
   ```bash
   cd /home/val/ai/stocks && python3 scripts/quant_screen.py {TICKER} --output-dir reports/{TICKER}/
   sleep 1
   ```
   (The 1-second delay avoids yfinance rate limiting.)

2. Read each `stocks/reports/{TICKER}/{TICKER}_quant.json`.

## Output

Present a ranked side-by-side comparison table:

| Rank | Ticker | Company | ROE | D/E | FCF Yield | P/E | Big 4 | Verdict |
|------|--------|---------|-----|-----|-----------|-----|-------|---------|

Sort by Big 4 pass count descending; break ties by FCF Yield descending.

After the table, provide a 2-sentence assessment of the best-looking ticker. Recommend running `/analyze {best_ticker}` for a full deep-dive.
