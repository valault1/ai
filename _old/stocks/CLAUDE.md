# Stocks — Long-Term Value Investing Analysis

This project contains processes, scripts, and frameworks for analyzing stocks through the lens of a long-term value investor (think Buffett/Munger style).

## Goals

- Build repeatable, documented processes for evaluating individual stocks
- Focus on fundamentals: business quality, competitive moat, management, valuation
- Avoid short-term noise; prioritize durable earnings power and intrinsic value

## Structure

- `processes/` — Markdown files documenting analysis frameworks and checklists
- `scripts/` — Python scripts for data fetching, computation, and the live dashboard server
- `systemd/` — systemd user service unit file for the dashboard server
- `reports/` — Generated JSON and markdown artifacts per ticker; `.progress.json` for live status

## Dashboard Server

The live dashboard runs as a systemd user service on port 7842, accessible over Tailscale.

**Start / enable (once):**
```bash
mkdir -p ~/.config/systemd/user
cp systemd/stocks-dashboard.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now stocks-dashboard
```

**After any changes to `scripts/server.py` (UI updates, new endpoints, etc.):**
```bash
systemctl --user restart stocks-dashboard
```

**Check status / logs:**
```bash
systemctl --user status stocks-dashboard
journalctl --user -u stocks-dashboard -f
```

## Philosophy

- Long-term horizon (5–10+ years)
- Prefer high-quality businesses at fair prices over cheap businesses at bargain prices
- Margin of safety is non-negotiable
- Understand the business before valuing it
