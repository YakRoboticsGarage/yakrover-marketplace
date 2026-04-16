# DECISIONS.md — Single Source of Truth

> All product decisions, technical constraints, data models, and out-of-scope rules live here.
> Other documents reference this file rather than restating these items.
> When a decision changes, update it **only here**.

**Last updated:** 2026-04-12 (v1.4.1 complete — 100-robot fleet, EAS attestation, delivery schemas)

---

## Product Decisions

### PD-1 · Auction Mechanism: RFQ (Request for Quote)
The auction stays open indefinitely. It closes only when the Agent **accepts** a bid or **withdraws** the request. No timer. No forced close.

**Why:** Handles global robot latency gracefully. Agent controls selection criteria. Validated by TraderBots (CMU) and Fetch.ai's Contract Net Protocol in production.

---

### PD-2 · Bid Engine: Automated, Not Manual
Each robot runs a `bid_engine(task) -> Bid | None` function autonomously. Robot operators tune the pricing function — they never manually submit individual bids.

**Why:** Scales to thousands of concurrent tasks. Prevents missed opportunities. Validated by Akash Network's bid engine microservice pattern.

---

### PD-3 · Bids Are Signed from Day One
Every bid is signed with the robot's ERC-8004 signer key. The `bid_hash` field is non-negotiable and always present.

**Why:** Non-repudiable bids are the foundation for future reputation, dispute resolution, and audit trails. Adding signing later is harder than including it from the start.

**Phase 0 exception:** Phase 0 simulation uses HMAC-SHA256 mock signing (no real Ed25519). Real ERC-8004 signing begins in Phase 1.

---

### PD-4 · Payment: Full Amount on Delivery (updated 2026-04-05)
- **No upfront reservation.** Full payment on delivery confirmation only.
- **Commit-on-hire:** Buyer signs ERC-2612 permit on award (commits to pay, no money moves). Money moves when buyer accepts delivery.
- **Escrow:** Deferred to later version for high-value tasks (>$10K). See roadmap.

**Why:** Simplified from the original 25%/75% split. Permit-based commitment gives the operator confidence without moving money upfront.

---

### PD-5 · Delivery QA: Schema-Driven, No Surprises (updated 2026-04-05)
The task spec includes a `delivery_schema` that serves three purposes:
1. **Robot reads it** before starting work — knows exactly what to return
2. **Robot self-validates** before submitting — same validation function as the marketplace
3. **QA engine validates** delivery against it — same schema, same rules

The schema supports: `required`, `type`, `minimum`/`maximum`, `minItems`/`maxItems`, `minLength`, nested `properties` and `items`. No task-type-specific code in the QA engine.

**Why:** The robot should never be surprised by a QA check. Same contract for both sides. Adding new task types means adding schema templates, not changing QA code.

---

### PD-6 · On Rejection: Task Re-Pools, No Retry
When an Agent rejects a payload: robot is notified with the rejection reason; task goes back to open bid pool; no automatic retry.

**Why:** Keeps the system stateless and simple. Any robot (including the original) can re-bid on the re-pooled task.

---

### PD-7 · High-Trust Seed Network in v1
v1 assumes good-faith actors. No disputes, arbitration, reputation slashing, or fraud detection.

**Why:** Building dispute resolution before the network has volume creates premature complexity. Trust mechanisms should be informed by real failure patterns observed at scale.

---

### PD-8 · Fiat Accessibility is First-Class
A person with a corporate credit card must be able to participate without any blockchain knowledge. The crypto payment path is additive, not required.

---

## Technical Constraints

### TC-1 · Minimum Task Price: $0.50
No task may have a `budget_ceiling` below **$0.50 USD** (or equivalent).

**Enforce at:** `post_task()` — reject at the API boundary before any auction logic runs.

**Why:** Stripe's minimum charge for USD card transactions is $0.50. Tasks below this threshold cannot be directly charged to a card. Sub-$0.50 task support is on the roadmap (requires Stripe Billing Meters or a nano-wallet model).

**Roadmap:** Sub-$0.50 support via aggregated micropayments — deferred post-Milestone 3.

---

### TC-2 · Fiat Payment Uses Prepaid Wallet Model
Card payments are not made per-task. Buyers purchase credit bundles upfront (e.g. $5, $10, $25 USD). Each task debits credits from an internal ledger. A Stripe Transfer to the robot operator fires on delivery confirmation.

**Why:** Per-task Stripe charges for small tasks ($0.50–$2.00) would all be near the minimum threshold and incur disproportionate fees. The wallet model batches card exposure into bundle purchases.

**Single capture constraint:** Stripe allows only one capture per PaymentIntent authorization. The 25%/75% split cannot be implemented as two Stripe captures from one auth. It is enforced in the internal ledger only.

---

### TC-3 · Fiat Stack: Stripe Connect Express + Separate Charges and Transfers
- **Buyer payments:** Stripe PaymentIntent (for wallet top-ups)
- **Operator payouts:** Stripe Connect Express accounts; triggered via `stripe.Transfer.create()`
- **No Stripe Treasury** in v1 — Separate Charges model (funds sit in platform Stripe balance) is sufficient
- **Operator onboarding:** Stripe-hosted Express KYB (~2 min); Finnish/EU operators fully supported via SEPA EUR
- **Agent-initiated payments:** Stripe Shared Payment Tokens (SPTs) — production-ready

**Live test findings (2026-03-25):**
- **Currency:** DE-based (Germany) Stripe accounts must use **EUR**, not USD. The API rejects USD charges on DE accounts. All `currency` parameters must be `'eur'`.
- **Topups:** `stripe.Topup.create()` does not work for DE accounts with USD. Use `stripe.Charge.create(source='tok_bypassPending', currency='eur')` to fund the platform's available balance in test mode.
- **Connect Express capabilities:** US-based Connect accounts require both `card_payments` and `transfers` capabilities requested at creation time.
- **Onboarding flow:** After `stripe.Account.create(type='express')`, generate a `stripe.AccountLink` for the operator to complete hosted onboarding. Capabilities transition: `inactive` -> `pending` -> `active` (may take a few seconds in test mode).
- **Platform balance before transfer:** The platform must have available balance before calling `stripe.Transfer.create()`. In test mode, fund via `Charge.create(source='tok_bypassPending')`.
- **Verified working:** Transfer `tr_1TEjtAFtukkQW2Gp6uPBWNjn` — EUR 0.35 to Connect account `acct_1TEjjLC2lXDckgmS` with `request_id` metadata.

---

### TC-4 · Crypto Stack: Commit-on-Hire Gasless USDC (updated 2026-04-05)
- **Settlement:** Two-phase gasless USDC. (1) Buyer signs ERC-2612 permit on task award — payment committed, no money moves. (2) After delivery + QA validation, buyer clicks Release — Worker submits `permit()` + `transferFrom()` on-chain.
- **Relay wallet:** `0x4b5974229f96ac5987d6e31065d73d6fd8e130d9` — funded on Base mainnet, Ethereum mainnet, Base Sepolia, Eth Sepolia.
- **Platform wallet:** `0xe33356d0d16c107eac7da1fc7263350cbdb548e5` — receives 12% commission.
- **Wallets supported:** Rabby, MetaMask, Coinbase Wallet (any EIP-1193 + EIP-712 wallet).
- **Chains supported:** Base mainnet, Ethereum mainnet, Base Sepolia, Eth Sepolia.
- **Gas cost:** ~$0.005/tx (Base), ~$0.15/tx (Ethereum mainnet). Platform pays.
- **x402:** NOT used for marketplace settlement. Reserved for agent-to-robot control.
- **Splits.org:** NOT used for demo. Available for production-scale distribution.
- **Robot wallet discovery:** `getAgentWallet(agentId)` on ERC-8004 identity registry.
- **Escrow:** `RobotTaskEscrow.sol` deferred (not needed for demo amounts).
- **Fiat rail:** Stripe destination charges with `application_fee_amount` (12%).
- **Discovery:** Direct subgraph query from browser + `eth_call` for wallet. No server dependency.

---

### TC-5 · 7-Day Stripe Authorization Hold Maximum
Standard US card authorizations expire in **7 days**. Tasks must be completed and payment captured within this window or a new authorization is required.

**Practical impact:** Relevant for Phase 3+ multi-day workflows. Not a constraint for short sensor/movement tasks in Phase 0–2.

---

## Architectural Decisions

### AD-1 · New Auction Code Lives in `auction/`
All new code for the auction layer goes in `auction/` (does not exist yet). It does not go in `src/`.

**Why:** Keeps the auction experiment isolated from the inherited yakrover framework. When ready for upstream contribution (Phase 5), a clean PR can be prepared from `auction/`.

---

### AD-2 · Changes to `src/` Must Be Backward-Compatible
Any modification to `src/core/` or `src/robots/` must not break the existing tumbller, tello, or fakerover plugins. New methods on `RobotPlugin` must have default implementations that return `None` or no-op.

---

### AD-3 · `request_id` Is the Universal Audit Key
Every task is assigned a UUID at `post_task()` time. This `request_id` must be:
- Immutable for the lifetime of the task
- Included in all bid, payment, delivery, and rejection events
- Embedded in Stripe payment metadata and crypto transaction memos

---

### AD-4 · In-Memory State in v1
The bid pool and task state are held in-memory on the fleet server. No database or persistent store in Phase 0–2.

**Implication:** Task state is lost on fleet server restart. Acceptable for development and initial testing. Persistent state is a Phase 3+ concern.

---

### AD-5 · Capability Matching Uses Two-Phase Filter-then-Score
Task matching runs in two distinct passes:

**Phase 1 — Hard Constraint Filter (deterministic):** Does the robot have the required sensors, IP rating, mobility type, and location proximity? Binary pass/fail. Robots that fail any hard constraint do not bid at all. Implemented in `check_hard_constraints()`.

**Phase 2 — Soft Scoring (probabilistic):** Among eligible robots, rank by price/SLA/confidence/reputation. This is the `score_bids()` function.

The `capability_requirements` field in DM-1 uses a `hard/soft/payload` structure to separate these phases. See DM-1 below.

**Why:** Every production marketplace (Thumbtack, Akash, Fetch.ai) implements this exact separation. Thumbtack's "Instant Results" system pre-computes a constraint index for sub-200ms matching. Mixing hard constraints into scoring produces garbage bids from incapable robots.

**Source:** research/raw/07_capability_taxonomies_matching.md

---

### AD-6 · Scoring Function Weights (Configurable)
Default scoring weights (TraderBots-inspired):
| Factor | Weight | Formula |
|--------|--------|---------|
| Price | 40% | `1 - (bid.price / task.budget_ceiling)` |
| SLA commitment | 25% | `1 - (sla_seconds / task.sla_seconds)`, capped at 1.0 |
| AI confidence | 20% | `bid.ai_confidence` (0–1) |
| Reputation | 15% | `bid.reputation_metadata.get("success_rate", 0.5)` |

Weights are constants at the top of `score_bids()`. They are configurable but not exposed as API parameters in v1. Reputation score uses `completion_rate` as the primary signal (validated by TaskRabbit/Fiverr level systems).

---

### AD-7 · Auto-Accept Timer on Delivery
Every task has an `auto_accept_seconds` field (default: 3600 = 1 hour). If the buying Agent does not call `confirm_delivery()` or `reject_delivery()` within this window, the delivery is **auto-accepted** and the 75% payment is released to the robot operator.

**Why:** Every major human service marketplace has this pattern. Fiverr uses 3-day auto-accept. Upwork uses 14-day auto-release. Without this, a stuck/offline buying agent blocks the robot and payment indefinitely. For robot tasks measured in seconds/minutes, 1 hour is appropriate.

**Source:** research/raw/08_task_marketplace_backend_patterns.md

---

### AD-8 · Task Lifecycle State Machine
Tasks move through defined states. Every state transition should emit a logged event (even in v1 with in-memory state).

```
POSTED → BIDDING → BID_ACCEPTED → IN_PROGRESS → DELIVERED
   │         │           │              │            │
   │         │           │              │            ├→ VERIFIED → SETTLED
   │         │           │              │            └→ REJECTED → RE_POOLED → BIDDING
   │         │           │              └→ ABANDONED → RE_POOLED
   │         │           └→ PROVIDER_CANCELLED → RE_POOLED
   │         └→ WITHDRAWN
   └→ EXPIRED (future, out of scope v1)
```

Post-award states (`IN_PROGRESS`, `DELIVERED`, `VERIFIED`, `FAILED`) map to Google A2A protocol states (`working`, `completed`, `failed`) for future interoperability.

**Source:** research/raw/08_task_marketplace_backend_patterns.md, research/raw/06_agent_protocols_a2a_ap2_wot.md

---

### AD-9 · Capability Metadata Uses WoT TD-Inspired Schema
Robot capability metadata in bids follows a structure inspired by the W3C Web of Things Thing Description: `sensors[]` (typed, with accuracy/range), `actions[]` (typed, with modes), `physical{}` (IP rating, mobility, battery), `marketplace{}` (pricing, availability, location).

Sensor types use a controlled vocabulary anchored on OCF resource type tokens with optional SOSA/SSN semantic URIs: `temperature`, `humidity`, `rgb_camera`, `thermal_camera`, `lidar_2d`, `imu`, `gps`, etc.

**Why:** WoT TD is the closest existing standard to robot capability description — machine-parseable JSON-LD, protocol-agnostic, with typed data schemas. Human skill taxonomies (O*NET, ISCO) are too coarse for hardware specs.

**Source:** research/raw/07_capability_taxonomies_matching.md

---

## Canonical Data Models

### DM-1 · Task

```python
@dataclass
class Task:
    request_id: str           # UUID, immutable, generated at post_task()
    description: str          # Natural language
    task_category: str        # Controlled: env_sensing | visual_inspection | mapping | delivery_ground | aerial_survey
    capability_requirements: dict  # Structured: {"hard": {...}, "soft": {...}, "payload": {...}} — see AD-5
    budget_ceiling: Decimal   # Must be ≥ $0.50 (see TC-1)
    sla_seconds: int          # Acceptable completion window in seconds
    auto_accept_seconds: int  # Default 3600; auto-accept delivery if agent doesn't respond (see AD-7)
    posted_at: datetime
```

**`capability_requirements` structure (see AD-5):**
```python
{
    "hard": {                          # Binary pass/fail — robot must satisfy ALL
        "sensors_required": ["temperature", "humidity"],
        "sensor_accuracy": {"temperature": {"max_error_celsius": 1.0}},
        "indoor_capable": True,
        "max_distance_meters": 100
    },
    "soft": {                          # Scoring bonus — nice-to-have
        "preferred_sensors": ["thermal_camera"]
    },
    "payload": {                       # What the robot must produce
        "type": "sensor_reading",
        "fields": ["temperature_celsius", "humidity_percent", "timestamp"],
        "format": "json"
    }
}
```

---

### DM-2 · Bid

```python
@dataclass
class Bid:
    request_id: str
    robot_id: str             # ERC-8004 registered identity
    price: Decimal            # Must be ≤ task.budget_ceiling
    sla_commitment_seconds: int
    ai_confidence: float      # 0.0–1.0
    capability_metadata: dict # WoT TD-inspired: sensors[], actions[], physical{}, marketplace{} — see AD-9
    reputation_metadata: dict # See DM-5 below
    bid_hash: str             # sign(robot_id + request_id + price) with ERC-8004 key
```

---

### DM-3 · AuctionResult

```python
@dataclass
class AuctionResult:
    request_id: str
    winning_bid: Bid | None   # None if no bids or all withdrawn
    all_bids: list[Bid]
    scores: dict[str, float]  # robot_id → composite score
    reason: str               # "accepted", "no_capable_robots", "budget_exceeded", "withdrawn"
```

---

### DM-4 · DeliveryPayload

```python
@dataclass
class DeliveryPayload:
    request_id: str
    robot_id: str
    data: dict                # Task-specific payload (sensor readings, image bytes, etc.)
    delivered_at: datetime
    sla_met: bool
```

---

### DM-5 · ReputationMetadata

```python
reputation_metadata = {
    "tasks_completed": int,         # total completed
    "completion_rate": float,       # completed / accepted (0.0–1.0) — primary signal for scoring
    "on_time_rate": float,          # delivered within SLA / completed
    "rejection_rate": float,        # buyer-rejected / delivered
    "rolling_window_days": int      # computation window (default 30)
}
```

**Source:** TaskRabbit Elite metrics, Fiverr Level System, Upwork JSS. `completion_rate` is the universal primary signal across all platforms.

---

### DM-6 · TaskState (Enum)

```python
class TaskState(str, Enum):
    POSTED = "posted"
    BIDDING = "bidding"
    BID_ACCEPTED = "bid_accepted"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SETTLED = "settled"
    RE_POOLED = "re_pooled"
    ABANDONED = "abandoned"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"           # Future — out of scope v1
```

See AD-8 for the full state transition diagram.

---

### AD-10 · `task_category` Is Optional (Inferred from Capabilities)
`task_category` is no longer required in `post_task()`. When omitted or empty, it is inferred from `capability_requirements.hard.sensors_required` via `infer_task_category()`. Temperature/humidity sensors map to `env_sensing`, cameras to `visual_inspection`, lidar to `mapping`. Default fallback is `env_sensing`.

**Why:** Agents rarely know the correct category enum value. Inferring it from capability requirements reduces friction and eliminates a common source of validation errors.

---

### AD-11 · `validate_task_spec()` Returns All Errors at Once
The validation function returns a `list[str]` of all errors rather than raising on the first failure. The MCP tool surfaces these as an `errors` array in the response.

**Why:** Agents fix errors in batches. Returning one error at a time forces multiple round-trips. Returning all errors lets the agent fix everything in a single retry.

---

### AD-12 · `auction_quick_hire` Convenience Tool
A single MCP tool that runs the entire auction lifecycle: post task, collect bids, accept the best, execute, and confirm delivery. Returns the sensor data, cost, and robot ID.

**Why:** For simple tasks, the 5-step individual tool flow is unnecessary overhead. `auction_quick_hire` reduces a temperature reading from 5 tool calls to 1. The individual tools remain available for fine-grained control.

---

### AD-13 · `next_action` Pattern in Responses
Every non-terminal response from `accept_bid()` includes a `next_action` string telling the agent what tool to call next. Example: `"Call auction_execute(request_id) to dispatch the task to the winning robot."`

**Why:** Agents work better with explicit guidance. Instead of requiring the agent to memorize the state machine, each response says what to do next.

---

### AD-14 · `available_actions` in `get_status` Responses
`auction_get_status()` returns an `available_actions` list of tool names valid in the current state, plus a `hint` string describing the expected next step.

**Why:** Agents can programmatically determine which tools are callable without hardcoding state machine knowledge. Combined with AD-13, this makes the auction fully navigable without documentation.

---

### AD-15 · Structured Error Responses (No Python Exceptions in MCP)
Every MCP tool catches exceptions and returns a dict with `error_code`, `message`, and `hint`. Python exception class names are never exposed to MCP consumers. Error codes are stable strings like `VALIDATION_ERROR`, `WALLET_NOT_FOUND`, `SLA_TIMEOUT`, `NOT_FOUND`.

**Why:** MCP consumers are LLMs, not Python programs. They need actionable error messages, not stack traces. The `hint` field tells the agent how to recover.

---

## Out of Scope (v1)

These items are **explicitly not built** in Phases 0–4. Do not implement them even if they seem useful.

| Item | Deferred to |
|------|-------------|
| Sub-$0.50 task pricing | Post-Milestone 3 |
| Task TTL / expiry for abandoned requests | Phase 3+ |
| Robot job queue and concurrent job locking | Phase 3+ |
| Compound / multi-step workflow tasks | Phase 5+ (Dark Factory) |
| Private or filtered task requests | Phase 3+ |
| Retry mechanism on payload rejection | Phase 3+ |
| Dispute resolution and arbitration | Phase 4+ |
| Reputation system and on-chain reviews | Phase 4+ |
| Operator staking and slashing | Phase 4+ |
| Cross-fleet trust tiers | Phase 4+ |
| Robot-to-robot sub-contracting | Phase 5+ |
| Stripe Treasury financial accounts | Phase 3+ (if needed) |

---

## Supersession Notes (v1.0.1 / v1.1.1 Construction Pivot)

> **Added:** 2026-03-29. The decisions above remain the canonical record. This section notes which have been superseded or recontextualized by the construction survey focus (see `ROADMAP_v4.md`).

### AD-3 — Partially Superseded by FD-4 (Commitment Hash)

AD-3 specifies that `request_id` should be embedded in Stripe payment metadata and crypto transaction memos. **FD-4** (Foundational Design Decision, `ROADMAP_v4.md`) replaces the raw `request_id` in on-chain memos with a commitment hash `H(request_id || salt)`. Audit capability is preserved via the platform-side plaintext mapping. AD-3 still applies to Stripe metadata (fiat path), but the crypto memo policy is now governed by FD-4.

### TC-1 — Recontextualized at Construction Scale

TC-1's $0.50 minimum was designed for generic sensor readings ($0.35-$2.00). At construction survey scale ($1,000-$72,000+ per task), the minimum is not a practical constraint. However, TC-1 remains relevant as a floor for the USDC rail and for potential future expansion to smaller task types. See Risk 4 in `ROADMAP_v4.md`.

### TC-2 — Wallet Model Extended for Construction

TC-2's prepaid wallet model was designed for small credit bundles ($5-$25). For construction, three commitment mechanisms now exist: (a) payment bond upload (public projects), (b) ACH-funded milestone escrow via Plaid (private projects), (c) prepaid credit bundles ($5,000 typical). The internal ledger accounting model from TC-2 remains the foundation — the new mechanisms are funding sources, not replacements.

### New Foundational Design Decisions (v1.5+)

The following decisions are defined in `ROADMAP_v4.md` and govern all versions from v1.5 forward:

| ID | Decision | Summary |
|----|----------|---------|
| **FD-1** | Settlement Abstraction Layer | 4-mode interface (immediate/batched x transparent/private). Only Mode 1 implemented in v1.5. |
| **FD-3** | Chain Decision — Base + Horizen L3 | Base is primary. Horizen L3 evaluated in v1.5 for Mode 2 (v3.0). |
| **FD-4** | On-Chain Memo Policy | Commitment hash `H(request_id \|\| salt)` replaces raw `request_id` in on-chain memos. |
| **FD-5** | Horizen L3 Evaluation | Deploy test escrow on Horizen L3 testnet in v1.5; decide Mode 2 path. |
| **PP-2** | Hidden Wallet Addresses | Robot wallet addresses never appear in public API responses. Platform-internal `robot_id` only. |

See `ROADMAP_v4.md` § "Foundational Design Decisions" for full rationale.

### New Decisions (v1.4.1, 2026-04-11/12)

| ID | Decision | Summary |
|----|----------|---------|
| **AD-20** | EAS Over Metadata Attestation | Platform attestation uses EAS (Ethereum Attestation Service), not ERC-8004 `setMetadata`. `setMetadata` is owner-only — platform can't attest operator-owned robots. EAS is a separate on-chain attestation signed by the platform wallet, revocable, with structured schema. Schema UID: `0x70a6cca5...` on Base Sepolia + mainnet. |
| **AD-21** | Per-Category MCP Servers | Each robot category gets its own Fly.io app (9 total), not a single server with namespace routing. Single-server approach caused tool name collisions (`ground_gpr_robot_submit_bid` vs `robot_submit_bid`). Per-category servers match the 8004 protocol — each robot's MCP endpoint has plain tool names. |
| **AD-22** | Geographic Hard Cutoff | Robot excluded if task location > `service_radius_km` (haversine distance). Hard filter, not a scoring factor. Robots without location metadata still bid on all tasks. |
| **AD-23** | Busy State Duration by Task Type | Winning robot gets `_busy_until` set for task-type-specific duration. `env_sensing`: 15s. `topo_survey`: 1hr. `corridor_survey`: 2hr. Robot excluded from bidding while busy. |
| **AD-24** | Delivery Schema Per Task Category | QA validates delivery data against category-specific schemas (8 types). Auto-injected by engine if not in task spec. Schemas in `auction/delivery_schemas.py`. |
| **AD-25** | Fleet Taxonomy via EAS | Three attestation types: `live_production` (real robots), `demo_fleet` (test fleet), `legacy` (deprecated). Discovery filters by attestation. Revocable. |
| **AD-26** | Business Docs in Separate Repo | Pitch, outreach, financial model moved to `rafaeldavid/robotTAM`. Engineering repo contains only code + technical docs. |
| **AD-27** | Protocol/Commercial Separation | Auction engine (`auction/core.py`, `engine.py`, `deliverable_qa.py`, `reputation.py`, `wallet.py`, `store.py`, `discovery_bridge.py`) is the protocol layer — MIT-licensed, no commercial imports. Commercial layer (Stripe, frontend, worker, EAS curation) imports protocol, never the reverse. Full separation at v3.0; dependency direction enforced from v1.5. See `docs/architecture/ASSESSMENT_PROTOCOL_SEPARATION.md`. |
