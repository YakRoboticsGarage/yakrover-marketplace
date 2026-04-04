# YAK ROBOTICS — Robot Task Auction Marketplace

A marketplace where AI agents post construction survey tasks, certified robot operators bid autonomously, and the best one delivers. Starting with construction site surveying, scaling to mining, infrastructure, and lunar operations.

**Live demo:** [yakrobot.bid](https://yakrobot.bid)

## The Problem

Construction survey scheduling is a 2-3 week bottleneck costing GCs missed bids. 368,000+ Part 107 holders own survey drones but lack a demand pipeline. No platform exists where AI agents post physical-world tasks and robots bid autonomously.

## The Product

Upload an RFP → the system extracts survey requirements → decomposes into independently biddable tasks → certified operators bid → you review winners with automated compliance checks → sign and activate → get Civil 3D-ready deliverables.

**Demo flow:** [yakrobot.bid](https://yakrobot.bid) walks through a real MDOT I-94 Drainage Tunnel RFQ.

**Architecture note:** Performance/Lien/Schedule (PLS) payment bond verification is automatable — the bond-verification skill handles compliance checks against contract requirements, removing a manual bottleneck from construction payment flows.

## Project Structure

```
yakrover-marketplace/
│
├── auction/                     ← Core auction engine (Python)
│   ├── core.py                  # Task, Bid, scoring, signing, commitment hash
│   ├── engine.py                # AuctionEngine — state machine, rate limits
│   ├── api.py                   # HTTP API for web frontend
│   ├── settlement.py            # 4-mode settlement abstraction (FD-1)
│   ├── mcp_tools.py             # 35 MCP tool handlers
│   ├── wallet.py                # WalletLedger with thread-safe mutations
│   ├── stripe_service.py        # Stripe SDK with idempotency keys
│   ├── store.py                 # SQLite persistence
│   ├── reputation.py            # ReputationTracker
│   └── tests/                   # 264 tests + integration stubs
│
├── demo/                        ← Live website (yakrobot.bid)
│   └── index.html               # Full interactive demo
│
├── docs/                        ← Documentation
│   ├── ROADMAP_v4.md            # Construction → Mining → Infra → Lunar
│   ├── USER_JOURNEY_CONSTRUCTION_v01.md  # Marco's journey
│   ├── FEATURE_REQUIREMENTS_v15.md       # v1.5 build spec
│   ├── DECISIONS.md             # All product/technical decisions
│   ├── DEVELOPMENT_STRATEGY.md  # Testing & code safety (5-layer strategy)
│   ├── mcp_demo/
│   │   └── index.html           # Live MCP demo (yakrobot.bid/mcp-demo)
│   ├── research/                # 52 research docs (see research/README.md)
│   │   ├── PRODUCT_DSL_v2.yaml  # ← THE product ontology (3,200+ lines)
│   │   ├── market/              # Wedge analysis, competitive landscape
│   │   ├── legal/               # Contracts, bonds, payment flows
│   │   ├── technical/           # Architecture, execution gaps
│   │   └── operator/            # Onboarding, equipment, sensors
│   └── feedback/                # Audits, critiques, founder feedback
│
├── .claude/
│   ├── skills/
│   │   ├── rfp-to-robot-spec/   # RFP → auction task specs
│   │   ├── rfp-to-site-recon/   # RFP → execution context
│   │   ├── bond-verification/   # Payment bond compliance checks
│   │   └── legal-terms-compare/ # Survey contract term comparison
│   └── hooks/block-secrets.sh   # Prevents committing API keys
│
├── .github/workflows/test.yml   # CI: tests + ruff + mypy
├── CLAUDE.md                    # Payment safety rules for Claude
├── serve_with_auction.py        # MCP gateway server
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

# Or connect as MCP server
claude mcp add-json yakrover '{"type":"http","url":"http://localhost:8001/fleet/mcp"}'
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for full setup including Stripe and robot simulator.

## Key Documents

Start here, in this order:

| # | Document | What it tells you |
|---|----------|-------------------|
| 1 | **[PRODUCT_DSL_v2.yaml](docs/research/PRODUCT_DSL_v2.yaml)** | The entire product in one file — vision, bets, users, architecture, market, legal, roadmap |
| 2 | **[Research README](docs/research/README.md)** | Index of all 52 research documents |
| 3 | **[User Journey](docs/USER_JOURNEY_CONSTRUCTION_v01.md)** | Marco's story — pre-bid survey for a highway project |
| 4 | **[Roadmap v4](docs/ROADMAP_v4.md)** | Construction → Mining → Infrastructure → Lunar |
| 5 | **[Decisions](docs/DECISIONS.md)** | Every product and technical decision with rationale |
| 6 | **[Feature Requirements v1.5](docs/FEATURE_REQUIREMENTS_v15.md)** | What's being built next (12 features with acceptance criteria) |
| 7 | **[Wave 1 Engagement Packages](docs/wave1/)** | GC + operator outreach decks and one-pagers |
| 8 | **[Financial Analysis](docs/research/financial/)** | Unit economics, pricing model, revenue projections |
| 9 | **[Style Guide](_REPORT-STYLE.md)** | Report formatting, tone, and tropes.fyi reference |
| 10 | **[Pitch Deck](https://yakrobot.bid/pitch)** | Investor/partner deck (live at yakrobot.bid/pitch) |

## Live Sites

| URL | What it is |
|-----|-----------|
| **[yakrobot.bid](https://yakrobot.bid)** | Interactive demo — MDOT I-94 RFQ walkthrough |
| **[yakrobot.bid/mcp-demo](https://yakrobot.bid/mcp-demo/)** | Live auction demo — Claude orchestrates real MCP tools |
| **[yakrobot.bid/mcp-demo-2](https://yakrobot.bid/mcp-demo-2/)** | Payment demo — real robot discovery, IPFS delivery, Stripe + USDC settlement |
| **[yakrobot.bid/yaml](https://yakrobot.bid/yaml)** | YAML ontology explorer — browse PRODUCT_DSL_v2 live |
| **[yakrobot.bid/pitch](https://yakrobot.bid/pitch)** | Pitch deck — investor/partner presentation |

## Skills

Four Claude Code skills for processing construction RFPs:

| Skill | What it does |
|-------|-------------|
| **rfp-to-robot-spec** | Extracts survey requirements from RFPs → structured JSON task specs for the auction engine |
| **rfp-to-site-recon** | Generates execution context from RFPs + public data → site boundary, airspace, weather, utilities |
| **bond-verification** | Verifies payment bond compliance against construction contract requirements |
| **legal-terms-compare** | Compares legal terms across survey contracts, flags deviations from standard |

All four follow the [skill-creator-springett](https://github.com/bglek/skill-creator-springett) framework with validation scripts, reference docs, and eval test cases.

## Related Repositories

| Repository | What it contains |
|-----------|-----------------|
| **[yakrover-8004-mcp](https://github.com/YakRoboticsGarage/yakrover-8004-mcp)** | Robot framework — MCP servers, ERC-8004 discovery, robot plugins |
| **[yakrover-protocols](https://github.com/YakRoboticsGarage/yakrover-protocols)** | Protocol specifications |
| **[yakrover-skills](https://github.com/YakRoboticsGarage/yakrover-skills)** | Robot discovery skills |

## Key Numbers

- **35 MCP tools** — auction lifecycle, RFP parsing, bond verification, operator compliance, agreement generation, event tracking, feedback
- **238 tests** passing, with integration test stubs for Stripe and fleet
- **50 commits** across the project
- **31 research topics** in automated research roadmap (2 completed, 6 improvement proposals)
- **Live payment demo** at yakrobot.bid/mcp-demo-2 with real robot discovery, IPFS delivery, Stripe + USDC settlement
- **3,243 line YAML** product ontology covering the entire product
- **43 real MDOT RFPs** analyzed for survey requirements
- **6 real equipment platforms** with verified specs and pricing
- **CI pipeline** with ruff (security linting), mypy, and pytest on every push

## Construction Survey Focus

The marketplace targets construction site surveying as its wedge market (scored 4.25/5 across 8 industries). Real equipment on the platform:

| Operator | Equipment | Capability |
|----------|-----------|-----------|
| Apex Aerial Surveys | DJI Matrice 350 RTK + Zenmuse L2 | Aerial LiDAR, topo surveys |
| SiteScan Robotics | Boston Dynamics Spot + Leica BLK ARC | Ground scanning, tunnel survey |
| Trident Autonomous | Skydio X10 | Visual + thermal inspection |
| ClearLine Survey | Autel EVO II Pro RTK | Aerial survey (budget entry) |
| Meridian Geospatial | DJI Matrice 350 RTK + Zenmuse P1 | Photogrammetry |

## License

Apache 2.0
