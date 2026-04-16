# Assessment: Protocol vs. Commercial Separation

**Date:** 2026-04-12
**Status:** Assessment complete — informs roadmap v3.0+ planning
**Trigger:** Evaluate how the auction engine could exist as an open protocol independent of the YAK ROBOTICS commercial marketplace.

---

## The Question

The robot task auction marketplace has two distinct halves:

1. **A protocol** — how tasks get posted, bids get scored, robots get matched, and deliverables get verified.
2. **A product** — how buyers find us, how operators onboard, how payments settle, and how the platform makes money.

Every successful open protocol marketplace (Akash, Uniswap, The Graph, Filecoin, Ocean Protocol) draws the line at the same place: **verifiable state transitions are the protocol; convenience, curation, compliance, and UX are the product.**

This assessment maps our codebase to that split, identifies what needs to change, and proposes a phased path.

---

## Precedent Analysis

Five open protocol marketplaces were analyzed. The pattern is consistent:

| Project | Protocol Layer | Commercial Layer | Revenue Model |
|---------|---------------|-----------------|---------------|
| **Akash** | On-chain bid engine (Cosmos SDK), Kubernetes manifest matching, escrow deposits | Akash Console (web UI), managed providers, provider incentive programs | AKT staking + take rate on deployments |
| **Uniswap** | AMM smart contracts (immutable, on-chain) | Uniswap Labs frontend, Uniswap Wallet, routing API, interface fees | 0.15% interface fee on hosted frontend |
| **The Graph** | Subgraph indexing protocol, query payment channels, curation market | Graph Explorer, hosted service (deprecated), Subgraph Studio | GRT query fees + curation signal |
| **Filecoin** | Storage deal protocol, Proof-of-Spacetime, retrieval market | Filecoin Plus (verified deals), web3.storage, Lighthouse | FIL block rewards + deal collateral |
| **Ocean Protocol** | Datatokens (ERC-20 per dataset), Compute-to-Data | Ocean Market (frontend), data farming, enterprise tools | OCEAN staking + marketplace fees |

**Common pattern:** The protocol is a set of smart contracts and/or a specification that anyone can build against. The commercial entity runs the canonical frontend and captures value via interface fees, token economics, or premium services. The protocol is typically governed by a foundation or DAO. The commercial entity is a separate legal entity.

**Key insight:** In every case, the protocol was designed to be forkable from day one. Uniswap's contracts are immutable and MIT-licensed. Akash's bid engine is open-source Cosmos SDK. The commercial value comes from network effects, UX, and curation — not from locking up the matching logic.

---

## Current Codebase Split

### Protocol candidates (~10.8K lines)

These modules implement the core matching/verification logic and contain no business logic, branding, or payment processing:

| Module | LOC | What It Does | Protocol Purity |
|--------|-----|-------------|-----------------|
| `auction/core.py` | ~1,200 | Task, Bid, scoring, signing, commitment hash | **Pure** — no external dependencies |
| `auction/engine.py` | ~900 | State machine, bid collection, geographic filter, busy state | **Pure** — orchestration only |
| `auction/deliverable_qa.py` | ~400 | Schema-driven QA validation | **Pure** — generic validator |
| `auction/delivery_schemas.py` | ~300 | Category-specific delivery schemas | **Pure** — data only |
| `auction/reputation.py` | ~250 | Rolling reputation tracker | **Pure** — stateless math |
| `auction/rfp_processor.py` | ~500 | RFP → structured task spec | **Near-pure** — depends on LLM |
| `auction/operator_registry.py` | ~400 | Operator profiles, equipment, activation | **Pure** — registry logic |
| `auction/compliance.py` | ~600 | Document verification (Part 107, COI, PLS) | **Near-pure** — domain rules |
| `auction/bond_verifier.py` | ~500 | Payment bond validation vs Treasury data | **Near-pure** — domain rules |
| `auction/terms_comparator.py` | ~180 | Contract terms comparison | **Near-pure** — domain rules |
| `auction/agreement.py` | ~400 | Subcontract generation | **Near-pure** — template logic |
| `auction/store.py` | ~780 | SQLite persistence | **Adapter** — swappable |
| `auction/wallet.py` | ~280 | Internal ledger | **Protocol** — accounting math |
| `auction/discovery_bridge.py` | ~300 | ERC-8004 robot discovery | **Protocol** — on-chain query |
| `auction/mock_fleet.py` | ~920 | Test fleet simulation | **Test only** |
| `auction/mcp_robot_adapter.py` | ~350 | Bridge to robot MCP servers | **Protocol** — interop layer |

### Commercial layer (~10.5K lines)

These modules implement the YAK ROBOTICS product — branding, payment processing, deployment, and user experience:

| Module | LOC | What It Does | Commercial Reason |
|--------|-----|-------------|-------------------|
| `mcp_server.py` | ~680 | REST API server with EAS filtering, fleet discovery | **Product** — our specific API surface |
| `worker/src/index.js` | ~2,465 | Cloudflare Worker: payment endpoints, demo proxy | **Product** — our payment rails |
| `demo/marketplace/index.html` | ~4,256 | Live auction demo UI | **Product** — our frontend |
| `demo/landing/index.html` | ~3,100 | Landing page | **Product** — our brand |
| `auction/stripe_service.py` | ~190 | Stripe Connect integration | **Product** — our payment provider |
| `auction/mcp_tools.py` | ~1,800 | 37 MCP tool handlers | **Mixed** — tool surface is protocol, wiring is product |
| `auction/settlement.py` | ~200 | Settlement abstraction (4-mode) | **Mixed** — interface is protocol, implementations are product |
| `auction/api.py` | ~300 | FastAPI router | **Product** — our HTTP API |

### The gray zone: `mcp_tools.py` and `settlement.py`

These two files sit at the protocol/product boundary:

- **`mcp_tools.py`** defines the 37 tool signatures that any MCP client can call. The tool names and schemas (`auction_post_task`, `auction_accept_bid`, etc.) are the protocol's API surface. But the implementation wiring (EAS filtering, demo overrides, Stripe-specific payment creation) is commercial.
- **`settlement.py`** defines the `SettlementInterface` protocol (settle, verify, batch_settle). The interface is protocol. `StripeSettlement` and `BaseX402Settlement` are commercial implementations.

**This is exactly where every precedent draws the line.** The interface/schema is open. The implementation is the product.

---

## What the Protocol Would Be

### Robot Task Auction Protocol (RTAP)

A specification for how AI agents post tasks, certified robots bid autonomously, deliverables are verified, and settlement is triggered. Independent of any specific payment rail, frontend, or hosting platform.

**Core specification:**

1. **Task schema** — JSON structure for task specs (category, requirements, budget, deadline, delivery schema, geographic bounds)
2. **Bid schema** — JSON structure for signed bids (price, SLA, confidence, capability proof)
3. **Scoring function** — Deterministic 4-factor weighted scoring (configurable weights per vertical)
4. **State machine** — 11 states with enforced transitions (POSTED → BIDDING → BID_ACCEPTED → IN_PROGRESS → DELIVERED → VERIFIED → SETTLED)
5. **QA validation** — Schema-driven delivery verification (same schema for robot self-check and platform QA)
6. **Identity** — ERC-8004 agent cards for robot identity and capability discovery
7. **Reputation** — Rolling 30-day window with completion/on-time/rejection rates
8. **Settlement interface** — Abstract `settle()` / `verify()` that any payment implementation can fulfill

**What the protocol explicitly does NOT specify:**
- Which payment rail to use (Stripe, USDC, MPP, wire transfer)
- How buyers find the marketplace (frontend, API, agent discovery)
- How operators onboard (KYB, compliance, credential upload)
- How the platform makes money (fees, tokens, subscriptions)
- How disputes are resolved (arbitration, refund, reputation slashing)

### On-chain components

| Component | Current | Protocol version |
|-----------|---------|-----------------|
| Robot identity | ERC-8004 on Base | Same — already an open standard |
| Attestation | EAS on Base | Same — already an open standard |
| Escrow | `RobotTaskEscrow.sol` (planned) | Deploy as immutable contract, anyone can interact |
| Scoring | Off-chain in `core.py` | Publish reference implementation, allow on-chain verification |
| Task registry | Off-chain in SQLite | Optional on-chain task registry for censorship resistance |

---

## Separation Architecture

### Layer diagram

```
┌─────────────────────────────────────────────────────────┐
│                   COMMERCIAL LAYER                       │
│                                                         │
│  YAK ROBOTICS marketplace  │  Future competitor X       │
│  - yakrobot.bid frontend   │  - their own frontend      │
│  - Stripe Connect          │  - different payment rail   │
│  - Cloudflare Workers      │  - different hosting        │
│  - EAS curation            │  - different curation       │
│  - Construction focus      │  - different vertical       │
│  - Interface fee           │  - different revenue model  │
├─────────────────────────────────────────────────────────┤
│                    PROTOCOL LAYER                        │
│                                                         │
│  rtap-core (Python SDK)                                 │
│  - Task/Bid/AuctionResult schemas                       │
│  - score_bids() reference implementation                │
│  - State machine with enforced transitions              │
│  - Schema-driven QA validator                           │
│  - ERC-8004 discovery bridge                            │
│  - SettlementInterface (abstract)                       │
│  - Reputation tracker                                   │
│                                                         │
│  rtap-contracts (Solidity)                              │
│  - RobotTaskEscrow.sol (immutable)                      │
│  - On-chain task registry (optional)                    │
│  - Scoring verification (optional)                      │
│                                                         │
│  rtap-spec (docs)                                       │
│  - JSON schemas for Task, Bid, Delivery                 │
│  - State machine specification                          │
│  - Scoring algorithm specification                      │
│  - MCP tool interface definitions                       │
├─────────────────────────────────────────────────────────┤
│                   STANDARDS LAYER                        │
│                                                         │
│  ERC-8004 (robot identity)  │  EAS (attestation)        │
│  Base (settlement chain)    │  MCP (tool protocol)      │
│  IPFS (agent cards)         │  USDC (settlement token)  │
└─────────────────────────────────────────────────────────┘
```

### Revenue model for the commercial layer

Following the Uniswap model: the protocol is free and open. The commercial entity captures value through:

1. **Interface fee** — 1-3% on transactions through the YAK ROBOTICS frontend (like Uniswap's 0.15%)
2. **Managed operator onboarding** — compliance verification, insurance tracking, PLS routing as a premium service
3. **Enterprise features** — private task matching, TEE compute, government compliance packages
4. **Curation** — EAS attestation from the YAK ROBOTICS platform carries reputation weight; operators pay for certification
5. **MPP/ACP integration** — agent commerce tooling built on the open protocol

Anyone can fork the protocol and run their own marketplace with zero fees. YAK ROBOTICS competes on UX, curation, operator network density, and compliance tooling.

---

## What Needs to Change

### Now (v1.5 — architectural preparation)

These changes don't require protocol separation but make it possible later without rewrite:

| Change | Why | Effort |
|--------|-----|--------|
| **Extract `SettlementInterface` to standalone module** | Currently in `auction/settlement.py` alongside Stripe implementation. Separate the abstract interface from the Stripe-specific code. | Small — file split |
| **Define MCP tool schemas as JSON Schema** | Tool signatures are currently Python function signatures in `mcp_tools.py`. Publishing them as JSON Schema makes them language-agnostic. | Medium — schema extraction |
| **License decision** | Current repo has no LICENSE file. Protocol code needs an open license (MIT/Apache 2.0). Commercial code can be proprietary or source-available. | Decision + file |
| **Separate `auction/` imports** | `mcp_tools.py` imports both protocol code (engine, core) and commercial code (stripe_service, EAS). Clean the dependency direction: commercial imports protocol, never the reverse. | Medium — refactor |
| **Add `rtap-core` package boundary** | `pyproject.toml` should define `rtap-core` as an installable package (just `auction/core.py`, `engine.py`, `deliverable_qa.py`, `reputation.py`, `wallet.py`, `store.py`). Third parties can `pip install rtap-core`. | Medium — packaging |

### Medium term (v2.0 — SDK extraction)

| Change | Why | Effort |
|--------|-----|--------|
| **Publish `rtap-core` as a separate repo/package** | Third-party marketplaces can build on the protocol. | Large — repo split + CI |
| **Publish JSON Schema specs for Task, Bid, Delivery** | Language-agnostic protocol definition. | Medium — documentation |
| **Deploy `RobotTaskEscrow.sol` as immutable, ownerless** | Anyone can use the escrow contract without the platform. | Medium — contract design |
| **MCP tool interface specification** | Standardize the 37 tool names/schemas so any MCP server can implement them. | Medium — spec writing |
| **Reference frontend** | Minimal open-source UI that talks to `rtap-core`. Separate from yakrobot.bid. | Large — new frontend |

### Long term (v3.0+ — governance and foundation)

| Change | Why | Effort |
|--------|-----|--------|
| **Foundation or DAO for protocol governance** | Protocol upgrades (new task categories, scoring changes, schema versions) need multi-stakeholder governance. | Large — legal + org |
| **On-chain task registry** | Censorship-resistant task posting. Currently tasks live only in the platform's SQLite. | Large — contract + indexer |
| **Protocol token (evaluate, not assumed)** | Akash and The Graph use tokens for staking/coordination. Uniswap launched without one. Evaluate whether a token serves a real coordination purpose or is premature. | Decision — depends on network size |
| **Multi-marketplace interop** | Operators registered once (ERC-8004) can bid on tasks from any RTAP marketplace. Bids are portable. | Large — protocol extension |

---

## What to Decide Now

Even though full separation is v3.0+, three decisions have compounding consequences if deferred:

### 1. License

**Recommendation:** Dual license.
- `auction/core.py`, `engine.py`, `deliverable_qa.py`, `delivery_schemas.py`, `reputation.py`, `wallet.py`, `store.py`, `discovery_bridge.py`, `mcp_robot_adapter.py` → **MIT** or **Apache 2.0**
- Everything else → **Source-available** (BSL 1.1 like Uniswap v3, or proprietary)

Why now: changing license later is legally complex if external contributors have submitted code under an implied license. Setting it now is free.

### 2. Dependency direction

**Recommendation:** Enforce that protocol modules never import commercial modules.

Currently `mcp_tools.py` is the only violation — it imports both `engine` (protocol) and `stripe_service` (commercial). This can be fixed by making `mcp_tools.py` a commercial module that composes protocol + payment, which it conceptually already is.

Why now: every new feature that adds a commercial import to a protocol module makes extraction harder. A simple lint rule (`ruff` custom check or import boundary in `pyproject.toml`) prevents drift.

### 3. Scoring transparency

**Recommendation:** Publish the scoring algorithm as a specification, not just code.

`score_bids()` is the protocol's most important function. If operators can't independently verify how they were scored, the protocol isn't credibly neutral. Publish the algorithm (weights, normalization, hard constraint filters) as a versioned specification alongside the code.

Why now: changing scoring after operators have calibrated their bid engines to it requires a governance process. Treating it as a spec (not just an implementation detail) sets the right expectations.

---

## Relationship to Existing Decisions

| Decision | Protocol Impact |
|----------|----------------|
| **FD-1** (Settlement abstraction) | The `SettlementInterface` IS the protocol's payment boundary. Already designed correctly — just needs extraction. |
| **PD-2** (Automated bid engine) | Bid engine per-robot is protocol-native. Operators tune their own `bid_engine()`. |
| **PD-3** (Signed bids) | Cryptographic bid signing is protocol infrastructure. Already built. |
| **PD-5** (Schema-driven QA) | Same schema for robot + platform = protocol-level agreement. Already built. |
| **AD-20** (EAS attestation) | EAS is the curation layer — commercial, not protocol. Platform attestation = product value. |
| **R-053** (MPP) | MPP integration is commercial (specific payment rail). Protocol only needs `SettlementInterface.settle()`. |
| **TC-4** (USDC on Base) | Base USDC is the reference settlement token. Protocol-compatible. |

---

## Proposed Roadmap Additions

### v2.0 additions (existing section)
- **RTAP SDK alpha:** Extract `rtap-core` Python package from `auction/`. Publish to PyPI as `rtap-core`. Third-party developers can import and build.
- **JSON Schema publication:** Task, Bid, Delivery, and MCP tool schemas published as versioned JSON Schema documents.
- **License applied:** MIT for protocol code, BSL 1.1 for commercial code.

### v3.0 additions (new subsection: "Protocol Governance")
- **Foundation evaluation:** Assess whether a foundation (like Filecoin Foundation) or a lighter structure (like Uniswap's governance forum) is appropriate for protocol governance at current network size.
- **Immutable escrow deployment:** `RobotTaskEscrow.sol` deployed as ownerless, immutable contract on Base. Any RTAP marketplace can use it.
- **Multi-marketplace operator portability:** Operator registers once via ERC-8004, bids across any RTAP-compatible marketplace. Protocol spec for cross-marketplace bid routing.
- **Scoring specification v1.0:** Published, versioned algorithm spec. Changes require governance proposal.

### v4.0 note
- Lunar operations benefit enormously from protocol separation — JAXA/NASA won't use a single-vendor marketplace. RTAP as an open protocol makes the lunar track credible.

---

## Key Takeaway

The codebase is already ~50% protocol, ~50% product. The protocol half (`auction/`) is well-isolated with clean interfaces. Full separation is a v3.0 effort, but three decisions made now (license, dependency direction, scoring transparency) prevent architectural debt that would make the split painful later.

The Uniswap model is the closest analogue: immutable protocol contracts + commercial frontend with interface fees. The auction engine is the AMM. The marketplace is the app.

**Make the auction engine the protocol. Make discovery and UX the product.**
