# Robot Task Auction Marketplace

## Project Overview

A marketplace where AI agents post construction survey tasks, certified robot operators bid autonomously, and the best one delivers. Starting with construction site surveying ($1K-$200K tasks), scaling to mining, infrastructure, and lunar operations. Winners are paid via Stripe (fiat) or USDC on Base (crypto). This project handles real money — payment code requires extreme care.

**Wedge market:** Construction site surveying (pre-bid topo, GPR subsurface, progress monitoring). Typical tasks: $1,000-$10,000. Full project lifecycle: $25,000-$72,000+.
**v1.0 status:** Built. 280 tests, 35 MCP tools, ~17,009 LOC.
**v1.1 status:** Complete (2026-04-06). Real Tumbller robot moves + reads sensors via MCP. Marketplace + fleet on Fly.io (always on). Stripe inline authorize/capture. USDC gasless on Base. Demo-3 self-sustaining. Tags: `v1.1-milestone-tumbller-live`.
**Next:** v1.5 (settlement abstraction + construction task specs + privacy foundation). See `docs/FEATURE_REQUIREMENTS_v15.md`.
**Live sites:** [yakrobot.bid](https://yakrobot.bid), [yakrobot.bid/mcp-demo-5](https://yakrobot.bid/mcp-demo-5/) (current demo), [yakrobot.bid/yaml](https://yakrobot.bid/yaml), [yakrobot.bid/pitch](https://yakrobot.bid/pitch). Older demos archived in `docs/archive/`.

## Architecture

- **Auction engine:** `auction/` — Task, Bid, AuctionResult, score_bids(), state machine, settlement abstraction
- **Payment:** Stripe Connect (fiat) + USDC on Base via x402 (crypto, v1.5). Construction scale: $10K-$200K per project, not micro-payments.
- **Escrow:** `RobotTaskEscrow.sol` on Base with 4-mode settlement abstraction (FD-1, v1.5)
- **Fleet:** Robot/operator discovery via ERC-8004, 35 MCP tools for agent interaction
- **Persistence:** SQLite via `SyncTaskStore`
- **Demo site:** `demo/index.html` — interactive demo at [yakrobot.bid](https://yakrobot.bid)
- **Live MCP demo:** `docs/mcp_demo/index.html` — Claude orchestrates real auction at [yakrobot.bid/mcp-demo](https://yakrobot.bid/mcp-demo/)
- **Chatbot worker:** `chatbot/src/index.js` — Cloudflare Worker proxying to Anthropic API
- **Hosting:** here.now (yakrobot.bid) + Cloudflare Workers (/api/*)

## Key Commands

```bash
uv sync --all-extras                                    # Install everything
uv run pytest auction/tests/ -q --tb=short              # Unit tests (fast, no keys needed)
uv run pytest auction/tests/integration/ -m stripe      # Stripe integration (needs STRIPE_SECRET_KEY)
uv run pytest auction/tests/integration/ -m blockchain  # On-chain tests (needs BASE_SEPOLIA_RPC_URL)
uv run pytest auction/tests/integration/ -m fleet       # Fleet e2e (needs running fleet server)
uv run ruff check auction/ src/                         # Lint (includes security rules)
uv run mypy auction/                                    # Type check
uv run pytest --cov=auction auction/tests/              # Coverage report
```

## Payment Code Rules

- **NEVER** hardcode Stripe API keys, wallet private keys, or USDC addresses in source code. Use `.env` with `python-dotenv`.
- **ALL** payment operations must be idempotent — handle retries safely. Use idempotency keys for Stripe mutations.
- Stripe test mode (`sk_test_*`) for all development. Live keys only in production environment variables.
- **EVERY** payment state change must be logged to the audit trail in SQLite.
- Webhook handlers **MUST** verify Stripe signatures before processing.
- On-chain transactions **MUST** use commitment hash `H(request_id || salt)` per FD-4, never raw `request_id`.
- Robot wallet addresses must **NEVER** appear in API responses per PP-2. Use platform-internal `robot_id`.
- The settlement abstraction (FD-1) routes payments — do not add chain-specific logic outside the settlement layer.

## Testing Requirements

- Run `uv run pytest auction/tests/ -q` before committing any payment-related code change.
- Run `uv run ruff check` before committing any change.
- New payment features require both happy-path and failure-path tests.
- Property-based tests (hypothesis) for cryptographic operations and financial calculations.
- Wallet/escrow balances must never go negative under any test scenario.

## Decision Reference

Decisions live in `docs/DECISIONS.md` with IDs:
- **AD-X** = Architectural decisions
- **TC-X** = Technical constraints
- **PD-X** = Product decisions
- **FD-X** = Foundational design (cross-track, v1.5+)
- **PP-X** = Privacy-specific
- **LD-X** = Lunar-specific

Key decisions for v1.5: FD-1 (settlement abstraction), FD-4 (commitment hash), FD-5 (Horizen L3 eval), PP-2 (hidden wallet addresses).

## Project Structure

```
yakrover-marketplace/
│
├── auction/                     # Core auction engine (Python)
│   ├── core.py                  # Task, Bid, scoring, signing, commitment hash
│   ├── engine.py                # AuctionEngine — state machine, rate limits
│   ├── api.py                   # HTTP API for web frontend
│   ├── settlement.py            # 4-mode settlement abstraction (FD-1)
│   ├── mcp_tools.py             # 35 MCP tool handlers
│   ├── wallet.py                # WalletLedger with thread-safe mutations
│   ├── stripe_service.py        # Stripe SDK with idempotency keys
│   ├── store.py                 # SQLite persistence
│   ├── reputation.py            # ReputationTracker
│   ├── discovery_bridge.py      # ERC-8004 robot discovery
│   ├── mock_fleet.py            # Simulated robots for testing
│   ├── demo.py                  # Demo script
│   └── tests/                   # 280 tests + integration stubs
│
├── demo/                        # Live website (yakrobot.bid)
│   └── index.html               # Full interactive demo
│
├── chatbot/                     # Cloudflare Worker (yakrobot-chat)
│   └── src/index.js             # Chat + demo API proxy
│
├── mcp_server.py                # Standalone REST API (35 MCP tools, Cloudflare Tunnel)
│
├── docs/                        # Documentation
│   ├── mcp_demo/index.html      # Live MCP demo (yakrobot.bid/mcp-demo)
│   ├── ROADMAP_v4.md            # Construction → Mining → Infra → Lunar
│   ├── USER_JOURNEY_CONSTRUCTION_v01.md  # Marco's journey
│   ├── FEATURE_REQUIREMENTS_v15.md       # v1.5 build spec
│   ├── DECISIONS.md             # All product/technical decisions
│   ├── DEVELOPMENT_STRATEGY.md  # Testing & code safety (5-layer strategy)
│   ├── SCOPE.md                 # Version boundaries
│   ├── DIAGRAM_SYSTEM.md        # System architecture diagrams
│   ├── DIAGRAM_USER_JOURNEY.md  # User journey diagrams
│   ├── research/                # 52 research docs (see research/README.md)
│   │   ├── PRODUCT_DSL_v2.yaml  # THE product ontology (3,243 lines)
│   │   ├── market/              # Wedge analysis, competitive landscape
│   │   ├── legal/               # Contracts, bonds, payment flows
│   │   ├── technical/           # Architecture, execution gaps
│   │   └── operator/            # Onboarding, equipment, sensors
│   └── feedback/                # Audits, critiques, founder feedback
│
├── docs/wave1/                  # GC + operator engagement packages
│   ├── docs/pitch/                  # Pitch deck source
│   ├── docs/site/                   # YAML ontology explorer (yakrobot.bid/yaml)
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
├── CLAUDE.md                    # Payment safety rules for Claude (this file)
├── _REPORT-STYLE.md             # Report formatting and tone guide
├── serve_with_auction.py        # MCP gateway server
└── pyproject.toml               # Dependencies, ruff, mypy config
```

## Style Guide

All reports, engagement packages, and outreach documents follow the conventions in **`_REPORT-STYLE.md`**. See also [tropes.fyi](https://tropes.fyi) for anti-patterns to avoid in writing.

## Environment Variables

```
STRIPE_SECRET_KEY=sk_test_...     # Stripe test mode only (DE accounts: use EUR, not USD)
STRIPE_OPERATOR_ACCOUNT=acct_...  # Connect Express test account
AUCTION_DB_PATH=:memory:          # SQLite path (:memory: for tests)
SIGNING_MODE=ed25519              # or hmac for Phase 0
MCP_BEARER_TOKEN=                 # Fleet server auth
BASE_SEPOLIA_RPC_URL=             # For on-chain tests (v1.5)
FAKEROVER_URL=http://localhost:8080
```

## Payment Scale Reference

Construction survey tasks operate at significantly higher amounts than generic sensor readings:

| Task Type | Typical Range | Example |
|-----------|--------------|---------|
| Aerial LiDAR topo (12 acres) | $1,500-$3,000 | SR-89A pre-bid survey |
| GPR subsurface scan | $1,000-$2,000 | Utility detection |
| Monthly progress monitoring | $800-$1,500/flight | Cut/fill volume tracking |
| Full project lifecycle (14 mo) | $25,000-$72,000+ | Pre-bid + monitoring + as-built |
| Credit bundle (typical) | $5,000 | Single card charge |

The TC-1 minimum ($0.50) is not a practical constraint for construction tasks. Prepaid credit bundles, payment bonds, and escrow are the primary payment methods at this scale.
