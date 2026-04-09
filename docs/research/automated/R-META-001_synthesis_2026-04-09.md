# R-META-001: Weekly Research Synthesis and Pipeline Self-Critique

**Date:** 2026-04-09  
**Topic ID:** R-META-001  
**Module:** system  
**Status:** complete  
**Trigger:** 8 completed topics since last synthesis (threshold: 7)

---

## Executive Summary

- **8 topics completed** (R-001, R-006, R-009, R-024, R-025, R-031, R-034, R-035) across four research tracks: DOT compliance, deliverable QA, payment infrastructure, and operator identity. Research quality is high but skewed toward payment/crypto topics (4 of 8 topics).
- **3 data integrity bugs found** in RESEARCH_ROADMAP.yaml: duplicate IDs R-026, R-027, and R-028 each appear twice with different titles — one set is from original roadmap, one set spawned by R-024 (2026-04-03). Requires immediate deduplication.
- **2 stalled in_progress topics** (R-007, R-027) have no output files and must be reset to `queued`.
- **3 improvement proposals are implemented but still marked `proposed`**: IMP-021, IMP-023 (EPSG codes), and IMP-027 (EIP-3009) were committed in the past 3 days. Backlog metadata is stale.
- **3 new research topics warranted** by code shipped since last synthesis: ACH fraud patterns (v1.3), zero-knowledge foundation (roadmap v4.9), and mobile wallet UX (IMP-039 proposed but unresearched).

---

## 1. Research Quality Critique

### R-001 — Multi-State DOT Survey Standards
**Quality: High.** Thorough state-by-state breakdown of MDOT, ODOT, TxDOT, Caltrans with specific accuracy, density, and deliverable requirements. Four improvement proposals (IMP-017–020) are well-specified.  
**Critique:** No NCDOT section despite noting it as a "fifth distinct standards regime." R-001 notes NCDOT uses USGS QL-based standards but does not document the specifics — creates an incomplete picture for potential North Carolina expansion.  
**Action:** No immediate action. If NC market is targeted, extend R-001 findings.

### R-006 — State PLS Board API Availability
**Quality: Medium.** Found 3 states with free or structured APIs (CO, IN, MA) and correctly escalated to Checkr/MeshVerify as commercial solutions. Spawned R-006b/c/d for deeper dives.  
**Critique:** Entire research track (IMP-001/002/003) was correctly deferred when product direction shifted to entity-level KYB (see R-027). However, R-006b (Checkr vs MeshVerify), R-006c (CA DCA endpoint), and R-006d (Michigan LARA bulk data) remain queued even though the decision to defer individual PLS verification makes them less urgent. These should be marked **low priority** unless R-027 concludes that per-credential verification is still needed for high-value tasks.

### R-009 — LAS/LAZ Point Cloud Validation
**Quality: High.** Implemented as `auction/deliverable_qa.py` with 4-level QA system. IMP-004, IMP-006, IMP-007, IMP-008, IMP-009 all implemented. The PDAL path (IMP-005) is the one open item, blocked by packaging complexity (R-009a queued).  
**Critique:** R-009a (PDAL packaging) is the only blocker for production-grade density checks on QL-gated tasks. It is queued at high priority but has not been scheduled in 7 days. This is the right call for a high-priority topic — it should be near the top of the queue.

### R-024 / R-025 — Fiat-to-USDC Checkout and Stripe USDC
**Quality: High.** Correctly identified Stripe Connect USDC payouts (sole proprietors only), Coinbase Onramp (zero-fee card→USDC), and PayRam (newly launched card→Splits). R-025 was efficiently answered within R-024 without a separate session.  
**Issue:** The spawned topics from R-024 were assigned IDs R-027 and R-028, which were already used in the roadmap for different topics. This created duplicate ID collisions. See Section 3 (YAML Bugs) for the fix.

### R-031 — State Plane Zone Auto-Detection
**Quality: High.** Identified the `stateplane` library as the right tool, corrected EPSG codes in `standards-reference.md`, and provided the full 4-state 16-zone table. IMP-021 and IMP-023 were implemented within 1 day of the research (commits `b76a4f1`).  
**Note:** IMP-022 (adding `_infer_state_plane_epsg()` to rfp_processor.py) and IMP-024 (duplicate `_load_reference()` removal) remain proposed and unimplemented.

### R-034 — ERC-2612 Permit Relay Security
**Quality: High.** Identified the non-atomicity MEV vulnerability in the live permit+transferFrom pattern, correctly assessed ERC-4337 as over-engineering, and recommended EIP-3009 as the structural fix. Five targeted improvement proposals (IMP-027–031).  
**Implementation status:** IMP-027 (EIP-3009 migration) implemented in commit `a58560f`. IMP-028 (server-side signature pre-verification), IMP-029 (relay wallet gas monitoring), IMP-030 (relay address exposure), and IMP-031 (deadline floor) remain **proposed and unimplemented**. These are small, targeted fixes — recommend bundling into a single PR.

### R-035 — EIP-3009 Implementation Guide
**Quality: High.** Precise ABI strings, signing payload, Multicall3 integration, and frontend code. The guide directly drove the IMP-027 implementation.  
**Open items:** IMP-035 (full relay endpoint rewrite with Multicall3), IMP-036 (cancelAuthorization in task cancel flow), IMP-037 (authorizationState nonce freshness check) remain proposed. IMP-027 was a partial implementation (EIP-3009 preferred with permit fallback) — IMP-035 is the full rewrite to drop the permit fallback entirely. Assess whether the fallback should stay permanently.

---

## 2. Cross-Module Pattern Analysis

### Pattern A: Multi-State RFP Intelligence Layer
**Topics:** R-001 (DOT standards) + R-031 (State Plane zones) + [queued: R-032 route geocoding, R-033 GEOID18 datums, R-030 TxDOT UAS, R-029 ODOT .dgn]

These four completed and four queued topics collectively define a "multi-state RFP intelligence" capability. The logical sequence is:
1. ✅ State detection from RFP text (IMP-017 proposed)
2. ✅ Standards loading per state (IMP-018/019/020 proposed)
3. ✅ EPSG zone lookup (IMP-021/023 implemented)
4. 🔄 Route-based geocoding (R-032 queued)
5. 🔄 Vertical datum selection (R-033 queued)

**Recommendation:** Bundle IMP-017–020 as a single "multi-state standards" implementation sprint. Prioritize R-030 (TxDOT pre-approval) as Texas is explicitly identified as a high-TAM market.

### Pattern B: USDC Payment Security Stack
**Topics:** R-034 (MEV vulnerability) + R-035 (EIP-3009) + [queued: R-036 Flashbots Protect, R-038 validBefore window]

The security progression is:
1. ✅ Identified MEV vulnerability in permit+transferFrom (R-034)
2. ✅ Implemented EIP-3009 with fallback (IMP-027, commit `a58560f`)
3. 🔄 Remaining server-side hardening (IMP-028, 029, 030, 031 — small, same file)
4. 🔄 Full relay rewrite with Multicall3 (IMP-035)
5. 🔄 Cancel and nonce freshness (IMP-036, 037)
6. ⬜ Flashbots Protect for residual MEV (R-036 queued) — reduced priority now that EIP-3009 is live
7. ⬜ validBefore window for commit-on-hire (R-038 queued) — still relevant

**Recommendation:** Run IMP-028/029/030/031 as a bundled PR immediately (combined effort: ~1 day). Defer R-036 to low priority — the EIP-3009 migration eliminates the primary MEV vector.

### Pattern C: Operator Verification Strategy
**Topics:** R-006 (PLS APIs) + R-027 in_progress (operator identity verification, stalled)

The direction is clear: **entity-level KYB, not per-credential PLS verification.** This is supported by the IMP-001/002/003 deferral notes. R-027 (operator identity) was started but never completed — its output file is missing. The queued R-028 (Stripe Connect KYC) logically follows R-027 and cannot start until R-027 completes.

**Recommendation:** Reset R-007 and the first R-027 to `queued` status. Prioritize the first R-027 (operator identity) as it unblocks R-028 and is critical for production operator onboarding.

---

## 3. Data Integrity Bugs in RESEARCH_ROADMAP.yaml

### Bug 1: Duplicate ID R-026
- **First occurrence** (line 366): "publish.new — agent-native marketplace with x402/MPP payments" — status: queued, priority: high
- **Second occurrence** (line 434): "Feedback signal quality — what rating data actually predicts" — status: queued, priority: medium, spawned_from: `git:ac9be52`

**Fix:** Rename second occurrence to **R-039** (next available ID after deduplication).

### Bug 2: Duplicate ID R-027
- **First occurrence** (line 324): "Robot operator identity verification — individuals and businesses" — status: **in_progress**, priority: critical
- **Second occurrence** (line 407): "PayRam production reliability audit and fee structure confirmation" — status: queued, priority: high, spawned_from: R-024

**Fix:** Rename second occurrence to **R-040**. The "do not conduct before 2026-05-01" note means R-040 should remain queued with a conditional note.

### Bug 3: Duplicate ID R-028
- **First occurrence** (line 334): "Stripe Identity and Connect KYC as operator verification" — status: queued, priority: high, depends_on: [R-027]
- **Second occurrence** (line 420): "Operator entity-type distribution — sole proprietors vs. LLCs" — status: queued, priority: medium, spawned_from: R-024

**Fix:** Rename second occurrence to **R-041**.

---

## 4. Stalled In-Progress Topics

### R-007 — Electronic survey seal/stamp regulations by state
**Status:** marked `in_progress` — no output file exists. Started in a previous session that was interrupted.  
**Action:** Reset to `queued`. Priority remains critical (affects PLS stamp requirement for all design survey deliverables).

### R-027 (first occurrence) — Robot operator identity verification
**Status:** marked `in_progress` — no output file exists. Started in a previous session that was interrupted.  
**Action:** Reset to `queued`. Priority remains critical (unblocks R-028 and production operator onboarding).

---

## 5. Improvement Proposal Status Corrections

These proposals are marked `proposed` but were implemented based on recent commits:

| IMP | Title | Evidence | Correct Status |
|-----|-------|----------|----------------|
| IMP-021 | Fix incorrect EPSG codes in standards-reference.md | commit `b76a4f1` "IMP-021/023: Fix EPSG codes + expand 4-state zone table" | **implemented** |
| IMP-023 | Complete EPSG zone table for 4-state target markets | commit `b76a4f1` | **implemented** |
| IMP-027 | Migrate permit relay to EIP-3009 transferWithAuthorization | commit `a58560f` "IMP-027: EIP-3009 transferWithAuthorization (preferred, permit fallback)" | **implemented** |

Note: IMP-027 is a partial implementation (permit fallback retained). IMP-035 covers the full rewrite. Mark IMP-027 as implemented and keep IMP-035 as proposed.

---

## 6. Priority Re-Ranking for Remaining Queue

### Upgrade to Higher Priority
- **R-007** (electronic survey seals) — reset to queued, **critical** — affects all design survey deliverables, PLS stamp is a legal requirement in every target state
- **R-027/first** (operator identity verification) — reset to queued, **critical** — blocks production operator onboarding and R-028
- **R-009a** (PDAL packaging) — remains **high** — only blocker for IMP-005 (density QA for QL-gated tasks)
- **R-019** (competitive landscape) — remains **high** — no research done on DroneBase/Zeitview/Skydio since April 1; 3 weeks is stale for a competitive analysis

### Downgrade
- **R-006b** (Checkr vs MeshVerify) — downgrade to **low** — IMP-001 deferred pending R-027 conclusion; premature to evaluate a service we've decided not to use yet
- **R-006c** (CA DCA JSON endpoint) — downgrade to **low** — same rationale
- **R-006d** (Michigan LARA bulk data) — downgrade to **medium** — Michigan is primary market; bulk sync is still useful for entity-level matching even without individual PLS lookups
- **R-036** (Flashbots Protect on Base) — downgrade to **low** — EIP-3009 eliminates the MEV allowance window; Flashbots is residual defense-in-depth, not blocking

### Keep as-is
- R-005 (GC bid evaluation practices) — high
- R-008 (ACORD 25 COI PDF extraction) — high
- R-010 (DOT deliverable QA checklists) — high (depends R-009 ✓)
- R-012 (construction escrow platforms) — high
- R-020 (Michigan construction survey market sizing) — high
- R-026/first (publish.new agent-native marketplace) — high
- R-032 (route-based geocoding for DOT corridors) — medium
- R-033 (GEOID18 vs NAVD88 datum selection) — medium
- R-038 (validBefore window for commit-on-hire) — medium

### Recommended run order for next 7 sessions
1. **R-007** (electronic survey seals — critical, reset to queued)
2. **R-027** (operator identity verification — critical, reset to queued)
3. **R-009a** (PDAL packaging — high, unblocks IMP-005)
4. **R-019** (competitive landscape — high, 3 weeks stale)
5. **R-005** (GC bid evaluation — high, no deps)
6. **R-008** (ACORD 25 COI parsing — high, no deps)
7. **R-META-001** (re-synthesis at 7-topic mark — high, recurring)

---

## 7. New Topics Identified

### R-042: ACH Payment Fraud Patterns and Risk Controls for Marketplace Platforms
**Module:** M15_stripe_service  
**Priority:** high  
**Trigger:** v1.3 shipped ACH bank transfer payment (commit `5ceaa8e`). ACH has distinct fraud vectors vs card payments: ACH return codes (R02 insufficient funds, R10 unauthorized, R29 corporate check), Nacha rules, and the 2-3 business day settlement delay.  
**Questions:** (1) What ACH fraud rates should we expect at $1K–$10K construction task prices? (2) What is Stripe's ACH return handling behavior — who bears the loss on an R10 return after delivery? (3) Should ACH be disabled for first-time buyers or tasks above a value threshold? (4) What velocity controls does Stripe apply automatically to ACH vs card?

### R-043: Zero-Knowledge Proofs for Construction Survey Data Privacy (v1.5 ZK Track)
**Module:** system  
**Priority:** low  
**Trigger:** Commit `cca6ae2` "Roadmap v4.9: add v1.5 zero-knowledge research." This is a pre-research topic to understand whether ZK proofs are the right approach for survey data privacy (location privacy for sensitive sites, bid confidentiality, credential verification without disclosure).  
**Questions:** (1) What are the most practical ZK proof systems for off-chain data attestation in 2026 (Groth16, PLONK, STARKs)? (2) Does Horizen L3 (FD-5) support ZK-based credential verification? (3) Are there existing survey/geospatial privacy frameworks that use ZK? (4) What is the compute cost of ZK proof generation for a typical LAS point cloud metadata proof?

### R-044: WalletConnect v2 Integration for Mobile USDC Payments
**Module:** M38_browser_wallet  
**Priority:** medium  
**Trigger:** IMP-039 proposed (mobile USDC fails without window.ethereum) but no research conducted.  
**Questions:** (1) What is the WalletConnect v2 integration path in a vanilla JS frontend (no wagmi/RainbowKit)? (2) Does WalletConnect v2 support `signTypedData_v4` (required for EIP-3009 EIP-712 messages)? (3) What are the Cloudflare Worker CORS implications for WalletConnect relay server calls? (4) Is WalletConnect or `@metamask/sdk` simpler for a mobile-first single-page demo? (5) What is the user session handling model (reconnect across page refreshes)?

---

## 8. Proposals to Bundle

The following improvement proposals address the same file and should be implemented together to minimize review overhead:

### Bundle 1: Payment relay server-side hardening (chatbot/src/index.js)
- IMP-028: Server-side permit signature pre-verification
- IMP-029: Relay wallet gas balance monitoring (Cron Trigger)
- IMP-030: Remove relay_address from API success response
- IMP-031: Add deadline floor to handleRelayUsdc
**Combined effort:** ~1 day. All target chatbot/src/index.js + wrangler.toml. No behavior change for valid requests.

### Bundle 2: EIP-3009 full relay rewrite (chatbot/src/index.js)
- IMP-035: Full EIP-3009 relay endpoint with Multicall3
- IMP-036: cancelAuthorization in task cancellation
- IMP-037: authorizationState nonce freshness check before submission
**Combined effort:** ~2 days. All target the same relay/commit-on-hire flow.

### Bundle 3: Multi-state RFP intelligence (rfp_processor.py + standards-reference.md)
- IMP-017: State-detection logic in rfp_processor.py
- IMP-018: Create txdot-standards.md reference file
- IMP-019: ODOT-specific operator capability constraints
- IMP-020: Caltrans Type A/B mapping
- IMP-022: Add stateplane library + _infer_state_plane_epsg() helper
- IMP-024: Remove duplicate _load_reference() definition
**Combined effort:** ~3 days. All target M1_rfp_processor. IMP-021/023 already implemented.

---

## 9. Topics to Mark Stale

None of the existing topics are fully superseded, but the following can be deprioritized:

- **R-022** (A2A protocol adoption) — low priority, no operational impact until v2.0
- **R-023** (MCP server discovery patterns) — low priority, our MCP server works well; ecosystem is still early
- **R-018** (W3C Verifiable Credentials) — low priority, depends on ZK track maturity (v1.5+)

These should remain `queued` but should not be scheduled before higher-priority operational topics are addressed.

---

## 10. Research Pipeline Health

| Metric | Value | Assessment |
|--------|-------|------------|
| Topics complete | 8 (9 incl. R-025) | On pace |
| Topics in_progress | 2 (stalled) | Needs reset |
| Topics queued | ~32 | Healthy backlog |
| IMP proposals total | 47 | Growing correctly |
| IMP implemented | 7 + 3 uncounted | Backlog stale |
| IMP proposed, unstarted | ~35 | High — prioritization needed |
| Avg session gap | ~1 topic/day | Good cadence |
| YAML data integrity | 3 duplicate IDs | Needs repair |
| Feedback issues processed | None (GitHub MCP tools unavailable in this session) | Follow up in next session |

**Overall assessment:** Research pipeline is healthy and producing actionable output. The primary issues are housekeeping: YAML deduplication, stalled in_progress resets, and backlog status sync with recent code commits.

---

## Appendix: Completed Research Files

| ID | Title | Date | Key Output |
|----|-------|------|------------|
| R-001 | Multi-State DOT Survey Standards | 2026-04-05 | 4 state specs, IMP-017–020 |
| R-006 | State PLS Board APIs | 2026-04-01 | 3-tier verification routing |
| R-009 | LAS/LAZ Point Cloud Validation | 2026-04-02 | deliverable_qa.py (4 levels) |
| R-024 | Fiat-to-USDC Checkout Services | 2026-04-03 | Stripe USDC, Coinbase Onramp, PayRam |
| R-025 | Stripe Crypto Payouts (folded into R-024) | 2026-04-03 | Sole-proprietor USDC constraint |
| R-031 | State Plane Zone Auto-Detection | 2026-04-05 | stateplane library, EPSG corrections |
| R-034 | ERC-2612 Permit Relay Security | 2026-04-06 | MEV vulnerability, EIP-3009 recommendation |
| R-035 | EIP-3009 Implementation Guide | 2026-04-07 | Multicall3 batch, signing UX |
