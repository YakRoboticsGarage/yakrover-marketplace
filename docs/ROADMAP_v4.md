# Product Roadmap v4 — Robot Task Auction Marketplace

**Project:** yakrover-auction-explorer
**Owner:** Product
**Last updated:** 2026-03-28 (rev 4.1, payment bonds + award confirmation + legal framework)
**Status:** v1.0 built (151 tests, 15 MCP tools). v1.5 next. This roadmap is built around construction site surveying as the wedge market.

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
- 15 MCP tools including `auction_quick_hire`
- Structured error responses, `available_actions`, `next_action` patterns (per AD-13, AD-14, AD-15)
- 151 passing tests, ~11,400 LOC

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

**Payment bond verification (NEW — from payment flow research):**
- Bond verification API: GC uploads payment bond certificate (PDF), marketplace extracts bond number, surety name, principal, penal sum, project
- Cross-reference against surety verification portals (Travelers, Liberty Mutual, CNA, Zurich, Hartford)
- Treasury Dept Circular 570 check for surety standing on federal bonds
- Tasks marked **"Payment Bonded"** (public projects) or **"Escrow Funded"** (private projects) -- visible to operators before bidding
- Supports three commitment mechanisms: (a) payment bond upload, (b) ACH-funded milestone escrow via Plaid, (c) prepaid credit bundle
- Replaces credit card as default payment for construction tasks over $5K

**Basic insurance and license verification (NEW — from legal framework research):**
- COI intake: operator uploads ACORD 25 certificate of insurance
- Basic field extraction: coverage types, limits, policy expiration, additional insured status
- PLS license number capture and expiration tracking per state
- FAA Part 107 certificate number capture
- Hard constraint filter: operators below account-level insurance minimums are excluded from bidding
- Expiration alerts: yellow at 30 days, red at 7 days

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

**COI parsing and verification (NEW — ACORD 25 automated):**
- Automated parsing of ACORD 25 certificates: producer, insurer names + NAIC numbers, policy numbers, dates, coverage types, limits, additional insured (ADDL INSD), waiver of subrogation (SUBR WVD)
- Verification: policy current, limits meet task-specific minimums, additional insured endorsement present
- Integration path: myCOI or Jones for real-time certificate tracking
- CGL professional services exclusion flagging (E&O required separately for survey work)

**PLS license verification (NEW):**
- Validation against state licensing board databases (starting with AZ, NV, NM, MI)
- Firm Certificate of Authorization check (required in Michigan per MCL 339.2007)
- Multi-state license tracking for operators covering multiple geographies
- Continuing education compliance monitoring (30 hrs/biennium in Michigan)

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
