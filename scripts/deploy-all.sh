#!/usr/bin/env bash
# Deploy everything: worker + demo frontend.
#
# Usage:
#   ./scripts/deploy-all.sh          # deploy worker then demo
#   ./scripts/deploy-all.sh --check  # pre-flight checks only
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  Full Deploy: Worker + Demo"
echo "=========================================="
echo ""

"$SCRIPT_DIR/deploy-worker.sh" "${1:-}"

echo ""
echo "=========================================="

"$SCRIPT_DIR/deploy-demo.sh"

echo ""
echo "=========================================="
echo "  All deployments complete."
echo "  Worker: https://yakrobot-chat.rafaeldf2.workers.dev"
echo "  Demo:   https://yakrobot.bid/mcp-demo/"
echo "=========================================="
