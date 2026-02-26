#!/usr/bin/env bash
# Run the ACP-India reference implementation locally using SQLite.
# No Docker, no Postgres — just Python + uvicorn.
#
# Usage:
#   ./scripts/run_dev.sh
#
# Then try:
#   curl http://localhost:8000/health
#   curl http://localhost:8001/health
#   curl http://localhost:8000/indus/capabilities

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Install deps (once)
echo "[1/3] Installing dependencies..."
pip install -r "$ROOT/merchant/requirements.txt" -q
pip install -r "$ROOT/indus/requirements.txt" -q

# Start Merchant (background)
echo "[2/3] Starting Merchant on :8001..."
cd "$ROOT/merchant"
DATABASE_URL="sqlite:///$ROOT/merchant.db" \
INDUS_API_KEYS="demo_key" \
INDUS_BASE_URL="http://localhost:8000" \
INDUS_API_KEY="demo_key" \
MERCHANT_NAME="Demo Merchant" \
MERCHANT_URL="https://merchant.example.com" \
MERCHANT_PRIVACY_URL="https://merchant.example.com/privacy" \
MERCHANT_TOS_URL="https://merchant.example.com/terms" \
RATE_LIMIT_ENABLED="false" \
  uvicorn app.main:app --port 8001 --log-level warning &
MERCHANT_PID=$!

sleep 2

# Start Indus (foreground)
echo "[3/3] Starting Indus on :8000..."
echo ""
echo "  Indus:    http://localhost:8000"
echo "  Merchant: http://localhost:8001"
echo ""
echo "  Try: curl http://localhost:8000/indus/capabilities"
echo "  Try: curl http://localhost:8001/capabilities"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

cd "$ROOT/indus"
DATABASE_URL="sqlite:///$ROOT/indus.db" \
MERCHANT_API_KEYS="demo_key" \
INDUS_API_KEY="demo_key" \
TOKEN_TTL_SECONDS="86400" \
RATE_LIMIT_ENABLED="false" \
  uvicorn app.main:app --port 8000 --log-level info

# Cleanup on exit
kill $MERCHANT_PID 2>/dev/null || true
