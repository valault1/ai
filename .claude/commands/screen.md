Run a quantitative screen for: **$ARGUMENTS**

**If `$ARGUMENTS` is blank or missing**, stop immediately and tell the user: "Please provide a ticker symbol, e.g. `/screen AAPL`"

The working directory for all commands is `/home/val/ai/stocks`. Use that as the base for all relative paths.

Follow `stocks/processes/01-quantitative-screen.md`, substituting `$ARGUMENTS` for `{TICKER}`.

Run the screen script as:
```bash
cd /home/val/ai/stocks && python3 scripts/quant_screen.py $ARGUMENTS --output-dir reports/$ARGUMENTS/
```
