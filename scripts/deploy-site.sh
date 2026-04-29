#!/usr/bin/env bash
# Deploy a yakrobot.bid site to here.now.
#
# Slug + source dir are looked up from docs/SLUG_REGISTRY.yaml — never hardcoded
# here. Post-publish smoke test verifies the live <title> matches the source,
# which catches "wrong content uploaded to slug X" mistakes (the kind that
# accidentally turned yakrobot.bid into the Product Brief in April 2026).
#
# Usage:
#   ./scripts/deploy-site.sh landing   # demo/landing/     → yakrobot.bid/
#   ./scripts/deploy-site.sh demo      # demo/marketplace/ → yakrobot.bid/demo/
#   ./scripts/deploy-site.sh yaml      # demo/explorer/    → yakrobot.bid/yaml/
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY="$REPO_ROOT/docs/SLUG_REGISTRY.yaml"

TARGET="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}OK${NC}  $1"; }
warn() { echo -e "  ${YELLOW}WARN${NC}  $1"; }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; }

case "$TARGET" in
  landing) URL_SUFFIX="" ;;
  demo)    URL_SUFFIX="demo/" ;;
  yaml)    URL_SUFFIX="yaml/" ;;
  "")
    fail "Missing target. Usage: deploy-site.sh {landing|demo|yaml}"
    exit 1
    ;;
  *)
    fail "Unknown target '$TARGET'. Expected: landing|demo|yaml"
    exit 1
    ;;
esac

EXPECTED_URL="https://yakrobot.bid/${URL_SUFFIX}"

# Parse SLUG_REGISTRY.yaml: find the entry whose `url:` matches EXPECTED_URL,
# emit "<slug> <source>". Relies on field order: url → slug → source within
# each list item under `sites:`.
read -r SLUG SOURCE_REL < <(awk -v want="$EXPECTED_URL" '
  /^[[:space:]]*-[[:space:]]*url:/ { gsub(/["]/, ""); url=$3; slug=""; source="" }
  /^[[:space:]]*slug:/             { slug=$2 }
  /^[[:space:]]*source:/           { source=$2; if (url==want) { print slug, source; exit } }
' "$REGISTRY") || true

if [[ -z "${SLUG:-}" || -z "${SOURCE_REL:-}" ]]; then
  fail "No registry entry for $EXPECTED_URL in $REGISTRY"
  exit 1
fi

SOURCE_DIR="$REPO_ROOT/${SOURCE_REL%/}"

echo "=== Site Deploy: $EXPECTED_URL ==="
echo "  Target: $TARGET"
echo "  Source: $SOURCE_DIR"
echo "  Slug:   $SLUG"
echo ""

# --- Pre-flight ---

echo "Pre-flight checks:"

if [[ ! -f "$SOURCE_DIR/index.html" ]]; then
  fail "index.html not found in $SOURCE_DIR"
  exit 1
fi
ok "index.html exists"

if [[ ! -f ~/.herenow/credentials ]]; then
  fail "~/.herenow/credentials not found — authenticate with here.now first"
  exit 1
fi
ok "here.now credentials present"

PUBLISH_SCRIPT="$HOME/.claude/skills/here-now/scripts/publish.sh"
if [[ ! -x "$PUBLISH_SCRIPT" ]]; then
  fail "publish.sh not found at $PUBLISH_SCRIPT"
  exit 1
fi
ok "publish.sh available"

LOCAL_TITLE=$(grep -o '<title>[^<]*</title>' "$SOURCE_DIR/index.html" | head -1 || true)
if [[ -z "$LOCAL_TITLE" ]]; then
  warn "No <title> tag in source — smoke test will be skipped"
fi

# --- Build ---

echo ""
echo "Building..."

BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT
cp "$SOURCE_DIR"/* "$BUILD_DIR/" 2>/dev/null || true

if grep -q "__BUILD_TIMESTAMP__" "$BUILD_DIR/index.html" 2>/dev/null; then
  TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
  sed -i '' "s|__BUILD_TIMESTAMP__|$TIMESTAMP|g" "$BUILD_DIR/index.html"
  ok "Build timestamp: $TIMESTAMP"
fi

FILE_COUNT=$(ls "$BUILD_DIR" | wc -l | tr -d ' ')
ok "Build ready ($FILE_COUNT files)"

# --- Deploy ---

echo ""
echo "Deploying..."

"$PUBLISH_SCRIPT" "$BUILD_DIR" --slug "$SLUG" --client claude-code 2>&1

# --- Verify ---

echo ""
echo "Verifying..."

sleep 3
CANONICAL_URL="https://${SLUG}.here.now/"

if [[ -n "$LOCAL_TITLE" ]]; then
  REMOTE_TITLE=$(curl -s "$CANONICAL_URL" 2>/dev/null | grep -o '<title>[^<]*</title>' | head -1 || true)
  if [[ "$REMOTE_TITLE" == "$LOCAL_TITLE" ]]; then
    ok "Title matches source: $LOCAL_TITLE"
  else
    fail "Title mismatch — published content does not match source"
    fail "  Expected: $LOCAL_TITLE"
    fail "  Got:      $REMOTE_TITLE"
    fail "  Slug $SLUG may have been deployed with the wrong source dir."
    exit 1
  fi
fi

PUBLIC_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$EXPECTED_URL" 2>/dev/null || echo "000")
if [[ "$PUBLIC_CODE" == "200" ]]; then
  ok "$EXPECTED_URL is live (HTTP $PUBLIC_CODE)"
else
  warn "$EXPECTED_URL returned HTTP $PUBLIC_CODE (may need propagation time)"
fi

echo ""
echo "=== Done ==="
