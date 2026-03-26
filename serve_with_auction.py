"""
Start the MCP gateway with the auction marketplace enabled.

This wraps the standard yakrover serve.py and adds:
- An AuctionEngine with wallet, reputation, and optional Stripe/SQLite
- 15 auction MCP tools registered on the fleet server
- Mock robots for the auction (alongside real MCP robot plugins)

Usage:
    # From the repo root:
    PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py

    # With fakerover only:
    PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py --robots fakerover

    # With Stripe (test mode):
    STRIPE_SECRET_KEY=sk_test_xxx PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py

    # With persistent SQLite:
    AUCTION_DB_PATH=./auction.db PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py

Then connect Claude Code:
    claude mcp add --transport http fleet http://localhost:8000/fleet/mcp

And talk naturally:
    "Check the temperature in Bay 3"
    "What robots are available?"
    "Fund my wallet with $5"
"""

import argparse
import os
import sys

# Ensure src/ and marketplace/ are on the path
repo_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(repo_root, "src"))
sys.path.insert(0, os.path.join(repo_root, "marketplace"))

from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

import uvicorn

from robots import discover_plugins
from core.server import create_robot_server, create_fleet_server, _compose_lifespans
from core.plugin import RobotPlugin
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastmcp import FastMCP

# Auction imports
from auction.engine import AuctionEngine
from auction.wallet import WalletLedger
from auction.reputation import ReputationTracker
from auction.mock_fleet import create_demo_fleet
from auction.mcp_tools import register_auction_tools
from auction.core import log

# Optional: Stripe and SQLite
try:
    from auction.stripe_service import StripeService
except ImportError:
    StripeService = None

try:
    from auction.store import SyncTaskStore
except ImportError:
    SyncTaskStore = None


def build_auction_engine():
    """Create and configure the AuctionEngine with all v1.0 features."""

    # Wallet
    wallet = WalletLedger()
    wallet.create_wallet("buyer", Decimal("0"))
    wallet.fund_wallet("buyer", Decimal("10.00"), note="Default demo credits")
    log("AUCTION", f"Buyer wallet created: ${wallet.get_balance('buyer')}")

    # Reputation
    reputation = ReputationTracker()

    # Stripe (optional)
    stripe_service = None
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if stripe_key and StripeService:
        stripe_service = StripeService(api_key=stripe_key)
        log("AUCTION", "Stripe: live (test mode)")
    else:
        if StripeService:
            stripe_service = StripeService(api_key=None)  # stub mode
        log("AUCTION", "Stripe: stub (set STRIPE_SECRET_KEY for live)")

    # SQLite (optional)
    store = None
    db_path = os.environ.get("AUCTION_DB_PATH")
    if db_path and SyncTaskStore:
        store = SyncTaskStore(db_path)
        store.initialize()
        log("AUCTION", f"SQLite: {db_path}")
    else:
        log("AUCTION", "SQLite: disabled (set AUCTION_DB_PATH to enable)")

    # Robot fleet — use mock robots for now
    # TODO: Replace with discover_and_adapt() for on-chain robot discovery
    fleet = create_demo_fleet()
    log("AUCTION", f"Fleet: {len(fleet)} mock robots ({', '.join(r.robot_id for r in fleet)})")

    # Build engine
    engine = AuctionEngine(
        fleet,
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_service,
    )

    return engine, wallet, reputation


def create_auction_gateway(plugins: dict[str, RobotPlugin]) -> FastAPI:
    """Create the FastAPI gateway with auction tools on the fleet server."""

    engine, wallet, reputation = build_auction_engine()

    mcp_apps = {}
    mounted_robots: dict[str, str] = {}
    for name, plugin in plugins.items():
        mcp = create_robot_server(plugin)
        mcp_apps[name] = mcp.http_app()
        mounted_robots[name] = f"/{name}/mcp"

    # Fleet server with auction tools
    fleet_mcp = create_fleet_server(
        mounted_robots=mounted_robots,
        auction_engine=engine,
    )
    mcp_apps["fleet"] = fleet_mcp.http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with _compose_lifespans(mcp_apps.values()):
            yield

    app = FastAPI(title="Robot Fleet Gateway + Marketplace", lifespan=lifespan)

    for name, mcp_app in mcp_apps.items():
        app.mount(f"/{name}", mcp_app)

    @app.get("/")
    async def index():
        return {
            "service": "Robot Fleet Gateway + Marketplace",
            "robots": {
                name: {
                    "mcp_endpoint": f"/{name}/mcp",
                    "tools": plugin.tool_names(),
                }
                for name, plugin in plugins.items()
            },
            "fleet_endpoint": "/fleet/mcp",
            "auction": {
                "enabled": True,
                "wallet_balance": str(wallet.get_balance("buyer")),
                "stripe_mode": "live" if os.environ.get("STRIPE_SECRET_KEY") else "stub",
                "robots": [r.robot_id for r in engine.robots],
            },
        }

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start robot fleet gateway with auction marketplace")
    parser.add_argument("--robots", nargs="*", help="Robot plugins to load (default: all)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--ngrok", action="store_true", help="Open an ngrok tunnel")
    args = parser.parse_args()

    # Discover robot plugins
    all_plugins = discover_plugins()
    if args.robots:
        unknown = set(args.robots) - set(all_plugins.keys())
        if unknown:
            print(f"Unknown robot(s): {unknown}. Available: {list(all_plugins.keys())}")
            sys.exit(1)
        selected = {k: v for k, v in all_plugins.items() if k in args.robots}
    else:
        selected = all_plugins

    if not selected:
        print("No robot plugins found. Check src/robots/ for plugin packages.")
        sys.exit(1)

    plugins = {name: cls() for name, cls in selected.items()}

    print()
    print("Robot Fleet Gateway + Marketplace")
    print("=" * 40)
    print()
    print(f"Robot plugins ({len(plugins)}):")
    for name, plugin in plugins.items():
        meta = plugin.metadata()
        print(f"  /{name}/mcp — {meta.name} ({len(plugin.tool_names())} tools)")
    print(f"  /fleet/mcp  — Fleet orchestrator + 15 auction tools")
    print()

    app = create_auction_gateway(plugins)

    if args.ngrok:
        from core.tunnel import start_tunnel
        public_url = start_tunnel(args.port)
        print(f"ngrok tunnel: {public_url}")
        print(f"  {public_url}/fleet/mcp")
        for name in plugins:
            print(f"  {public_url}/{name}/mcp")

    print()
    print("Connect Claude Code:")
    print(f"  claude mcp add --transport http fleet http://localhost:{args.port}/fleet/mcp")
    print()
    print("Then ask:")
    print('  "Check the temperature in Bay 3"')
    print('  "What robots are available?"')
    print('  "Fund my wallet with $5"')
    print()

    try:
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    except KeyboardInterrupt:
        print("\nShutting down.")
