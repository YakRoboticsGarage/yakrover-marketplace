#!/bin/bash
# Start the MCP server with a free Cloudflare Tunnel.
# Gives a public URL anyone can connect their Claude to.
#
# Install cloudflared: brew install cloudflared
# Usage: ./deploy/tunnel.sh [port]

set -e

PORT=${1:-8001}
DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "  YAK ROBOTICS — Starting MCP server with tunnel"
echo "  ================================================"
echo ""

# Check cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "  cloudflared not found. Install:"
    echo "    brew install cloudflared"
    echo "    # or: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
fi

cd "$DIR"
PYTHONPATH=. uv run python mcp_server.py --port "$PORT" --tunnel
