# Robot Task Auction Marketplace

A task auction layer for the yakrover-8004-mcp framework. AI agents post tasks, physical robots bid, winners are paid via Stripe (fiat) or crypto, and digital payloads are delivered.

## Quick Start

See [GETTING_STARTED.md](GETTING_STARTED.md) for a full walkthrough. The short version:

```bash
# Start the MCP server with auction tools:
PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py

# Connect Claude Code:
claude mcp add --transport http fleet http://localhost:8000/fleet/mcp

# Then talk naturally:
#   "Check the temperature in Bay 3"
#   "What robots are available?"
```

Or run the standalone demo (no MCP connection needed):

```bash
# Terminal 1: Start the robot simulator
cd yakrover-8004-mcp
PYTHONPATH=src uv run python -m robots.fakerover.simulator

# Terminal 2: Run the auction demo
cd yakrover-8004-mcp
PYTHONPATH=marketplace uv run python marketplace/auction/demo.py
```

## What It Does

Three robots discover a temperature-reading task. A drone is filtered out (wrong sensors). Two rovers compete. The scoring function picks the best value — not just the cheapest. The winner reads a real sensor. Payment settles via Stripe.

Five demo scenarios: happy path, no capable robots, cheapest doesn't win, robot timeout with re-pool, bad payload with rejection and re-pool.

## Architecture

```
marketplace/
├── auction/
│   ├── core.py              # Data types, scoring, signing, constraints
│   ├── engine.py            # AuctionEngine — 11-state lifecycle, wallet, reputation
│   ├── wallet.py            # Internal ledger + Stripe wallet service
│   ├── reputation.py        # Computed from task history
│   ├── store.py             # SQLite persistence
│   ├── stripe_service.py    # Stripe SDK wrapper (stub/live dual mode)
│   ├── mcp_tools.py         # 15 FastMCP tools for fleet server
│   ├── discovery_bridge.py  # ERC-8004 discovery → auction adapter
│   ├── mock_fleet.py        # 5 simulated robots for demo/testing
│   ├── demo.py              # Runnable 5-scenario demo
│   └── tests/               # 151 tests across 10 test files
├── serve_with_auction.py      # Run as MCP server — connect Claude Code directly
├── docs/
│   ├── USER_JOURNEY.md      # Product story (investor-ready)
│   ├── ROADMAP.md           # v0.1 → v2.0 timeline
│   ├── DECISIONS.md         # All product/tech decisions (single source of truth)
│   └── SCOPE.md             # What's real vs stubbed per version
└── research/
    └── RESEARCH_SYNTHESIS.md # Research findings from 8 streams
```

## Key Numbers

- **~11,400 lines** of code across 35 files
- **151 tests** across 10 test files, all passing
- **15 MCP tools** for fleet server integration (including `auction_quick_hire` — the simplest way to use the marketplace)
- **5 demo scenarios** exercising happy path, failure recovery, and scoring
- **Stripe integration** with real test-mode payments verified
- **SQLite persistence** with write-through on every state transition
- **Ed25519 signing** with HMAC fallback for backward compatibility
- **Structured error responses** — every tool returns `error_code`/`message`/`hint`, never Python exceptions
- **`serve_with_auction.py`** — run the full MCP server and connect Claude Code directly

## Upstream Changes

Three files in the parent repo were modified to support the marketplace:

| File | Change |
|------|--------|
| `src/core/plugin.py` | Added `bid()` method to `RobotPlugin` (default returns None — backward compatible) |
| `src/core/server.py` | Added `auction_engine` parameter to `create_fleet_server()` (opt-in) |
| `src/robots/fakerover/__init__.py` | Added `bid()` override that queries simulator for live state |

All changes are backward-compatible. Existing robot plugins and fleet server behavior are unchanged when the marketplace is not configured.

## Running Tests

```bash
cd yakrover-8004-mcp
PYTHONPATH=marketplace uv run python -m pytest marketplace/auction/tests/ -v
```

## Documentation

| Document | Description |
|----------|-------------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Step-by-step setup guide with Stripe |
| [docs/USER_JOURNEY.md](docs/USER_JOURNEY.md) | The product story — what users experience |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Product roadmap v0.1 → v2.0 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every product and technical decision |
| [docs/SCOPE.md](docs/SCOPE.md) | What's real, stubbed, or cut per version |
