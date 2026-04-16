#!/usr/bin/env bash
# Deploy the yakrobot-chat Cloudflare Worker.
#
# Usage:
#   ./scripts/deploy-worker.sh          # deploy and verify
#   ./scripts/deploy-worker.sh --check  # verify only (no deploy)
#
# This script:
#   1. Validates no rogue wrangler config exists in parent directories
#   2. Deploys with explicit -c to guarantee correct config
#   3. Verifies secrets are present
#   4. Smoke-tests critical endpoints
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_DIR="$REPO_ROOT/worker"
WORKER_NAME="yakrobot-chat"
WORKER_URL="https://${WORKER_NAME}.rafaeldf2.workers.dev"
CONFIG="wrangler.toml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}OK${NC}  $1"; }
warn() { echo -e "  ${YELLOW}WARN${NC}  $1"; }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; }

CHECK_ONLY=false
if [[ "${1:-}" == "--check" ]]; then CHECK_ONLY=true; fi

echo "=== Worker Deploy: $WORKER_NAME ==="
echo ""

# --- Pre-flight checks ---

echo "Pre-flight checks:"

# 1. No rogue wrangler configs in parent directories
ROGUE_CONFIGS=()
for f in "$REPO_ROOT/wrangler.jsonc" "$REPO_ROOT/wrangler.json" "$REPO_ROOT/wrangler.toml"; do
  if [[ -f "$f" ]]; then ROGUE_CONFIGS+=("$f"); fi
done

if [[ ${#ROGUE_CONFIGS[@]} -gt 0 ]]; then
  fail "Rogue wrangler config(s) in parent directory — wrangler will use these instead of worker/wrangler.toml:"
  for f in "${ROGUE_CONFIGS[@]}"; do echo "       $f"; done
  echo "       Move or delete them before deploying."
  exit 1
fi
ok "No rogue wrangler configs in parent directories"

# 2. worker/wrangler.toml exists and has correct name
if [[ ! -f "$WORKER_DIR/$CONFIG" ]]; then
  fail "$WORKER_DIR/$CONFIG not found"
  exit 1
fi

TOML_NAME=$(grep '^name' "$WORKER_DIR/$CONFIG" | head -1 | sed 's/.*= *"\(.*\)"/\1/')
if [[ "$TOML_NAME" != "$WORKER_NAME" ]]; then
  fail "wrangler.toml name is '$TOML_NAME', expected '$WORKER_NAME'"
  exit 1
fi
ok "wrangler.toml name = $WORKER_NAME"

# 3. Source file exists
if [[ ! -f "$WORKER_DIR/src/index.js" ]]; then
  fail "src/index.js not found"
  exit 1
fi
LINES=$(wc -l < "$WORKER_DIR/src/index.js" | tr -d ' ')
ok "src/index.js exists ($LINES lines)"

# 4. Check new endpoints are in source
REQUIRED_ROUTES=("/api/create-ach-intent" "/api/transfer-to-operator" "/api/capture-payment" "/api/create-payment-intent" "/api/stripe-config")
MISSING_ROUTES=()
for route in "${REQUIRED_ROUTES[@]}"; do
  if ! grep -q "$route" "$WORKER_DIR/src/index.js"; then
    MISSING_ROUTES+=("$route")
  fi
done

if [[ ${#MISSING_ROUTES[@]} -gt 0 ]]; then
  warn "Missing routes in source: ${MISSING_ROUTES[*]}"
else
  ok "All required routes present in source"
fi

# --- Deploy ---

if [[ "$CHECK_ONLY" == true ]]; then
  echo ""
  echo "Check-only mode. Skipping deploy."
else
  echo ""
  echo "Deploying..."
  cd "$WORKER_DIR"
  npx wrangler@3 deploy -c "$CONFIG" 2>&1 | tee /tmp/wrangler-deploy.log

  # Verify it deployed to the right worker
  if grep -q "Uploaded $WORKER_NAME" /tmp/wrangler-deploy.log; then
    ok "Deployed to $WORKER_NAME"
  else
    fail "Deploy output doesn't mention $WORKER_NAME — check /tmp/wrangler-deploy.log"
    exit 1
  fi

  # Verify bindings
  if grep -q "KV Namespaces" /tmp/wrangler-deploy.log; then
    ok "KV bindings present"
  else
    fail "No KV bindings in deploy output — wrangler may have read wrong config"
    exit 1
  fi
fi

# --- Verify secrets ---

echo ""
echo "Checking secrets..."
cd "$WORKER_DIR"
SECRETS=$(npx wrangler@3 secret list -c "$CONFIG" 2>/dev/null || echo "[]")

REQUIRED_SECRETS=("ANTHROPIC_API_KEY" "STRIPE_SECRET_KEY" "STRIPE_PUBLISHABLE_KEY" "RELAY_PRIVATE_KEY" "PINATA_JWT")
OPTIONAL_SECRETS=("STRIPE_WEBHOOK_SECRET" "GITHUB_TOKEN" "ADMIN_KEY")
MISSING_SECRETS=()

for secret in "${REQUIRED_SECRETS[@]}"; do
  if echo "$SECRETS" | grep -q "\"$secret\""; then
    ok "Secret: $secret"
  else
    fail "Missing required secret: $secret"
    MISSING_SECRETS+=("$secret")
  fi
done

for secret in "${OPTIONAL_SECRETS[@]}"; do
  if echo "$SECRETS" | grep -q "\"$secret\""; then
    ok "Secret: $secret"
  else
    warn "Optional secret missing: $secret"
  fi
done

if [[ ${#MISSING_SECRETS[@]} -gt 0 ]]; then
  echo ""
  echo -e "${RED}Missing required secrets. Set them with:${NC}"
  for s in "${MISSING_SECRETS[@]}"; do
    echo "  npx wrangler@3 secret put $s -c $CONFIG"
  done
fi

# --- Smoke tests ---

echo ""
echo "Smoke tests ($WORKER_URL):"

# Health check — stripe-config is lightweight
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$WORKER_URL/api/stripe-config" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  STRIPE_OK=$(curl -s "$WORKER_URL/api/stripe-config" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if d.get('configured') else 'no')" 2>/dev/null || echo "error")
  if [[ "$STRIPE_OK" == "yes" ]]; then
    ok "/api/stripe-config — Stripe configured"
  else
    warn "/api/stripe-config — Stripe not configured (secrets missing?)"
  fi
else
  fail "/api/stripe-config returned HTTP $HTTP_CODE"
fi

# ACH endpoint exists
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER_URL/api/create-ach-intent" -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "500" || "$HTTP_CODE" == "400" || "$HTTP_CODE" == "200" ]]; then
  ok "/api/create-ach-intent — endpoint reachable (HTTP $HTTP_CODE)"
else
  fail "/api/create-ach-intent returned HTTP $HTTP_CODE (expected 400/500 without valid body)"
fi

# Card PI endpoint exists
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER_URL/api/create-payment-intent" -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "500" || "$HTTP_CODE" == "400" || "$HTTP_CODE" == "200" ]]; then
  ok "/api/create-payment-intent — endpoint reachable (HTTP $HTTP_CODE)"
else
  fail "/api/create-payment-intent returned HTTP $HTTP_CODE"
fi

# Transfer endpoint exists
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WORKER_URL/api/transfer-to-operator" -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "500" || "$HTTP_CODE" == "400" || "$HTTP_CODE" == "200" ]]; then
  ok "/api/transfer-to-operator — endpoint reachable (HTTP $HTTP_CODE)"
else
  fail "/api/transfer-to-operator returned HTTP $HTTP_CODE"
fi

echo ""
echo "=== Done ==="
