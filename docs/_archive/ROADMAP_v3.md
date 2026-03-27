# Product Roadmap v3 — Robot Task Auction Marketplace

**Project:** yakrover-auction-explorer
**Owner:** Product
**Last updated:** 2026-03-27 (rev 3, post user-profile mapping + frontend sprint)
**Status:** v1.0 built (151 tests, 15 MCP tools). v1.5 next. This is the unified roadmap incorporating marketplace, lunar, privacy, frontend, and platform operations tracks.

> All product decisions and technical constraints referenced by ID live in `docs/DECISIONS.md`.
> Version boundaries defined in `docs/SCOPE.md`. Milestone details in `docs/MILESTONES.md`.
> Feature requirements for the next build: `docs/FEATURE_REQUIREMENTS_v15.md`.
> User profiles: `docs/USER_PROFILES.md` (13 profiles). Missing-profile research: `research/RESEARCH_MISSING_USER_PROFILES.md`.
> Frontend design: `docs/FRONTEND_DESIGN_SPRINT.md`. Development strategy: `docs/DEVELOPMENT_STRATEGY.md`.
> Research backing: `research/RESEARCH_SYNTHESIS_LUNAR.md`, `research/RESEARCH_SYNTHESIS_PRIVATE.md`, `research/RESEARCH_CRITIQUE.md`, `research/RESEARCH_PRIVACY_CHAINS.md`, `research/FOUNDATIONAL_TECH_ANALYSIS.md`, `research/RESEARCH_BUY_A_ROBOT_STORY.md`.

---

## User Map

Every feature on this roadmap exists to serve a named user. If a feature cannot be traced to a persona below, it does not belong.

| Version | Persona | Type | Story | Key Action |
|---------|---------|------|-------|------------|
| **v1.0 (built)** | Sarah — Facilities Manager | Buyer | Marketplace | Hires robots for warehouse sensor readings via AI assistant |
| | Sarah's IT Admin | Admin | Marketplace | Sets up corporate account, payment, API keys |
| | Robot Operator (fleet, e.g. YakRobotics) | Operator | Marketplace | Registers fleet, configures pricing, receives payouts |
| | Claude (AI Agent) | Agent | All | Translates intent to structured tasks, runs auctions, verifies delivery |
| **v1.5** | Anonymous Web Visitor | Buyer (potential) | Marketplace | Explores platform, captures intent before authenticating |
| | Developer / Integrator | Buyer/Operator | Marketplace | Discovers and integrates via MCP or REST API |
| | Platform Administrator | Admin | All | Monitors health, manages payouts, resolves disputes |
| **v2.0** | Diane — Program Manager | Buyer | Privacy | Hires robots for classified inspections with encrypted specs |
| | Diane's Security Officer | Admin | Privacy | Configures encryption, viewer keys, private-task mode |
| | Diane's CFO | Auditor | Privacy | Audits private task spend via viewer key |
| | Alex — Independent Operator | Operator | Supply | Buys a robot, onboards it, earns revenue |
| | Enterprise Procurement | Buyer | Marketplace | Volume contracts, SLAs, consolidated invoicing |
| | Fleet Operator (multi-robot) | Operator | Marketplace | Manages commercial fleet, per-robot economics |
| **v2.1-L** | Kenji — Project Coordinator | Buyer | Lunar | Dispatches regolith surveys via DTN to lunar rovers |
| | Kenji's Ops Lead | Admin | Lunar | Manages project budgets, rover fleet, spending limits |
| **v3.0+** | Data Consumer | Buyer | Marketplace | Subscribes to recurring/aggregated sensor data |
| | Hardware Manufacturer | Partner | Supply | Lists marketplace-compatible starter kits |
| | Referral / Channel Partner | Partner | Growth | Brings buyers or operators, earns commission |

---

## Visual Timeline

```
              2026                                      2027                    2028+
Week  1    8    12   16   20   24   28   32   36   40   44   52    ...
      |----|----|----|----|----|----|----|----|----|----|----|----|-- - -

MAIN  ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
      v0.1──v1.0    v1.5         v2.0                   v3.0
      (BUILT)       Crypto Rail  Multi-Robot +           Convergence
                    + Foundation  Platform Privacy

FRONT              ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                   Ph0  Ph1     Ph2    Ph3
                   Land Claude  Pay+   Agent
                   +Intent      Auction Discovery

SUPPLY                   ░░░░░░░░░░░░░░░░░░░░░░░░
                         Stretch    v2.0
                         CLI+Reg   Dashboard+Heatmap

OPS                ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                   Basic admin     Full admin suite
                   (health,payouts) (disputes,verification)

LUNAR                                  ░░░░░░░░░░░░░░░░░░░░░░░░░░ · · ·
                                       v2.1-L             v2.2-L
                                       DTN-Tolerant       Multi-Project
                                       Auction            Coordination

PRIVACY                          ░░░░░░░░░░░░░░░░░░░░░░░░░░
                                 v2.0 (TEE)    v2.1-P
                                 Platform      Delegated ZK
                                 Privacy       Proofs

      ▓▓▓▓▓  build        ░░░░░  stabilize / field test        · · ·  horizon
```

---

## Shared Foundation (v1.0 — v1.5)

Everything built through v1.0 serves all three user stories. Sarah, Kenji, and Diane all rely on the same auction core.

### Already built (v1.0)

- Auction core library: `Task`, `Bid`, `AuctionResult`, `score_bids()` with four-factor weighted scoring (per AD-6)
- Hard constraint filter, HMAC + ERC-8004 Ed25519 bid signing (per PD-3)
- Failure recovery: robot offline, bad payload, auto-accept timer (per AD-7, PD-6)
- Internal wallet ledger with debit/credit log (per TC-2)
- Stripe wallet onboarding + Connect Express payouts (per TC-2, TC-3)
- Persistent state via SQLite `SyncTaskStore`
- 15 MCP tools including `auction_quick_hire`
- Structured error responses, `available_actions`, `next_action` patterns (per AD-13, AD-14, AD-15)

### Must be added in v1.5 for all three stories

These are not privacy or lunar features. They are foundational changes that prevent architectural debt across all tracks:

1. **Settlement abstraction layer** (FD-1). The `RobotTaskEscrow.sol` contract and payment middleware must support a settlement interface that can route to four future modes: immediate transparent, immediate private, batched transparent, batched private. Only mode 1 (immediate transparent on Base) is implemented in v1.5.

2. **Cryptographic commitment replaces `request_id` in on-chain memos** (FD-4). Replace with `H(request_id || salt)` on-chain; plaintext mapping in the platform database. Audit capability preserved; privacy leak eliminated.

3. **Robot wallet addresses not exposed in public API** (PP-2). Use platform-internal identifiers in the API layer; translate to on-chain addresses only at settlement.

---

## v1.5 — Crypto Rail + Privacy-Aware Foundation + Frontend + Dev Infrastructure

> **Detailed feature requirements:** See `docs/FEATURE_REQUIREMENTS_v15.md` for acceptance criteria and test plan.
> **Frontend spec:** See `docs/FRONTEND_DESIGN_SPRINT.md` for wireframes and architecture.
> **Dev strategy:** See `docs/DEVELOPMENT_STRATEGY.md` for testing layers and CI/CD.

| | |
|---|---|
| **Timeline** | Weeks 13-16 (4 weeks) |
| **Milestone** | Milestone 5 (Crypto Rail + Foundation + Frontend + Dev Infra) |
| **Serves** | Sarah, IT Admin, Claude, Anonymous Visitor, Developer/Integrator, Platform Admin |
| **Goal** | USDC on Base alongside Stripe. Settlement abstraction designed for all future modes. Frontend live with intent capture. CI/CD and testing infrastructure in place. Basic platform admin tooling. |

### What the user can do that they couldn't before

Sarah's crypto-native colleague pays for a robot task with USDC on Base. Payment clears in seconds via x402. Fiat buyers continue using Stripe. An on-chain commitment hash proves the transaction is linked to a task without revealing which one. Task specs are encrypted at rest.

An anonymous visitor lands on yakrobot.bid, types "temperature reading in my warehouse," sees an estimated cost and available robots -- all without creating an account. After connecting Claude and payment, they complete their first task in under 2 minutes.

A developer fetches `/.well-known/mcp.json` and discovers the MCP endpoint, tool list, and auth flow.

The platform operator monitors a basic health dashboard showing task volume, payout status, and system health.

### Key deliverables

**Crypto rail (F-1 through F-4):**
- x402 middleware on `accept_bid()` endpoint (per TC-4)
- `RobotTaskEscrow.sol` deployed on Base with settlement interface abstraction (FD-1) -- 4-mode interface, only Mode 1 implemented
- USDC wallet top-up on Base alongside Stripe credit bundles
- Payment method selection at task posting (`"stripe"` | `"usdc"` | `"auto"`)
- ERC-8004 agent card extended with `min_price`, `accepted_currencies`, `reputation` fields (F-8)

**Privacy-aware foundation (F-5 through F-9):**
- **FD-1 / F-5:** Settlement abstraction interface -- `SettlementInterface` protocol with `settle()`, `verify()`, `batch_settle()`. Both `StripeSettlement` and `BaseX402Settlement` implement it. Modes 2-4 are documented stubs.
- **FD-4 / F-6:** Cryptographic commitment hash `H(request_id || salt)` in on-chain memos. Plaintext mapping in platform database.
- **PP-2 / F-7:** Platform-internal robot identifiers in API; wallet addresses hidden from public endpoints.
- **PP-5-pre / F-9:** Task specs encrypted at rest (AES-256-GCM) in SQLite. Transparent to MCP tools.

**Design-only deliverables (F-10, F-11):**
- **LD-2-pre / F-10:** DTN message schema in `DTN_MESSAGE_SCHEMA.md` -- message types, idempotency model, LunaNet size estimates.
- **FD-2-pre / F-11:** BBS+ credential schema in `BBS_CREDENTIAL_SCHEMA.md` -- fields, update protocols (Earth + lunar), selective disclosure profiles.

**Evaluation (F-12):**
- **FD-5 / F-12:** Deploy test escrow on Horizen L3 testnet. Evaluate USDC bridging, HCCE, x402 compatibility. Go/no-go for Mode 2.

**Frontend Phase 0 -- Static Landing + Intent Capture (1 week):**
- Next.js project deployed to Vercel with Tailwind CSS
- Landing page: search bar, example prompts, robot cards, live feed ticker (mock data initially)
- `/api/intent` endpoint stores raw search text + anonymous session ID
- `/.well-known/mcp.json` static file (503 for MCP transport until Phase 1)
- `schema.org/WebApplication` JSON-LD, responsive layout, Lighthouse > 90

**Frontend Phase 1 -- Claude Integration + Structured Requests (2 weeks):**
- Anthropic OAuth via NextAuth.js ("Sign in with Claude")
- Raw intent sent to Claude for structuring; structured spec displayed with edit capability
- SSE endpoint for global feed connected to `AuctionEngine` events (live data replaces mock)
- Robot discovery via `discovery_bridge.discover()` renders real robot cards
- Intent-to-task conversion analytics

**Development infrastructure:**
- CI/CD pipeline: GitHub Actions (unit tests + ruff lint + mypy type-check on every push)
- Stripe test-mode integration test suite (5-8 tests)
- Base Sepolia escrow test suite (Foundry + Python)
- Settlement abstraction unit tests, commitment hash property tests (hypothesis)
- CLAUDE.md with payment safety rules, pre-commit hooks for secret detection
- pytest markers separating unit / stripe / blockchain / fleet tests

**Platform operations (basic):**
- Admin health dashboard: active robots, task volume, error rates, system uptime
- Payout monitoring: pending/completed payouts, settlement status
- Basic audit log viewer (all payment state changes per CLAUDE.md rules)

**Supply-side stretch goals:**
- Operator registration CLI (`yakrover register`) -- firmware flash, WiFi config, ERC-8004 registration, sensor calibration
- Gas-sponsored ERC-8004 registration for new operators (< $0.10/registration on Base)

### Success criteria

- End-to-end task completed with USDC on Base Sepolia (under $1)
- On-chain transaction includes commitment hash; no raw `request_id` in any on-chain data
- Fiat path still works -- all 151 existing tests pass
- Robot wallet addresses never appear in any MCP tool response
- Settlement abstraction reviewed for lunar/privacy extensibility
- Task specs encrypted in SQLite (verifiable by reading raw database)
- DTN and BBS+ design docs reviewed
- Horizen L3 evaluation report completed with go/no-go
- Frontend Phase 0 live at public URL; intent capture working
- Frontend Phase 1: user can type request, sign in with Claude, see structured spec and real robots
- CI pipeline passes on every push; ruff + mypy configured
- Admin can view system health and payout status

### What is NOT included

- No cross-chain support (Base only; Horizen L3 is evaluation only)
- No automated escrow dispute resolution -- operator-controlled release only
- No staking or slashing
- No TEE infrastructure or encrypted matching (v2.0)
- No BBS+ credential issuance code (v2.0)
- No DTN transport code (v2.1-L)
- No ZKsync Prividium (wrong model -- permissioned enterprise, not open marketplace)
- No Aleo integration (monitor only per FD-3)
- No payment flow in frontend (Phase 2, requires v1.5 crypto rail)

---

## v2.0 — Multi-Robot Workflows + Platform Privacy + Full Frontend + Operator Dashboard

| | |
|---|---|
| **Timeline** | Weeks 17-28 (12 weeks) |
| **Milestone** | Milestone 6 (Upstream Contribution) + Privacy Phase 1 |
| **Serves** | Diane, Security Officer, CFO, Alex, Enterprise Procurement, Fleet Operator, Platform Admin |
| **Goal** | Compound tasks across multiple robots. TEE-based privacy for Diane. Full operator dashboard for Alex. Payment + live auction in frontend. Agent discovery. Full platform admin suite. |

### What the user can do that they couldn't before

Sarah posts a compound task: "Inspect Bay 3 with thermal camera, then send a ground rover for a close-up of any hotspot." The system decomposes it, auctions each step, and chains the results.

Diane posts the same kind of task with `privacy: true`. Her task spec is encrypted, matched inside a TEE enclave, and only the winning robot sees the full details. Her CFO audits via viewer key.

Alex sees the marketplace dashboard showing task activity, clicks "Become an Operator," orders an ESP32 sensor rover for EUR 60, onboards it via the CLI in 30 minutes, and earns his first EUR 0.35 within hours. A demand heatmap shows him where unserved tasks exist.

An enterprise procurement team sets up volume pricing, SLA terms, and consolidated monthly invoicing for 500 readings/month across 12 facilities.

The platform admin resolves disputes, verifies operators, and manages the full fee schedule.

### Key deliverables

**Multi-robot (all users):**
- Compound task decomposition: parent task splits into ordered sub-tasks
- Sub-task chaining: output of step N feeds spec for step N+1
- Robot-to-robot handoff protocol
- Upstream PRs: `bid()` on `RobotPlugin`, fleet MCP auction tools, x402 middleware (opt-in via `AUCTION_ENABLED=true`)
- Updated agent card schema with pricing and reputation fields

**Platform privacy (Diane's story, Phase 1):**
- TEE-based confidential compute (Intel TDX) for task matching and scoring (PP-4)
- Encrypted task specs: decrypted only inside TEE enclaves (PP-5)
- Public capability vectors for robot matching -- generalized classes to limit leakage (PP-6)
- Viewer keys: CFO sees metadata, buyer sees full detail (PP-7)
- Platform escrow key in HSM for lawful regulatory access (PP-8)
- TEE attestation verification before every enclave session; graceful degradation on failure (PP-9)

**Reputation (shared infrastructure):**
- BBS+ credential schema operational (FD-2): task count, success rate, avg completion time, capability attestations, environmental survival history
- Threshold BBS+ issuance across 3+ platform nodes (PP-10) -- acknowledged: single-issuer at seed scale
- Selective disclosure: robots prove aggregate stats without revealing task history
- Credential update protocol for Earth (low-latency) and lunar (DTN-tolerant)

**Frontend Phase 2 -- Payment + Live Auction (2 weeks):**
- Stripe Checkout for credit bundle purchase
- WalletConnect + wagmi for USDC wallet connection
- Payment step in progressive-disclosure funnel
- Auction live view with SSE: bids, scoring, winner, execution, delivery
- Result view with data display, JSON download, receipt link, "Hire Again"
- Error states: no robots, robot failure, insufficient balance

**Frontend Phase 3 -- Agent Discovery + Operator Dashboard (1 week):**
- `/.well-known/mcp.json` returns live MCP metadata (tools, auth, endpoints)
- MCP SSE and Streamable HTTP transports exposed publicly
- Schema.org structured data on all pages
- "Add to Claude Desktop" / "Add to Claude Code" / "Copy API Key" buttons
- OpenAPI spec at `/api/openapi.json`
- Operator dashboard: robot registration, pricing config, revenue/payout view, health monitoring, demand heatmap

**Supply-side (Alex's story):**
- Full operator dashboard: task history, revenue per robot, health alerts, payout history
- Demand heatmap API: unserved tasks by location and capability
- Starter kit marketplace page: recommended hardware by use case (ESP32 rover EUR 60, Tumbller EUR 40, Pi rover EUR 120, Tello EUR 100)
- Multi-robot management for operators scaling from 1 to 5 robots
- Operator reputation (BBS+ credentials for operators, not just robots)

**Enterprise procurement:**
- Organization accounts with role hierarchy (admin, buyer, finance)
- Volume pricing / committed-use discounts
- SLA definitions per contract (max response time, uptime guarantees)
- Invoice generation (net-30/net-60) alongside prepaid credits
- Approval workflows (budget holder -> manager -> procurement)

**Platform operations (full suite):**
- Dispute resolution workflow: buyer reports -> admin reviews -> refund or release
- Operator verification and management: approve, suspend, configure fee splits
- Content moderation for robot listings
- Payout reconciliation dashboard
- Auction parameter configuration (scoring weights, timeout values)
- Privacy infrastructure monitoring: TEE attestation success rates, escrow key access audit log

**Development infrastructure:**
- Real fleet integration test (fakerover + Stripe end-to-end)
- Branch protection on main
- Webhook idempotency tests
- TEE encrypted matching tests
- Chaos/adversarial test suite
- Coverage gating (>80% for payment code)

### Success criteria

- 2-step compound task completes end-to-end with different robots per step
- Upstream PRs merged into yakrover-8004-mcp
- Private task completes with encrypted spec; only winning robot sees details
- TEE attestation failure triggers user choice: retry, downgrade, or cancel
- Viewer key decrypts task metadata for CFO audit
- BBS+ credential schema reviewed for cross-environment use
- Privacy overhead < 15 seconds on standard sensor reading
- Frontend end-to-end: anonymous visit -> intent -> Claude -> payment -> auction -> result
- Agent discovers MCP endpoint from URL and completes task programmatically
- Alex onboards a robot and earns revenue within 1 hour of unboxing
- Admin resolves a dispute via the admin dashboard

### What is NOT included

- No full ZK proofs for task verification -- TEE-backed proofs only
- No Privacy Pools integration (not yet on Base)
- No Aleo settlement rail
- No DTN protocol -- lunar track starts in v2.1-L
- No robot-to-robot sub-contracting
- No reputation slashing

---

## v2.1-L — Lunar Phase 0: DTN-Tolerant Auction

| | |
|---|---|
| **Timeline** | Weeks 29-36 (8 weeks, parallel to main track) |
| **Milestone** | Lunar Milestone L-1 |
| **Serves** | Kenji, Ops Lead |
| **Goal** | Centralized Earth-side coordinator dispatches tasks to lunar rovers via DTN. Single operator, validating protocol end-to-end. Not a marketplace -- a dispatch system. |

### What the user can do that they couldn't before

Kenji asks his AI assistant for a regolith density survey at the lunar south pole. The coordinator transmits it as a DTN bundle to rovers at Shackleton rim. Three rovers evaluate locally and bid. The coordinator scores, assigns, and the rover executes autonomously. Kenji gets his density map in about 4 minutes. Settlement is batched every 6 hours.

### Key deliverables

- Centralized Earth-side coordinator with geographic failover (LD-1)
- DTN/Bundle Protocol (RFC 9171) integration for Moon-Earth protocol messages (LD-2)
- Deadline-based bid window: RFQ via DTN, configurable 30-120s window, score after close (LD-3)
- Thin Moon-side agent: minimal C/Rust state machine (~100 KB) for bid generation, task acceptance, completion proofs (LD-4)
- Lunar task spec extensions: `thermal_window`, `power_budget_wh`, `max_duration_hours`, `illumination_required`, `comm_window_required`, `safety_zone`, `checkpoint_intervals`, `failure_recovery_mode` (LD-5)
- Lunar scoring factors: price 30%, speed 20%, confidence 15%, track record 10%, power margin 15%, dust exposure 10% (LD-6)
- Optimistic verification: structured completion proof, 24-hour dispute window (LD-7)
- Batched transparent settlement via Mode 3 of settlement abstraction (LD-8)
- Pessimistic self-locking: rover marks itself unavailable on task acceptance (LD-9)
- Lunar night queue: tasks with TTL auto-execute at lunar dawn (LD-10)
- Checkpoint-and-resume for long-duration tasks and approaching lunar night (LD-11)

### Success criteria

- End-to-end: task dispatched from Earth, executed by simulated rover via DTN, results verified, settlement batched on Base
- Bid window handles 3-8 second RTT without protocol failure
- Checkpoint-and-resume produces pro-rated payment and resumable checkpoint
- All protocol messages are idempotent DTN bundles tolerating replay and reordering

### What is NOT included

- No competitive marketplace -- single-operator dispatch (3-10 rovers too few for auction dynamics)
- No cross-robot attestation
- No lunar sidechain or on-Moon consensus
- No privacy for lunar tasks (deferred to v3.0)
- No real lunar hardware -- terrestrial DTN testbed only

---

## v2.1-P — Privacy Phase 2: Delegated ZK Proofs + Horizen L3 Settlement

| | |
|---|---|
| **Timeline** | Weeks 29-36 (8 weeks, parallel to lunar track) |
| **Milestone** | Privacy Milestone P-2 |
| **Serves** | Diane, Security Officer, CFO |
| **Goal** | Upgrade from TEE-only to delegated ZK proofs. Implement Mode 2 settlement on Horizen L3 if v1.5 evaluation was positive. BBS+ anonymous reputation at operational scale. |
| **Depends on** | v2.0 TEE infrastructure. v1.5 Horizen L3 evaluation (FD-5). |

### What the user can do that they couldn't before

Diane's task completion is verified by a ZK proof -- not just TEE attestation. A delegated prover generates a proof that results satisfy the spec without seeing the spec or results in plaintext. Diane's robot proves reputation via BBS+: "847 tasks, 99.1% success rate" -- without revealing which tasks.

If Horizen L3 evaluation was positive: private tasks settle on Horizen L3 (Mode 2). Same Solidity escrow, USDC bridges from Base.

### Key deliverables

**ZK proof infrastructure:**
- SP1 proving circuit for sensor verification (PP-11)
- Delegated proving via Succinct Prover Network on Phala Cloud TEE (PP-12)
- Benchmarked proof time: target < 5 seconds (PP-13)

**Horizen L3 Mode 2 settlement (conditional on FD-5):**
- `RobotTaskEscrow.sol` on Horizen L3 mainnet (PP-19)
- USDC bridge: Base L2 -> Horizen L3 automated (PP-20)
- x402 facilitator adapted for Horizen selective disclosure (PP-21)
- `HorizenL3Settlement` implements `SettlementInterface` (PP-22)
- Confidential task matching via HCCE (PP-23)

**Reputation:**
- BBS+ anonymous reputation operational: threshold issuance, selective disclosure, per-task updates (PP-14)
- Semaphore-based anonymous group membership (PP-15)

**Settlement privacy:**
- Privacy Pools on Base **if 0xbow has deployed** (PP-16). Otherwise defer to v3.0.
- TEE compromise fallback plan (PP-17)
- On-chain settlement: only amount, escrow address, nonce, commitment hash (PP-18)

### Success criteria

- ZK proof for standard sensor task in < 5 seconds (benchmarked)
- Robot proves reputation via BBS+ without revealing task history
- TEE attestation failure triggers graceful degradation
- Privacy overhead < 15 seconds total
- If Horizen L3 positive: Mode 2 end-to-end (deposit on Base -> bridge -> escrow -> release -> bridge back)

### What is NOT included

- No Aleo (no non-EU market identified; monitor only per FD-3)
- No ZKsync Prividium (wrong model; see `research/RESEARCH_PRIVACY_CHAINS.md`)
- No FHE scoring (4-5 orders of magnitude too slow)
- No MPC sealed-bid auctions (trivial with 2-3 robots; revisit at 10+)

---

## v2.2-L — Lunar Phase 1: Multi-Project Coordination

| | |
|---|---|
| **Timeline** | Weeks 37-44 (8 weeks) |
| **Milestone** | Lunar Milestone L-2 |
| **Serves** | Kenji, Ops Lead |
| **Goal** | 2-3 operators share the coordinator. Tasks assigned by priority and capability. Cross-rover attestation for high-value tasks. |

### Key deliverables

- Priority-based scheduling across 2-3 projects with configurable SLA tiers (LD-13)
- Cross-robot attestation: independent operator required, verification bounty from task fee (LD-14)
- Lunar night transition management: automated task checkpointing fleet-wide (LD-15)
- Multi-project queue with advance booking across lunar days (LD-16)
- Coordinator governance: auditable logs, open-source algorithm, multi-party oversight API (LD-17)
- Sensitivity-aware economic model: pessimistic/realistic/optimistic scenarios (LD-18)

### Success criteria

- 2 projects with different priority tiers schedule on shared fleet without conflict
- Cross-robot attestation completes within one DTN round-trip
- Lunar night transition: all tasks checkpoint cleanly, no stuck escrow, all resume at dawn

### What is NOT included

- No competitive auction (robot populations still < 15)
- No full decentralization -- centralized coordinator with governance
- No privacy for lunar tasks (v3.0)

---

## v3.0 — Convergence

| | |
|---|---|
| **Timeline** | Weeks 45-52+ |
| **Milestone** | Unified platform release |
| **Serves** | All personas. Data Consumer and Hardware Manufacturer enter here. |
| **Goal** | All three tracks merge. Private tasks on Earth and Moon. Multi-robot workflows with confidential chained tasks. Cross-fleet competition where populations support it. |

### What the user can do that they couldn't before

Kenji posts a multi-step site assessment at Shackleton rim. The task is decomposed, dispatched to rovers from two operators, and results are confidential -- operators cannot see each other's work. Settlement is batched and private. On Earth, Diane runs a compound private inspection across three corridors with different robots, each step's encrypted output feeding the next, all inside the TEE boundary.

A data consumer subscribes to recurring temperature readings across 50 warehouses, receiving daily aggregated datasets.

### Key deliverables

- Private lunar tasks: TEE on Earth-side coordinator protects metadata from competing operators
- Batched private settlement (Mode 4) -- if Privacy Pools on Base is available
- BBS+ credentials unified across Earth and lunar: same schema, DTN-tolerant updates
- Cross-fleet competition on Earth: robots from different operators scored on BBS+ reputation
- Encrypted chained task outputs for multi-robot private workflows
- Competitive marketplace dynamics where populations exceed ~15 (Earth first)
- Recurring task scheduling and data aggregation API (Data Consumer)
- Partner application and hardware listing workflow (Hardware Manufacturer)
- Referral tracking and commission system (Referral Partner)

### Success criteria

- Private compound task completes with 2+ robots from different operators
- Lunar task metadata invisible to non-participating operators
- BBS+ credential from lunar rover verifies on Earth-side scorer
- Settlement abstraction supports all four modes in production

---

## Future (Beyond v3.0)

Explicitly deferred. Will be informed by real usage data, regulatory developments, and robot population growth.

| Item | Depends on | Track |
|------|------------|-------|
| Fully decentralized lunar marketplace (30+ rovers) | v2.2-L + population growth | Lunar |
| Aleo private settlement (non-EU markets) | Identified non-EU market + Aleo maturity | Privacy |
| Privacy Pools on Base | 0xbow Base deployment | Privacy |
| Aztec evaluation | Transactions live + USDC bridge + EU clarity | Privacy |
| Fhenix CoFHE on Base | FHE performance breakthrough | Privacy |
| FHE encrypted scoring | FHE performance breakthrough | Privacy |
| MPC sealed-bid auctions (10+ independent robots) | Fleet diversity growth | Privacy |
| Dark Factory (fully autonomous facilities) | v3.0 converged | Main |
| Cislunar DTN testing (real relay links) | Lunar Pathfinder / Moonlight | Lunar |
| Dispute resolution (arbitrator mechanism) | Real payment history | Main |
| Operator staking / slashing | Reputation system + crypto rail | Main |
| Multi-party private workflows (full ZK) | v3.0 TEE workflows | Privacy |
| Insurance / risk provider role | Task volume + failure data | Main |

---

## Cross-Track Dependencies

| Feature | Source | Enables / Blocks | Target |
|---------|--------|------------------|--------|
| Settlement abstraction (FD-1) | Main v1.5 | **Enables** batched settlement | Lunar v2.1-L |
| Settlement abstraction (FD-1) | Main v1.5 | **Enables** private settlement | Privacy v2.1-P |
| Commitment hash (FD-4) | Main v1.5 | **Enables** unlinkable payments | Privacy v2.0+ |
| Encrypted task specs (PP-5-pre) | Main v1.5 | **Preparatory for** TEE matching | Privacy v2.0 |
| Horizen L3 evaluation (FD-5) | Main v1.5 | **Go/no-go for** Mode 2 | Privacy v2.1-P |
| DTN message schema (LD-2-pre) | Main v1.5 | **Design for** DTN transport | Lunar v2.1-L |
| BBS+ credential schema (FD-2-pre) | Main v1.5 | **Design for** reputation | Privacy v2.0, Lunar v2.1-L |
| Frontend Phase 0-1 | Frontend v1.5 | **Enables** anonymous conversion | Supply v2.0 (Alex discovers marketplace) |
| Frontend Phase 2 | Frontend v2.0 | **Requires** v1.5 crypto rail (F-1, F-3, F-4, F-5) | Main v1.5 |
| Admin dashboard (basic) | Ops v1.5 | **Enables** production operation | All v1.5+ |
| TEE infrastructure (PP-4) | Privacy v2.0 | **Enables** confidential lunar coordinator | Lunar v3.0 |
| BBS+ issuance (FD-2) | Privacy v2.0 | **Required by** lunar reputation scoring | Lunar v2.1-L |
| BBS+ DTN-tolerant updates | Privacy v2.0 | **Required by** lunar credential freshness | Lunar v2.2-L |
| Multi-robot workflows | Main v2.0 | **Required by** lunar multi-rover tasks | Lunar v2.2-L |
| Multi-robot workflows | Main v2.0 | **Required by** private compound tasks | Privacy v3.0 |
| Operator dashboard | Supply v2.0 | **Enables** Alex onboarding story | Supply v2.0+ |
| Demand heatmap | Supply v2.0 | **Informs** operator deployment decisions | Supply v2.0+ |
| Lunar scoring factors (LD-6) | Lunar v2.1-L | **Informs** BBS+ lunar credential fields | Privacy v2.0 (schema) |
| Horizen L3 Mode 2 (PP-19-23) | Privacy v2.1-P | **Enables** private settlement without platform TEE | Privacy v3.0 |
| Cross-robot attestation (LD-14) | Lunar v2.2-L | **Requires** independent operators | Lunar ecosystem |
| Competitive marketplace | Main v3.0 | **Requires** robot population > 15 | External (fleet growth) |

---

## Foundational Design Decisions

These decisions are made now (v1.5 timeframe) and affect all future tracks. They are architectural commitments, not features.

### FD-1: Settlement Abstraction Layer

**Decision:** Design the settlement interface to support four modes from v1.5, implementing only mode 1.

| Mode | Timing | Privacy | Chain | Version |
|------|--------|---------|-------|---------|
| 1. Immediate transparent | Real-time | Public | Base / x402 | v1.5 (implemented) |
| 2. Immediate private | Real-time | Shielded | Horizen L3 or Base + TEE | v2.1-P |
| 3. Batched transparent | Async / DTN | Public | Base | v2.1-L |
| 4. Batched private | Async / DTN | Shielded | Base + Privacy Pools or future chain | v3.0 |

**Interface:** Escrow contract and middleware accept a `SettlementMode` enum. `settle(task_id, mode)` routes to mode-specific logic. Base-specific assumptions isolated to Mode 1 implementation.

**Why now:** Both lunar (batched) and privacy (shielded) tracks depend on this. Building without it creates rewrite debt at v2.1.

### FD-2: Unified BBS+ Credential Schema

**Decision:** Single credential schema for robot reputation across Earth and lunar.

**Fields:** `task_count`, `success_rate`, `avg_completion_time`, `capability_attestations`, `environmental_survival_history` (lunar), `operator_id`.

**Update protocol:** Earth -- reissued within seconds. Lunar -- reissued on Earth, relayed via DTN. Stale credentials accepted with configurable scoring discount (default 5% per missed window).

### FD-3: Chain Decision — Base + Horizen L3

**Decision:** Base is primary settlement chain through v2.0+. Horizen L3 on Base is the leading Mode 2 candidate (evaluated in v1.5, implemented in v2.1-P if positive). Aleo is monitor-only.

**Rationale (per `research/RESEARCH_PRIVACY_CHAINS.md`):**
- EU AMLR Article 79 eliminates fully private chains for EU market
- ZKsync Prividium: production-ready ($112M TVL) but permissioned enterprise; wrong model
- Aztec: pre-transaction; Noir not Solidity; too early
- Horizen L3: live on Base mainnet (March 2026), TEE-based, EVM-compatible, same USDC liquidity, selective disclosure

**Chains NOT selected:**

| Chain | Reason |
|-------|--------|
| ZKsync Prividium | Permissioned enterprise; no USDC |
| Aztec | Pre-transaction; Noir not Solidity |
| Polygon Miden | Testnet only; Miden Assembly not Solidity |
| Fhenix CoFHE | Interesting but Base support not live |
| Aleo | No EU market; monitor only |

### FD-4: On-Chain Memo Policy

**Decision:** Memos carry only amount, escrow address, nonce, and `H(request_id || salt)`. Plaintext mapping in platform database only.

**Replaces:** AD-3's raw `request_id`. Audit benefit preserved via commitment hash.

### FD-5: Horizen L3 Evaluation

**Decision:** Evaluate in v1.5. Deploy test escrow, test USDC bridging, evaluate HCCE, test x402 compatibility.

**If negative:** Mode 2 falls back to application-layer TEE on Base. The settlement abstraction ensures zero code changes to the escrow contract.

---

## Dependencies and Risks

### Risk 1 — EU AMLR Article 79 interpretation uncertainty

**Blocks:** v2.0 privacy, v2.1-P Privacy Pools
**Tracks:** Privacy, Lunar (ESA member state operators face same regulation)
**Description:** Article 79 prohibits CASPs from handling privacy-preserving digital assets by July 2027. Whether this covers privacy mechanisms (shielded transfers) or only privacy-native tokens (Monero, Zcash) depends on EBA implementing acts not yet finalized.
**Mitigation:** Legal opinion before v2.0 architecture finalized. Platform-mediated TEE model designed for most conservative interpretation.

### Risk 2 — TEE trust and compromise

**Blocks:** v2.0 platform privacy, v3.0 lunar privacy
**Description:** SGX side-channel attacks are documented. TEE compromise exposes encrypted task specs.
**Mitigation:** Attestation verified per session (PP-9). Fallback: degrade to generalized capability classes (PP-17). ZK proofs (v2.1-P) reduce TEE dependency.

### Risk 3 — Lunar communication relay availability

**Blocks:** v2.1-L, v2.2-L
**Description:** Lunar Pathfinder (late 2026) provides intermittent coverage. ESA Moonlight full ops not until 2030. Multi-hour blackouts are the default.
**Mitigation:** Idempotent DTN bundles. Conservative availability assumptions (< 50% uptime). Batched settlement tolerates hours-to-days delay.

### Risk 4 — Lunar rover population too small for marketplace

**Blocks:** Competitive marketplace features
**Description:** Through 2028, 3-10 rovers from 2-3 operators at any site. Auction dynamics require 15-30+.
**Mitigation:** Phase 0 and 1 are dispatch systems. Competitive bidding deferred to 2030+.

### Risk 5 — Stripe minimum charge constrains pricing

**Blocks:** All fiat versions
**Description:** Per TC-1, no task below $0.50 on Stripe. Many Earth tasks price at $0.20-$0.40.
**Mitigation:** Prepaid wallet model (TC-2): credit bundles, per-task internal ledger debits.

### Risk 6 — SP1 proof time unvalidated

**Blocks:** v2.1-P proof targets
**Description:** "1-5 second" proof time is extrapolated, not measured.
**Mitigation:** Build minimal SP1 circuit and benchmark on Succinct Prover Network during v2.0.

### Risk 7 — Horizen L3 evaluation may be negative

**Blocks:** v2.1-P Mode 2 on Horizen L3
**Description:** HCCE may be immature, USDC bridging unreliable, or x402 verification incompatible.
**Mitigation:** Settlement abstraction (FD-1) ensures fallback to application-layer TEE on Base. Re-evaluate in 6 months.

### Risk 8 — BBS+ threshold issuance meaningless at seed scale

**Blocks:** v2.0 reputation credibility
**Description:** Threshold requires 3+ independent nodes. At seed scale, platform runs all nodes.
**Mitigation:** Acknowledged. Single-issuer credentials still useful for selective disclosure. Real trust distribution when 3+ independent operators run nodes.

### Risk 9 — Supply-demand chicken-and-egg

**Blocks:** Operator revenue viability (Alex's story)
**Description:** Alex's robot earns nothing without buyers posting tasks in his location. Moderate utilization (10+ tasks/day) needed for breakeven within 30 days.
**Mitigation:** Demand heatmap shows unserved areas before operator deploys. Location-based incentives for underserved zones. "Certified compatible" hardware list limits fragmentation.

### Risk 10 — Frontend conversion funnel drop-off

**Blocks:** Growth from v1.5 frontend
**Description:** Anonymous visitors may bounce before authenticating. Every gate (Claude auth, payment) risks drop-off.
**Mitigation:** Progressive disclosure (DD-1): intent before identity. Capture anonymous intent for demand analytics regardless of conversion. Measure funnel at each step.

---

## Demo to Production

### Earth Marketplace (Sarah)

| Component | Demo (now) | Production |
|-----------|------------|------------|
| **Robots** | `mock_fleet.py` (5 simulated) | Real robots via ERC-8004 discovery |
| **Hosting** | `localhost:8000` | Cloud host or `--ngrok` static domain |
| **Stripe** | `sk_test_xxx` | `sk_live_xxx` (real charges) |
| **Card onboarding** | Manual `.env` | Stripe SPTs -- agent-initiated |
| **Operator payouts** | Stub or test transfers | Stripe Connect Express |
| **Persistence** | In-memory / local SQLite | Durable storage |
| **Crypto rail (v1.5)** | Base Sepolia testnet | Base mainnet USDC |
| **On-chain memos** | Commitment hash (Sepolia) | Commitment hash (mainnet) |
| **Frontend** | localhost:3000 | Vercel edge deployment |
| **CI/CD** | GitHub Actions (unit+lint) | Full pipeline with integration tests |

### Private Tasks (Diane)

| Component | Demo (v2.0) | Production |
|-----------|-------------|------------|
| **TEE** | Local simulator | Intel TDX cloud (Azure/GCP confidential VMs) |
| **Encrypted specs** | Test enclave | TEE attestation + HSM-backed keys |
| **Viewer keys** | Test key pairs | Organization-managed, HSM storage |
| **BBS+ credentials** | Single issuer | Threshold issuance across operator nodes |
| **ZK proofs (v2.1-P)** | Succinct testnet | Succinct Prover Network production |

### Lunar Dispatch (Kenji)

| Component | Demo (v2.1-L) | Production |
|-----------|---------------|------------|
| **DTN transport** | Terrestrial testbed (simulated latency) | Lunar Pathfinder / Moonlight relay |
| **Moon-side agents** | Simulated rovers with constraints | RAD750-class C/Rust agents |
| **Coordinator** | Single instance, local | Geographic failover, multi-party oversight |
| **Settlement** | Batched on Base Sepolia | Batched on Base mainnet, 6-hour cycle |
| **Fleet** | 3-5 simulated rovers | 3-10 real lunar rovers at Shackleton rim |

The auction engine, scoring function, state machine, wallet ledger, and MCP tools are shared across all three tracks. Track-specific components (TEE, DTN, BBS+, frontend) are additive modules, not replacements.

---

## How to Read This Document

- **Decision references** (e.g., "per TC-1", "per AD-6") point to `docs/DECISIONS.md`. That file is the single source of truth.
- **Decision ID prefixes:** AD = architectural, TC = technical constraint, PD = product, FD = foundational design (cross-track), PP = privacy-specific, LD = lunar-specific, DD = frontend design decision.
- **User references** point to `docs/USER_PROFILES.md` (13 profiles) and `research/RESEARCH_MISSING_USER_PROFILES.md` (gap analysis).
- **Milestone references** point to `docs/MILESTONES.md`.
- **Track notation:** versions suffixed with `-L` are lunar, `-P` are privacy. Unsuffixed are main track.
- **Parallel tracks** run concurrently and do not block each other unless noted in the Cross-Track Dependencies table.
- **Frontend phases** (Ph0-Ph3) run in parallel with backend development. Ph0-1 ship with v1.5; Ph2-3 ship with v2.0.
- **Platform operations** track runs continuously from v1.5 onward, expanding in scope each version.
