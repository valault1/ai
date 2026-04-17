# Process 01: Quantitative Screen

Use this process to run the initial quantitative screen for a stock. This is always the first step before any qualitative analysis.

## Steps

### 1. Run the script

```bash
python3 scripts/quant_screen.py {TICKER} --output-dir reports/{TICKER}/
```

This saves `reports/{TICKER}/{TICKER}_quant.json` and `reports/{TICKER}/{TICKER}_quant.md`.

### 2. Read the JSON output

Read `reports/{TICKER}/{TICKER}_quant.json` to get the structured results.

### 3. Present results

Show the user:
- The verdict (**PASS** / **BORDERLINE** / **FAIL**) prominently at the top
- The Big 4 metrics table with pass/fail for each
- The Supporting metrics table
- A 2-sentence plain-English assessment

Example format:
```
**AAPL — BORDERLINE**

Big 4: ROE ✓ | D/E ✓ | FCF Yield ✗ | P/E ✗
Supporting: Current Ratio ✗ | Op Margin ✓ | Shares ✓

Apple has strong returns and manageable debt but trades at a stretched
valuation with modest FCF yield. Worth deeper investigation given its
wide competitive moat.
```

### 4. Apply the decision gate

Check `quant_gate` in the JSON:

- **`"HALT"`** — More than 2 Big 4 failures. Stop here. Tell the user this stock fails the minimum quality threshold and is not suitable for further analysis at this time. Do NOT proceed to qualitative analysis.
- **`"PROCEED"`** — 0–2 Big 4 failures. Recommend running `/deep-dive {TICKER}` for qualitative analysis, or note that the full pipeline can be run with `/analyze {TICKER}`.

## Notes

- If yfinance returns N/A for a metric, it does **not** count as a failure
- The D/E threshold (< 0.50x) is already applied correctly in the script — the divide-by-100 conversion from yfinance's format is handled internally
- A BORDERLINE verdict (1–2 failures) still gets qualitative analysis; it may still be a good business at the wrong price or with fixable issues
