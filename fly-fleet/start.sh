#!/bin/bash
set -e

cd /app

echo "=== Starting Fakerover Simulator (port 8080) ==="
PYTHONPATH=src uv run python -m robots.fakerover.simulator &

# Wait for simulator to be ready
sleep 2

echo "=== Starting Robot MCP Server (port 8000) ==="
PYTHONPATH=src uv run python scripts/serve.py --robots fakerover --port 8000
