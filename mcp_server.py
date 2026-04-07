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
from auction.mock_fleet import create_full_fleet
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


def _discover_onchain_robots():
    """Query ERC-8004 subgraph for yakrover robots and create MCP adapters."""
    import httpx
    from auction.mcp_robot_adapter import MCPRobotAdapter

    SUBGRAPH_URL = "https://gateway.thegraph.com/api/536c6d8572876cabea4a4ad0fa49aa57/subgraphs/id/43s9hQRurMGjuYnC1r2ZwS6xSQktbFyXMPMqGKUFJojb"
    YAKROVER_HEX = "0x79616b726f766572"

    query = (
        '{ agentMetadata_collection(where: {key: "fleet_provider", value: "'
        + YAKROVER_HEX
        + '"}, first: 20) { agent { agentId owner registrationFile { name description active mcpEndpoint } '
        'metadata(first: 10) { key value } } } }'
    )

    resp = httpx.post(SUBGRAPH_URL, json={"query": query}, timeout=10.0)
    data = resp.json()

    agents = data.get("data", {}).get("agentMetadata_collection", [])
    adapters = []

    for entry in agents:
        agent = entry.get("agent", {})
        rf = agent.get("registrationFile", {})
        meta = {m["key"]: m["value"] for m in agent.get("metadata", [])}

        name = rf.get("name", "Robot")
        mcp_endpoint = rf.get("mcpEndpoint", "")
        wallet = meta.get("agentWallet")
        active = rf.get("active", False)

        # Skip robots without a real MCP endpoint
        if not mcp_endpoint or "placeholder" in mcp_endpoint or not active:
            log("DISCOVERY", f"  Skip {name}: no MCP endpoint or inactive")
            continue

        # Bearer token for authenticated robot MCP servers
        fleet_token = os.environ.get("FLEET_MCP_TOKEN")

        adapter = MCPRobotAdapter(
            robot_id=name,
            mcp_endpoint=mcp_endpoint,
            wallet=wallet,
            chain_id=8453,
            description=rf.get("description", ""),
            bearer_token=fleet_token,
        )
        adapters.append(adapter)
        log("DISCOVERY", f"  {name} — {mcp_endpoint[:50]}...")

    return adapters


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

    # Start with mock fleet (fast startup)
    fleet = create_full_fleet()
    log("SERVER", f"Fleet: {len(fleet)} operators (mock fleet — on-chain discovery on first request)")

    # Event tracking
    from auction.events import EventEmitter
    events = EventEmitter(store=store)
    log("SERVER", "Event tracking enabled")

    # Engine
    engine = AuctionEngine(
        fleet,
        wallet=wallet,
        reputation=reputation,
        store=store,
        stripe_service=stripe_service,
        events=events,
    )

    # Lazy discovery: runs once on first auction request, then caches
    engine._discovery_done = False
    engine._simulator_only = False

    def discover_and_swap_fleet():
        """Discover on-chain robots, probe liveness, hot-swap the engine fleet."""
        if engine._discovery_done:
            return
        engine._discovery_done = True

        try:
            from auction.mcp_robot_adapter import MCPRobotAdapter
            discovered = _discover_onchain_robots()
            if not discovered:
                log("DISCOVERY", "No on-chain robots found — keeping mock fleet")
                return

            # Pre-wake Fly fleet server (cold starts take 10-15s)
            try:
                import httpx as _httpx
                _httpx.get("https://yakrover-fleet.fly.dev/", timeout=20.0)
                log("PROBE", "Fleet server warmed up")
            except Exception:
                log("PROBE", "Fleet server warm-up failed (may be starting)")

            log("PROBE", f"Probing {len(discovered)} robot(s) in parallel...")
            import concurrent.futures

            def _probe(adapter):
                return adapter, adapter.is_reachable(timeout=15.0)

            real_online, sim_online = [], []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(discovered)) as pool:
                for adapter, reachable in pool.map(_probe, discovered):
                    kind = "simulator" if adapter.is_simulator else "real"
                    if reachable:
                        if adapter.is_simulator:
                            # Only include simulators on our infrastructure (Fly.io = always on)
                            if "fly.dev" in adapter.mcp_endpoint:
                                sim_online.append(adapter)
                                log("PROBE", f"  ✓ {adapter.robot_id} ({kind}, fly.dev)")
                            else:
                                log("PROBE", f"  ~ {adapter.robot_id} ({kind}, external — skipped)")
                        else:
                            real_online.append(adapter)
                            log("PROBE", f"  ✓ {adapter.robot_id} ({kind})")
                    else:
                        log("PROBE", f"  ✗ {adapter.robot_id} ({kind})")

            from auction.mock_fleet import create_construction_fleet
            if real_online and not engine._simulator_only:
                new_fleet = create_construction_fleet() + real_online
                label = f"{len(real_online)} real robot(s) — simulators excluded"
            elif sim_online:
                new_fleet = create_construction_fleet() + sim_online
                label = f"{len(sim_online)} simulator(s) — no real robots"
            else:
                log("DISCOVERY", "No robots reachable — keeping mock fleet")
                return

            engine.robots = new_fleet
            engine._robots_by_id = {r.robot_id: r for r in new_fleet}
            log("SERVER", f"Fleet updated: {len(new_fleet)} operators ({label})")

        except Exception as e:
            log("DISCOVERY", f"Discovery failed: {e}")
            engine._discovery_done = False  # Allow retry on next request

    engine._discover = discover_and_swap_fleet

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

        # Lazy discovery: run on first auction-related call
        if tool_name in ("auction_post_task", "auction_process_rfp") and hasattr(engine, "_discover"):
            import asyncio
            await asyncio.to_thread(engine._discover)

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

    async def handle_feedback_onchain(request: Request) -> JSONResponse:
        """Submit feedback to ERC-8004 reputation registry on-chain via agent0-sdk."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        agent_id = body.get("agent_id")  # e.g. "8453:38947"
        rating = body.get("rating", 0)  # 1-5 stars
        comment = body.get("comment", "")
        task_description = body.get("task_description", "")
        payment_tx = body.get("payment_tx", "")
        buyer_address = body.get("buyer_address", "")

        if not agent_id or not rating:
            return JSONResponse({"error": "agent_id and rating required"}, status_code=400)

        # Use relay wallet for feedback (doesn't own any robots → no self-feedback block)
        # Falls back to SIGNER_PVT_KEY if relay not available
        signer_key = os.environ.get("RELAY_PRIVATE_KEY") or os.environ.get("SIGNER_PVT_KEY")
        pinata_jwt = os.environ.get("PINATA_JWT")

        if not signer_key:
            return JSONResponse({"error": "No signer key configured for on-chain feedback"}, status_code=500)

        try:
            from agent0_sdk import SDK

            sdk_kwargs = dict(
                chainId=8453,
                rpcUrl="https://1rpc.io/base",
                signer=signer_key,
            )
            if pinata_jwt:
                sdk_kwargs["ipfs"] = "pinata"
                sdk_kwargs["pinataJwt"] = pinata_jwt

            sdk = SDK(**sdk_kwargs)

            feedback_file = {
                "text": comment or f"{rating}/5 stars",
                "task": task_description,
                "skill": "env_sensing",
                "capability": "temperature,humidity",
                "proofOfPayment": payment_tx,
                "buyerAddress": buyer_address,
                "submittedVia": "yakrobot.bid marketplace",
            }

            # value: rating scaled to 0-100 (1 star=20, 5 stars=100)
            value = rating * 20

            log("FEEDBACK", f"Submitting on-chain feedback for {agent_id}: {value}/100")
            tx = sdk.giveFeedback(
                agentId=agent_id,
                value=value,
                tag1="marketplace",
                tag2="env_sensing",
                feedbackFile=feedback_file if pinata_jwt else None,
            )
            log("FEEDBACK", f"Transaction submitted: {tx.tx_hash}")
            mined = tx.wait_mined(timeout=60)
            log("FEEDBACK", f"Feedback mined for {agent_id}")

            return JSONResponse({
                "ok": True,
                "agent_id": agent_id,
                "tx_hash": tx.tx_hash,
                "value": value,
                "8004scan_url": f"https://8004scan.io/agents/base/{agent_id.split(':')[-1]}?tab=feedback",
            })
        except Exception as e:
            log("FEEDBACK", f"On-chain feedback failed: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    async def handle_fleet_mode(request: Request) -> JSONResponse:
        """Set fleet mode: simulator_only=true excludes real robots."""
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        sim_only = body.get("simulator_only", False)
        old_mode = engine._simulator_only
        engine._simulator_only = sim_only

        # Force re-discovery if mode changed
        if sim_only != old_mode:
            engine._discovery_done = False
            log("SERVER", f"Fleet mode changed: simulator_only={sim_only} — re-discovery on next request")

        return JSONResponse({"ok": True, "simulator_only": sim_only})

    # Build combined app: REST routes + MCP mount
    mcp_starlette = mcp.streamable_http_app()

    app = Starlette(
        routes=[
            Route("/health", handle_health, methods=["GET"]),
            Route("/api/tools", handle_tool_list, methods=["GET"]),
            Route("/api/tool/{name}", handle_tool_call, methods=["POST"]),
            Route("/api/fleet-mode", handle_fleet_mode, methods=["POST"]),
            Route("/api/feedback-onchain", handle_feedback_onchain, methods=["POST"]),
            Mount("/mcp", app=mcp_starlette),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["https://yakrobot.bid", "https://yakrover.online", "http://localhost:*", "https://*.here.now"],
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["*"],
                allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.here\.now|https://yakrobot\.bid|https://.*\.yakrover\.online",
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
