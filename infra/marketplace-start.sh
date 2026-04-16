#!/bin/bash
# Start all 3 services for the marketplace demo
# Runs inside the Fly.io container

set -e

echo "=== Starting Fakerover Simulator (port 8080) ==="
cd /app/yakrover-8004-mcp
PYTHONPATH=src python -m robots.fakerover.simulator &

echo "=== Starting Robot MCP Server (port 8000) ==="
PYTHONPATH=src python scripts/serve.py --robots fakerover --port 8000 &

echo "=== Starting Marketplace MCP Server (port 8001) ==="
cd /app/marketplace
PYTHONPATH=. python mcp_server.py --port 8001

# mcp_server.py runs in foreground — if it dies, container restarts
