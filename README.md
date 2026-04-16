# Robot Task Auction Protocol

An open protocol for agent-mediated procurement of physical-world tasks. AI agents post structured task specifications, qualified executors (robots or human operators) bid autonomously, completion is verified algorithmically, and payment settles programmatically.

The first vertical is **construction site surveying**. The protocol is domain-agnostic.

**Live demo:** [yakrobot.bid/demo](https://yakrobot.bid/demo/) — 100 robots across 18 Michigan operators, 9 RFP presets, EAS attestation, geographic filtering

## Why This Exists

Physical-world tasks — surveying a highway corridor, inspecting a bridge deck, scanning a foundation — are procured through phone calls, personal networks, and repeat engagements. This works because each task requires human judgment to scope, quality verification requires physical presence, and the cost of a bad decision is high and irreversible.

A task becomes liquid — algorithmically discoverable, matchable, executable, verifiable, and settleable — when four preconditions are met:

1. **Structured specification.** The task is describable in machine-readable terms precise enough to determine what constitutes successful completion. Construction, infrastructure, and environmental monitoring have decades of regulatory standards that define tasks numerically.

2. **Qualified executor discovery.** The system can determine, programmatically, whether a given executor is qualified: licensed, insured, equipped, and available.

3. **Machine-verifiable completion.** The system can determine, algorithmically, whether the task was completed successfully — without requiring a human inspector at the point of verification.

4. **Programmatic settlement.** Payment is triggerable by verified completion, without human invoice review and approval cycles.

Robots change the qualifier dynamics. A human surveyor's quality varies with skill and fatigue — trust must be built over years. A robot executing a programmed mission produces the same result each time. Quality becomes a computed property of the dataset, not a judgment call. Availability becomes queryable state, not a phone call. The robot doesn't just fill a labor gap — it makes the task structurally compatible with algorithmic procurement.

No AI agent procures physical-world services today. But agents procure digital services routinely. The gap is these four preconditions, not the agent itself.

## Protocol Architecture

Five components, each mapping to one precondition plus a coordination layer:

```
Task Registry ──→ Executor Registry ──→ Verification Engine ──→ Settlement Layer
     │                    │                      │                      │
  Structured          Qualified              Machine-              Programmatic
  specs from          executors with         verifiable             escrow +
  regulatory          credentials,           completion             release on
  standards           equipment,             against spec           verification
                      coverage
                           │
                    Coordination Protocol
                    (post → discover → match → execute → verify → settle → record)
```

| Component | What it does | This repo |
|-----------|-------------|-----------|
| **Task Registry** | Structured schemas per domain — spec reference, tolerances, required qualifications, deliverable format, verification method | `auction/core.py` (Task, Bid, scoring) |
| **Executor Registry** | Credentials, equipment, coverage, performance history, insurance | `auction/operator_registry.py`, ERC-8004 on-chain identity |
| **Verification Engine** | Spec + measurement → compliance judgment, confidence metric, audit trail | `auction/deliverable_qa.py`, `auction/delivery_schemas.py` |
| **Settlement Layer** | Escrow on task initiation, release on verified completion, hold on dispute | `auction/settlement.py`, Stripe Connect, USDC on Base |
| **Coordination Protocol** | Post → discover → match → execute → verify → settle → record | `auction/engine.py` (state machine), `auction/mcp_tools.py` (41 MCP tools) |

## Protocol vs. Product

The protocol is the auction engine. The product is the vertical application built on it.

| Layer | What's here | License |
|-------|-------------|---------|
| **Protocol** | Task/Bid schemas, scoring, state machine, QA validator, reputation, executor discovery, settlement interface | MIT |
| **Vertical: Construction** | ASPRS/USGS delivery schemas, Part 107 compliance, PLS licensing, bond verification, ConsensusDocs agreements, RFP parsing | MIT |
| **Commercial** | YAK ROBOTICS marketplace frontend, Stripe integration, Cloudflare Worker, EAS curation, demo sites | Source-available |

See [Protocol Separation Assessment](docs/architecture/ASSESSMENT_PROTOCOL_SEPARATION.md) for the full analysis.

## Project Structure

```
yakrover-marketplace/
│
├── auction/                     # Protocol + construction vertical (Python)
│   ├── core.py                  # Task, Bid, scoring, signing, haversine geo filter
│   ├── engine.py                # AuctionEngine — state machine, geo + busy filtering
│   ├── contracts.py             # On-chain addresses (single source of truth)
│   ├── mcp_tools.py             # 41 MCP tool handlers
│   ├── delivery_schemas.py      # 8 category-specific QA schemas [vertical: construction]
│   ├── compliance.py            # Part 107, PLS, COI verification [vertical: construction]
│   ├── rfp_processor.py         # Construction RFP parsing [vertical: construction]
│   ├── bond_verifier.py         # Treasury Circular 570 [vertical: construction]
│   ├── mcp_robot_adapter.py     # Bridges marketplace to robot MCP servers
│   ├── deliverable_qa.py        # Schema-driven delivery validation
│   └── tests/                   # Unit + integration tests
│
├── demo/                        # Live sites (published via here.now)
│   ├── marketplace/             # yakrobot.bid/demo — auction demo
│   ├── landing/                 # yakrobot.bid — landing page
│   └── explorer/                # yakrobot.bid/yaml — ontology browser
│
├── infra/                       # Deployment configs
│   ├── fleet/                   # Fleet MCP server (Fly.io)
│   ├── fleet-sim/               # 9 category simulator servers (Fly.io)
│   └── deploy/                  # Tunnel + deployment scripts
│
├── data/                        # Static data
│   ├── fleet_manifest.yaml      # 100-robot fleet database
│   └── sample_certs/            # FAA Part 107, ACORD 25, PLS, OSHA samples
│
├── scripts/                     # CLI tools
│   ├── register_fleet.py        # Batch robot registration on-chain
│   ├── eas_attest.py            # EAS attestation management
│   └── deploy-*.sh              # Deployment scripts (worker, demo, all)
│
├── worker/                      # Cloudflare Worker — payment, demo proxy, balance monitor
├── docs/                        # Documentation
│   ├── architecture/            # System design docs, protocol separation assessment
│   ├── research/                # 43 research docs + PRODUCT_DSL ontology + backlog
│   ├── guides/                  # Getting started, operations runbook
│   ├── onboarding/              # Operator onboarding guides
│   ├── site/                    # Product brief site (yakrobot.bid/yaml)
│   └── archive/                 # Historical versions
│
├── mcp_server.py                # MCP API server entry point
├── Dockerfile, fly.toml         # Marketplace deployment (Fly.io)
└── pyproject.toml               # Dependencies, ruff, mypy config
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/YakRoboticsGarage/yakrover-marketplace.git
cd yakrover-marketplace && uv sync --all-extras

# Run tests
uv run pytest auction/tests/ -q --tb=short

# Run the demo auction
PYTHONPATH=. uv run python auction/demo.py

# Connect to the live server and start Claude
claude mcp add-json yakrover '{"type":"http","url":"https://yakrover-marketplace.fly.dev/mcp"}' && claude
# Then say: "Use yakrover to help me with an aerial LiDAR topo survey near Kalamazoo, MI"

# Or connect to a local server
claude mcp add-json yakrover '{"type":"http","url":"http://localhost:8001/mcp"}' && claude
```

See [Getting Started](docs/guides/GETTING_STARTED.md) for full setup including Stripe and robot simulator.

## Key Documents

| # | Document | What it tells you |
|---|----------|-------------------|
| 1 | **[PRODUCT_DSL_v2.yaml](docs/research/PRODUCT_DSL_v2.yaml)** | The entire product in one file — vision, bets, users, architecture, market, legal, roadmap |
| 2 | **[Roadmap v4](docs/ROADMAP_v4.md)** | Construction → Mining → Infrastructure → Lunar |
| 3 | **[Decisions](docs/DECISIONS.md)** | Every product and technical decision with rationale |
| 4 | **[Protocol Separation](docs/architecture/ASSESSMENT_PROTOCOL_SEPARATION.md)** | Protocol vs. commercial boundary — what's open, what's product |
| 5 | **[Architecture](docs/architecture/)** | System design docs, implementation plans, tech assessments |
| 6 | **[Operations](docs/guides/OPERATIONS.md)** | Secrets, deployments, rotation procedures, alert response |

## Construction Vertical (v1.0–v1.4)

The first domain implementation. 100 test robots, 18 Michigan operators, 14 real commercial models.

- **41 MCP tools** — auction lifecycle, RFP parsing, operator registration, compliance, EAS attestation
- **9 category MCP servers** on Fly.io — aerial LiDAR, photo, thermal, GPR, bridge, corridor, tunnel, confined, env sensing
- **101 EAS attestations** — 100 demo_fleet (Base Sepolia) + 1 live_production (Base mainnet)
- **Geographic filtering** — haversine hard cutoff, robots only bid within service radius
- **9 RFP presets** — real Michigan projects (MDOT I-94, MSU Farm Lane, US-31 bridge)
- **3-method payment** — Card, Bank Transfer (ACH), Stablecoin (USDC on Base)
- **Delivery QA** — 8 category-specific schemas (ASPRS, USGS, ASCE 38, ASTM, NBI standards)

## Live Sites

| URL | What it is |
|-----|-----------|
| **[yakrobot.bid/demo](https://yakrobot.bid/demo/)** | Live auction — 100 robots, 9 RFP presets, EAS attestation, 3-method payment |
| **[yakrobot.bid](https://yakrobot.bid)** | Landing page — MDOT I-94 RFQ walkthrough |
| **[yakrobot.bid/yaml](https://yakrobot.bid/yaml)** | YAML ontology explorer |

## Related Repositories

| Repository | What it contains |
|-----------|-----------------|
| **[robotTAM](https://github.com/rafaeldavid/robotTAM)** | Business strategy — pitch, outreach, financial model |
| **[yakrover-8004-mcp](https://github.com/YakRoboticsGarage/yakrover-8004-mcp)** | Robot framework — MCP servers, ERC-8004 discovery, robot plugins |

## License

Protocol and construction vertical: MIT. Commercial application: source-available. See [AD-27](docs/DECISIONS.md).
