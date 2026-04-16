#!/bin/bash
# Pull worker feedback from Cloudflare KV into docs/feedback/worker-feedback-log.json
#
# Usage: cd worker && ./pull-feedback.sh
#
# Requires: wrangler authenticated (npx wrangler whoami)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WRANGLER="node ${SCRIPT_DIR}/node_modules/wrangler/bin/wrangler.js"
KV_ID="13e99192baa4498b9879087c0fec8746"
OUTPUT="${SCRIPT_DIR}/../docs/feedback/worker-feedback-log.json"

echo "Fetching feedback keys from KV..."
KEYS=$($WRANGLER kv key list --namespace-id="$KV_ID" 2>/dev/null | grep -o '"name":"feedback:[^"]*"' | sed 's/"name":"//;s/"//')

if [ -z "$KEYS" ]; then
  echo "No feedback entries found."
  exit 0
fi

COUNT=0
ENTRIES="["

while IFS= read -r key; do
  if [ $COUNT -gt 0 ]; then
    ENTRIES="${ENTRIES},"
  fi
  VALUE=$($WRANGLER kv key get --namespace-id="$KV_ID" "$key" 2>/dev/null)
  ENTRIES="${ENTRIES}${VALUE}"
  COUNT=$((COUNT + 1))
done <<< "$KEYS"

ENTRIES="${ENTRIES}]"

mkdir -p "$(dirname "$OUTPUT")"
echo "$ENTRIES" | python3 -m json.tool > "$OUTPUT"

echo "Pulled $COUNT feedback entries to $OUTPUT"
