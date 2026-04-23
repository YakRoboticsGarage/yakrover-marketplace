# Feature Requirements — v1.5 Crypto Rail (with Privacy-Aware Foundation)

**Version:** 1.5
**Last updated:** 2026-04-09
**Status:** Planned — gated on v1.4 completion (operator registration in production)
**Timeline:** Weeks 13-16 (4 weeks)
**Depends on:** v1.4 (operator sign-up and registration in production, at least 1 operator onboarded). Build base: v1.3 (284 tests, 35 MCP tools, ~17,042 LOC).

> **Goal:** USDC on Base accepted alongside Stripe. Settlement abstraction designed for future privacy (Diane) and lunar (Kenji) modes. Three privacy-aware changes ship to prevent architectural debt. Horizen L3 on Base identified as Mode 2 candidate for v2.1-P.

**Research backing:**
- `research/RESEARCH_SYNTHESIS_PRIVATE.md` — privacy architecture findings
- `research/RESEARCH_SYNTHESIS_LUNAR.md` — lunar settlement requirements
- `research/RESEARCH_CRITIQUE.md` — cross-story unified recommendations
- `research/FOUNDATIONAL_TECH_ANALYSIS.md` — six foundational considerations
- `research/RESEARCH_PRIVACY_CHAINS.md` — ZKsync Prividium, Horizen L3, Aztec comparative analysis

---

## Feature Summary

| # | Feature | Type | Decision ID | Priority |
|---|---------|------|-------------|----------|
| F-1 | x402 payment middleware | Crypto rail | TC-4 | **Must** |
| F-2 | RobotTaskEscrow.sol on Base | Crypto rail | TC-4 | **Must** |
| F-3 | USDC wallet top-up (Base) | Crypto rail | TC-4 | **Must** |
| F-4 | Payment method selection at task posting | Crypto rail | PD-8 | **Must** |
| F-5 | Settlement abstraction interface | Foundation | FD-1 | **Must** |
| F-6 | Commitment hash in on-chain memos | Foundation | FD-4 (replaces AD-3) | **Must** |
| F-7 | Robot wallet addresses hidden from API | Foundation | PP-2 | **Must** |
| F-8 | ERC-8004 agent card extensions | Crypto rail | — | **Should** |
| F-9 | Encrypted task specs at rest (API layer) | Foundation | PP-5-pre | **Should** |
| F-10 | DTN message schema (design only) | Foundation | LD-2-pre | **Should** |
| F-11 | BBS+ credential schema (design only) | Foundation | FD-2-pre | **Should** |
| F-12 | Horizen L3 escrow deployment test | Evaluation | FD-5 | **Could** |

---

## Feature Details

### F-1: x402 Payment Middleware

**Decision:** TC-4
**What:** Integrate `x402[fastapi]` middleware on the `accept_bid()` endpoint so robot tasks can be paid with USDC on Base.

**Requirements:**
- Install `x402[fastapi]` (Coinbase official Python SDK v2)
- Add `PaymentMiddlewareASGI` to the fleet server on `accept_bid()`
- Middleware verifies USDC payment on Base before allowing bid acceptance
- x402 facilitator validates payment receipt on-chain
- Fiat path (Stripe) continues to work alongside — no regression

**Acceptance criteria:**
- [ ] `accept_bid()` accepts USDC payment via x402 on Base Sepolia
- [ ] Fiat `accept_bid()` via Stripe still works (regression test)
- [ ] x402 facilitator correctly verifies payment amounts match bid price

---

### F-2: RobotTaskEscrow.sol on Base

**Decision:** TC-4, FD-1
**What:** Deploy an escrow smart contract on Base that holds USDC during task execution and releases to operator on delivery confirmation.

**Requirements:**
- Solidity contract with operator-controlled release
- Escrow flow: buyer deposits on bid acceptance → held during execution → released to operator on `confirm_delivery()` → returned to buyer on timeout/failure
- **CRITICAL (FD-1):** Contract MUST be designed with a `SettlementMode` enum and `settle(task_id, mode)` interface. Mode-specific logic is encapsulated behind the interface. Base-specific assumptions (EIP-3009, x402 facilitator calls) are isolated to Mode 1 implementation, NOT baked into the core escrow logic.
- The settlement interface must support four future modes without contract rewrite:

| Mode | Timing | Privacy | Implemented in |
|------|--------|---------|----------------|
| 1. Immediate transparent | Real-time | Public | **v1.5 (this release)** |
| 2. Immediate private | Real-time | Shielded | v2.1-P (Horizen L3 candidate) |
| 3. Batched transparent | Async / DTN | Public | v2.1-L (lunar) |
| 4. Batched private | Async / DTN | Shielded | v3.0 |

**Acceptance criteria:**
- [ ] Contract deploys on Base Sepolia
- [ ] USDC escrow, hold, and release works end-to-end
- [ ] `SettlementMode` enum exists with 4 modes; only mode 1 has implementation
- [ ] Modes 2-4 have stub functions that revert with `NotImplemented`
- [ ] Contract reviewed for settlement interface extensibility (no Base-specific assumptions in core logic)
- [ ] 25%/75% payment split works: 25% reserved on acceptance, 75% released on delivery

---

### F-3: USDC Wallet Top-Up (Base)

**Decision:** TC-4
**What:** Allow buyers to fund their platform wallet with USDC on Base, alongside existing Stripe credit bundles.

**Requirements:**
- Buyer sends USDC to platform wallet address on Base
- Platform detects deposit and credits internal wallet ledger
- Internal ledger works identically for USDC and Stripe-funded balances
- Minimum deposit: $5 USDC equivalent

**Acceptance criteria:**
- [ ] USDC deposit on Base Sepolia credits internal wallet
- [ ] Wallet balance correctly reflects both Stripe and USDC funding sources
- [ ] `auction_fund_wallet` MCP tool supports `method: "usdc"` parameter

---

### F-4: Payment Method Selection at Task Posting

**Decision:** PD-8
**What:** Buyer (or their AI agent) can choose payment method (fiat/crypto) when posting or accepting a task.

**Requirements:**
- `post_task()` accepts optional `payment_method` field: `"stripe"` | `"usdc"` | `"auto"`
- `"auto"` (default) selects based on wallet funding source
- Payment method is passed through to settlement layer
- Robot operators don't see or care about payment method — they receive payouts regardless

**Acceptance criteria:**
- [x] Task can be posted with explicit `payment_method` — implemented pre-v1.5, validated on `Task.__post_init__` against `VALID_PAYMENT_METHODS`
- [ ] `"auto"` correctly selects based on wallet state
- [ ] **Payment method is passed through to settlement layer** — currently not: `confirm_delivery` hardcodes `wallet.debit("buyer", ...)` at `engine.py:1061` with no branch on `task.payment_method`. Any agent calling `auction_post_task` through the marketplace MCP always settles via the in-memory demo ledger (+ Stripe Connect transfer if configured). See **IMP-109** for the concrete scope of wiring `payment_method == "usdc"` through to an EIP-3009 gasless on-chain transfer from buyer to operator on Base mainnet. Surfaced during the NPC ROBOT live rollout (2026-04-22): task settled in demo credits despite a real buyer wallet with 12.77 USDC on Base mainnet; no on-chain transfer occurred.
- [ ] Operator payout works regardless of buyer's payment method

---

### F-5: Settlement Abstraction Interface

**Decision:** FD-1
**What:** Design and implement the settlement abstraction layer that all future settlement modes (privacy, lunar batched) will build on. This is the single highest-leverage foundational decision.

**Requirements:**
- Define `SettlementInterface` protocol/abstract class with:
  - `settle(task_id: str, mode: SettlementMode, amount: Decimal, recipient: str) -> SettlementReceipt`
  - `verify(receipt: SettlementReceipt) -> bool`
  - `batch_settle(settlements: list[PendingSettlement]) -> BatchReceipt` (stub for mode 3/4)
- `SettlementMode` enum: `IMMEDIATE_TRANSPARENT`, `IMMEDIATE_PRIVATE`, `BATCHED_TRANSPARENT`, `BATCHED_PRIVATE`
- `SettlementReceipt` dataclass with: `tx_hash`, `commitment_hash`, `mode`, `timestamp`, `metadata`
- Mode 1 implementation: Base x402 (real)
- Modes 2-4: raise `NotImplementedError` with descriptive message of planned implementation
- The existing Stripe settlement becomes a separate `StripeSettlement` that implements the same interface
- Both `StripeSettlement` and `BaseX402Settlement` implement `SettlementInterface`
- Settlement routing logic: `payment_method` → appropriate settlement implementation

**Acceptance criteria:**
- [ ] `SettlementInterface` protocol defined with full type signatures
- [ ] `BaseX402Settlement` implements mode 1
- [ ] `StripeSettlement` implements the same interface for fiat
- [ ] Settlement routing correctly dispatches based on payment method
- [ ] Modes 2-4 are documented stubs (not silent no-ops — they raise with explanatory messages)
- [ ] Interface documentation includes example of how Mode 2 (Horizen L3) and Mode 3 (DTN batched) would plug in

---

### F-6: Commitment Hash in On-Chain Memos

**Decision:** FD-4 (replaces AD-3)
**What:** Replace raw `request_id` in on-chain transaction memos with a cryptographic commitment hash. This prevents permanent public task-payment linkage on the immutable blockchain.

**Requirements:**
- On-chain memo contains: `H(request_id || salt)` where `H` is SHA-256
- Salt is generated per-task and stored in platform database alongside `request_id`
- Platform database maintains the mapping: `commitment_hash ↔ (request_id, salt)`
- Audit workflow: given a `request_id`, compute `H(request_id || salt)` and match against on-chain memo to prove linkage
- Stripe metadata continues to use raw `request_id` (Stripe is not public/immutable; this is fine)

**Acceptance criteria:**
- [ ] On-chain USDC transactions contain commitment hash, not raw `request_id`
- [ ] Platform database stores `(request_id, salt, commitment_hash)` mapping
- [ ] Audit function: `verify_task_payment(request_id) -> (tx_hash, chain, amount)` works via hash lookup
- [ ] No raw `request_id` appears in any on-chain data (transaction memo, event logs, or contract storage)
- [ ] Stripe metadata still contains raw `request_id` (no change to fiat path)

---

### F-7: Robot Wallet Addresses Hidden from API

**Decision:** PP-2
**What:** Public API responses use platform-internal robot identifiers, never raw blockchain wallet addresses. Translation to on-chain addresses happens only inside the settlement layer.

**Requirements:**
- API responses use `robot_id` (ERC-8004 identity) not wallet addresses
- New internal mapping: `robot_id ↔ wallet_address` stored in platform database
- Settlement layer translates `robot_id` → `wallet_address` at payment time
- No wallet address appears in: MCP tool responses, task status, bid details, delivery confirmations, or any public endpoint
- Admin/operator dashboard MAY show wallet addresses to the operator who owns the robot (not to other users)

**Acceptance criteria:**
- [ ] Zero wallet addresses in any MCP tool response (grep all tool outputs)
- [ ] Settlement layer correctly resolves `robot_id` → `wallet_address` for USDC transfers
- [ ] Operator can see their own robot's wallet address in operator-facing endpoints
- [ ] External API consumers cannot derive wallet addresses from any public data

---

### F-8: ERC-8004 Agent Card Extensions

**Decision:** —
**What:** Extend the ERC-8004 agent card with marketplace-relevant fields for robot discovery.

**Requirements:**
- Add to agent card: `min_price`, `accepted_currencies` (`["usd", "usdc"]`), `reputation_score`
- **CONSTRAINT:** Do NOT add wallet addresses, detailed pricing history, or task history to the on-chain agent card. These are privacy-sensitive per the research findings. Keep on-chain metadata minimal.
- `reputation_score` is a single aggregate number (0-100), not a detailed breakdown

**Acceptance criteria:**
- [ ] Agent card includes new fields
- [ ] Discovery flow reads and uses `min_price` for pre-bid filtering
- [ ] `accepted_currencies` correctly filters robots that don't accept USDC

---

### F-9: Encrypted Task Specs at Rest (API Layer)

**Decision:** PP-5-pre (preparatory for v2.0 PP-5)
**What:** Task specifications are encrypted when stored in the platform database. This is the first step toward Diane's privacy story — it doesn't add TEE or encrypted matching yet, but ensures task data isn't stored in plaintext.

**Requirements:**
- Task specs encrypted with AES-256-GCM before writing to SQLite
- Encryption key managed per-platform-instance (initially from environment variable; HSM in production)
- Task specs decrypted on read for matching/scoring (plaintext in memory only during processing)
- No change to MCP tool interface — encryption is transparent to the agent
- Lays groundwork for v2.0 where decryption moves inside TEE enclaves

**Acceptance criteria:**
- [ ] Task specs in SQLite are encrypted (verify by reading raw database)
- [ ] All existing MCP tools work unchanged (encryption is transparent)
- [ ] Encryption key rotation supported (re-encrypt existing records)
- [ ] No performance regression > 5% on task posting/retrieval

---

### F-10: DTN Message Schema (Design Only)

**Decision:** LD-2-pre (preparatory for v2.1-L)
**What:** Define the message schema that will be used for DTN/Bundle Protocol communication with lunar rovers. Design only — no DTN transport implementation.

**Requirements:**
- Define message types: `RFQ_BUNDLE`, `BID_BUNDLE`, `TASK_ASSIGNMENT`, `COMPLETION_PROOF`, `SETTLEMENT_BATCH`, `CREDENTIAL_UPDATE`
- Each message type has: header (message_id, timestamp, ttl, priority, idempotency_key), body (type-specific payload), signature
- Messages must be idempotent (safe to replay) and order-independent (safe to reorder)
- Schema must support carrying encrypted task specs (for future lunar privacy)
- Schema must support carrying BBS+ credential updates
- Document as a design spec in `docs/DTN_MESSAGE_SCHEMA.md` — no code implementation

**Acceptance criteria:**
- [ ] `DTN_MESSAGE_SCHEMA.md` defines all message types with field-level documentation
- [ ] Schema reviewed for idempotency and ordering safety
- [ ] Schema supports encrypted payloads and credential bundles
- [ ] Message sizes estimated for LunaNet S-band (36 Kbps) and Ka-band (50 Mbps) constraints

---

### F-11: BBS+ Credential Schema (Design Only)

**Decision:** FD-2-pre (preparatory for v2.0)
**What:** Define the BBS+ credential schema for robot reputation that works across Earth and lunar environments. Design only — no BBS+ implementation.

**Requirements:**
- Define credential fields: `task_count`, `success_rate`, `avg_completion_time`, `capability_attestations`, `environmental_survival_history` (lunar), `operator_id`
- Define update protocol for Earth (low-latency, immediate reissuance) and lunar (DTN-tolerant, stale credentials accepted with scoring discount)
- Define threshold issuance model (3+ nodes; acknowledge single-issuer reality at seed scale)
- Define selective disclosure profiles: what a buyer sees vs. what an auditor sees vs. what a competing robot sees
- Document as a design spec in `docs/BBS_CREDENTIAL_SCHEMA.md` — no code implementation

**Acceptance criteria:**
- [ ] `BBS_CREDENTIAL_SCHEMA.md` defines schema, update protocols, and disclosure profiles
- [ ] Schema reviewed for cross-environment compatibility (Earth + lunar)
- [ ] Credential staleness model defined with configurable scoring discount
- [ ] Selective disclosure profiles cover: buyer, auditor, competing operator, regulatory

---

### F-12: Horizen L3 Escrow Deployment Test (Evaluation)

**Decision:** FD-5 (new)
**What:** Deploy a test instance of `RobotTaskEscrow.sol` on Horizen L3 testnet to evaluate viability for Mode 2 (immediate private) settlement.

**Requirements:**
- Deploy the same Solidity escrow contract on Horizen L3 testnet (should work unchanged — Horizen is EVM-compatible OP Stack)
- Test USDC bridging from Base Sepolia → Horizen L3 testnet
- Measure: deployment cost, transaction latency, bridge transfer time
- Evaluate Horizen Confidential Compute Environment (HCCE) — can it serve as the TEE layer for encrypted task matching?
- Test x402 facilitator verification with Horizen's selective disclosure
- Document findings in `docs/research/HORIZEN_L3_EVALUATION.md`

**Acceptance criteria:**
- [ ] Escrow contract deploys on Horizen L3 testnet
- [ ] USDC bridge transfer from Base → Horizen L3 completes (record latency)
- [ ] Evaluation report covers: cost, latency, HCCE maturity, x402 compatibility
- [ ] Go/no-go recommendation for Horizen L3 as Mode 2 settlement target

---

### F-13: Firmware-level auth for public-exposed teleop robots

**Source:** NPC ROBOT live rollout (2026-04-22), tracked as **IMP-110**
**What:** Any live_production robot whose HTTP surface is reachable from the public internet (e.g. via Cloudflare Tunnel) needs an auth layer beyond "URL obscurity" — otherwise anyone who discovers the tunnel subdomain can issue motor/sensor commands without paying. Current posture: NPC ROBOT ships with no `/motor/*` auth, matching Finland's model. Finland is safe because it's LAN-only; NPC ROBOT is not.

**Options to evaluate:**

| Option | Description | Tradeoff |
|---|---|---|
| **A** | Firmware checks `Authorization: Bearer <token>` on `/motor/*`. Token baked at build time (fleet-size-1) or NVS-stored (fleet-size ≥2). | Self-contained, defense-in-depth, rotation needs reflash or NVS write |
| **B** | Cloudflare Access policy on the tunnel subdomain, service-token JWT signed by the operator's Fly MCP. | No firmware change; auth at the edge; cost of Cloudflare Access if a paid tier is required |
| **C** | Network-layer isolation (Cloudflare WARP Connector or IP allowlist) restricting the tunnel to the operator's Fly app egress range. | Tightest surface; ops burden if operator deploys move |

**Acceptance criteria:**
- [ ] Decision recorded (A, B, or C) after review with Anuraj
- [ ] Documented in ROBOT_OPERATOR_ONBOARDING / ACTIVATION_SUMMARY as a required step for `live_production` attestation when robot is publicly reachable
- [ ] Retrofitted for NPC ROBOT as a worked example

---

## What Is NOT Included in v1.5

| Item | Reason | Planned for |
|------|--------|-------------|
| TEE infrastructure | Needs cloud confidential VMs, out of scope | v2.0 |
| TEE-based encrypted matching | Depends on TEE infra | v2.0 |
| BBS+ credential issuance (code) | Design-only in v1.5 | v2.0 |
| DTN transport implementation | Design-only in v1.5 | v2.1-L |
| Horizen L3 production deployment | Evaluation-only in v1.5 | v2.1-P |
| Privacy Pools integration | Not yet on Base | v2.1-P or v3.0 |
| Aleo integration | No identified non-EU market | Monitoring only |
| ZKsync Prividium | Wrong model (permissioned enterprise) | Not planned |
| Dispute resolution | Premature (PD-7) | v3.0+ |
| Staking/slashing | Needs reputation system first | v3.0+ |
| Cross-chain support | Base only | Future |
| Automated escrow dispute | Operator-controlled release only | Future |

---

## Decisions Updated by v1.5

| Decision | Change | Reason |
|----------|--------|--------|
| **AD-3** | Raw `request_id` no longer embedded in on-chain memos. Replaced by commitment hash `H(request_id \|\| salt)` per FD-4. | Privacy research: permanent public task-payment linkage on immutable chain is irreversible. |
| **TC-4** | Escrow contract now requires settlement abstraction interface (FD-1). x402/Base-specific logic isolated to Mode 1. | Cross-story research: lunar (batched) and privacy (shielded) tracks both depend on this abstraction. |

## New Decisions Introduced

| ID | Decision | Rationale |
|----|----------|-----------|
| **FD-1** | Settlement abstraction with 4 modes; only Mode 1 implemented | Both lunar and privacy tracks depend on this; building without it creates rewrite debt |
| **FD-2** | Unified BBS+ credential schema for Earth + lunar | Designing two systems and merging is more expensive than one schema |
| **FD-3** | Base for v1.5-v2.0; Aleo monitor only; Horizen L3 evaluate for v2.1-P | EU AMLR Art. 79 makes privacy chains legally risky; Horizen L3 on Base is the pragmatic candidate |
| **FD-4** | Commitment hash replaces raw request_id on-chain | Blockchain immutability means privacy leaks are permanent |
| **FD-5** | Evaluate Horizen L3 on Base for Mode 2 settlement | Best-fit privacy chain: same EVM, same USDC liquidity, TEE-based compliant privacy, live on Base mainnet |
| **PP-2** | Robot wallet addresses hidden from public API | Preserves future option for rotating/shielded addresses |
| **PP-5-pre** | Encrypted task specs at rest in v1.5 (preparatory) | First step toward Diane's story; prevents plaintext task data accumulation |

---

## Test Plan

### Crypto Rail Tests
- [ ] End-to-end: post task → fund wallet with USDC → accept bid → execute → settle on Base Sepolia
- [ ] Fiat regression: full lifecycle still works with Stripe
- [ ] Mixed: USDC-funded buyer, Stripe-funded operator payout
- [ ] Edge: insufficient USDC balance → clear error message
- [ ] Edge: x402 facilitator timeout → graceful failure

### Settlement Abstraction Tests
- [ ] Mode 1 (immediate transparent) completes end-to-end
- [ ] Modes 2-4 raise `NotImplementedError` with descriptive message
- [ ] `SettlementInterface` enforced via protocol/ABC (type-check test)
- [ ] Stripe settlement implements same interface
- [ ] Settlement routing selects correct implementation

### Privacy Foundation Tests
- [ ] On-chain memo contains commitment hash, not raw request_id
- [ ] Commitment hash verifiable via audit function
- [ ] No wallet address in any MCP tool response (automated grep)
- [ ] Task specs encrypted in SQLite (read raw DB to verify)
- [ ] Encryption transparent to MCP tools (no behavior change)

### Backward Compatibility
- [ ] All 151 existing v1.0 tests pass
- [ ] Stripe-only workflow unchanged
- [ ] `auction_quick_hire` works with both payment methods
- [ ] Existing `request_id` metadata in Stripe unchanged
