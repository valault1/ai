# Process 02: Qualitative Analysis

Use this process after a quant screen that returned `quant_gate: "PROCEED"`. Runs four sub-steps to assess business quality. Outputs `{TICKER}_qualitative.json` and `{TICKER}_qualitative.md`.

---

## Sub-step 2.1 — Circle of Competence

**Goal:** Can we understand this business in one sentence?

1. Fetch 10-K Item 1 (Business Description):
   ```bash
   python3 scripts/sec_fetcher.py {TICKER} --section 1 --output-dir reports/{TICKER}/
   ```
2. Read the extracted text at `reports/{TICKER}/{TICKER}_10k_section1.txt`.
3. Summarize the revenue model in **one sentence** (what does the company sell, to whom, and how does it get paid?).
4. Classify complexity:
   - **Simple** — the revenue model can be explained in one step
   - **Complex** — requires more than 3 steps to explain (e.g. financial derivatives, complex insurance structures, conglomerates with opaque cross-subsidies)

---

## Sub-step 2.2 — Moat Assessment

**Goal:** Does the company have a durable competitive advantage?

1. Fetch 10-K Item 7 (MD&A):
   ```bash
   python3 scripts/sec_fetcher.py {TICKER} --section 7 --output-dir reports/{TICKER}/
   ```
2. Read `reports/{TICKER}/{TICKER}_10k_section7.txt`.
3. Classify the moat type (pick the **primary** one):
   - **Brand Power** — customers pay a premium specifically for the name/reputation
   - **Switching Costs** — customers are locked in by data, integrations, or workflows
   - **Cost Advantage** — structural cost efficiency competitors cannot easily replicate
   - **Network Effect** — the product becomes more valuable as more people use it
   - **Multiple** — clearly has 2+ of the above
   - **None** — no durable advantage evident
4. Classify moat strength: **Wide** / **Narrow** / **None**
5. Find one direct quote from the filing that demonstrates pricing power or competitive differentiation. Note the source (section, fiscal year).

---

## Sub-step 2.3 — Risk Assessment

**Goal:** What could seriously hurt this business?

1. Fetch 10-K Item 1A (Risk Factors):
   ```bash
   python3 scripts/sec_fetcher.py {TICKER} --section 1A --output-dir reports/{TICKER}/
   ```
2. Read `reports/{TICKER}/{TICKER}_10k_section1A.txt`.
3. Identify the **top 2 material risks** — the ones most likely to damage long-term earnings power, not boilerplate legal disclaimers.
4. Calculate **Years to Payoff**:
   - Read `total_debt` and `avg_fcf_3yr` from the quant JSON (or from yfinance info)
   - `years_to_payoff = total_debt / avg_fcf_3yr`
   - If `years_to_payoff > 4` → flag as **High Risk**; otherwise **Low Risk**
   - If FCF is negative → flag as **High Risk** with note

---

## Sub-step 2.4 — Valuation Context

**Goal:** Is the stock cheap or expensive relative to its own history?

1. Run the valuation script:
   ```bash
   python3 scripts/valuation.py {TICKER}
   ```
2. Review the output: current P/E, 5-year avg P/E, premium/discount.
3. If the stock trades at a **heavy discount** (>20% below historical avg P/E), use a web search to understand why — is it a temporary dip or a structural problem?

---

## Output

After all four sub-steps, write two files:

### `reports/{TICKER}/{TICKER}_qualitative.md`

A human-readable summary:
```
- Company: {Name} ({TICKER})
- Revenue Model: {one sentence}
- Complexity: Simple / Complex
- Moat Type: {classification}
- Moat Strength: Wide / Narrow / None
- Pricing Power Evidence: "{quote}" — {source}
- Top Risks: 1. {title} ({severity}) — {brief description}
             2. {title} ({severity}) — {brief description}
- Debt Payoff: {N} years — Low / High Risk
- Valuation: {Premium/Discount} to historical ({current}x vs {avg}x P/E)
- Overall Assessment: {2–3 sentences synthesizing the above}
```

### `reports/{TICKER}/{TICKER}_qualitative.json`

Write the full structured JSON to `reports/{TICKER}/{TICKER}_qualitative.json`:

```json
{
  "ticker": "{TICKER}",
  "company_name": "{Name}",
  "analysis_date": "{YYYY-MM-DD}",
  "analysis_type": "qualitative",
  "circle_of_competence": {
    "revenue_model": "{one sentence}",
    "complexity": "Simple",
    "complexity_reasoning": "{brief reason}"
  },
  "moat": {
    "type": "Brand Power",
    "strength": "Wide",
    "pricing_power_quote": "{direct quote from filing}",
    "pricing_power_source": "10-K Item 7, FY{year}",
    "moat_evidence": "{1–2 sentences of your own analysis}"
  },
  "risks": {
    "top_risks": [
      { "rank": 1, "title": "{title}", "description": "{1–2 sentences}", "severity": "Medium" },
      { "rank": 2, "title": "{title}", "description": "{1–2 sentences}", "severity": "Low" }
    ],
    "years_to_payoff": {number or null},
    "years_to_payoff_display": "{N} years",
    "debt_risk_level": "Low",
    "total_debt": {number or null},
    "avg_fcf_3yr": {number or null}
  },
  "valuation": {
    "current_pe": {number or null},
    "historical_avg_pe": {number or null},
    "pe_period": "5-year",
    "premium_discount_pct": {number or null},
    "premium_discount_label": "Premium",
    "valuation_context": "{1–2 sentence summary}"
  },
  "overall_assessment": "{2–3 sentence synthesis}"
}
```

**Field constraints:**
- `moat.type` must be one of: `"Brand Power"`, `"Switching Costs"`, `"Cost Advantage"`, `"Network Effect"`, `"Multiple"`, `"None"`
- `moat.strength` must be one of: `"Wide"`, `"Narrow"`, `"None"`
- `risks.severity` must be one of: `"Low"`, `"Medium"`, `"High"`
- `valuation.premium_discount_label` must be `"Premium"` or `"Discount"`
- All number fields should be `null` (not `"N/A"`) when data is unavailable
