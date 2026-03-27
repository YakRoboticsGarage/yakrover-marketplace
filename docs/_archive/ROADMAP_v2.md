# Product Roadmap v2 — Robot Task Auction Marketplace

**Project:** yakrover-auction-explorer
**Owner:** Product
**Last updated:** 2026-03-26 (rev 2, post privacy-chain analysis)
**Status:** v1.0 built (151 tests, 15 MCP tools). v1.5 next. This is the unified roadmap incorporating marketplace, lunar, and privacy tracks.

> All product decisions and technical constraints referenced by ID live in `docs/DECISIONS.md`.
> Version boundaries defined in `docs/SCOPE.md`. Milestone details in `docs/MILESTONES.md`.
> Feature requirements for the next build: `docs/FEATURE_REQUIREMENTS_v15.md`.
> Research backing: `research/RESEARCH_SYNTHESIS_LUNAR.md`, `research/RESEARCH_SYNTHESIS_PRIVATE.md`, `research/RESEARCH_CRITIQUE.md`, `research/RESEARCH_PRIVACY_CHAINS.md`, `research/FOUNDATIONAL_TECH_ANALYSIS.md`.

---

## Visual Timeline

```
              2026                              2027                    2028+
Week  1    8    12   16   20   24   28   32   36   40   44   52    ...
      |----|----|----|----|----|----|----|----|----|----|----|----|-- - -

MAIN  ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
      v0.1──v1.0    v1.5         v2.0                   v3.0
      (BUILT)       Crypto Rail  Multi-Robot +           Convergence
                    + privacy-   Platform Privacy
                    aware design

LUNAR                                  ░░░░░░░░░░░░░░░░░░░░░░░░░░ · · ·
                                       v2.1-L             v2.2-L
                                       DTN-Tolerant       Multi-Project
                                       Auction            Coordination

PRIVACY                          ░░░░░░░░░░░░░░░░░░░░░░░░░░
                                 v2.0 (TEE)    v2.1-P
                                 Platform      Delegated ZK
                                 Privacy       Proofs

      ▓▓▓▓▓  build        ░░░░░  stabilize / field test        · · ·  horizon

      ──── Main track      ──── Lunar track (parallel)     ──── Privacy track
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

1. **Settlement abstraction layer** (see Foundational Design Decisions, FD-1). The `RobotTaskEscrow.sol` contract and payment middleware must support a settlement interface that can route to four future modes: immediate transparent, immediate private, batched transparent, batched private. Only mode 1 (immediate transparent on Base) is implemented in v1.5. The interface is designed now.

2. **Cryptographic commitment replaces `request_id` in on-chain memos** (PP-1). The current v1.0 design embeds `request_id` in on-chain memos (per AD-3). This creates a permanent public link between payments and tasks. Replace with a cryptographic commitment hash: `H(request_id || salt)` on-chain, plaintext mapping in the platform database. Audit capability preserved; privacy leak eliminated.

3. **Robot wallet addresses not exposed in public API** (PP-2). Use platform-internal identifiers in the API layer; translate to on-chain addresses only at settlement. Preserves the option for rotating/shielded addresses later.

---

## v1.5 — Crypto Rail (with Privacy-Aware Foundation)

> **Detailed feature requirements:** See `docs/FEATURE_REQUIREMENTS_v15.md` for the complete feature list with acceptance criteria, decision IDs, and test plan.

| | |
|---|---|
| **Timeline** | Weeks 13-16 (4 additional weeks) |
| **Milestone** | Milestone 5 (Crypto Rail + On-Chain Audit + Foundation) |
| **Goal** | USDC on Base accepted alongside Stripe. Settlement abstraction designed for future privacy and lunar modes. Privacy-aware foundation ships to prevent architectural debt. Horizen L3 on Base evaluated as Mode 2 candidate. |

### What the user can do that they couldn't before

Sarah's crypto-native colleague pays for a robot task with USDC on Base. Payment clears in seconds via x402. Fiat buyers continue using Stripe. An on-chain commitment hash proves the transaction is linked to a task without revealing which one. Task specs are encrypted at rest in the platform database — no plaintext accumulation.

### Key deliverables

**Crypto rail (features F-1 through F-4):**
- x402 middleware on `accept_bid()` endpoint (per TC-4)
- `RobotTaskEscrow.sol` deployed on Base with **settlement interface abstraction** (FD-1) — operator-controlled release, 4-mode interface with only Mode 1 (immediate transparent) implemented
- USDC wallet top-up on Base alongside Stripe credit bundles
- Payment method selection at task posting (`"stripe"` | `"usdc"` | `"auto"`)
- ERC-8004 agent card extended with `min_price`, `accepted_currencies`, `reputation` fields

**Privacy-aware foundation (features F-5 through F-9):**
- **FD-1 / F-5:** Settlement abstraction interface — `SettlementInterface` protocol with `settle()`, `verify()`, `batch_settle()`. Both `StripeSettlement` and `BaseX402Settlement` implement it. Modes 2-4 are documented stubs.
- **FD-4 / F-6:** Cryptographic commitment hash `H(request_id || salt)` in on-chain memos (replaces raw `request_id` per AD-3). Plaintext mapping in platform database.
- **PP-2 / F-7:** Platform-internal robot identifiers in API; wallet addresses hidden from public endpoints, resolved only at settlement.
- **PP-5-pre / F-9:** Task specs encrypted at rest (AES-256-GCM) in SQLite. Transparent to MCP tools. Preparatory for v2.0 TEE-based encrypted matching.

**Design-only deliverables (features F-10 through F-11):**
- **LD-2-pre / F-10:** DTN message schema documented in `DTN_MESSAGE_SCHEMA.md` — message types, idempotency model, size estimates for LunaNet constraints. No code implementation.
- **FD-2-pre / F-11:** BBS+ credential schema documented in `BBS_CREDENTIAL_SCHEMA.md` — fields, update protocols (Earth + lunar), selective disclosure profiles. No code implementation.

**Evaluation (feature F-12):**
- **FD-5 / F-12:** Deploy test escrow on Horizen L3 testnet. Evaluate USDC bridging, HCCE (Confidential Compute Environment), and x402 facilitator compatibility. Findings in `HORIZEN_L3_EVALUATION.md`. Go/no-go for Mode 2 settlement.

### Success criteria

- End-to-end task completed with real USDC (under $1 on Base Sepolia)
- On-chain transaction includes commitment hash; platform database maps hash to `request_id`
- No raw `request_id` in any on-chain data (memo, event logs, contract storage)
- Fiat path still works — no regression. All 151 existing tests pass.
- Buyer can choose payment method at task posting time
- Robot wallet addresses never appear in any MCP tool response
- Settlement abstraction interface reviewed and approved for lunar/privacy extensibility
- Task specs encrypted in SQLite (verifiable by reading raw database)
- DTN message schema and BBS+ credential schema design docs reviewed
- Horizen L3 evaluation report completed with go/no-go recommendation

### What is NOT included

- No cross-chain support (Base only; Horizen L3 is evaluation, not production)
- No automated escrow dispute resolution — operator-controlled release only
- No staking or slashing mechanics
- No TEE infrastructure or encrypted matching (v2.0)
- No BBS+ credential issuance code (v2.0)
- No DTN transport code (v2.1-L)
- No ZKsync Prividium (wrong model — permissioned enterprise, not open marketplace)
- No Aleo integration (no identified non-EU market; monitor only per FD-3)

---

## v2.0 — Multi-Robot Workflows + Platform Privacy

| | |
|---|---|
| **Timeline** | Weeks 17-28 (12 weeks) |
| **Milestone** | Milestone 6 (Upstream Contribution) + Privacy Phase 1 |
| **Goal** | Compound tasks across multiple robots. TEE-based platform privacy for buyers who need confidential task specs. BBS+ credential design finalized for Earth + lunar use. |

### What the user can do that they couldn't before

Sarah posts a compound task: "Inspect Bay 3 with thermal camera, then send a ground rover for a close-up of any hotspot." The system decomposes it, auctions each step, and chains the results.

Diane posts the same kind of task with `privacy: true`. Her task spec is encrypted, matched inside a TEE enclave, and only the winning robot receives the full details. Her CFO can audit via a viewer key. External observers see nothing.

### Key deliverables

**Multi-robot (all users):**
- Compound task decomposition: parent task splits into ordered sub-tasks
- Sub-task chaining: output of step N feeds into the spec for step N+1
- Robot-to-robot handoff protocol
- Upstream PRs: `bid()` on `RobotPlugin`, fleet MCP auction tools, x402 middleware (opt-in via `AUCTION_ENABLED=true`)
- Updated agent card schema with pricing and reputation fields

**Platform privacy (Diane's story, Phase 1):**
- TEE-based confidential compute (Intel TDX) for task matching and scoring (PP-4)
- Encrypted task specs: encrypted at rest, decrypted only inside TEE enclaves (PP-5)
- Public capability vectors for robot matching — generalized capability classes to limit information leakage (PP-6)
- Viewer keys: enterprise buyers get a key pair for internal audit; CFO sees metadata, buyer sees full detail (PP-7)
- Platform escrow key in HSM for lawful regulatory access (PP-8)
- TEE attestation verification before every enclave session; graceful degradation on failure (PP-9)

**Reputation (shared infrastructure):**
- BBS+ credential schema designed for Earth + lunar (FD-2): task count, success rate, avg completion time, capability attestations, environmental survival history (lunar)
- Threshold BBS+ issuance across 3+ platform nodes (meaningful only when 3+ independent operators exist; at seed scale, platform is the trusted issuer — this is acknowledged) (PP-10)
- Selective disclosure: robots prove aggregate stats without revealing individual task history
- Credential update protocol supporting both low-latency (Earth) and high-latency (DTN) reissuance

### Success criteria

- 2-step compound task completes end-to-end with different robots for each step
- Upstream PRs merged into yakrover-8004-mcp
- Private task completes with encrypted spec; only winning robot sees full details
- TEE attestation failure triggers user choice: retry, downgrade to standard, or cancel
- Viewer key decrypts task metadata for CFO audit
- BBS+ credential schema reviewed and approved for cross-environment use
- Privacy overhead < 15 seconds on a standard sensor reading task

### What is NOT included

- No full ZK proofs for task verification — TEE-backed proofs only
- No Privacy Pools integration (not yet on Base)
- No Aleo settlement rail
- No DTN protocol — lunar track starts in v2.1-L
- No robot-to-robot sub-contracting
- No reputation slashing

---

## v2.1-L — Lunar Phase 0: DTN-Tolerant Auction

| | |
|---|---|
| **Timeline** | Weeks 29-36 (8 weeks, parallel to main track) |
| **Milestone** | Lunar Milestone L-1 |
| **Goal** | A centralized Earth-side coordinator dispatches tasks to lunar rovers via DTN. One operator, their own rovers, validating the protocol end-to-end. Not a marketplace — a dispatch system. |
| **Tracks** | Parallel to main track. Does not block v2.0 or v2.1-P. |

### What the user can do that they couldn't before

Kenji, a project coordinator in Tsukuba, asks his AI assistant for a regolith density survey at the lunar south pole. The assistant posts the task to the Earth-side coordinator, which transmits it as a DTN bundle to rovers at Shackleton rim. Three rovers evaluate locally and bid. The coordinator scores, assigns, and the rover executes autonomously. Kenji gets his density map in about 4 minutes. Settlement is batched and posted on-chain every 6 hours.

### Key deliverables

- Centralized Earth-side coordinator with geographic failover (LD-1)
- DTN/Bundle Protocol (RFC 9171) integration for all Moon-Earth protocol messages (LD-2)
- Deadline-based bid window model: publish RFQ via DTN, collect bids for configurable window (30-120s), score after window closes (LD-3)
- Thin Moon-side agent: minimal C/Rust state machine (~100 KB binary) for bid generation, task acceptance, and structured completion proofs (LD-4)
- Lunar task spec extensions: `thermal_window`, `power_budget_wh`, `max_duration_hours`, `illumination_required`, `comm_window_required`, `safety_zone`, `checkpoint_intervals`, `failure_recovery_mode` (LD-5)
- Lunar scoring factors: price (30%), speed (20%), confidence (15%), track record (10%), power margin (15%), dust exposure (10%) — hard constraints on thermal window and comm coverage (LD-6)
- Optimistic verification: robot submits structured completion proof (GPS, timestamps, data hashes); 24-hour dispute window (LD-7)
- Batched transparent settlement via the v1.5 settlement abstraction (mode 3: batched transparent on Base) (LD-8)
- Pessimistic self-locking: rover marks itself unavailable upon task acceptance (LD-9)
- Lunar night queue: tasks with TTL auto-execute when rovers return to service after lunar dawn (LD-10)
- Checkpoint-and-resume failure recovery for long-duration tasks and approaching lunar night (LD-11)

### Success criteria

- End-to-end task dispatched from Earth, executed by a simulated lunar rover via DTN, results verified, settlement batched on Base
- Bid window model handles 3-8 second RTT without protocol failure
- Checkpoint-and-resume: partially completed task produces pro-rated payment and a resumable checkpoint
- Lunar night queue: task stored with TTL and auto-posted when rover availability resumes
- All protocol messages are idempotent DTN bundles that tolerate replay and reordering
- Settlement batches post correctly on-chain during simulated communication windows

### What is NOT included

- No competitive marketplace — single-operator dispatch only (per research: 3-10 rovers is too few for auction dynamics)
- No cross-robot attestation (requires independent operators + incentive mechanism, see LD-12)
- No lunar sidechain or on-Moon consensus
- No privacy for lunar tasks (deferred to v2.2-L / v3.0 convergence)
- No real lunar hardware — DTN-over-terrestrial-testbed only
- No multi-project scheduling — single project queue

---

## v2.1-P — Privacy Phase 2: Delegated ZK Proofs + Horizen L3 Settlement

| | |
|---|---|
| **Timeline** | Weeks 29-36 (8 weeks, parallel to lunar track) |
| **Milestone** | Privacy Milestone P-2 |
| **Goal** | Upgrade from TEE-only verification to delegated ZK proofs for task completion. Implement Mode 2 (immediate private) settlement on Horizen L3 on Base if evaluation (F-12) was positive. Add BBS+ anonymous reputation at operational scale. Begin Privacy Pools integration if available on Base. |
| **Tracks** | Parallel to v2.1-L. Depends on v2.0 TEE infrastructure. Depends on v1.5 Horizen L3 evaluation (FD-5). |

### What the user can do that they couldn't before

Diane's task completion is now verified by a zero-knowledge proof — not just TEE attestation. A delegated prover (SP1/Succinct on Phala Cloud TEE) generates a proof that the robot's results satisfy the task spec without seeing the spec or results in plaintext. The proof is stored alongside the encrypted task record. Diane's robot proves its reputation via BBS+ credential: "847 tasks, 99.1% success rate" — without revealing which tasks, for whom, or what they involved.

If Horizen L3 evaluation was positive: private tasks settle on Horizen L3 (Mode 2). The escrow contract deploys on Horizen L3 (same Solidity, same EVM). USDC bridges from Base L2 to Horizen L3. x402 facilitator gets selective disclosure access to payment receipts via Horizen's TEE-based privacy.

### Key deliverables

**ZK proof infrastructure:**
- SP1 proving circuit for sensor verification: "returned data satisfies task spec" (PP-11)
- Delegated proving via Succinct Prover Network on Phala Cloud TEE — encrypted witness, private inputs never leave enclave (PP-12)
- Benchmarked proof time for standard sensor task (target: < 5 seconds; must be measured, not extrapolated) (PP-13)

**Horizen L3 Mode 2 settlement (conditional on FD-5 evaluation):**
- `RobotTaskEscrow.sol` deployed on Horizen L3 mainnet (same contract, different chain) (PP-19)
- USDC bridge integration: Base L2 → Horizen L3 automated deposit/withdrawal (PP-20)
- x402 facilitator adapted for Horizen selective disclosure — facilitator verifies payment receipt via TEE attestation, not public on-chain lookup (PP-21)
- Mode 2 implementation in settlement abstraction: `HorizenL3Settlement` implements `SettlementInterface` (PP-22)
- Confidential task matching via Horizen HCCE — task specs decrypted and scored inside Horizen's TEE, replacing or augmenting platform-operated TEE from v2.0 (PP-23)

**Reputation:**
- BBS+ anonymous reputation operational: threshold issuance, selective disclosure, credential updates after each task (PP-14)
- Semaphore-based anonymous group membership: "prove you are a registered robot without revealing which one" (PP-15)

**Settlement privacy:**
- Privacy Pools integration on Base **if 0xbow has deployed to Base** — association-set proofs for settlement privacy (PP-16). If not available, defer to v3.0.
- TEE compromise fallback plan: degrade to generalized capability classes, notify affected parties, rotate enclave keys (PP-17)
- On-chain settlement carries only amount, escrow contract, nonce, and commitment hash — no linkable metadata (PP-18)

### Success criteria

- ZK proof generated for a standard sensor task in < 5 seconds (benchmarked, not extrapolated)
- Proof verifies on-chain (or off-chain with on-chain commitment) that task spec was satisfied
- Robot proves reputation via BBS+ without revealing individual task history
- TEE attestation failure triggers graceful degradation, not system failure
- Privacy overhead < 15 seconds total (TEE + proof + verification) on standard task
- If Horizen L3 evaluation positive: Mode 2 settlement completes end-to-end (deposit USDC on Base → bridge to Horizen L3 → escrow → release → bridge back)
- If Privacy Pools available: settlement transaction includes association-set proof

### What is NOT included

- No Aleo integration (no identified non-EU market; monitoring target only per FD-3)
- No ZKsync Prividium (wrong model — permissioned enterprise, not open marketplace; see `research/RESEARCH_PRIVACY_CHAINS.md`)
- No FHE scoring (4-5 orders of magnitude too slow; deferred indefinitely)
- No MPC sealed-bid auctions (collusion-trivial with 2-3 robots; revisit at 10+ independent robots)
- No multi-party private workflows (encrypted chained task outputs; deferred to v4.0+)

---

## v2.2-L — Lunar Phase 1: Multi-Project Coordination

| | |
|---|---|
| **Timeline** | Weeks 37-44 (8 weeks) |
| **Milestone** | Lunar Milestone L-2 |
| **Goal** | 2-3 operators share the coordinator. Tasks assigned by priority and capability. Cross-rover attestation for high-value tasks. Lunar night queue management across projects. |

### What the user can do that they couldn't before

Kenji's project competes for rover time with two other Artemis-era construction projects at Shackleton rim. The coordinator assigns tasks by priority tier (contractual SLAs), capability match, and rover availability. When a high-value foundation survey completes, a second rover independently confirms the results. During lunar night transitions, the coordinator manages graceful task handoff and checkpoint queuing across all projects.

### Key deliverables

- Priority-based scheduling across 2-3 projects with configurable SLA tiers (LD-13)
- Cross-robot attestation for high-value tasks: independent operator required, verification bounty from task fee (LD-14)
- Lunar night transition management: automated task checkpointing across the fleet as the terminator approaches (LD-15)
- Multi-project queue with advance booking across lunar days (LD-16)
- Coordinator governance: auditable scheduling logs, open-source scheduling algorithm, multi-party oversight API (LD-17)
- Sensitivity-aware economic model: pessimistic (6 lunar days, 4 hrs/day), realistic (12 days, 6 hrs/day), optimistic (24 days, 8 hrs/day) scenarios integrated into pricing (LD-18)

### Success criteria

- 2 projects with different priority tiers schedule tasks on a shared rover fleet without conflict
- Cross-robot attestation completes within one DTN round-trip of task completion
- Lunar night transition: all active tasks checkpoint cleanly, no stuck escrow, all resumed on next lunar day
- Coordinator scheduling decisions are auditable by all participating operators

### What is NOT included

- No competitive auction dynamics (robot populations still < 15; dispatch model continues)
- No full decentralization — coordinator remains centralized with governance guarantees
- No privacy for lunar tasks (convergence in v3.0)
- No real cislunar DTN testing (terrestrial testbed continues)

---

## v3.0 — Convergence

| | |
|---|---|
| **Timeline** | Weeks 45-52+ |
| **Milestone** | Unified platform release |
| **Goal** | All three tracks merge: private task execution works on Earth and Moon. Multi-robot workflows support confidential chained tasks. Lunar operators can protect competitive intelligence. Cross-fleet competition begins where robot populations support it. |

### What the user can do that they couldn't before

Kenji posts a multi-step site assessment at Shackleton rim. The task is decomposed, dispatched to rovers from two operators, and the results are confidential — Selene Robotics cannot see what LunaOps surveyed, and vice versa. Settlement is batched, private (if Privacy Pools on Base is available), and verifiable. On Earth, Diane runs a compound private inspection across three corridors with different robots, each step's encrypted output feeding the next, all inside the TEE boundary.

### Key deliverables

- Private lunar tasks: TEE-based confidential compute on the Earth-side coordinator protects task metadata (location, type, pricing) from competing operators
- Batched private settlement (mode 4 of the settlement abstraction) — if Privacy Pools on Base is available
- BBS+ credentials unified across Earth and lunar: same schema, DTN-tolerant update protocol, credential staleness model for intermittent connectivity
- Cross-fleet competition on Earth: robots from different operators compete for tasks, scored on BBS+ reputation
- Encrypted chained task outputs for multi-robot private workflows (TEE-boundary, not full ZK)
- Competitive marketplace dynamics where robot populations exceed ~15 (Earth first, lunar when population warrants)

### Success criteria

- Private compound task completes end-to-end with 2+ robots from different operators
- Lunar task metadata invisible to non-participating operators
- BBS+ credential from a lunar rover verifies on Earth-side scorer without custom protocol
- Settlement abstraction supports all four modes in production

### What is NOT included

- No full ZK for chained workflows (TEE-mediated privacy only)
- No lunar sidechain
- No Aleo integration (still monitoring; no non-EU market identified)

---

## Future (Beyond v3.0)

These items are explicitly deferred. They will be informed by real usage data, regulatory developments, and robot population growth.

| Item | Description | Depends on | Track |
|------|-------------|------------|-------|
| **Fully decentralized lunar marketplace** | On-chain auction when rover populations reach 30+. Requires relay constellation maturity (ESA Moonlight, NASA LCRNS). | v2.2-L + robot population growth | Lunar |
| **Aleo private settlement rail** | For non-EU markets where full cryptographic privacy is legally viable. Add Aleo + USDCx as optional settlement mode. Application layer remains chain-agnostic. | Identified non-EU market + Aleo ecosystem maturity | Privacy |
| **Privacy Pools on Base** | If 0xbow deploys on Base, integrate association-set proofs for compliant settlement privacy. Proves funds are not sanctioned while shielding transaction details. | 0xbow Base deployment | Privacy |
| **Aztec evaluation** | Re-evaluate when transactions are live and USDC bridge exists. Strongest long-term cryptographic privacy but Noir language barrier and EU regulatory risk remain. | Aztec transactions live + USDC bridge + EU AMLR clarity | Privacy |
| **Fhenix CoFHE on Base** | FHE coprocessor for encrypted on-chain computation. Could enable encrypted scoring without TEE trust. Currently 4-5 orders of magnitude too slow. | FHE performance breakthrough + Fhenix Base deployment | Privacy |
| **FHE encrypted scoring** | Score bids on encrypted data without TEE trust. Currently 4-5 orders of magnitude too slow. | FHE performance breakthrough | Privacy |
| **MPC sealed-bid auctions** | Cryptographically sealed bids when fleet size reaches 10+ independent robots. Sub-100ms for 100 bidders demonstrated. | Fleet diversity growth | Privacy |
| **Dark Factory** | Fully autonomous facilities. Robots monitor, maintain, and report without human prompting. Daily digests replace individual requests. | v3.0 (all tracks converged) | Main |
| **Cislunar DTN testing** | Test DTN protocols on actual Earth-Moon relay links (Lunar Pathfinder, Moonlight). | Relay infrastructure availability | Lunar |
| **Dispute resolution** | Arbitrator mechanism for contested deliveries. Deferred per PD-7: premature without real failure data. | v1.0+ real payment history | Main |
| **Operator staking** | Bond required to bid; slashed on no-show. | Reputation system + v1.5 crypto rail | Main |
| **Multi-party private workflows** | Encrypted output of step N feeds step N+1 without leaving TEE boundary. Full ZK for chained tasks. | v3.0 TEE workflows | Privacy |

---

## Cross-Track Dependencies

| Feature | Track | Blocks / Enables | In Track |
|---------|-------|------------------|----------|
| Settlement abstraction (FD-1) | Main v1.5 | **Enables** batched settlement | Lunar v2.1-L |
| Settlement abstraction (FD-1) | Main v1.5 | **Enables** private settlement modes | Privacy v2.1-P |
| Commitment hash in memos (FD-4) | Main v1.5 | **Enables** unlinkable on-chain payments | Privacy v2.0+ |
| Encrypted task specs at rest (PP-5-pre) | Main v1.5 | **Preparatory for** TEE encrypted matching | Privacy v2.0 |
| Horizen L3 evaluation (FD-5) | Main v1.5 | **Go/no-go for** Mode 2 settlement | Privacy v2.1-P |
| DTN message schema (LD-2-pre) | Main v1.5 | **Design dependency for** DTN transport | Lunar v2.1-L |
| BBS+ credential schema (FD-2-pre) | Main v1.5 | **Design dependency for** reputation | Privacy v2.0, Lunar v2.1-L |
| TEE infrastructure (PP-4) | Privacy v2.0 | **Enables** confidential lunar coordinator | Lunar v3.0 |
| BBS+ credential issuance (FD-2) | Privacy v2.0 | **Required by** lunar reputation scoring | Lunar v2.1-L |
| BBS+ DTN-tolerant update protocol | Privacy v2.0 | **Required by** lunar credential freshness | Lunar v2.2-L |
| Multi-robot workflows | Main v2.0 | **Required by** lunar multi-rover tasks | Lunar v2.2-L |
| Multi-robot workflows | Main v2.0 | **Required by** private compound tasks | Privacy v3.0 |
| Lunar scoring factors (LD-6) | Lunar v2.1-L | **Informs** BBS+ lunar credential fields | Privacy v2.0 (schema design) |
| Horizen L3 Mode 2 settlement (PP-19-23) | Privacy v2.1-P | **Enables** private settlement without platform TEE | Privacy v3.0 |
| Privacy Pools on Base | Privacy v2.1-P | **Enables** batched private settlement | Lunar v3.0 |
| Cross-robot attestation (LD-14) | Lunar v2.2-L | **Requires** independent operators | Lunar (operator ecosystem) |
| Competitive marketplace dynamics | Main v3.0 | **Requires** robot population > 15 | External (fleet growth) |

---

## Foundational Design Decisions

These decisions are made now (v1.5 timeframe) and affect all future tracks. They are not features — they are architectural commitments.

### FD-1: Settlement Abstraction Layer

**Decision:** Design the settlement interface to support four modes from v1.5, implementing only mode 1.

| Mode | Timing | Privacy | Chain | Version |
|------|--------|---------|-------|---------|
| 1. Immediate transparent | Real-time | Public | Base / x402 | v1.5 (implemented) |
| 2. Immediate private | Real-time | Shielded | Base + Privacy Pools or future chain | v2.1-P (if Privacy Pools on Base) |
| 3. Batched transparent | Async / DTN windows | Public | Base | v2.1-L (implemented) |
| 4. Batched private | Async / DTN windows | Shielded | Base + Privacy Pools or future chain | v3.0 |

**Interface contract:** The escrow contract and payment middleware accept a `SettlementMode` enum. The application layer calls `settle(task_id, mode)` and the settlement layer handles routing. Mode-specific logic (batching, privacy proofs, DTN bundling) is encapsulated behind this interface. Base-specific assumptions (EIP-3009, x402 facilitator calls) are isolated to the mode 1 implementation, not baked into the escrow contract.

**Why now:** Both the lunar track (needs batched settlement) and the privacy track (needs private settlement) depend on this abstraction. Building mode 1 without the abstraction creates rewrite debt at v2.1.

### FD-2: Unified BBS+ Credential Schema

**Decision:** Design a single credential schema for robot reputation across Earth and lunar environments.

**Schema fields:**
- `task_count` — total completed tasks
- `success_rate` — percentage of tasks completed without failure
- `avg_completion_time` — mean task duration
- `capability_attestations` — list of verified sensor/actuator capabilities
- `environmental_survival_history` (lunar only) — lunar day/night cycles survived, dust exposure rating
- `operator_id` — issuing operator (for cross-operator verification)

**Update protocol:**
- **Earth (low-latency):** Credential reissued by threshold issuers within seconds of task completion. Robot presents fresh credential on next bid.
- **Lunar (DTN-tolerant):** Credential reissued on Earth, relayed via DTN. Stale credentials accepted with a staleness discount in scoring (configurable, default: 5% discount per missed update window). Rovers carry their most recent credential locally.

**Why now:** Designing two separate reputation systems (one for Earth, one for lunar) and merging them later is more expensive than designing one schema that handles both environments.

### FD-3: Chain Decision — Base Ecosystem, with Horizen L3 for Privacy

**Decision:** Base is the primary settlement chain for all versions through v2.0+. For private settlement (Mode 2), **Horizen L3 on Base** is the leading candidate — evaluated in v1.5 (FD-5), implemented in v2.1-P if evaluation is positive. Aleo is a monitoring target only.

**Rationale (updated with privacy chain research — see `research/RESEARCH_PRIVACY_CHAINS.md`):**
- EU AMLR Article 79 bans CASPs from handling privacy-preserving digital assets by July 2027. Finland (seed market) is an early enforcer. This eliminates fully private chains (Aztec, Aleo) for the EU market.
- **ZKsync Prividium** is production-ready ($112M TVL, Deutsche Bank) but is permissioned enterprise — wrong model for an open marketplace. Each Prividium is a private appchain; the operator sees everything. Also focused on tokenized bank deposits, not USDC commerce.
- **Aztec** is pre-transaction on mainnet (Ignition chain live Nov 2025, empty blocks). Requires Noir (not Solidity). Too early and too different.
- **Horizen L3 on Base** is the best fit: live on Base mainnet (March 2026), TEE-based compliant privacy, fully EVM-compatible (same Solidity), inherits Base's $4.1B USDC liquidity, designed for selective disclosure. Being an L3 within the Base ecosystem means minimal bridging friction.
- **Privacy is an application-layer concern, not a chain-layer concern** — the useful privacy features (encrypted specs, confidential scoring, viewer keys) work on any chain. Horizen L3 simplifies Mode 2 by moving confidential compute to the chain's TEE rather than operating our own.
- The settlement abstraction (FD-1) preserves full optionality. Horizen L3, Aleo, or future Privacy Pools on Base can be added as settlement modes without rewriting escrow logic.

**Chains NOT selected:**
| Chain | Reason |
|-------|--------|
| ZKsync Prividium | Permissioned enterprise; wrong model for open marketplace; no USDC |
| Aztec | Pre-transaction; Noir not Solidity; too early |
| Polygon Miden | Testnet only; Miden Assembly not Solidity |
| Fhenix CoFHE | Interesting but very early; Base support not live |
| Aleo | Strong tech but no EU market; monitor only until non-EU deployment identified |

### FD-5: Horizen L3 Evaluation (NEW)

**Decision:** Evaluate Horizen L3 on Base in v1.5 as the Mode 2 (immediate private) settlement target. Deploy test escrow, test USDC bridging, evaluate HCCE, test x402 compatibility. Go/no-go for v2.1-P.

**Rationale:**
- Horizen L3 launched on Base mainnet March 2026
- Same EVM (OP Stack) — our Solidity escrow deploys unchanged
- Same USDC liquidity (one bridge hop from Base L2)
- TEE-based confidential compute (same trust model as our v2.0 plan)
- Selective disclosure satisfies EU AMLR requirements
- x402 facilitator can verify via Horizen's selective disclosure (most compatible privacy model)

**If evaluation is negative** (HCCE immature, bridge unreliable, x402 incompatible): Mode 2 falls back to application-layer TEE on Base (platform-operated), which is the v2.0 architecture. The settlement abstraction ensures this fallback requires zero code changes to the escrow contract.

### FD-4: On-Chain Memo Policy

**Decision:** On-chain transaction memos carry only: amount, escrow contract address, nonce, and a cryptographic commitment `H(request_id || salt)`. The plaintext `request_id` mapping is stored in the platform database only.

**Replaces:** AD-3's original specification of embedding raw `request_id` in on-chain memos. The audit benefit of AD-3 is preserved (the commitment hash proves linkage) while eliminating a permanent public privacy leak.

---

## Dependencies and Risks

### Risk 1 — EU AMLR Article 79 interpretation uncertainty

**Blocks:** v2.0 privacy features, v2.1-P Privacy Pools integration
**Tracks:** Privacy, Lunar (ESA member state operators face same regulation)
**Description:** Article 79 prohibits CASPs from handling privacy-preserving digital assets by July 2027. Whether this covers privacy-preserving *mechanisms* (shielded USDC transfers) or only privacy-native *tokens* (Monero, Zcash) depends on EBA implementing acts not yet finalized. Finland is an early enforcer.
**Mitigation:** Obtain legal opinion before v2.0 architecture is finalized. The platform-mediated privacy model (TEE-based, platform retains compliance data) is designed to satisfy the most conservative interpretation. If Article 79 is interpreted broadly, Privacy Pools integration (PP-16) may not be viable in the EU.

### Risk 2 — TEE trust and compromise

**Blocks:** v2.0 platform privacy, v3.0 lunar privacy
**Tracks:** Privacy, Lunar
**Description:** All platform privacy depends on TEE (Intel TDX) integrity. SGX side-channel attacks are well-documented. A TEE compromise exposes all encrypted task specs processed in the compromised enclave.
**Mitigation:** TEE attestation verified before every session (PP-9). Fallback on attestation failure: degrade to generalized capability classes with reduced matching efficiency, notify affected parties, rotate enclave keys (PP-17). Long-term: ZK proofs (v2.1-P) reduce TEE dependency for verification.

### Risk 3 — Lunar communication relay availability

**Blocks:** v2.1-L, v2.2-L
**Track:** Lunar
**Description:** Continuous Earth-Moon communication requires orbital relay infrastructure only now deploying. Lunar Pathfinder (late 2026) provides intermittent southern hemisphere coverage. ESA Moonlight full ops not until 2030. Multi-hour blackouts are the default.
**Mitigation:** All protocol messages designed as idempotent DTN bundles. System handles multi-hour blackouts gracefully. Phase 0 targets a single relay provider with conservative availability assumptions (< 50% uptime). Batched settlement tolerates hours-to-days confirmation delay.

### Risk 4 — Lunar rover population too small for marketplace dynamics

**Blocks:** Competitive marketplace features
**Track:** Lunar
**Description:** Through 2028, surface mobile robot populations at any single site will be 3-10 units from 2-3 operators. Most CLPS landings deploy fixed payloads, not mobile rovers. Competitive auction dynamics require 15-30+ robots. The "30 robotic landings/year" figure (secondary sources) does not translate to 30 mobile task-capable robots.
**Mitigation:** Phase 0 and Phase 1 are dispatch systems, not marketplaces. Competitive bidding deferred to Phase 2 (2030+). The dispatch model provides value at any fleet size by optimizing utilization.

### Risk 5 — Stripe minimum charge ($0.50) constrains task pricing

**Blocks:** v1.0 and all fiat payment versions
**Track:** Main
**Description:** Per TC-1, no task can be priced below $0.50 due to Stripe's minimum. Many Earth sensor tasks price at $0.20-$0.40.
**Mitigation:** Prepaid wallet model (per TC-2) — buyers purchase credit bundles and individual tasks debit the internal ledger.

### Risk 6 — SP1 proof time for robot tasks is unvalidated

**Blocks:** v2.1-P proof time targets
**Track:** Privacy
**Description:** The "1-5 second" proof time for simple sensor verification circuits is extrapolated from Ethereum block benchmarks, not measured. Proof generation has fixed overhead that does not scale linearly with circuit complexity.
**Mitigation:** Build a minimal SP1 circuit for sensor range verification and benchmark actual proving time on Succinct Prover Network before committing to v2.1-P timeline. Task added to v2.0 deliverables.

### Risk 7 — Horizen L3 evaluation may be negative

**Blocks:** v2.1-P Mode 2 settlement on Horizen L3
**Track:** Privacy
**Description:** Horizen L3 on Base launched March 2026. HCCE (Confidential Compute Environment) may be immature, USDC bridging from Base L2 may be unreliable, or x402 facilitator verification via selective disclosure may not work as expected. If FD-5 evaluation is negative, Mode 2 falls back to application-layer TEE on Base.
**Mitigation:** The settlement abstraction (FD-1) ensures Mode 2 has a fallback path. Application-layer TEE on Base (platform-operated, v2.0 architecture) achieves the same privacy goals with more infrastructure to operate. No code changes needed — only the `SettlementInterface` implementation differs. Re-evaluate Horizen L3 in 6 months if initial evaluation is negative.

### Risk 8 — BBS+ threshold issuance meaningless at seed scale

**Blocks:** v2.0 reputation credibility
**Track:** Privacy
**Description:** Threshold BBS+ issuance requires 3+ independent nodes. At seed scale, the platform operator runs all nodes, providing no meaningful trust distribution.
**Mitigation:** Acknowledged. At seed scale, the platform is the trusted issuer. The threshold protocol is implemented but trust distribution is real only when 3+ independent operators run issuer nodes. The system degrades gracefully — single-issuer BBS+ credentials are still useful for selective disclosure even without threshold trust.

---

## Demo to Production

v1.0 is built. The path to production differs by track:

### Earth Marketplace (Sarah)

| Component | Demo (now) | Production |
|-----------|------------|------------|
| **Robots** | `mock_fleet.py` (5 simulated) | Real robots via ERC-8004 on-chain discovery (`discovery_bridge.py`) |
| **Hosting** | `localhost:8000` | Cloud host with public URL or `--ngrok` static domain |
| **Stripe** | `sk_test_xxx` (test mode) | `sk_live_xxx` (real charges and payouts) |
| **Card onboarding** | Manual `.env` setup | Stripe Shared Payment Tokens (SPTs) — agent-initiated |
| **Operator payouts** | Stub or test transfers | Stripe Connect Express — hosted KYB onboarding |
| **Persistence** | In-memory or local SQLite | `AUCTION_DB_PATH` on durable storage |
| **Crypto rail (v1.5)** | Base Sepolia testnet | Base mainnet USDC |
| **On-chain memos** | Raw `request_id` | Commitment hash `H(request_id \|\| salt)` |

### Private Tasks (Diane)

| Component | Demo (v2.0) | Production |
|-----------|-------------|------------|
| **TEE infrastructure** | Local TEE simulator | Intel TDX cloud instances (Azure/GCP confidential VMs) |
| **Encrypted task specs** | Encrypted in test enclave | TEE attestation verified per session; HSM-backed keys |
| **Viewer keys** | Test key pairs | Organization-managed key pairs with HSM storage |
| **BBS+ credentials** | Platform-issued (single issuer) | Threshold issuance across independent operator nodes |
| **ZK proofs (v2.1-P)** | Succinct testnet prover | Succinct Prover Network production |

### Lunar Dispatch (Kenji)

| Component | Demo (v2.1-L) | Production |
|-----------|---------------|------------|
| **DTN transport** | Terrestrial DTN testbed (simulated latency) | Lunar Pathfinder / Moonlight relay |
| **Moon-side agents** | Simulated rovers with artificial constraints | RAD750-class processors running minimal C/Rust agents |
| **Earth-side coordinator** | Single instance, local | Geographic failover, auditable logs, multi-party oversight |
| **Settlement** | Batched on Base Sepolia | Batched on Base mainnet, 6-hour cycle |
| **Rover fleet** | 3-5 simulated rovers | 3-10 real lunar rovers at Shackleton rim |

The auction engine, scoring function, state machine, wallet ledger, and MCP tools are shared across all three tracks. Track-specific components (TEE, DTN, BBS+) are additive modules, not replacements.

---

## How to Read This Document

- **Decision references** (e.g., "per TC-1", "per AD-6") point to `docs/DECISIONS.md`. That file is the single source of truth for product and technical decisions.
- **New decision IDs** introduced in this roadmap:
  - **FD-X** — Foundational Design decisions affecting all tracks
  - **PP-X** — Privacy-specific decisions and deliverables
  - **LD-X** — Lunar-specific decisions and deliverables
- **Milestone references** point to `docs/MILESTONES.md` for detailed deliverables and exit criteria.
- **Scope boundaries** are defined in `docs/SCOPE.md`.
- **User journeys** by track: `USER_JOURNEY_MARKETPLACE_v01.md` (Sarah), `USER_JOURNEY_LUNAR_v01.md` (Kenji), `USER_JOURNEY_PRIVATE_v01.md` (Diane).
- **Research backing**: `research/RESEARCH_SYNTHESIS_LUNAR.md`, `research/RESEARCH_SYNTHESIS_PRIVATE.md`, `research/RESEARCH_CRITIQUE.md`, `research/RESEARCH_PRIVACY_CHAINS.md`, `research/FOUNDATIONAL_TECH_ANALYSIS.md`.
- **Feature requirements**: `FEATURE_REQUIREMENTS_v15.md` contains the detailed build spec for v1.5 with acceptance criteria and test plan.
- **Track notation**: versions suffixed with `-L` are lunar track, `-P` are privacy track. Unsuffixed versions are main track and apply to all stories.
- **Parallel tracks** run concurrently with the main track and do not block each other unless noted in the Cross-Track Dependencies table.
