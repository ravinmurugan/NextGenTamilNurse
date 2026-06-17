# COS-FULL Indicator — Switch-Over Guide

This replaces the **`rio-ema`** signals (EMA-crossover, no stop, no filter) that
produced losing whipsaw trades like *BUY 30527 → SELL 30347.75 (−179 pts)*.

`COS_FULL_Indicator.pine` is a discretionary **study** for manual entry on the
MNQ 1-minute chart. It carries the proven COS guards plus profit boosters.

## Why this fixes the rio-ema loss

| rio-ema failure | COS fix |
|---|---|
| Lagging EMA-cross entry near the top | Requires **volume surge ≥ 3.5×** + **close vs session VWAP** + bar direction |
| No stop loss → loss ran −179 pts | **Hard TP/SL** on every signal (M1 12/6 pts, M2 8/4 pts; or ATR-adaptive) |
| Trades into chop/reversals | **Skip HIGH-ATR regime, Tuesdays, 3-day exhaustion**; 9:30–11:00 ET window |
| No conviction gauge | **0–100 confluence score** on every signal + dashboard |

## 1. Add the indicator to TradingView
1. Open the MNQ1! chart, **1-minute** timeframe.
2. Pine Editor → paste `COS_FULL_Indicator.pine` → **Save** → **Add to chart**.
3. Confirm the dashboard (top-right) and yellow VWAP / orange EMA lines appear.

## 2. Retire the rio-ema alert (important)
- Alerts panel (clock icon) → find the **`rio-ema`** alert → **delete or pause** it.
  Leaving it on will keep firing the losing signals into Telegram.

## 3. Wire the new alert (optional — only if you want Telegram pushes)
- Create alert → Condition: **"COS-FULL ⚡ Indicator" → Any alert() function call**.
- Webhook URL: `http://187.77.4.163:8002/cos-signal`
- Leave the message box blank — the script emits the JSON itself.
- The payload uses `"strategy":"COS"` and is enriched with `surge`, `vwap`,
  `confluence_score`, so the Telegram message shows full context (no more `?`).

> For **manual entry** you don't even need the webhook — the on-chart triangles,
> TP/SL lines, and confluence % are enough to decide and place the trade yourself.

## 4. Tuning for better profit (A/B test before live)
- Start in **score-only** mode: keep `Min confluence score = 0`, watch which
  signals score ≥ 70% vs the losers. Then raise the gate (e.g. 70) to filter.
- `EMA trend filter` is **ON** by default (blocks counter-trend). Turn it OFF to
  reproduce the exact original COS-FULL signal set.
- Try `ATR-adaptive TP/SL` on volatile days so targets scale with range.
- Keep **`Relax Filters` OFF** for live trading (it disables the safety filters).

## Files
- `COS_FULL_Indicator.pine` — the indicator (this is what you run).
- Webhook handler `cos_webhook_handler.py` lives on the VPS (port 8002).
