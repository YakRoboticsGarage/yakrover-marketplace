#!/usr/bin/env bash
# Deploy the demo frontend to here.now (yakrobot.bid/mcp-demo).
#
# Usage:
#   ./scripts/deploy-demo.sh                  # deploy marketplace demo to yakrobot.bid/demo
#   ./scripts/deploy-demo.sh --dir demo/marketplace  # explicit source dir
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Slug from docs/SLUG_REGISTRY.yaml — yakrobot.bid/demo/
SLUG="sturdy-riddle-vvar"
DEMO_DIR="${1:-$REPO_ROOT/demo/marketplace}"

# Parse --dir flag
if [[ "${1:-}" == "--dir" ]]; then
  DEMO_DIR="${2:?Usage: deploy-demo.sh --dir <path>}"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}OK${NC}  $1"; }
warn() { echo -e "  ${YELLOW}WARN${NC}  $1"; }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; }

echo "=== Demo Deploy: yakrobot.bid/mcp-demo ==="
echo "  Source: $DEMO_DIR"
echo "  Slug:   $SLUG"
echo ""

# --- Pre-flight ---

echo "Pre-flight checks:"

if [[ ! -f "$DEMO_DIR/index.html" ]]; then
  fail "index.html not found in $DEMO_DIR"
  exit 1
fi
ok "index.html exists"

# Check here.now credentials
if [[ ! -f ~/.herenow/credentials ]]; then
  fail "~/.herenow/credentials not found — authenticate with here.now first"
  exit 1
fi
ok "here.now credentials present"

# Check publish script
PUBLISH_SCRIPT="$HOME/.claude/skills/here-now/scripts/publish.sh"
if [[ ! -x "$PUBLISH_SCRIPT" ]]; then
  fail "publish.sh not found at $PUBLISH_SCRIPT"
  exit 1
fi
ok "publish.sh available"

# Check WORKER_BASE points to correct worker
WORKER_BASE=$(grep "WORKER_BASE" "$DEMO_DIR/index.html" | head -1 | sed "s/.*'\(https:[^']*\)'.*/\1/" || echo "not found")
echo "  Worker URL in demo: $WORKER_BASE"

# --- Build ---

echo ""
echo "Building..."

# Copy to temp dir so we don't modify source
BUILD_DIR=$(mktemp -d)
cp "$DEMO_DIR"/* "$BUILD_DIR/" 2>/dev/null || true

# Stamp build timestamp (only if placeholder exists)
if grep -q "__BUILD_TIMESTAMP__" "$BUILD_DIR/index.html"; then
  TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
  sed -i '' "s|__BUILD_TIMESTAMP__|$TIMESTAMP|g" "$BUILD_DIR/index.html"
  ok "Build timestamp: $TIMESTAMP"
else
  warn "No __BUILD_TIMESTAMP__ placeholder found"
fi

FILE_COUNT=$(ls "$BUILD_DIR" | wc -l | tr -d ' ')
ok "Build ready ($FILE_COUNT files)"

# --- Deploy ---

echo ""
echo "Deploying..."

"$PUBLISH_SCRIPT" "$BUILD_DIR" --slug "$SLUG" --client claude-code 2>&1

# --- Cleanup ---

rm -rf "$BUILD_DIR"

# --- Verify ---

echo ""
echo "Verifying..."

SITE_URL="https://yakrobot.bid/mcp-demo/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  ok "$SITE_URL is live (HTTP $HTTP_CODE)"
else
  warn "$SITE_URL returned HTTP $HTTP_CODE (may need propagation time)"
fi

echo ""
echo "=== Done ==="
