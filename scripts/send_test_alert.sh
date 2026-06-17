#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# send_test_alert.sh — fire a REAL COS test alert into your Telegram board.
#
# RUN THIS ON A MACHINE WITH INTERNET (your VPS 187.77.4.163, or your Mac).
# It CANNOT run from the Claude Code web sandbox — that container has no egress.
#
# Usage:
#   ./scripts/send_test_alert.sh                 # reads ./.env, sends BUY test
#   ./scripts/send_test_alert.sh SELL            # send a SELL test
#   ENV_FILE=/root/mnq_bot/.env ./scripts/send_test_alert.sh
#   ./scripts/send_test_alert.sh BUY --webhook   # POST through the COS handler
#                                                # (tests the full pipeline on :8002)
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ACTION="${1:-BUY}"
MODE="${2:-direct}"
ENV_FILE="${ENV_FILE:-./.env}"

# Load .env if present (does not print secrets)
if [[ -f "$ENV_FILE" ]]; then
  set -a; # shellcheck disable=SC1090
  source "$ENV_FILE"; set +a
fi

# Accept either variable name (handler uses TELEGRAM_TOKEN; .env uses TELEGRAM_BOT_TOKEN)
TOKEN="${TELEGRAM_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
CHAT="${TELEGRAM_CHAT_ID:-}"

if [[ -z "$TOKEN" || -z "$CHAT" ]]; then
  echo "ERROR: TELEGRAM_(BOT_)TOKEN and TELEGRAM_CHAT_ID must be set (in $ENV_FILE or env)." >&2
  exit 1
fi

# Sample MNQ levels for the test
ENTRY=21500.25
if [[ "$ACTION" == "BUY" ]]; then TP=21512.25; SL=21494.25; ARROW="🟢 LONG"; else TP=21488.25; SL=21506.25; ARROW="🔴 SHORT"; fi

if [[ "$MODE" == "--webhook" ]]; then
  # Test the WHOLE pipeline: TradingView-shaped JSON → COS handler → Telegram
  PORT="${VPS_WEBHOOK_PORT:-8002}"
  echo "POSTing test COS signal to local handler on :$PORT/cos-signal ..."
  curl -sS -X POST "http://localhost:${PORT}/cos-signal" \
    -H "Content-Type: application/json" \
    -d "{\"symbol\":\"MNQ\",\"action\":\"${ACTION}\",\"strategy\":\"COS\",\"module\":\"COS-PRO\",\"entry\":${ENTRY},\"qty\":1,\"tp\":${TP},\"sl\":${SL},\"surge\":3.87,\"vwap\":21495.00,\"confluence_score\":85,\"isAutomated\":true}" \
    -w "\nHTTP:%{http_code}\n"
else
  # Send directly to Telegram (proves token + chat work, independent of the handler)
  MSG=$(printf '📊 *COS Signal — TEST*\n%s MNQ\nEntry: \`%s\` | TP: \`%s\` | SL: \`%s\`\nSurge: 3.87× | VWAP: 21495.00\nConfluence: 85%%' "$ARROW" "$ENTRY" "$TP" "$SL")
  echo "Sending direct Telegram message to chat ${CHAT} ..."
  curl -sS "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT}" \
    --data-urlencode "text=${MSG}" \
    -d "parse_mode=Markdown" \
    -w "\nHTTP:%{http_code}\n"
fi
echo "Done. Check your Telegram board."
