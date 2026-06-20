"""
Charlie Telegram notifier — Gate 3 (TAKEOFF / ARRIVAL / CANCELLED alerts).

Charlie's server.py is a local web "flight board" (http://127.0.0.1:8788) and does
NOT send Telegram (README lists it as Gate 3, unbuilt). This adds it WITHOUT editing
server.py: run it alongside the board and it polls /board, pushing a Telegram message
the moment a watchlist name flips INTO an actionable status. De-duped via
alert_state.json so the 60s refresh never spams.

PAPER ONLY. These are co-pilot nudges to look — not orders, not advice.

── Run (on the Mac that runs charlie; it has internet, this sandbox does not) ──
    cd "Trading Universe/07_AI_Trading/charlie"
    export TELEGRAM_BOT_TOKEN=<the Rio_PA bot token>   # chat_id is already in config.json
    ./run.sh &            # the board on :8788
    ../mnq_bot/.venv/bin/python notify.py   # this watcher → Telegram

Quick one-shot test (sends a sample TAKEOFF to your board):
    ../mnq_bot/.venv/bin/python notify.py --test

Env: TELEGRAM_BOT_TOKEN (or TELEGRAM_TOKEN). chat_id from TELEGRAM_CHAT_ID or
config.json -> telegram.chat_id. Reuses the existing Rio_PA bot.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "alert_state.json")
BOARD_URL = os.environ.get("CHARLIE_BOARD_URL", "http://127.0.0.1:8788/board")

# Statuses worth a phone buzz. Entry, exit-for-profit, and thesis-stop.
ALERT_STATUSES = {"TAKEOFF", "ARRIVAL", "CANCELLED"}


def _token():
    return os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or ""


def _chat(cfg):
    return os.environ.get("TELEGRAM_CHAT_ID") or (cfg.get("telegram") or {}).get("chat_id", "")


def _load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(s):
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(s, f)
    except Exception:
        pass


def _send(token, chat, text):
    data = urllib.parse.urlencode(
        {"chat_id": chat, "text": text, "parse_mode": "Markdown"}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            ok = 200 <= r.status < 300
            if not ok:
                print(f"[telegram] HTTP {r.status}", flush=True)
            return ok
    except Exception as e:
        print(f"[telegram] {e}", flush=True)
        return False


def _fmt(row):
    st = row.get("status")
    icon = {"TAKEOFF": "🛫", "ARRIVAL": "🛬", "CANCELLED": "🛑"}.get(st, "✈️")
    lines = [f"{icon} *Charlie — {st}*  `{row.get('ticker')}`"]
    if row.get("reason"):
        lines.append(row["reason"])
    if row.get("strike"):
        lines.append(f"Strike `{row['strike']}`  exp `{row.get('expiry','')}`  ({row.get('dte','?')} dte)")
    prem = row.get("premium", row.get("cur_premium"))
    if prem is not None:
        lines.append(f"Premium ~`${prem}`  Δ`{row.get('delta','?')}`")
    if row.get("pnl") is not None:
        lines.append(f"P&L `${row['pnl']}`  ({row.get('pct_to_target','?')}% to target)")
    if row.get("score") is not None:
        lines.append(f"Spot `{row.get('spot','?')}`  score `{row['score']}`  RSI `{row.get('rsi','?')}`")
    lines.append("_paper co-pilot — verify before you act_")
    return "\n".join(lines)


def notify_board(board, cfg):
    """Send one Telegram per NEW actionable status. Safe to call every refresh."""
    token, chat = _token(), _chat(cfg)
    if not token or not chat:
        print("[notify] TELEGRAM_BOT_TOKEN / chat_id not set — skipping", flush=True)
        return 0
    state = _load_state()
    changed = sent = 0
    for row in board.get("rows", []):
        t, st = row.get("ticker"), row.get("status")
        if not t:
            continue
        if st not in ALERT_STATUSES:
            if state.pop(t, None) is not None:   # left alert status → allow re-alert later
                changed += 1
            continue
        if state.get(t) == st:
            continue                              # already alerted for this exact status
        if _send(token, chat, _fmt(row)):
            state[t] = st
            changed += 1
            sent += 1
    if changed:
        _save_state(state)
    return sent


def _poll(cfg, interval):
    print(f"Charlie Telegram watcher → {BOARD_URL} every {interval}s; "
          f"alerting on {', '.join(sorted(ALERT_STATUSES))}", flush=True)
    while True:
        try:
            with urllib.request.urlopen(BOARD_URL, timeout=10) as r:
                board = json.load(r)
            n = notify_board(board, cfg)
            if n:
                print(f"[notify] sent {n} alert(s)", flush=True)
        except Exception as e:
            print(f"[poll] {e} (is the board running? ./run.sh)", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    with open(os.path.join(HERE, "config.json")) as f:
        cfg = json.load(f)

    if "--test" in sys.argv:
        sample = {"rows": [{
            "ticker": "NVDA", "status": "TAKEOFF",
            "reason": "BULL + not overextended — deep-ITM entry, BUY",
            "strike": 120, "expiry": "2026-09-18", "dte": 90,
            "premium": 21.40, "delta": 0.76, "spot": 138.2, "score": 100, "rsi": 61,
        }]}
        # bypass de-dup for the test
        try:
            os.remove(STATE_PATH)
        except OSError:
            pass
        n = notify_board(sample, cfg)
        print("test sent" if n else "test FAILED — check token/chat/network")
        sys.exit(0 if n else 1)

    _poll(cfg, cfg.get("data", {}).get("refresh_seconds", 60))
