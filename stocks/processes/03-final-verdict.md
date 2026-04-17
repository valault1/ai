# Process 03: Final Verdict

Use this process after completing both the quantitative screen (Process 01) and qualitative analysis (Process 02). Synthesizes everything into an investment verdict.

---

## Verdict Criteria

| Verdict | Criteria |
|---------|----------|
| **STRONG BUY** | All Big 4 pass + moat strength Wide + discount to historical valuation |
| **WATCHLIST** | Mostly passes (0–1 Big 4 failures) + at least Narrow moat + not grossly overvalued |
| **MORE RESEARCH** | Borderline on multiple dimensions — quality is unclear, valuation is mixed, or data gaps exist |
| **PASS** | Failed quant screen (HALT) OR no moat (None) OR high debt risk + poor financials |

Use your judgment when signals are mixed. The verdict should reflect where you would actually want to put capital.

---

## Scoring (1–10 integers)

| Dimension | What to assess |
|-----------|---------------|
| `business_quality` | How good is the underlying business? Revenue stability, margins, brand/product strength. |
| `financial_strength` | Balance sheet health, FCF generation, debt management. |
| `moat_durability` | How defensible is the competitive advantage over 5–10 years? |
| `valuation_attractiveness` | How cheap is the stock relative to its intrinsic value and historical norms? |
| `overall` | Holistic score — this is the leaderboard sort key. |

---

## Elevator Pitch

Write a 2–3 sentence "elevator pitch" in plain English:
- What does this business do and why is it good (or not)?
- What is the key risk?
- Is now a good time to buy?

Keep it sharp. No jargon. Write like you're explaining it to a smart friend who doesn't follow stocks.

---

## Output

Write two files:

### `reports/{TICKER}/{TICKER}_final.md`

```
# Final Verdict — {Name} ({TICKER})

## Verdict: {VERDICT}

### Elevator Pitch
{2–3 sentences}

### Scores
- Business Quality:       {N}/10
- Financial Strength:     {N}/10
- Moat Durability:        {N}/10
- Valuation Attractiveness: {N}/10
- **Overall:**            {N}/10

### Reasoning
{2–3 sentences explaining the verdict}

### Target Entry Note
{Optional: at what price or P/E would this become more attractive?}

### Summary
- Quant: {verdict} ({pass_count}/4 Big 4)
- Moat: {type}, {strength}
- Debt Risk: {Low/High}
- Valuation: {Premium/Discount}
- Top Risk: {title}
```

### `reports/{TICKER}/{TICKER}_final.json`

```json
{
  "ticker": "{TICKER}",
  "company_name": "{Name}",
  "analysis_date": "{YYYY-MM-DD}",
  "analysis_type": "final_verdict",
  "verdict": "WATCHLIST",
  "verdict_reasoning": "{2–3 sentences}",
  "elevator_pitch": "{2–3 sentences}",
  "target_entry_note": "{optional string or null}",
  "scores": {
    "business_quality": {1-10},
    "financial_strength": {1-10},
    "moat_durability": {1-10},
    "valuation_attractiveness": {1-10},
    "overall": {1-10}
  },
  "summary": {
    "quant_verdict": "PASS",
    "big4_pass_count": {number},
    "big4_fail_count": {number},
    "moat_type": "{type}",
    "moat_strength": "{strength}",
    "debt_risk": "Low",
    "valuation_stance": "Premium",
    "top_risk": "{title of risk #1}"
  }
}
```

**Field constraints:**
- `verdict` must be exactly one of: `"STRONG BUY"`, `"WATCHLIST"`, `"PASS"`, `"MORE RESEARCH"`
- All `scores` values must be integers 1–10
- `summary` is a flat view for the dashboard leaderboard — must be complete

---

## Special case: HALT from quant gate

If `quant_gate` was `"HALT"`, write a minimal final JSON:

```json
{
  "ticker": "{TICKER}",
  "company_name": "{Name}",
  "analysis_date": "{YYYY-MM-DD}",
  "analysis_type": "final_verdict",
  "verdict": "PASS",
  "verdict_reasoning": "Failed quantitative screen: {N} of 4 Big 4 metrics fail.",
  "elevator_pitch": null,
  "target_entry_note": null,
  "scores": null,
  "summary": {
    "quant_verdict": "FAIL",
    "big4_pass_count": {number},
    "big4_fail_count": {number},
    "moat_type": null,
    "moat_strength": null,
    "debt_risk": null,
    "valuation_stance": null,
    "top_risk": null
  }
}
```
