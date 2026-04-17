Run a qualitative deep-dive for: **$ARGUMENTS**

The ticker is `$ARGUMENTS`. All commands run from `/home/val/ai/stocks`.

Assume the quantitative screen has already been run and `stocks/reports/$ARGUMENTS/$ARGUMENTS_quant.json` exists. If it doesn't, run the quant screen first per `stocks/processes/01-quantitative-screen.md`.

1. Follow `stocks/processes/02-qualitative-analysis.md` for all four sub-steps, prefixing all `python3 scripts/...` commands with `cd /home/val/ai/stocks &&`.
2. Follow `stocks/processes/03-final-verdict.md` to synthesize the final verdict.
3. Present the verdict, scores, and elevator pitch to the user.
