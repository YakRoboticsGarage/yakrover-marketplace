"""YAK ROBOTICS — Standalone MCP server for construction survey marketplace.

Runs the full auction engine with 32 MCP tools and 7 Michigan construction
operators. Zero external dependencies beyond the auction/ package — no
yakrover-8004-mcp repo needed.

Usage:
    # Start locally
    PYTHONPATH=. uv run python mcp_server.py

    # With Cloudflare Tunnel (free public URL)
    PYTHONPATH=. uv run python mcp_server.py --tunnel

    # With bearer token auth
    MCP_BEARER_TOKEN=mysecret PYTHONPATH=. uv run python mcp_server.py

    # With SQLite persistence
    AUCTION_DB_PATH=./auction.db PYTHONPATH=. uv run python mcp_server.py

Then connect Claude Code:
    claude mcp add --transport http yak-robotics http://localhost:8001/mcp

Or Claude Desktop (add to config):
    {"mcpServers": {"yak-robotics": {"type": "http", "url": "http://localhost:8001/mcp"}}}

Then ask:
    "I need a topographic survey for a 3-mile highway corridor in Michigan"
"""

import argparse
import os
import subprocess
import sys
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

from auction.engine import AuctionEngine
from auction.wallet import WalletLedger
from auction.reputation import ReputationTracker
from auction.mock_fleet import create_construction_fleet
from auction.mcp_tools import register_auction_tools
from auction.core import log

# Optional persistence
try:
    from auction.store import SyncTaskStore
except ImportError:
    SyncTaskStore = None

# Optional Stripe
try:
    from auction.stripe_service import StripeService
except ImportError:
    StripeService = None


def build_engine():
    """Create and configure the auction engine with construction fleet."""
    # Wallet — auto-funded for demo
    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("500000"), note="Demo credits — $500K")
    log("SERVER", f"Buyer wallet: ${wallet.get_balance('buyer'):,}")

    # Reputation
    reputation = ReputationTracker()

    # Stripe (optional)
    stripe_service = None
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if stripe_key and StripeService:
        stripe_service = StripeService(api_key=stripe_key)
        log("SERVER", "Stripe: live (test mode)")
    else:
        log("SERVER", "Stripe: disabled (set STRIPE_SECRET_KEY to enable)")

    # SQLite (optional)
    store = None
    db_path = os.environ.get("AUCTION_DB_PATH")
    if db_path and SyncTaskStore:
        store = SyncTaskStore(db_path)
        store.initialize()
        log("SERVER", f"SQLite: {db_path}")
    else:
        log("SERVER", "SQLite: in-memory (set AUCTION_DB_PATH for persistence)")

    # Construction fleet — 7 Michigan operators
    fleet = create_construction_fleet()
    log("SERVER", f"Fleet: {len(fleet)} operators")
    for r in fleet:
        name = getattr(r, "name", r.robot_id)
        sensors = r.capability_metadata.get("sensors", [])
        sensor_str = ", ".join(sensors[:3])
        log("FLEET", f"  {name} ({r.robot_id}) — {sensor_str}")

    # Engine
    engine = AuctionEngine(
        fleet,
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_service,
    )

    return engine, wallet, stripe_service


def create_app():
    """Create the MCP server app with both MCP and REST endpoints."""
    from mcp.server.fastmcp import FastMCP
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route, Mount
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware

    engine, wallet, stripe_service = build_engine()

    mcp = FastMCP(
        "yak-robotics",
        instructions="""You are connected to the YAK ROBOTICS construction survey marketplace.

You have 32 tools for managing the full survey lifecycle:
- Process RFPs into task specs (auction_process_rfp)
- Post tasks and collect bids from 7 Michigan operators
- Review bids with compliance checks
- Verify payment bonds against real Treasury Circular 570 data
- Generate ConsensusDocs 750 agreements
- Track execution and manage multi-task projects

The buyer wallet is pre-funded with $500K demo credits.

Start by asking the user what survey they need, or process an RFP they provide.""",
    )

    register_auction_tools(mcp, engine, stripe_service=stripe_service)

    tool_count = len(mcp._tool_manager._tools)
    log("SERVER", f"Registered {tool_count} MCP tools")

    # --- REST API for tool calls (used by Cloudflare Worker demo) ---

    import asyncio
    import json

    async def handle_tool_call(request: Request) -> JSONResponse:
        """REST endpoint: POST /api/tool/{name} — calls an MCP tool by name."""
        tool_name = request.path_params["name"]
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        # Find the tool
        tools = mcp._tool_manager._tools
        if tool_name not in tools:
            return JSONResponse(
                {"error": f"Unknown tool: {tool_name}", "available": sorted(tools.keys())},
                status_code=404,
            )

        # Call the tool
        try:
            tool_fn = tools[tool_name].fn
            # MCP tools are async — call with the input as kwargs or positional
            if isinstance(body, dict):
                result = await tool_fn(**body)
            else:
                result = await tool_fn(body)
            return JSONResponse({"result": result})
        except TypeError as e:
            return JSONResponse({"error": f"Invalid parameters: {e}"}, status_code=400)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def handle_health(request: Request) -> JSONResponse:
        """Health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "tools": tool_count,
            "fleet": len(engine.robots),
            "wallet": str(wallet.get_balance("buyer")),
        })

    async def handle_tool_list(request: Request) -> JSONResponse:
        """List all available tools with descriptions."""
        tools_info = []
        for name, tool in sorted(mcp._tool_manager._tools.items()):
            desc = (tool.description or "")[:200]
            tools_info.append({"name": name, "description": desc})
        return JSONResponse({"tools": tools_info, "count": len(tools_info)})

    # Build combined app: REST routes + MCP mount
    mcp_starlette = mcp.streamable_http_app()

    app = Starlette(
        routes=[
            Route("/health", handle_health, methods=["GET"]),
            Route("/api/tools", handle_tool_list, methods=["GET"]),
            Route("/api/tool/{name}", handle_tool_call, methods=["POST"]),
            Mount("/mcp", app=mcp_starlette),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["https://yakrobot.bid", "http://localhost:*", "https://*.here.now"],
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["*"],
                allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.here\.now|https://yakrobot\.bid",
            ),
        ],
    )

    return app, mcp


def start_tunnel(port: int) -> str | None:
    """Start a Cloudflare Tunnel (free, no account needed)."""
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # cloudflared prints the URL to stderr
        import time
        for _ in range(30):
            line = proc.stderr.readline().decode()
            if "trycloudflare.com" in line or "cfargotunnel.com" in line:
                # Extract URL
                import re
                match = re.search(r"(https://[^\s]+)", line)
                if match:
                    return match.group(1)
            time.sleep(0.5)
        log("TUNNEL", "Timeout waiting for tunnel URL")
        return None
    except FileNotFoundError:
        log("TUNNEL", "cloudflared not found. Install: brew install cloudflared")
        return None


def main():
    parser = argparse.ArgumentParser(description="YAK ROBOTICS MCP Server")
    parser.add_argument("--port", type=int, default=8001, help="Port (default 8001)")
    parser.add_argument("--tunnel", action="store_true", help="Start Cloudflare Tunnel for public access")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")
    args = parser.parse_args()

    print()
    print("  YAK ROBOTICS — Construction Survey Marketplace")
    print("  =" * 25)
    print()

    app, mcp = create_app()

    # Tunnel
    tunnel_url = None
    if args.tunnel:
        log("TUNNEL", "Starting Cloudflare Tunnel...")
        tunnel_url = start_tunnel(args.port)
        if tunnel_url:
            log("TUNNEL", f"Public URL: {tunnel_url}")
        else:
            log("TUNNEL", "Failed to start tunnel. Server will run on localhost only.")

    base_url = tunnel_url or f"http://localhost:{args.port}"

    print()
    print("  Endpoints:")
    print(f"    MCP:    {base_url}/mcp")
    print(f"    REST:   {base_url}/api/tool/{{name}}")
    print(f"    Health: {base_url}/health")
    print(f"    Tools:  {base_url}/api/tools")
    print()
    print("  Connect Claude Code:")
    print(f"    claude mcp add --transport http yak-robotics {base_url}/mcp")
    print()
    print("  Connect Claude Desktop (add to config):")
    print(f'    {{"mcpServers": {{"yak-robotics": {{"type": "http", "url": "{base_url}/mcp"}}}}}}')
    print()
    print("  Then ask:")
    print('    "I need a topo survey for a highway project in Michigan"')
    print('    "Process this RFP: [paste RFP text]"')
    print('    "What operators are available for bridge inspection?"')
    print()

    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
