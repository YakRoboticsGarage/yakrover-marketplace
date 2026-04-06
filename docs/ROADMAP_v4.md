# Product Roadmap v4 — Robot Task Auction Marketplace

**Project:** yakrover-auction-explorer
**Owner:** Product
**Last updated:** 2026-04-06 (rev 4.6, v1.1 milestone 5 — real Tumbller live execution)
**Status:** v1.0 built. **v1.1 milestone 5 reached** (273 tests, 35 MCP tools). Real Tumbller moves + reads sensors at waypoints via MCP. Full pipeline end-to-end. Demo-3 at yakrobot.bid/mcp-demo-3.

> All product decisions and technical constraints referenced by ID live in `docs/DECISIONS.md`.
> Feature requirements for the next build: `docs/FEATURE_REQUIREMENTS_v15.md`.
> User journey: `docs/USER_JOURNEY_CONSTRUCTION_v01.md` (Marco).
> Research backing: `research/SYNTHESIS_JTBD_WEDGE_PROPOSAL.md`, `research/RESEARCH_ROBOTS_AND_SENSORS.md`, `research/RESEARCH_WEDGE_INDUSTRY_ANALYSIS.md`.
> Payment/legal research: `research/RESEARCH_CONSTRUCTION_PAYMENT_FLOWS.md`, `research/RESEARCH_PAYMENT_BOND_VERIFICATION.md`, `research/RESEARCH_LEGAL_FRAMEWORK_SURVEY_CONTRACTS.md`.
> Gap analysis: `research/ANALYSIS_AUTONOMOUS_EXECUTION_GAPS.md`. Feedback: `feedback/FEEDBACK_AWARD_CONFIRMATION.md`.

---

## User Map

Every feature on this roadmap exists to serve a named user. If a feature cannot be traced to a persona below, it does not belong.

| Version | Persona | Type | Key Action |
|---------|---------|------|------------|
| **v1.0 (built)** | Sarah — Facilities Manager | Buyer | Warehouse sensor readings via AI assistant |
| | Robot Operator (fleet) | Operator | Registers fleet, configures pricing, receives payouts |
| | Claude (AI Agent) | Agent | Translates intent to structured tasks, runs auctions |
| **v1.5** | Marco — Senior Estimator | Buyer | Pre-bid surveys, progress monitoring via AI assistant |
| | Drone/Robot Operator (regional) | Operator | Bids on construction survey tasks, uploads data |
| | Platform Administrator | Admin | Monitors health, manages payouts |
| **v2.0** | Marco (multi-robot) | Buyer | Compound surveys: aerial + ground + GPR in one job |
| | Alex — Independent Operator | Operator | Onboards robot, earns revenue, sees demand heatmap |
| | Diane — Program Manager | Buyer | Classified inspections with encrypted specs |
| **v2.5** | Mine Surveyor | Buyer | Volumetric stockpile surveys, highwall inspections |
| **v3.0** | Bridge Program Manager | Buyer | Federally mandated bridge inspections |
| | Diane (government contracts) | Buyer | Privacy-compliant infrastructure inspections |
| **v4.0** | Kenji — JAXA Project Coordinator | Buyer | Lunar regolith surveys via DTN to rovers |

---

## Wave 1: Market Validation (Immediate — before v1.5 code work)

Three parallel workstreams to validate demand before building the next version:

### 1. GC Outreach
- Engagement packages for general contractors (see `docs/wave1/`)
- Target: 5-10 GC conversations to validate survey pain points, willingness to use a marketplace, and pricing expectations
- Deliverable: Validated demand signal or pivot insight

### 2. Operator Outreach
- Engagement packages for drone/robot operators (see `docs/wave1/`)
- Target: 5-10 operator conversations to validate supply-side economics, willingness to bid on tasks, and equipment readiness
- Deliverable: Letter-of-intent pipeline or operator onboarding commitments

### 3. MCP Deployment
- Deploy the MCP server as a live tool that prospective users (GCs, operators, agents) can interact with
- Demonstrate the RFP-to-auction flow end-to-end via Claude Desktop or similar MCP client
- Deliverable: Live MCP endpoint at yakrobot.bid with real interaction data

**Gate:** Wave 1 results determine whether v1.5 code work proceeds as planned, pivots scope, or changes the wedge market entirely.

---

## Visual Timeline

```
              2026                                    2027                  2028+
Week  1    8    12   16   20   24   28   32   40   48   52    ...
      |----|----|----|----|----|----|----|----|----|----|-- - -

      ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
      v0.1──v1.0    v1.5         v2.0         v2.5    v3.0         v4.0
      (BUILT)       Crypto Rail  Multi-Robot   Mining  Infra +      Lunar
                    + Constr.    + Operator    Expand  Privacy
                    Task Specs   Dashboard

      ▓▓▓▓▓  built        ░░░░░  in development        · · ·  horizon
```

---

## v1.0 — Auction Engine (BUILT)

Everything built through v1.0 is the shared foundation. Marco, Kenji, and Diane all rely on the same auction core.

### What exists

- Auction core: `Task`, `Bid`, `AuctionResult`, `score_bids()` with four-factor weighted scoring (per AD-6)
- Hard constraint filter, HMAC + ERC-8004 Ed25519 bid signing (per PD-3)
- Failure recovery: robot offline, bad payload, auto-accept timer (per AD-7, PD-6)
- Internal wallet ledger with debit/credit log (per TC-2)
- Stripe wallet onboarding + Connect Express payouts (per TC-2, TC-3)
- Persistent state via SQLite `SyncTaskStore`
- 35 MCP tools: auction lifecycle, RFP processing, bond verification, operator compliance, agreement generation
- Structured error responses, `available_actions`, `next_action` patterns (per AD-13, AD-14, AD-15)
- Standards-aligned task specs: ASPRS accuracy classes, USGS quality levels, EPSG CRS codes, structured deliverables
- 278 passing tests, ~16,500 LOC
- Live demo at yakrobot.bid, yakrobot.bid/mcp-demo (Claude tool_use), yakrobot.bid/yaml (ontology explorer)
- Chatbot worker on Cloudflare, MCP server with Cloudflare Tunnel

---

## v1.0.2 — Tracking & Observability (IN PROGRESS)

| | |
|---|---|
| **Timeline** | 1-2 weeks |
| **Serves** | All personas — buyer tracking, operator progress, admin metrics |
| **Goal** | Event infrastructure + execution progress model. Foundation for buyer/operator/admin dashboards. |

> **Detailed requirements:** `docs/research/ANALYSIS_TRACKING_DASHBOARDS.md`

### Key deliverables

**Event log infrastructure:**
- `events` table in SQLite: event_type, request_id, actor_id, actor_role, data_json, timestamp
- `EventEmitter` class wired into AuctionEngine — all state transitions emit events
- Wallet operations emit payment events
- Queryable via new MCP tools

**Execution progress model:**
- 6 operator-reported soft states: mobilizing → en_route → on_site → capturing → processing → uploading
- `auction_update_progress` MCP tool (operator pushes updates)
- `auction_get_task_feed` MCP tool (query event timeline per task or actor)
- Progress data included in `auction_track_execution` response

**Dashboard surfaces (planned, not this sprint):**
- Buyer dashboard: "Where's my survey?" — task timeline, SLA countdown, project rollup
- Operator dashboard: "What's on my plate?" — task discovery, active jobs, earnings
- Admin console: "How's the platform?" — GMV, SLA rates, operator health, compliance alerts

---

## v1.1 — Live Payment Settlement (MILESTONE REACHED 2026-04-05)

| | |
|---|---|
| **Milestone 2** | Base mainnet USDC payment with real ERC-8004 robot + correct user journey (2026-04-05) |
| **Serves** | Marco (buyer), operators, investors (proof of real settlement) |
| **Goal** | Real-money payment through a real auction. Both Stripe (fiat) and USDC (crypto). |
| **Demo** | https://yakrobot.bid/mcp-demo-2/ |
| **Revert tags** | `v1.1-milestone-payment-e2e` (Sepolia), `v1.1-milestone-base-mainnet` (mainnet + UX) |

> **Detailed plan:** `docs/research/PLAN_PAYMENT_SETTLEMENT_DEMO_v4.md`

### What's built
- **Robot discovery from browser** — direct subgraph query + on-chain `getAgentWallet()` RPC call. No server dependency. Discovers `fleet_provider: yakrover` robots on Base + Sepolia.
- **Tumbller found on Sepolia** — agent #989, wallet `0x99a55d71682807fde9c81e0984aBdd2C7AcCE136`, active, MCP endpoint live
- **Stripe Checkout endpoint** — worker creates destination charges with 12% `application_fee_amount`
- **Payment-after-delivery UX** — auction runs free, payment is the climax (post-critique redesign)
- **Truthful state** — demo shows exactly what's real at every step

### Decisions (resolved 2026-04-02)
- **Stripe:** Production mode (`sk_live_...`). Real cards, real charges.
- **Crypto:** Direct USDC transfer to robot wallet (read from on-chain `getAgentWallet`). No x402 for settlement.
- **Robot discovery:** Subgraph + RPC from browser. `fleet_provider: yakrover` filter.
- **Robot wallet:** Already set on ERC-8004 contract. `getAgentWallet(989)` returns `0x99a5...E136`.
- **Delivery:** IPFS upload via Pinata worker endpoint. Real CID shown to buyer.
- **Chain:** Base for production. Sepolia for current demo (Tumbller registered there).
- **Feedback:** Demo → Cloudflare KV + GitHub issue → research agent processes → improvement proposals.

### What's done (confirmed working 2026-04-05)
- [x] Browser robot discovery (subgraph + getAgentWallet RPC + agentWallet metadata)
- [x] Gasless USDC payment (ERC-2612 permit + relay, platform pays gas)
- [x] Commit-on-hire: buyer signs permit on award, money moves on delivery acceptance
- [x] **End-to-end USDC payment on Base Sepolia** — permit signed, committed, released, USDC transferred
- [x] **End-to-end USDC payment on Base mainnet** — real ERC-8004 robot (FakeRover-Finland-01, agent #38801), real USDC
- [x] Two-phase demo: auction stops after award → buyer commits payment → robot executes → QA → release
- [x] Correct user journey: data payload blurred until payment released
- [x] Resumable payment execution (permit/transfer steps tracked individually, survives partial failures)
- [x] Multi-wallet: Rabby, MetaMask, Coinbase Wallet
- [x] Multi-chain: Base mainnet, Ethereum mainnet, Base Sepolia, Eth Sepolia
- [x] Relay wallet funded (0x4b59...0d9) on all 4 chains
- [x] Worker-safe RPC endpoints (1rpc.io — Base/Eth public RPCs blocked CF Workers)
- [x] Stripe Checkout endpoint with 12% application_fee
- [x] IPFS delivery upload (Pinata via worker)
- [x] Schema-driven delivery QA: task spec includes delivery_schema, robot self-checks, QA validates same schema
- [x] 4-level QA (buyer-configurable: none → basic/schema → standards → PLS)
- [x] Self-contained mock fleet (sensor robots generate schema-compliant data without external simulator)
- [x] Async-safe MCP REST API (blocking LLM calls wrapped in asyncio.to_thread)
- [x] Feedback loop (demo → GitHub issues → research agent)
- [x] Worker deployed with GITHUB_TOKEN + RELAY_PRIVATE_KEY + RELAY wallet funded
- [x] Robot operator onboarding guide published
- [x] CI fully green (lint, mypy 0 errors, 265 tests)
- [x] Repo renamed to yakrover-marketplace
- [x] Stripe Payment Element (inline authorize/capture, no redirect)
- [x] Demo-3 redesigned: light theme, phase breadcrumbs, sidebar feed, payment mode selector
- [x] MCPRobotAdapter: marketplace calls real robot MCP endpoints for bid + execute
- [x] On-chain robot discovery at MCP server startup (subgraph query, mock fleet excluded when real robots available)
- [x] 3 FakeRover-Berlin robots registered on Base mainnet (#38918, #38919, #38921)
- [x] Payment amount from robot's actual bid price (not hardcoded)
- [x] Payment routed to auction winner's on-chain wallet (not hardcoded first robot)
- [x] Real Tumbller live execution: move forward → read sensor → repeat at 3 waypoints (real SHT3x data from Finland)
- [x] Liveness probe with real-robot preference (Tumbller online → FakeRovers excluded)
- [x] Bearer token auth for robot MCP endpoints (FLEET_MCP_TOKEN)
- [x] Waypoint-by-waypoint execution: adapter calls tumbller_move + tumbller_get_temperature_humidity per waypoint

### v1.1 blockers — ALL RESOLVED
- [x] ~~Robot registered on Base or Ethereum mainnet~~ — FakeRover-Finland-01 (#38801) + 3 Berlin rovers (#38918, #38919, #38921) on Base
- [x] ~~8004 team: `robot_submit_bid` + `robot_execute_task` MCP tools~~ — Anuraj delivered (Stages 1-5), merged to main. Marketplace calls them via MCPRobotAdapter.
- [x] ~~End-to-end test: real robot bids → real execution → real sensor data → schema QA → USDC payment~~ — Confirmed 2026-04-06. Berlin robots bid $0.50 via MCP, execute via fakerover simulator, QA PASS, USDC settled on Base mainnet.
- [x] ~~IPFS upload of delivery data from real robot execution~~ — demo-3 uploads via `/api/upload-delivery` after execution, CID shown after payment release
- [x] ~~Unskip fakerover bid tests~~ — rewritten for new bid format (8 tests, 0 skipped, all pass)

### Next phase
- [ ] **Stable tunnel URLs** — Replace random `trycloudflare.com` with named Cloudflare tunnels (`mcp.yakrobot.bid`, `fleet.yakrobot.bid`). See `docs/research/PLAN_REAL_ROBOT_INTEGRATION.md`.
- [ ] **8004scan feedback** — Broadcast auction feedback (rating, comment) to the robot's on-chain profile at https://8004scan.io/agents/base/{agentId}?tab=feedback. Buyers rate the robot after delivery, visible to future buyers.
- [ ] Stripe Connect per robot: operator Stripe Connect ID in ERC-8004 metadata.
- [ ] Production Stripe: switch `sk_test_` → `sk_live_`, operator Connect onboarding.
- [ ] Stripe payment confirmation visible to robot/operator.
- [ ] Stripe webhook for payment status tracking.

### Dropped from earlier plans
- ~~x402 middleware~~ — wrong tool for marketplace settlement (pay-to-access, not escrow)
- ~~Splits.org for demo~~ — direct transfer simpler; Splits for production scale
- ~~Wallet funding before auction~~ — payment is the climax, not the prelude
- ~~Internal wallet ledger for real payments~~ — Stripe/blockchain IS the ledger
- ~~25/75 payment split~~ — simplified to full payment on delivery

---

## v1.2 — Platform Administration (PLANNED)

| | |
|---|---|
| **Timeline** | After v1.1 demo is complete |
| **Serves** | Platform operators (us) |
| **Goal** | Operational runbook, key management, wallet monitoring, service health dashboard. |

> **Research:** R-032 (admin console), R-033 (secret management)

### Current operational inventory
| Category | Items | Management |
|----------|-------|-----------|
| Worker secrets | ANTHROPIC_API_KEY, GITHUB_TOKEN, RELAY_PRIVATE_KEY, PINATA_JWT, STRIPE_SECRET_KEY (pending), STRIPE_WEBHOOK_SECRET (pending) | Cloudflare dashboard / `wrangler secret put` |
| On-chain wallets | Platform (`0xe333...8e5`), Relay (`0x4b59...0d9`) | Manual funding, no balance alerts |
| External services | Stripe, Pinata, Cloudflare Workers, here.now, The Graph subgraph | Separate dashboards, no unified monitoring |
| Scheduled agents | Daily research (9am), Daily docs-sync + code review (7pm) | claude.ai/code/scheduled |
| Domains | yakrobot.bid (here.now + Cloudflare), mcp.yakrobot.bid (tunnel, DNS pending) | Porkbun + here.now |

### What's needed
- [ ] Operational runbook: how to rotate each secret, fund wallets, deploy worker
- [ ] Relay wallet balance monitoring (ETH runs out = payments stop)
- [ ] Service health endpoint aggregation (/api/health on worker, subgraph status, etc.)
- [ ] Key rotation strategy per secret (frequency, procedure, who has access)
- [ ] Production: KMS-backed signing for relay wallet (not env var)
- [ ] Admin dashboard or at minimum a status page

---

## v1.5 — Crypto Rail + Construction Task Specs + Foundation

| | |
|---|---|
| **Timeline** | Weeks 13-16 (4 weeks) |
| **Serves** | Marco, Drone/Robot Operators, Claude, Platform Admin |
| **Goal** | USDC on Base alongside Stripe. Settlement abstraction for all future modes. Construction-specific task extensions. Frontend Phase 0-1. CI/CD. |

> **Detailed feature requirements:** `docs/FEATURE_REQUIREMENTS_v15.md`

### What the user can do that they couldn't before

Marco's assistant posts a construction survey task with structured specs -- accuracy requirements, deliverable formats, weather constraints. A crypto-native operator receives USDC payout on Base. An on-chain commitment hash proves payment linkage without revealing the task. A visitor lands on the site and captures intent before authenticating.

### Key deliverables

**Crypto rail (F-1 through F-4):**
- x402 middleware on `accept_bid()` (per TC-4)
- `RobotTaskEscrow.sol` on Base with settlement abstraction (FD-1) -- 4-mode interface, only Mode 1 implemented
- USDC wallet top-up alongside Stripe credit bundles
- Payment method selection (`"stripe"` | `"usdc"` | `"auto"`)

**Settlement abstraction (F-5):**
- `SettlementInterface` protocol: `settle()`, `verify()`, `batch_settle()`
- Both `StripeSettlement` and `BaseX402Settlement` implement it
- Modes 2-4 are documented stubs that raise `NotImplementedError`

**Privacy-aware foundation (F-6, F-7, F-9):**
- Commitment hash `H(request_id || salt)` in on-chain memos (FD-4)
- Robot wallet addresses hidden from public API (PP-2)
- Task specs encrypted at rest in SQLite (PP-5-pre)

**Construction task spec extensions (NEW):**
- `survey_type` enum: `topographic`, `existing_conditions`, `subsurface_gpr`, `progress_monitoring`, `as_built`
- `accuracy_requirement`: horizontal and vertical tolerance in cm (e.g., 5 cm H / 4 cm V for LiDAR)
- `deliverable_formats`: list of required output formats (`landxml`, `dxf`, `csv`, `geotiff`, `las`, `pdf`)
- `weather_constraints`: max wind speed (mph), precipitation (boolean), visibility minimum (statute miles)
- `survey_area`: GeoJSON polygon or corridor definition (centerline + offset)
- `deadline`: hard deadline for processed deliverable delivery (not just task execution)
- `reference_data`: optional baseline terrain model for progress comparison
- Validation: reject tasks where accuracy requirement exceeds sensor capability

**Payment bond verification (BUILT — real Treasury data):**
- Bond verification against real Treasury Circular 570 data (501 surety companies, downloaded from fiscal.treasury.gov)
- Checks: surety on Circular 570, state licensing, underwriting limit, penal sum extraction, coverage sufficiency
- PDF bond extraction via PyMuPDF
- Fuzzy surety name matching (exact + substring + word overlap)
- Tasks marked **"Payment Bonded"** (public projects) or **"Escrow Funded"** (private projects) -- visible to operators before bidding
- Supports three commitment mechanisms: (a) payment bond upload, (b) ACH-funded milestone escrow via Plaid, (c) prepaid credit bundle
- **Not available (no public API):** real-time bond-is-active check (surety portals are web forms, not REST APIs), Power of Attorney authentication, AM Best ratings ($5K+/yr subscription)
- **Planned:** SAM.gov Exclusions API integration (free, needs API key registration)
- Tested: 5 end-to-end scenarios with realistic bonds, all verified against Circular 570

**Basic insurance and license verification (BUILT — compliance checker):**
- ComplianceChecker stores and verifies 6 document types: FAA Part 107, insurance COI, PLS license, SAM.gov registration, DOT prequalification, DBE certification
- Each document returns VERIFIED / MISSING / EXPIRED / NOT_REQUIRED
- Upload via `auction_upload_compliance_doc` MCP tool
- Verify via `auction_verify_operator_compliance` MCP tool
- PLS gap detection: flags operators without PLS license, recommends PLS-as-a-service
- **Not yet automated:** ACORD 25 PDF parsing (field extraction from COI documents), state licensing board API lookups, FAA Part 107 database verification
- Hard constraint filter: operators below account-level insurance minimums excluded from bidding
- Expiration alerts: yellow at 30 days, red at 7 days (planned)

**ERC-8004 extensions (F-8):**
- Agent card: `min_price`, `accepted_currencies`, `reputation_score`
- NEW: `sensor_capabilities` list (lidar, gpr, rgb, thermal), `coverage_area` GeoJSON, `accuracy_spec`

**Design-only deliverables (F-10, F-11):**
- DTN message schema (`DTN_MESSAGE_SCHEMA.md`)
- BBS+ credential schema (`BBS_CREDENTIAL_SCHEMA.md`)

**Evaluation (F-12):**
- Deploy test escrow on Horizen L3 testnet, evaluate for Mode 2

**Frontend Phase 0-1:**
- Next.js landing page with intent capture
- Claude OAuth integration
- SSE live feed, robot discovery cards

**Development infrastructure:**
- CI/CD: GitHub Actions (unit + ruff + mypy on every push)
- pytest markers: unit / stripe / blockchain / fleet
- Pre-commit hooks for secret detection

### What is NOT included

- No multi-robot compound tasks (v2.0)
- No operator dashboard (v2.0)
- No TEE infrastructure (v2.0)
- No automated dispute resolution
- No cross-chain support (Base only)
- No payment flow in frontend (Phase 2, v2.0)
- No award confirmation flow (v2.0) -- v1.5 uses auto-award
- No auto-generated subcontracts (v2.0)
- No automated ACORD 25 parsing (v2.0) -- v1.5 captures COI fields manually
- No PLS license board API integration (v2.0) -- v1.5 captures license number and expiration only
- No escrow milestone management (v2.5)
- No retainage tracking (v2.5)
- No lien waiver automation (v2.5)

---

## v2.0 — Multi-Robot Workflows + Operator Dashboard + Construction Features

| | |
|---|---|
| **Timeline** | Weeks 17-28 (12 weeks) |
| **Serves** | Marco, Alex, Diane, Fleet Operators |
| **Goal** | Compound tasks across aerial + ground + GPR robots. Operator dashboard. Construction-specific project workflows. Platform privacy Phase 1. |

### What the user can do that they couldn't before

Marco posts one request: "topo + GPR + structure documentation for the SR-89A corridor." The system decomposes it into three subtasks, auctions each to the right robot type, coordinates schedules (drone morning, Spot afternoon), merges deliverables, and delivers a single data package. Marco sees one invoice line.

Alex sees unserved construction survey demand on the heatmap, deploys a Matrice 350 in Tucson, and earns his first $2,200 within a week.

Diane posts an inspection with `privacy: true`. Her task spec is encrypted, matched inside a TEE enclave, and only the winning robot sees details.

### Key deliverables

**Multi-robot workflows (critical for construction):**
- Compound task decomposition: parent task splits into ordered/parallel subtasks
- Subtask chaining: aerial topo output defines GPR scan extents
- Robot-to-robot schedule coordination: airspace deconfliction, sequential access
- Merged deliverable package: all subtask outputs combined into one data delivery
- Upstream PRs: `bid()` on `RobotPlugin`, fleet MCP auction tools

**Construction-specific features:**
- **Project-based task grouping:** All tasks for SR-89A live under one project. Pre-bid, monthly monitoring, and as-built linked to same baseline.
- **Civil 3D export pipeline:** LandXML terrain models, DXF plan overlays, GeoTIFF orthomosaics -- validated for Civil 3D / HeavyBid / B2W import.
- **Progress comparison:** Monthly flights compared against pre-bid baseline. Cut/fill heatmaps, volumetric summary tables, schedule conformance overlays.
- **Recurring task automation:** Monthly progress monitoring auto-scheduled. Agent posts task, collects bids, dispatches flight, delivers report -- no Marco input needed.
- **Weather-aware scheduling:** NOAA API integration. Tasks auto-schedule into flyable windows. Weather holds preserve partial data and auto-resume.

**Award confirmation flow (NEW — from feedback + legal research):**
- Recommended winner presented to buyer with qualification summary (insurance, licensing, track record)
- Buyer confirms award or rejects and advances to next-ranked bidder
- Rejection reasons tracked: conflict of interest, insufficient insurance, DBE shortfall, prohibited vendor, prior bad experience, PLS not licensed in state
- Automated pre-award checks: COI verification, PLS state validation, Part 107 status, DBE/MBE certification
- State machine transition: `AUCTION_COMPLETE` -> `RECOMMENDED` -> `AWARD_CONFIRMED` (or `AWARD_REJECTED` -> re-recommend) -> `AGREEMENT_PENDING` -> `AWARDED`

**Auto-generated subcontract (NEW — from legal framework research):**
- Template based on ConsensusDocs 751 (short form) with survey-specific exhibits
- Auto-populated from task spec + winning bid: scope, price, deliverables, accuracy, schedule, weather constraints
- Standard terms: data ownership (processed deliverables to client, raw data retained by operator), limitation of liability (1x task fee), mutual indemnification (each party's percentage of negligence), dispute resolution (negotiation -> mediation -> arbitration per ConsensusDocs model)
- Digital execution via ESIGN/UETA-compliant e-signature
- Both parties must sign before work is authorized

**COI parsing and verification (v2.0 — requires external service):**
- Automated parsing of ACORD 25 certificates: producer, insurer names + NAIC numbers, policy numbers, dates, coverage types, limits, additional insured (ADDL INSD), waiver of subrogation (SUBR WVD)
- Verification: policy current, limits meet task-specific minimums, additional insured endorsement present
- Integration path: myCOI or Jones for real-time certificate tracking
- CGL professional services exclusion flagging (E&O required separately for survey work)
- **Dependency:** myCOI/Jones partnership or PDF parsing library (no free API exists for COI verification)

**PLS license verification (v2.0 — requires state board access):**
- Validation against state licensing board databases (starting with AZ, NV, NM, MI)
- Firm Certificate of Authorization check (required in Michigan per MCL 339.2007)
- Multi-state license tracking for operators covering multiple geographies
- Continuing education compliance monitoring (30 hrs/biennium in Michigan)
- **Dependency:** State licensing boards publish searchable databases but not REST APIs. MI LARA has online search at michigan.gov. Scraping or partnership required.

**External service dependencies (v2.0+):**

| Service | Status | Blocker | Path Forward |
|---------|--------|---------|-------------|
| Treasury Circular 570 | LIVE (Excel download) | None | Refresh weekly from fiscal.treasury.gov |
| SAM.gov Exclusions API | Planned | API key registration | Free — register at api.data.gov |
| Surety portal (bond active?) | Not available | No public REST API | Partnership agreements with top 5 sureties, or accept manual verification |
| AM Best ratings | Not available | Paid subscription ($5K+/yr) | Defer until revenue supports cost |
| ACORD 25 COI parsing | Not available | No free API | myCOI/Jones partnership ($500-2K/mo) or build with PDF extraction |
| State PLS board lookup | Not available | No REST API | Web scraping per state or manual verification |
| DocuSign e-seal (PLS stamp) | Not available | API subscription | DocuSign or DocuSeal (open source) |
| FAA Part 107 database | Not available | No public API | Manual verification via FAADroneZone |

**DBE tracking (NEW — required for federally-funded projects):**
- DBE/MBE/WBE certification capture and verification
- MDOT MERS Form 2124A integration for DBE payment tracking
- DBE goal compliance monitoring at project level
- Reporting for GC's federal funding compliance

**Operator dashboard (Alex's story):**
- Robot registration, pricing config, coverage area definition
- Task history, revenue per robot, payout history
- Demand heatmap: unserved construction survey tasks by location
- Equipment health monitoring, maintenance reminders
- Starter kit recommendations by use case

**Platform privacy Phase 1 (Diane):**
- TEE-based confidential compute for encrypted task matching (PP-4, PP-5)
- Viewer keys for audit (PP-7)
- BBS+ credential schema operational (FD-2)

**Frontend Phase 2-3:**
- Payment flow (Stripe Checkout + WalletConnect)
- Live auction view with SSE
- Operator dashboard UI
- Agent discovery (`.well-known/mcp.json`)

### Success criteria

- 3-subtask compound survey (aerial + GPR + structure doc) completes end-to-end
- Marco's project view shows linked pre-bid and monitoring tasks with baseline comparison
- Weather hold pauses, preserves data, and resumes without manual intervention
- Alex onboards a drone and earns revenue within 1 hour
- Private task completes with encrypted spec; only winning robot sees details
- Award confirmation flow: Marco reviews recommended winner, checks qualifications, confirms or rejects
- Auto-generated subcontract executes digitally before work starts
- COI parsed from ACORD 25 with limits verified against task minimums
- PLS license validated against state board for at least one state (AZ)
- DBE tracking operational for MDOT-funded project tasks

---

## v2.5 — Mining and Quarrying Expansion

| | |
|---|---|
| **Timeline** | Weeks 29-36 (8 weeks) |
| **Serves** | Mine Surveyor, existing Operators |
| **Goal** | Same robots, same sensors, new buyer persona. Open-pit volumetric surveys, blast assessment, highwall inspection. |

### Why mining is next

Mining scored second (3.95/5) in the wedge analysis. The strongest lunar transfer path after construction. Same LiDAR/photogrammetry stack, same terrain navigation, same dust tolerance. The buyer (mine surveyor) has $5-20K budget per volumetric survey and recurring quarterly need. Many construction drone operators already serve mining clients -- supply side overlaps.

### Key deliverables

**Construction payment maturation (NEW — from payment flow research):**
- **Escrow milestone management:** Rolling escrow model -- GC funds each milestone 5 days before it's due. Milestone triggers: work verification (point cloud QA) -> invoice auto-generated -> GC has 5 business days to approve or dispute -> funds released. Supports both full escrow (GC deposits total upfront) and bond-backed (no cash escrowed, operator relies on bond claim).
- **Retainage tracking:** 5-10% retainage withheld per progress payment, tracked per project. Retainage release upon substantial completion / final QA period (30-60 days). Michigan public project support: retainage reduction to 0% after 50% completion.
- **Lien waiver exchange:** Auto-generated conditional and unconditional lien waivers at each payment milestone. Tracks waiver status per operator per project. Integration with GC's pay application workflow (AIA G702/G703 format).
- **Prompt payment compliance:** MDOT 10-day payment tracking (special provision). Michigan public project 1.5%/month penalty calculation for late payments. Dashboard alerts for approaching deadlines.

**Mining task spec extensions:**
- `survey_type` adds `volumetric_stockpile`, `blast_pattern`, `highwall_stability`, `haul_road_condition`
- **Mining deliverable formats:** volumetric change reports, MSHA-formatted safety reports, fragmentation analysis
- **Dust-hardened operation profiles:** extended sensor cleaning intervals, reduced-visibility flight patterns
- **Inventory reconciliation:** survey volumes correlated against truck-scale tonnage
- **Mining buyer onboarding:** tailored setup flow for mine surveyors and safety officers

### Success criteria

- Volumetric stockpile survey completes with accurate volume calculation (within 2% of manual survey)
- Same drone operator serves both construction and mining tasks from one dashboard
- Mine surveyor receives MSHA-formatted deliverables without manual reformatting
- Escrow milestone payment releases correctly after QA verification on a multi-milestone task
- Retainage tracked and released at project closeout
- Lien waivers auto-generated and exchanged at each payment milestone
- MDOT prompt payment compliance tracked with alerts for a live project

---

## v3.0 — Infrastructure Monitoring + Privacy

| | |
|---|---|
| **Timeline** | Weeks 37-48 (12 weeks) |
| **Serves** | Bridge Program Manager, Diane (government), Pipeline Operators |
| **Goal** | Federally mandated bridge inspections. Privacy features for government contracts. Specialized robot form factors. |

### Why infrastructure is third

Infrastructure scored third (3.65/5) with the strongest regulatory tailwind -- federal bridge inspection mandates (23 CFR 650) create non-discretionary demand for 600K+ bridges biennially. But it requires specialized form factors (bridge crawlers, confined-space drones) that take longer to aggregate on the supply side. By v3.0, the platform has proven multi-robot workflows and operator network density.

### Key deliverables

**Infrastructure inspection:**
- Bridge inspection task specs: NBI element-level condition ratings, under-deck access requirements
- Pipeline and power line corridor survey support
- Specialized robot form factors: Flyability ELIOS 3 (confined space), Gecko TOKA (wall-climbing UT)
- Federal reporting templates: NBI, SNBI, PHMSA compliance outputs

**Privacy for government contracts (Diane's story, Phase 2):**
- Delegated ZK proofs for task verification (SP1 proving circuit, PP-11)
- Horizen L3 Mode 2 settlement if v1.5 evaluation positive (PP-19 through PP-23)
- BBS+ anonymous reputation at operational scale
- Privacy Pools on Base if 0xbow has deployed (PP-16)
- Government contract compliance: encrypted specs, audit trails, viewer keys for oversight

**Convergence features:**
- BBS+ credentials unified across all verticals
- Cross-fleet competition where robot populations exceed ~15
- Recurring task scheduling and data aggregation API

### Success criteria

- Bridge inspection task completes with NBI-formatted deliverables
- Private infrastructure inspection end-to-end with ZK proof verification
- If Horizen L3 positive: Mode 2 settlement (deposit Base -> bridge -> escrow -> release)
- Privacy overhead < 15 seconds on standard inspection task

---

## v4.0 — Lunar Contracts

| | |
|---|---|
| **Timeline** | 2028+ |
| **Serves** | Kenji (JAXA/NASA Project Coordinator) |
| **Goal** | Everything built on Earth transfers to lunar surface operations. NASA/commercial ISRU site prep, Artemis base construction support. |

### What transfers

| Marco's Job (Earth) | Kenji's Job (Moon) | What Transfers Directly |
|---|---|---|
| Topographic survey of highway corridor | Terrain mapping at Shackleton Crater rim | LiDAR pipeline, DTM generation, volumetrics |
| Existing condition documentation | Boulder field and crater characterization | 3D photogrammetry, anomaly detection |
| Subsurface GPR assessment | Regolith depth and ice profiling for ISRU | GPR data processing, subsurface modeling |
| Progress monitoring (monthly cut/fill) | Tracking autonomous excavation of landing pads | Temporal baseline comparison, volume change |
| As-built verification | Habitat foundation confirmation before pressurization | Design-vs-actual deviation, BIM compliance |

### Key deliverables

- Centralized Earth-side coordinator with DTN/Bundle Protocol (RFC 9171) for Moon-Earth messaging (LD-1, LD-2)
- Thin Moon-side agent: minimal C/Rust state machine for bid generation and task execution (LD-4)
- Lunar task spec extensions: `thermal_window`, `power_budget_wh`, `illumination_required`, `comm_window_required` (LD-5)
- Lunar scoring factors: price 30%, speed 20%, confidence 15%, track record 10%, power margin 15%, dust exposure 10% (LD-6)
- Batched transparent settlement via Mode 3 (LD-8)
- Checkpoint-and-resume for lunar night transitions (LD-11)
- Lunar night queue: tasks with TTL auto-execute at dawn (LD-10)

### Success criteria

- End-to-end: task dispatched from Earth, executed by simulated rover via DTN, results verified, settlement batched on Base
- Bid window handles 3-8 second RTT without protocol failure
- All protocol messages are idempotent DTN bundles tolerating replay and reordering

---

## Foundational Design Decisions

These decisions are made now (v1.5) and affect all future versions. They are architectural commitments, not features.

### FD-1: Settlement Abstraction Layer

**Decision:** Design the settlement interface to support four modes from v1.5, implementing only Mode 1.

| Mode | Timing | Privacy | Chain | Version |
|------|--------|---------|-------|---------|
| 1. Immediate transparent | Real-time | Public | Base / x402 | v1.5 |
| 2. Immediate private | Real-time | Shielded | Horizen L3 (if eval positive) | v3.0 |
| 3. Batched transparent | Async / DTN | Public | Base | v4.0 |
| 4. Batched private | Async / DTN | Shielded | TBD | Future |

**Why now:** Both lunar (batched) and privacy (shielded) tracks depend on this. Building without it creates rewrite debt.

### FD-3: Chain Decision — Base + Horizen L3

**Decision:** Base is the primary settlement chain. Horizen L3 on Base is the leading Mode 2 candidate (evaluated in v1.5, implemented in v3.0 if positive). Aleo is monitor-only.

**Rationale:** EU AMLR Article 79 eliminates fully private chains for EU market. Horizen L3 is live on Base mainnet (March 2026), TEE-based, EVM-compatible, same USDC liquidity, selective disclosure.

### FD-4: On-Chain Memo Policy

**Decision:** Memos carry only amount, escrow address, nonce, and `H(request_id || salt)`. Plaintext mapping in platform database only.

**Replaces:** AD-3's raw `request_id`. Audit capability preserved via commitment hash.

---

## Key Risks

### Risk 1 — Survey operator supply in target geographies

**Affects:** v1.5-v2.0 (Marco's story)
**Description:** Marco needs operators in Phoenix, Sedona, Albuquerque. If no drone operators are registered near his project sites, the marketplace has zero value (Journey B).
**Mitigation:** Target the top 20 drone-as-a-service operators in Arizona/Nevada/New Mexico for launch. 67% of major US construction firms already use drones -- the supply exists, it just needs aggregation. Demand heatmap (v2.0) shows operators where unserved tasks concentrate.

### Risk 2 — Deliverable quality and format accuracy

**Affects:** v1.5+ (all construction tasks)
**Description:** Marco needs LandXML that imports cleanly into Civil 3D. If the processing pipeline produces files with coordinate system errors, wrong units, or missing metadata, the data is worthless regardless of how fast or cheap it was.
**Mitigation:** Validate deliverables against format specs before delivery. Civil 3D import test suite. Accuracy comparison against known control points. Operator reputation penalizes format errors.

### Risk 3 — Weather disruption frequency

**Affects:** v1.5+ (aerial surveys)
**Description:** In Arizona, monsoon season (July-September) and spring wind events can ground drones for days. If weather holds are too frequent, turnaround advantage over human crews erodes.
**Mitigation:** Weather-aware scheduling (v2.0) uses 72-hour forecasts to target flyable windows. Partial data preservation means weather holds extend but don't restart tasks. Ground robots (Spot) are less weather-sensitive than drones.

### Risk 4 — Stripe minimum charge constrains pricing

**Affects:** All fiat versions
**Description:** Per TC-1, no task below $0.50 on Stripe. Construction survey tasks are $1,000+ so this does not constrain the wedge market. But it limits expansion to smaller task types.
**Mitigation:** Prepaid wallet model (TC-2). USDC rail has no minimum.

### Risk 5 — EU AMLR Article 79 interpretation

**Affects:** v3.0 privacy features
**Description:** Article 79 prohibits CASPs from handling privacy-preserving digital assets by July 2027. Interpretation uncertain.
**Mitigation:** Platform-mediated TEE model designed for most conservative interpretation. Legal opinion before v3.0 architecture finalized.

### Risk 6 — Horizen L3 evaluation may be negative

**Affects:** v3.0 Mode 2 settlement
**Description:** HCCE may be immature, USDC bridging unreliable, or x402 verification incompatible.
**Mitigation:** Settlement abstraction (FD-1) ensures fallback to application-layer TEE on Base with zero code changes to escrow contract.

### Risk 7 — Multi-robot coordination complexity

**Affects:** v2.0 compound tasks
**Description:** Coordinating drone + Spot + GPR on the same corridor in one day requires airspace deconfliction, schedule sequencing, and data merge. Failure of one subtask may block others.
**Mitigation:** Parallel subtask design where possible (drone morning, Spot afternoon). Partial delivery model -- completed subtasks deliver even if others fail. Re-auction failed subtasks independently.

### Risk 8 — Regulatory compliance for payment facilitation

**Affects:** v1.5+ (bond verification, escrow, milestone payments)
**Description:** The marketplace facilitates payments between GCs and robot operators. Depending on implementation, this could trigger money transmitter licensing requirements at the state level. Escrow management may require trust account registration. Bond verification creates potential liability if the marketplace misrepresents a bond's validity and an operator relies on that representation.
**Mitigation:** Phase 1 (v1.5) uses prepaid credit bundles (already covered by Stripe's money transmitter licenses). Bond verification is informational only -- the marketplace displays bond status but does not guarantee payment. Escrow (v2.5) requires legal review of money transmitter obligations per state. Consult FinCEN guidance on marketplace payment facilitation before v2.5 architecture is finalized.

### Risk 9 — Insurance verification liability

**Affects:** v2.0+ (COI parsing, automated qualification checks)
**Description:** If the marketplace verifies an operator's insurance and the verification is wrong -- expired policy, insufficient limits, missing endorsement -- the marketplace may bear liability when a claim arises and the operator is underinsured. COI parsing is imperfect: ACORD 25 forms vary in layout, and a parsed "current" policy may have been cancelled since the certificate was issued.
**Mitigation:** Insurance verification is a snapshot, not a guarantee. Terms of service must disclaim marketplace liability for insurance accuracy. Integrate with real-time certificate tracking services (myCOI, Jones) in v2.0 to reduce staleness risk. Display verification date prominently. Require operators to update COIs when policies renew. Consider E&O coverage for the marketplace itself.

### Risk 10 — Lunar communication relay availability

**Affects:** v4.0
**Description:** Lunar Pathfinder (late 2026) provides intermittent coverage. Multi-hour blackouts are the default.
**Mitigation:** Idempotent DTN bundles. Batched settlement tolerates hours-to-days delay. Conservative availability assumptions (< 50% uptime).

---

## Demo to Production

### Construction Marketplace (Marco)

| Component | Demo (v1.5) | Production |
|-----------|-------------|------------|
| **Robots** | `mock_fleet.py` (simulated) | Real drones + Spot via ERC-8004 discovery |
| **Survey data** | Synthetic point clouds | Real LiDAR, GPR, photogrammetry data |
| **Processing** | Mock deliverable generation | Full point cloud pipeline, format validation |
| **Hosting** | `localhost:8000` | Cloud host with public URL |
| **Payment (bond)** | Mock bond upload + verification | Real surety portal cross-reference |
| **Payment (escrow)** | Plaid sandbox + test ACH | Plaid production + real ACH |
| **Stripe** | `sk_test_xxx` | `sk_live_xxx` (real charges) |
| **Crypto rail** | Base Sepolia testnet | Base mainnet USDC |
| **On-chain memos** | Commitment hash (Sepolia) | Commitment hash (mainnet) |
| **Insurance/COI** | Mock ACORD 25 parsing | myCOI/Jones real-time integration |
| **Licensing** | Mock PLS/Part 107 lookup | State board API integration |
| **Agreements** | Mock subcontract generation | DocuSign/Adobe Sign e-signature |
| **Frontend** | localhost:3000 | Vercel edge deployment |
| **Weather** | Mock NOAA responses | Live NOAA Aviation Weather API |
| **Operators** | Simulated bids | Regional drone service companies |

### Private Infrastructure (Diane, v3.0)

| Component | Demo | Production |
|-----------|------|------------|
| **TEE** | Local simulator | Intel TDX cloud (Azure/GCP confidential VMs) |
| **Encrypted specs** | Test enclave | TEE attestation + HSM-backed keys |
| **ZK proofs** | Succinct testnet | Succinct Prover Network production |
| **Horizen L3** | Testnet escrow | Mainnet (if eval positive) |

### Lunar Dispatch (Kenji, v4.0)

| Component | Demo | Production |
|-----------|------|------------|
| **DTN transport** | Terrestrial testbed (simulated latency) | Lunar Pathfinder / Moonlight relay |
| **Moon-side agents** | Simulated rovers | RAD750-class C/Rust agents on lunar rovers |
| **Settlement** | Batched on Base Sepolia | Batched on Base mainnet, 6-hour cycle |

The auction engine, scoring function, state machine, wallet ledger, and MCP tools are shared across all tracks. Construction-specific, privacy, and lunar components are additive modules -- not replacements.

---

## How to Read This Document

- **Decision references** (e.g., "per TC-1", "per AD-6") point to `docs/DECISIONS.md`.
- **Decision ID prefixes:** AD = architectural, TC = technical constraint, PD = product, FD = foundational design, PP = privacy, LD = lunar.
- **Feature references** (F-1 through F-12) point to `docs/FEATURE_REQUIREMENTS_v15.md`.
- **User journey:** `docs/USER_JOURNEY_CONSTRUCTION_v01.md` details Marco's full experience.
- **Research:** `research/SYNTHESIS_JTBD_WEDGE_PROPOSAL.md` is the analytical foundation for the construction wedge choice.

---

## Implementation Status — Real vs. Mocked (as of 2026-03-30)

### Production-Ready (Real Data, Verified Logic)

| Component | What's Real | Source |
|-----------|------------|--------|
| Bond verification | 501 surety companies from Treasury Circular 570 | fiscal.treasury.gov Excel |
| State licensing check | Surety licensed-in-state from Circular 570 columns | fiscal.treasury.gov |
| Underwriting limit check | Per-surety dollar limits from Circular 570 | fiscal.treasury.gov |
| Scoring algorithm | 4-factor weighted (price 40%, SLA 25%, confidence 20%, reputation 15%) | NCHRP/FHWA procurement standards |
| Task categories | 12 categories (5 sensor + 7 construction) | MDOT/AASHTO classifications |
| Bid signing | HMAC-SHA256 + Ed25519 cryptographic verification | Standard crypto |
| Anti-indemnity statutes | MI (MCL 691.991), OH, AZ, TX | State law |
| ConsensusDocs 750 baseline | 12-dimension terms comparison | Industry standard |
| Equipment specs | DJI M350 RTK, Leica BLK ARC, GSSI, Skydio X10, Trimble | Manufacturer specs |
| Survey accuracy specs | 2-5 cm horizontal, 1-5 cm vertical | MDOT Chapter 9 |
| Budget ranges | $1.5K-$120K by survey type | Industry pricing |

### Simulated (Plausible, Not Yet Connected to Real Systems)

| Component | What's Simulated | Path to Real |
|-----------|-----------------|-------------|
| RFP parsing | Keyword matching, not semantic NLP | Call Claude API with skill prompt |
| Mock fleet | 7 fictional MI operators with real equipment specs | Replace with real operator database |
| Operator profiles | Fabricated names, license numbers, reputation | Real operator onboarding |
| Bid pricing | Deterministic % of budget (70-90%) | Real operators set own prices |
| Task execution | Returns mock deliverable metadata | Real operator uploads real files |
| Agreement generation | Hardcoded template, not licensed ConsensusDocs | License ConsensusDocs 750 ($) |
| Terms comparison | Keyword spotting for clause detection | Claude API for semantic analysis |
| Wallet/ledger | In-memory balance tracking | Stripe + SQLite persistence |
| Reputation scores | Fabricated completion rates (94-99.7%) | Computed from real task history |

### Mocked (Placeholder — Blocks Real Deployment)

| Component | What's Mocked | Dependency |
|-----------|--------------|-----------|
| Compliance verification | Marks VERIFIED on upload, no API validation | FAA, state PLS boards, insurance carriers |
| Payment settlement | In-memory wallet, no real money | Stripe Connect + Plaid |
| Escrow | MockEscrowAccount (in-memory) | Stripe escrow or smart contract |
| Operator payout | MockOperatorPayout (returns fake IDs) | Stripe Connect Express |
| Mediation | MockMediationService (instant resolution) | AAA Construction Rules integration |
| File delivery | String file paths, no actual files | S3/blob storage + upload pipeline |
| PLS e-seal | Not implemented | DocuSign or DocuSeal API |

### External Services — No Public API Available

| Service | Why No API | Workaround | Cost |
|---------|-----------|-----------|------|
| Surety bond active status | Each surety has web forms, not REST APIs | Partnership agreements with top 5 sureties | Business development |
| AM Best ratings | Paid data subscription | Defer until revenue covers cost | $5K+/yr |
| ACORD 25 COI parsing | No free extraction API | myCOI or Jones partnership | $500-2K/mo |
| State PLS board lookup | State websites, no REST API | Per-state web scraping | Engineering time |
| FAA Part 107 database | FAADroneZone has no public API | Manual verification or scraping | Engineering time |
| DocuSign PLS e-seal | API subscription required | DocuSeal (open source alternative) | $0-500/mo |
| ConsensusDocs templates | Licensed content, not freely distributable | License agreement with ConsensusDocs | ~$500/yr |

### External Services — Free API Available (Not Yet Integrated)

| Service | API | Status | What It Does |
|---------|-----|--------|-------------|
| SAM.gov Exclusions | api.sam.gov/entity-information/v4/exclusions | Planned | Check if operator/surety is debarred |
| SAM.gov Entity | api.sam.gov/entity-information/v4/entities | Planned | Verify federal registration |
| NOAA Weather | api.weather.gov | Planned | Flight weather constraints |
| FAA LAANC | via Aloft/AirHub SDK | Planned | Controlled airspace authorization |
| Geocoding | Nominatim or Google Maps API | Planned | RFP location to coordinates |

### MCP Tool Count: 27 (as of 2026-03-30)

| Phase | Tools | Category |
|-------|-------|----------|
| v1.0 | 15 | Core auction lifecycle (post, bid, accept, execute, confirm, cancel, status, schema, wallet, operator) |
| Phase 2 | 3 | RFP processing (process_rfp, validate_specs, site_recon) |
| Phase 3 | 2 | Buyer review (review_bids, award_with_confirmation) |
| Phase 4 | 4 | Compliance (verify_bond, verify_compliance, upload_doc, compare_terms) |
| Phase 5 | 3 | Agreements + project mgmt (generate_agreement, track_execution, list_tasks) |

### Test Coverage

| Suite | Count | Status |
|-------|-------|--------|
| Unit tests | 180 passing | 4 pre-existing fakerover failures (require running fleet server) |
| Scenario 1: Dan's Excavating | 16 steps, 0 gaps | Multi-task highway RFP, full lifecycle |
| Scenario 2: C.A. Hull | 13 steps, 0 gaps | Bridge inspection, compliance-heavy |
| Scenario 3: Kamminga | 11 steps, 0 gaps | Progress monitoring, budget tier |
| Scenario 4: Ajax Paving | 14 steps, 0 gaps | Dual-task, PLS-as-a-service gap |
| Scenario 5: Anlaan | 16 steps, 0 gaps | I-94 tunnel + topo, most complex |
