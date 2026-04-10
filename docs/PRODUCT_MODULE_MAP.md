# Product Module Map

A landscape view of every distinct component in the YAK ROBOTICS marketplace. Each module is an independently-scoped unit of development with defined inputs, outputs, and responsibilities.

**Updated:** 2026-04-05 | **Modules:** 39 | **Built:** 30 | **Building:** 1 | **Gaps:** 1 | **Planned:** 3 | **Deferred:** 4

---

## How to Read This Map

- **Built** = working code with tests, deployed or deployable
- **Designed** = interface/spec exists, implementation pending
- **Planned** = requirements defined, no code yet
- Arrows (-->) show data flow direction
- Each module lists its key file(s) and what it connects to

---

## 1. TASK INTAKE (RFP --> Structured Specs)

```
RFP Document
  |
  v
[M1: RFP Processor] --> [M2: Standards Engine] --> [M3: Task Validator]
  |                                                        |
  v                                                        v
[M4: Site Recon]                                    Task Specs (JSON)
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M1 | **RFP Processor** | Built | `auction/rfp_processor.py`, `.claude/skills/rfp-to-robot-spec/` | Converts construction RFP text into structured task specs. LLM-powered extraction with keyword fallback. References MDOT/AASHTO/federal standards. |
| M2 | **Standards Engine** | Built | `.claude/skills/rfp-to-robot-spec/references/`, `auction/core.py` (enums) | ASPRS accuracy classes, USGS quality levels, EPSG CRS codes, deliverable format versions. Lookup tables + validation. |
| M3 | **Task Validator** | Built | `auction/core.py` (validate_task_spec) | Schema validation: budget, category, capability requirements, ASPRS classes, EPSG codes, deliverables, MRTA classification. Returns all errors at once. |
| M4 | **Site Reconnaissance** | Built | `.claude/skills/rfp-to-site-recon/` | Generates execution context: site access, weather, airspace, terrain, utilities. Used by operators to plan flights. |

---

## 2. AUCTION ENGINE (Matching + Scoring)

```
Task Specs --> [M5: Auction Engine] <--> [M6: Fleet Registry]
                 |          |                    |
                 v          v                    v
          [M7: Scorer]  [M8: State Machine]  [M9: Mock Fleet]
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M5 | **Auction Engine** | Built | `auction/engine.py` | Orchestrator: post tasks, collect bids, accept, execute, confirm/reject delivery, re-pool. Rate limits (20 active tasks/wallet, 3 re-pool rounds). |
| M6 | **Operator Registry** | Built | `auction/operator_registry.py` | Operator profiles: equipment, sensors, certifications, pricing, activation status. Registration --> compliance --> activation flow. |
| M7 | **Bid Scorer** | Built | `auction/core.py` (score_bids) | 4-factor weighted scoring: 40% price, 25% SLA, 20% AI confidence, 15% reputation. Hard constraint filter first, then soft scoring. Configurable weights per vertical. |
| M8 | **State Machine** | Built | `auction/engine.py` (VALID_TRANSITIONS) | 11 states: POSTED --> BIDDING --> BID_ACCEPTED --> IN_PROGRESS --> DELIVERED --> VERIFIED --> SETTLED. Plus: WITHDRAWN, ABANDONED, REJECTED, RE_POOLED. Enforced transitions. |
| M9 | **Mock Fleet** | Built | `auction/mock_fleet.py` | 7 Michigan operators with deterministic bid engines. Used for testing and demo. Maps to real equipment (DJI M350, Spot + BLK ARC, Skydio X10, etc.). |

---

## 3. COMPLIANCE & VERIFICATION

```
Operator Docs --> [M10: Compliance Checker]
Bond PDF      --> [M11: Bond Verifier]
Contract      --> [M12: Terms Comparator]
Award         --> [M13: Agreement Generator]
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M10 | **Compliance Checker** | Built | `auction/compliance.py` | Verifies operator documents: FAA Part 107, insurance COI (ACORD 25 PDF parsing), PLS license, SAM.gov exclusion check, DOT prequalification, DBE status. |
| M11 | **Bond Verifier** | Built | `auction/bond_verifier.py` | Payment bond validation against real Treasury Circular 570 data (501 surety companies). Fuzzy name matching, state licensing, underwriting limits. PDF extraction via PyMuPDF. |
| M12 | **Terms Comparator** | Built | `auction/terms_comparator.py` | Compares survey contract terms across 12 dimensions against ConsensusDocs 750 baseline. Flags deviations, checks state anti-indemnity statutes. |
| M13 | **Agreement Generator** | Built | `auction/agreement.py` | Generates ConsensusDocs 750 subcontracts from task spec + winning bid. Scope, fee, schedule, insurance requirements, PLS supervision, retainage, dispute resolution. |

> **Known gap (M10):** PLS certification is tracked in compliance but **not enforced** in `check_hard_constraints()`. An operator without PLS can currently win tasks requiring PLS stamps. Must be fixed before production. See PLS section below.

---

## 3b. DELIVERABLE QA & PLS STAMP

```
Delivered Data --> [M35: Deliverable QA] --> [M36: PLS Review & Stamp]
                                                      |
                                                      v
                                               Stamped Deliverables
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M35 | **Deliverable QA** | Built | `auction/deliverable_qa.py` | Schema-driven validation: task spec includes `delivery_schema`, robot self-checks before submitting, QA validates same schema. 4 levels (none → schema → standards → PLS). Generic validator supports required, type, ranges, array counts, nested objects. No task-type-specific code. 40 tests. |
| M36 | **PLS Review & Stamp** | Gap | — | PLS-as-a-service routing: task completion triggers routing to available PLS in jurisdiction. PLS reviews via dashboard, applies electronic seal (DocuSign API). Two modes: operator-has-PLS (self-stamp) and marketplace-routes-PLS (external review). |

**PLS lifecycle (current vs needed):**

| Step | Current Status | What's Needed |
|------|---------------|---------------|
| Operator registers PLS info | Built (`operator_registry.set_pls()`) | -- |
| Compliance tracks PLS status | Built (`compliance.py`, VERIFIED/MISSING/EXPIRED) | -- |
| Task spec requires PLS | Built (`certifications_required: ["licensed_surveyor"]`) | -- |
| **Engine enforces PLS in bidding** | **GAP** — `check_hard_constraints()` ignores certifications | Add certification check to hard filter |
| **PLS jurisdiction validation** | **GAP** — MI license not checked against task state | Validate PLS state matches task jurisdiction |
| **PLS expiration enforcement** | **GAP** — compliance flags EXPIRED but engine ignores | Block expired-PLS operators from bidding |
| Agreement includes PLS clause | Built (`agreement.py` hard-codes PLS supervision) | -- |
| Delivery includes PLS status | Built (`pls_review_status: "PENDING"` in payload) | -- |
| **Deliverable QA pre-screening** | **GAP** | Automated point density, accuracy, format checks |
| **PLS review routing** | **GAP** | Route to available PLS, dashboard, electronic seal |
| **PLS-as-a-service for non-PLS operators** | **GAP** — test scenarios detect gap but don't resolve | Auto-route to PLS network, add review fee to cost |

**Research:** `docs/research/legal/RESEARCH_PLS_AUTOMATION_OPTIONS.md` — 5-option analysis with Michigan law citations (MCL 339.2007).

---

## 4. PAYMENT & SETTLEMENT

```
Buyer --> [M14: Wallet Ledger] --> [M15: Stripe Service]
                |                         |
                v                         v
         [M16: Settlement Router] --> [M17: Escrow Contract]
                |                     [M18: x402 Middleware]
                v
         [M37: Splits Distribution]
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M14 | **Wallet Ledger** | Built | `auction/wallet.py` | Internal accounting: debit/credit with entry types (reservation_25, delivery_75, refund, credit). Thread-safe. Source of truth for balances. |
| M15 | **Stripe Service** | Built | `auction/stripe_service.py` | Stripe Connect Express: wallet top-ups (PaymentIntent), operator payouts (Transfer), webhook validation. Live/stub dual mode. EUR/USD. Bug: currency hardcoded to USD — fix in v1.1 Phase 1. |
| M16 | **Settlement Router** | Designed | `auction/settlement.py` | 4-mode interface (FD-1): immediate_transparent (Base x402), immediate_private (Horizen L3), batched_transparent (DTN), batched_private. Routes by payment_method. |
| M17 | **On-Chain Escrow** | Planned (v1.1 Phase 3) | `contracts/RobotTaskEscrow.sol` (not yet created) | Base USDC escrow: hold on acceptance, release on delivery, refund on timeout. Commitment hash memos (FD-4). |
| M18 | **x402 Middleware** | Deferred | — | Reserved for agent-to-robot control sessions (Tumbller). NOT used for marketplace settlement (critique found wrong abstraction). |
| M37 | **Splits Distribution** | Deferred | — | Splits.org for production-scale multi-operator distribution. Not needed for demo (direct USDC transfer to robot wallet is simpler). |
| M38 | **Browser Wallet Connect** | Built | `docs/mcp_demo_2/` | Commit-on-hire gasless USDC. Buyer signs permit on award (no money moves), payment executes on delivery acceptance. Rabby, MetaMask, Coinbase Wallet. Base + Ethereum mainnet. |
| M39 | **Permit Relay** | Built | `chatbot/src/index.js` (`/api/commit-payment`, `/api/execute-payment`) | Two-phase: stores signed permit in KV on commit, submits on-chain on execute. Balance checks, expiry handling, double-execution prevention. Relay wallet `0x4b59...0d9`. |

---

## 5. IDENTITY & REPUTATION

```
Robot --> [M19: ERC-8004 Bridge] --> Agent Card (on-chain)
  |
  v
[M20: Reputation Tracker] --> [M21: BBS+ Credentials]
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M19 | **ERC-8004 Discovery Bridge** | Built | `auction/discovery_bridge.py`, `docs/mcp_demo_2/` (browser subgraph+RPC) | Server-side: adapts RobotPlugin to engine. Browser-side: direct subgraph query (`fleet_provider: yakrover`) + `getAgentWallet()` RPC call. No server dependency for discovery. |
| M20 | **Reputation Tracker** | Built | `auction/reputation.py` | Rolling 30-day window: completion rate, on-time rate, rejection rate. Records task outcomes. Used in bid scoring (15% weight). |
| M21 | **BBS+ Credential Schema** | Designed | — | Privacy-compatible reputation: selective disclosure of task count, success rate, capability attestations. Earth real-time + Lunar DTN update protocols. |

---

## 6. PERSISTENCE & INFRASTRUCTURE

```
Engine --> [M22: SQLite Store] --> auction.db
  |
  v
[M23: Commitment Hash] --> on-chain memo
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M22 | **SQLite Store** | Built | `auction/store.py` | Async + sync persistence: tasks, bids, wallet balances, ledger entries, reputation. WAL journal mode. JSON serialization for Decimal/datetime. |
| M23 | **Commitment Hash** | Built | `auction/core.py` (compute_commitment_hash) | H(request_id \|\| salt) for on-chain memos. Prevents permanent public task-payment linkage. Platform DB stores mapping for audit. |

---

## 7. API & INTEGRATION LAYER

```
Claude/Agent --> [M24: MCP Tools] --> Engine
Browser      --> [M25: REST API]  --> Engine
Tunnel       --> [M26: MCP Server] --> Engine
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M24 | **MCP Tool Layer** | Built | `auction/mcp_tools.py` | 36 FastMCP tools wrapping the auction engine. Structured JSON responses. Error standardization. Decimal serialization. |
| M25 | **REST API** | Built | `auction/api.py` | FastAPI router for web frontend: intent capture, task posting, bid retrieval. CORS. |
| M26 | **Standalone MCP Server** | Built | `mcp_server.py` | HTTP server exposing 36 tools via REST (/api/tool/{name}). Cloudflare Tunnel support. Health + discovery endpoints. |

---

## 8. FRONTEND & PRESENTATION

```
yakrobot.bid      --> [M27: Demo Site]
yakrobot.bid/mcp-demo --> [M28: MCP Demo]
/api/chat         --> [M29: Chatbot Worker]
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M27 | **Demo Site** | Built | `demo/index.html` | Interactive MDOT I-94 walkthrough. 6-step flow. Operator sign-up. Live feed. Mobile responsive. Hosted on here.now. |
| M28 | **MCP Demo** | Built | `docs/mcp_demo/index.html` | Claude orchestrates real auction via tool_use loop. Step feed with markdown rendering. Tunnel URL input. |
| M29 | **Chatbot Worker** | Built | `chatbot/src/index.js` | Cloudflare Worker: streaming chat proxy to Anthropic API. Rate-limited. Injection-protected. Demo tool_use loop endpoint. |

---

## 9. TRACKING & OBSERVABILITY

```
Engine events --> [M30: Event Log] --> [M31: Task Feed API]
                       |
         +-------------+-------------+
         |             |             |
  [M32: Buyer View] [M33: Operator View] [M34: Admin Console]
```

| # | Module | Status | Key Files | Description |
|---|--------|--------|-----------|-------------|
| M30 | **Event Log** | Building | `auction/events.py`, `auction/store.py` (events table) | Structured event stream: every state change, payment, progress update persisted with timestamp, actor, and context. Foundation for all dashboards. |
| M31 | **Task Feed API** | Building | `auction/mcp_tools.py` (auction_get_task_feed, auction_update_progress) | MCP tools for querying event timeline per task/actor and pushing execution progress updates. |
| M32 | **Buyer Dashboard** | Planned | — | "Where's my survey?" Task timeline, SLA countdown, project rollup, payment status. UberEats-style tracking. |
| M33 | **Operator Dashboard** | Planned | — | "What's on my plate?" Task discovery, active jobs, progress reporting, earnings, compliance alerts. |
| M34 | **Admin Console** | Planned | — | "How's the platform?" GMV, task volume, SLA rates, operator health, dispute queue, financials. |

---

## Module Dependency Graph

```
                    +-----------+
                    |  Frontend |  M27, M28, M29
                    +-----+-----+
                          |
                    +-----v-----+
                    |  API Layer |  M24, M25, M26
                    +-----+-----+
                          |
          +---------------+---------------+
          |               |               |
    +-----v-----+  +-----v-----+  +------v------+
    | Task Intake|  |  Auction  |  | Compliance  |  M1-M4, M5-M9, M10-M13
    +-----+-----+  +-----+-----+  +------+------+
          |               |               |
          +-------+-------+-------+-------+
                  |               |
            +-----v-----+  +-----v-----+
            |  Payment  |  |  Identity  |  M14-M18, M19-M21
            +-----+-----+  +-----+-----+
                  |               |
            +-----v-----+  +-----v-----+
            |  Storage  |  |  Infra    |  M22-M23
            +-----------+  +-----------+
```

---

## Development Priority by Phase

### v1.0 (Complete) -- 20 modules
M1-M15, M19-M20, M22-M28 -- core auction, payments, compliance, frontend

### v1.0.2 (In Progress) -- 2 modules
M30 (Event Log), M31 (Task Feed API) -- tracking infrastructure

### v1.1 (Complete 2026-04-06) -- 7 modules
M38 (Browser Wallet Connect), M39 (Permit Relay), M40 (MCPRobotAdapter), M41 (On-chain Discovery), M42 (Stripe Payment Element), M43 (8004scan Feedback), M44 (Fly.io Deployment). Demo at yakrobot.bid/mcp-demo-3. Real robots bid + execute via MCP. USDC on Base mainnet + Stripe inline. Always-on infrastructure on Fly.io.

### v1.5 (Next) -- 4 modules
M16 (Settlement Router), M23 (Commitment Hash on-chain), M32 (Buyer Dashboard), M33 (Operator Dashboard), M34 (Admin Console)

### v2.0+ (Future) -- 4 modules
M21 (BBS+ Credentials), ERC-8004 agent card extensions, compound task decomposition

---

## Quick Reference: Module --> File

| Module | Primary File |
|--------|-------------|
| M1 RFP Processor | `auction/rfp_processor.py` |
| M2 Standards Engine | `auction/core.py` + `references/standards-reference.md` |
| M3 Task Validator | `auction/core.py` |
| M4 Site Recon | `.claude/skills/rfp-to-site-recon/` |
| M5 Auction Engine | `auction/engine.py` |
| M6 Operator Registry | `auction/operator_registry.py` |
| M7 Bid Scorer | `auction/core.py` |
| M8 State Machine | `auction/engine.py` |
| M9 Mock Fleet | `auction/mock_fleet.py` |
| M10 Compliance Checker | `auction/compliance.py` |
| M11 Bond Verifier | `auction/bond_verifier.py` |
| M12 Terms Comparator | `auction/terms_comparator.py` |
| M13 Agreement Generator | `auction/agreement.py` |
| M14 Wallet Ledger | `auction/wallet.py` |
| M15 Stripe Service | `auction/stripe_service.py` |
| M16 Settlement Router | `auction/settlement.py` |
| M17 On-Chain Escrow | `contracts/RobotTaskEscrow.sol` (planned) |
| M18 x402 Middleware | (planned) |
| M19 ERC-8004 Bridge | `auction/discovery_bridge.py` |
| M20 Reputation Tracker | `auction/reputation.py` |
| M21 BBS+ Credentials | (designed) |
| M22 SQLite Store | `auction/store.py` |
| M23 Commitment Hash | `auction/core.py` |
| M24 MCP Tool Layer | `auction/mcp_tools.py` |
| M25 REST API | `auction/api.py` |
| M26 MCP Server | `mcp_server.py` |
| M27 Demo Site | `demo/index.html` |
| M28 MCP Demo | `docs/mcp_demo/index.html` |
| M29 Chatbot Worker | `chatbot/src/index.js` |
| M30 Event Log | `auction/events.py` |
| M31 Task Feed API | `auction/mcp_tools.py` |
| M32 Buyer Dashboard | (planned) |
| M33 Operator Dashboard | (planned) |
| M34 Admin Console | (planned) |
| M35 Deliverable QA | `auction/deliverable_qa.py` |
| M36 PLS Review & Stamp | (gap — PLS-as-a-service routing + electronic seal) |
| M37 Splits Distribution | (deferred — direct transfer for demo, Splits for production scale) |
| M38 Browser Wallet Connect | `docs/mcp_demo_2/` (gasless USDC, ERC-2612 permit) |
| M39 Permit Relay | `chatbot/src/index.js` (`/api/relay-usdc`) |
