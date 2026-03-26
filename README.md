# Robot Task Auction Marketplace

A standalone marketplace module where AI agents post tasks, physical robots bid, and winners are paid via Stripe (fiat) or crypto.

## Related Repositories

| Repository | What it contains |
|-----------|-----------------|
| **[robot-marketplace](https://github.com/YakRoboticsGarage/robot-marketplace)** (this repo) | The marketplace code — auction engine, wallet, scoring, MCP tools, tests |
| **[yakrover-protocols/marketplace](https://github.com/YakRoboticsGarage/yakrover-protocols/tree/main/marketplace)** | Protocol specification — user journey, decisions, diagrams, research |
| **[yakrover-8004-mcp](https://github.com/YakRoboticsGarage/yakrover-8004-mcp)** | Robot framework — MCP servers, ERC-8004 discovery, robot plugins |

## Quick Start

**Run as an MCP server** (connect Claude Code directly):

```bash
# 1. Clone this repo + the robot framework
git clone https://github.com/YakRoboticsGarage/robot-marketplace.git
git clone https://github.com/YakRoboticsGarage/yakrover-8004-mcp.git

# 2. Install dependencies
cd robot-marketplace && uv sync

# 3. Terminal 1 — start the robot simulator
cd ../yakrover-8004-mcp
PYTHONPATH=src uv run python -m robots.fakerover.simulator

# 4. Terminal 2 — start the auction MCP server
cd ../robot-marketplace
PYTHONPATH=.:../yakrover-8004-mcp/src uv run python serve_with_auction.py

# 5. Connect Claude Code
claude mcp add --transport http fleet http://localhost:8000/fleet/mcp

# 6. Talk naturally:
#   "Check the temperature in Bay 3"
#   "What robots are available?"
```

**Or run the standalone demo** (no MCP connection needed):

```bash
# Terminal 1: Start the robot simulator
cd yakrover-8004-mcp
PYTHONPATH=src uv run python -m robots.fakerover.simulator

# Terminal 2: Run the auction demo
cd robot-marketplace
PYTHONPATH=. uv run python auction/demo.py
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full walkthrough including Stripe setup.

## Architecture

```
robot-marketplace/              ← This repo
├── auction/
│   ├── core.py                 # Data types, scoring, signing, constraints
│   ├── engine.py               # AuctionEngine — 11-state lifecycle, wallet, reputation
│   ├── wallet.py               # Internal ledger + Stripe wallet service
│   ├── reputation.py           # Computed from task history
│   ├── store.py                # SQLite persistence
│   ├── stripe_service.py       # Stripe SDK wrapper (stub/live dual mode)
│   ├── mcp_tools.py            # 15 FastMCP tools for fleet server
│   ├── discovery_bridge.py     # ERC-8004 discovery → auction adapter
│   ├── mock_fleet.py           # 5 simulated robots for demo/testing
│   ├── demo.py                 # 5-scenario demo
│   └── tests/                  # 151 tests
├── serve_with_auction.py       # MCP server launcher
├── docs/                       # Architecture docs
└── research/                   # Research synthesis

yakrover-8004-mcp/              ← Peer dependency (robot framework)
├── src/core/plugin.py          # RobotPlugin with bid() method
├── src/core/server.py          # Fleet server with auction_engine hook
└── src/robots/fakerover/       # Simulated robot with bid() override
```

The marketplace connects to `yakrover-8004-mcp` via the `discovery_bridge.py` adapter. If the robot framework isn't installed, mock robots work standalone.

## Key Numbers

- **15 MCP tools** including `auction_quick_hire` (single-call auctions)
- **151 tests**, all passing
- **5 demo scenarios** — happy path, no robots, cheapest loses, timeout recovery, bad payload rejection
- **Stripe integration** verified with real test-mode transfers (EUR 0.35 → operator)
- **SQLite persistence** with write-through on every state transition
- **Ed25519 signing** with HMAC fallback
- **Structured error responses** — `error_code`/`message`/`hint`, never raw Python exceptions
- **State-aware navigation** — `next_action`, `available_actions` guide agents through the lifecycle

## Running Tests

```bash
cd robot-marketplace
PYTHONPATH=. uv run python -m pytest auction/tests/ -v
```

## Documentation

| Document | Description |
|----------|-------------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Step-by-step setup guide with Stripe |
| [docs/USER_JOURNEY.md](docs/USER_JOURNEY.md) | The product story — what users experience |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Product roadmap v0.1 → v2.0 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every product and technical decision |
| [docs/SCOPE.md](docs/SCOPE.md) | What's real, stubbed, or cut per version |
| [docs/DIAGRAM_SYSTEM.md](docs/DIAGRAM_SYSTEM.md) | Architecture and scoring diagrams (Mermaid) |
| [docs/DIAGRAM_USER_JOURNEY.md](docs/DIAGRAM_USER_JOURNEY.md) | User journey diagrams (Mermaid) |

Full protocol specification: [yakrover-protocols/marketplace](https://github.com/YakRoboticsGarage/yakrover-protocols/tree/main/marketplace)

## License

Apache 2.0
