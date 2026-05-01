# R-META-002: Weekly Research Synthesis and Pipeline Review — Run 2

**Date:** 2026-05-01  
**Topic ID:** R-META-002  
**Module:** system  
**Trigger:** 8 completed topics since R-META-001 (2026-04-09) — threshold: 7  
**Scope:** All research docs in `docs/research/automated/`, improvement backlog, recent git commits

---

## Executive Summary

- **8 topics completed since R-META-001:** R-027, R-007, R-007b, R-045, R-028, R-042, R-008, R-010. Research skewed heavily toward compliance/legal (4 topics) and QA/payment (2 each). Market research (R-019, R-020, R-021) remains entirely unexecuted — a significant strategic gap given we cannot validate product/market fit without it.
- **Nacha Phase 2 deadline is 52 days away (June 22, 2026).** IMP-101 (ACH fraud monitoring policy doc) is marked critical but still proposed and unwritten. This is a compliance obligation, not optional.
- **The compliance track has a coherent operator trust stack** now defined across R-027 → R-028 → R-007 → R-007b → R-045. The proposals form a sequential implementation ladder, but the most impactful items (IMP-085 `payouts_enabled` check, IMP-072/073/074 PLS gate) are still proposed. No single implementation PR has been cut from this track.
- **Two orphaned research docs recovered:** R-051 (IMR-LLM multi-robot planning, 2026-04-11) and R-053 MCP skills/plugins (2026-04-16, duplicate ID collision). R-051 contains actionable architectural insights for v2.0 multi-robot compound tasks. IMP-129 already tracks the R-053 ID collision.
- **R-047 (x402 / Stripe MPP analysis) is stale** — fully answered by the two R-053 documents. Mark stale and close.
- **Two new research directions** opened by recent code commits: ground robot survey deliverable standards (GROUND_DELIVERY_SCHEMA merged) and multi-robot compound task scheduling (IMR-LLM pattern from R-051).

---

## 1. Per-Topic Quality Critique

### R-027 — Operator Identity Verification (2026-04-12)
**Quality: High.** Correctly established the three-tier verification design (Stripe KYC → COI + FAA → Middesk KYB). Key finding: `OperatorProfile.stripe_account_id` existed but was never used as a payout gate. Proposals IMP-064–067 are well-scoped.  
**Concern:** IMP-064 (add `stripe_account_id` to activate gate) was noted as implemented in R-028's codebase assessment ("IMP-064 implemented — good") but the original IMP-064 status still shows `proposed`. Needs verification — is IMP-064 implemented or just the field exists?  
**Action:** Verify IMP-064 status in codebase before next code review session.

### R-007 — Electronic Survey Seal/Stamp Regulations (2026-04-13)
**Quality: High.** Definitive state-by-state breakdown with the critical PKI-vs-DocuSign distinction. Table form is clean and actionable.  
**Concern:** Proposals IMP-068–070 target the delivery schema and operator onboarding. Neither has been implemented. IMP-068 (`pls_seal_format` field) is a prerequisite for IMP-079 (`pls_required` on task specs) — the implementation order is: IMP-068 → IMP-072/079 → IMP-073/078.  
**Action:** Bundle IMP-068 + IMP-072/079 as the "PLS compliance round 1" PR.

### R-007b — NC Drone Mapping Ruling (2026-04-14)
**Quality: High.** Case confirmed correct; data collector model established as valid. Three material codebase gaps identified.  
**Concern:** The `verify_operator()` task-type unawareness (IMP-065) is the most operationally disruptive gap — non-topo operators are blocked by PLS requirements they don't have. This may be causing false negatives in the current demo that reduce operator count appearing "compliant."  
**Action:** IMP-065 (`NOT_REQUIRED` for task-irrelevant docs) should be the first operator compliance PR since it's small and fixes incorrect behavior.

### R-045 — Platform Intermediary Liability (2026-04-15)
**Quality: High.** Clear no-platform-enforcement precedent found; NY outlier identified; Zillow model articulated. IMP-080 (Terms of Service) and IMP-078 (PLS declaration in bid) are both high priority.  
**Concern:** IMP-080 (ToS update) is "critical" priority but is purely a legal/documentation task — it doesn't require code. This should be the easiest item on the entire compliance track to complete.  
**Action:** IMP-080 ToS update can be drafted without any code changes. Do this sprint.

### R-028 — Stripe Connect KYC (2026-04-16)
**Quality: High.** Three focused proposals. IMP-085 is a 5-line fix that closes a production-blocking gap.  
**Concern:** `activate()` not checking `payouts_enabled` means operators with stalled Stripe onboarding can be deployed and win tasks. This is a live risk in the demo.  
**Action:** IMP-085 is the single highest-impact/lowest-effort fix in the entire backlog at this moment. ~5 lines. High priority.

### R-042 — ACH Fraud Patterns (2026-04-21)
**Quality: High.** Identified platform R10 loss exposure, Nacha Phase 2 deadline, and specific code-level gaps with line numbers.  
**Critical finding: IMP-099 and IMP-101 are time-sensitive.** IMP-099 (hold operator transfer until delivery) prevents real financial loss. IMP-101 (Nacha policy doc) has a hard June 22, 2026 deadline — 52 days from today.  
**Action:** IMP-101 is a documentation task that must be done before June 22. Schedule as top priority.

### R-008 — ACORD 25 COI Extraction (2026-04-22)
**Quality: High.** Identified COI ParseAPI as the right integration; implementation path is clear (Tier 1 → Tier 2 → Tier 3).  
**Concern:** The current gap (every COI marked VERIFIED with zero validation) means zero insurance coverage checking is happening. A $100K CGL policy passes the same as a $5M one. An expired COI passes. This is a trust-signal failure.  
**Action:** IMP-107 (expiration auto-detection) is the smallest-effort highest-safety fix. Add `expires_at` extraction from PDF as Phase 1 before the full ParseAPI integration.

### R-010 — DOT QA Checklists (2026-04-23)
**Quality: High.** Four clearly-specified proposals with JSON Schema examples.  
**Concern:** IMP-120 (ASPRS RMSEz threshold validation) is described as "the highest-impact single change in the QA layer." It converts a check from "did the operator claim accuracy?" to "does the claimed accuracy meet the spec?" This is a significant quality improvement but requires no new external APIs.  
**Action:** IMP-119 + IMP-120 can be implemented together as a single PR touching delivery_schemas.py and deliverable_qa.py.

---

## 2. Orphaned Doc Analysis

### R-051: IMR-LLM Multi-Robot Task Planning (2026-04-11)
**Not yet reviewed in a meta run.** Key findings:  
- LLMs fail at direct scheduling for >3 robots / >10 operations (conflicts, deadlocks)
- The right pattern: LLM decomposes task into formal graph → deterministic FIFO solver finds schedule
- "Disjunctive graph" formalization handles resource conflicts and sequential constraints correctly
- Maps directly to v2.0 compound tasks (aerial LiDAR + GPR + progress monitoring for same project)

**Architectural implication for YAK v2.0:** The `score_bids()` function handles single-robot matching. For compound multi-robot tasks, we need: (1) LLM decomposes buyer RFP into operation set, (2) assign operators per operation type, (3) disjunctive graph solver generates feasible sequencing. This is speculative for now but IMP-139 tracks it as a v2.0 investigation item.

**Proposals extracted:** IMP-139 (see backlog appendix below).

### R-053 MCP Skills/Plugins (2026-04-16) — Duplicate ID
**Not yet reviewed in a meta run.** This doc covers the MCP protocol spec (2025-03-26), Skills in Claude Code, Plugins architecture, and an integration recommendation for YAK (hosted HTTP MCP + Claude Code plugin).  
**Key finding:** Deferred tool loading (ToolSearch, January 2026) reduces MCP tool context from ~77K tokens to ~8.7K tokens — highly relevant to our 42-tool server. The integration recommendation (remote HTTP MCP + Plugin bundling) is actionable for v1.5.  
**ID collision:** This is the file flagged by IMP-129. Action: rename to R-055 and add roadmap entry. The Stripe MPP doc retains R-053.

---

## 3. Cross-Module Patterns

### Pattern A: Operator Trust Stack (Compliance Track)
**Topics:** R-027 → R-028 → R-007 → R-007b → R-045  

These five topics define the full operator trust lifecycle:
```
Activation gate: stripe_account_id set (IMP-064) + payouts_enabled=True (IMP-085)
     ↓
Document compliance: task-type-aware verify_operator() (IMP-065)
     ↓
Survey task gate: pls_required flag (IMP-072/079) + PLS role declaration (IMP-073/075)
     ↓
Bid submission: PLS in responsible charge declaration (IMP-078)
     ↓
Platform terms: ToS licensing disclaimer (IMP-080)
     ↓
Delivery: pls_seal_format validation (IMP-068) + state cross-check (IMP-069)
```

**Current state:** None of the above has been implemented since R-027 was researched. The entire operator trust stack exists only as proposals.  
**Recommended sequencing:**
1. IMP-085 (5 lines, blocks live payout gap) — this week
2. IMP-065 (small, fixes false negatives for non-topo operators) — this week
3. IMP-080 (ToS update, documentation only) — this week
4. IMP-072/079 + IMP-073 (PLS gate on bid submission) — next sprint
5. IMP-068/070 (seal format in delivery schema) — next sprint

### Pattern B: Deliverable QA Stack
**Topics:** R-009 → R-010 → [queued: R-011 ortho/DEM, R-009a PDAL packaging]

The QA layer is mostly structural (4-level system implemented) but the level-2 checks are weak:
- ✅ Schema validation exists (Level 1)
- ⚠️ ASPRS accuracy check exists but doesn't validate against threshold (IMP-120)
- ⚠️ DOT-specific density thresholds not wired (IMP-118)
- ❌ Class 0 check missing (IMP-119)
- ❌ Swath Δz check missing (IMP-121)
- ❌ PDAL density computation still blocked (R-009a)

**Recommended sequencing:** IMP-119 + IMP-120 together (no new dependencies). Then IMP-118 (adds `dot_state` routing). Then IMP-121 (swath). Then R-009a (PDAL packaging research for IMP-005).

### Pattern C: ACH / Payment Safety
**Topics:** R-042 → [queued: R-054 Nacha SEC codes]

The payment safety track has a time-critical compliance item (IMP-101, June 22 deadline) and a financial risk item (IMP-099, operator transfer hold). Both are in `worker/src/index.js`.  
**R-054** (Nacha WEB vs CCD SEC code for B2B construction buyers) is unblocked and should run before the Nacha Phase 2 deadline to ensure the policy doc (IMP-101) correctly addresses which return code set applies.

### Pattern D: Market Intelligence (Biggest Gap)
**No topics completed in this track.** R-019 (competitive landscape), R-020 (Michigan market sizing), and R-021 (FAA Part 107 operator density) are all still queued. The entire product strategy rests on unverified assumptions about:
- Competitor feature gaps (are we differentiated?)
- Market size (does enough construction survey spend exist in Michigan?)
- Operator supply (are there enough Part 107 operators near target sites?)

This is the most alarming gap. Every compliance/QA improvement is worthless if the market doesn't exist or is already served.

---

## 4. Contradictions and Inconsistencies

### Contradiction 1: IMP-064 implementation status unclear
R-028 says "IMP-064 implemented — good" when assessing the codebase (noting `OperatorProfile.stripe_account_id` exists). But the backlog still shows IMP-064 as `proposed`. Either R-028 was wrong (the field exists but the gate logic wasn't added) or the backlog is stale. Verify before merging the IMP-085 fix.

### Contradiction 2: R-047 (x402 + Cloudflare Workers) vs. R-053_stripe_machine_payments_protocol.md
R-047 was queued to research "x402 protocol + Cloudflare Workers Agents SDK — agent payment evaluation." The R-053_stripe_machine_payments_protocol.md (orphaned, 2026-04-12) covers exactly this: x402, MPP, ACP, Cloudflare Workers integration, and a clear "don't adopt now" recommendation. R-047's key questions are answered. Mark R-047 as stale.

### Contradiction 3: IMP-099 vs. existing delivery confirmation flow
IMP-099 proposes holding operator ACH transfer until "delivery record is confirmed in KV." But the audit trail in SQLite (not KV) is the authoritative delivery record. The fix description mentions KV, but `confirm_delivery()` in `engine.py` writes to SQLite via `SyncTaskStore`. The implementation should check SQLite delivery status, not KV. Minor clarification needed when implementing.

### Contradiction 4: R-040 "do not conduct before 2026-05-01" — today is 2026-05-01
The embargo has lifted. R-040 (PayRam production reliability audit) was spawned 2026-04-03 and was waiting for 30 days to let the service stabilize. It should now be elevated to the active queue.

---

## 5. Priority Re-Ranking

### Immediate Actions (< 1 week, not research)
- **IMP-085** (payouts_enabled check in activate) — ~5 lines, closes live payout gap
- **IMP-065** (task-type aware verify_operator) — closes false-negative compliance gate
- **IMP-080** (ToS licensing disclaimer) — documentation only, highest legal urgency
- **IMP-101** (Nacha Phase 2 policy doc) — June 22 deadline (52 days), documentation task

### Research Queue Re-Ranked

**Elevated to critical:**
1. **R-019** (Competitive landscape) — biggest unvalidated assumption; market intelligence gap
2. **R-040** (PayRam reliability audit) — date embargo lifted today; payment architecture decision pending

**Elevated to high:**
3. **R-020** (Michigan market sizing) — TAM validation needed for pitch/investor readiness
4. **R-049** (PLS subcontract model) — needed before IMP-073/078 can be implemented; FlyGuys/Aerotas contract structure
5. **R-054** (Nacha SEC code for B2B) — needed before IMP-101 policy doc is final; easy 1-session topic

**Retained high:**
6. **R-009a** (PDAL packaging) — blocks IMP-005 (production-grade density checks)
7. **R-012** (Construction escrow) — payment mechanics benchmark; feeds v1.5 design
8. **R-050** (Stripe account.updated webhook) — needed for IMP-087 (auto-suspend OFAC-flagged operators)

**Retained medium:**
9. **R-038** (validBefore window for commit-on-hire EIP-3009) — still relevant, medium urgency
10. **R-044** (WalletConnect v2 mobile) — mobile payment UX gap
11. **R-032** (Route geocoding for DOT corridor RFPs) — medium, no hard dependency
12. **R-033** (GEOID18 vs NAVD88 vertical datum) — medium, TxDOT projects only

**Downgraded or stale:**
- **R-047** → stale (answered by R-053_stripe_machine_payments_protocol.md)
- **R-006b/c/d** → remain low (entity KYB via Middesk is the right path, per R-027)
- **R-036** (Flashbots Protect) → remains low (EIP-3009 eliminates primary MEV vector)
- **R-043** (ZK proofs) → remains low (v1.5 pre-research, not blocking)
- **R-023** (MCP discovery patterns) → partially answered by R-055 (MCP skills/plugins)

---

## 6. New Research Topics Spawned

### R-055: MCP Skills/Plugins Integration for YAK (Renamed from duplicate R-053)
The R-053_mcp_skills_plugins_agent_integration.md doc covers MCP spec 2025-03-26, Skills, Plugins, and a hosted HTTP + plugin distribution recommendation. This needs a proper roadmap entry at R-055.

### R-056: Ground Robot Survey Deliverable Standards
Commit `97ce983` added `GROUND_DELIVERY_SCHEMA` and `ground_robot` equipment type. YAK can now route ground robot tasks. Research gap: what quality standards apply to ground-based survey deliverables (terrestrial LiDAR, mobile LiDAR scanning, ground penetrating radar with position)? Do ASPRS, USGS, or DOT standards have ground-robot-specific tiers?  
**Key questions:** (1) Mobile LiDAR accuracy standards — ASPRS vs. RICS vs. DOT? (2) Is swath Δz applicable to mobile scans? (3) What is the typical GSD/accuracy for ground-based survey work vs aerial?

### R-057: Multi-Robot Compound Task Architecture (Building on R-051)
R-051 showed that LLMs fail at direct multi-robot scheduling for >3 robots. The disjunctive graph + FIFO solver pattern is the right architecture for YAK v2.0 compound tasks (aerial LiDAR + GPR + progress monitoring in one project scope). This is a speculative v2.0 topic but the architectural pattern is clear enough to prototype now.  
**Key questions:** (1) How does YAK's `score_bids()` extend to compound tasks with operator-type constraints? (2) What is the right graph formalism for aerial-ground sequential dependencies? (3) Can the LLM correctly decompose a construction RFP into an operation set with precedence constraints?

---

## 7. Code Commit Analysis (Since R-META-001)

Reviewing the 28 commits since 2026-04-09:

**Feature commits raising new research questions:**

| Commit | Change | Research implication |
|--------|--------|---------------------|
| `97ce983` | Add GROUND_DELIVERY_SCHEMA + ground_robot type | R-056: what standards apply? |
| `a07544b` | Separate platform vs sensor equipment in registration | No gap — sensible architecture |
| `39d11e6` | Release busy state on completion + `auction_get_robot_status` | Watchdog gap: what if robot crashes? No timeout. R-058 candidate? |
| `5edcf60` | MCPRobotAdapter: recover from remote MCP session invalidation | Intermittent connectivity — right fix; no new research needed |
| `ae72892` | Reject unknown equipment_type (no silent fallback) | Good defensive coding; no research gap |
| `ca66a68` | NPC ROBOT teleop preset (10th preset) | Real-money teleop now live; IMP-110 (firmware auth) is more urgent |
| `4f4dd5f` | Generalize site deploy script + title smoke test | IMP-135 (sed -i bug) now has a partial fix context |

**Docs-sync commits (IMP-127 through IMP-138):** These are all trivial code quality items (stale comments, dead code, missing env vars, CI lint issues). High volume, low effort, should be bundled.

**Key observation:** The majority of recent work is docs-sync + code audit. The last real feature commit was `97ce983` (ground robot schema). No compliance improvements have been implemented despite 8 research topics pointing directly at compliance gaps.

---

## 8. Recommendations for Next 7 Topics

In priority order:

1. **R-019** — Competitive landscape (DroneBase, Zeitview, Skydio, DroneDeploy). *Critical; market intelligence gap.*
2. **R-040** — PayRam production reliability audit. *Date embargo lifted today; payment architecture decision pending.*
3. **R-054** — Nacha SEC code (WEB vs CCD). *Quick 1-session topic; supports IMP-101 policy doc.*
4. **R-020** — Michigan construction survey market sizing (2026). *TAM validation; investor-readiness.*
5. **R-049** — PLS subcontract model (FlyGuys/Aerotas agreement structure). *Blocks IMP-073/IMP-078.*
6. **R-055** — MCP skills/plugins integration for YAK (rename + roadmap entry for existing doc). *Already complete, just needs tracking.*
7. **R-META-003** — Next weekly synthesis (after ~7 more completions).

---

## 9. Summary Metrics

| Metric | Run 1 (2026-04-09) | Run 2 (2026-05-01) |
|--------|--------|--------|
| Total topics complete | 8 | 16 + 2 orphans |
| Backlog proposals total | ~75 | 138 (44 implemented, 75 proposed, 18 deferred, 1 rejected) |
| Topics queued | ~30 | ~35 (queue growing due to spawns) |
| Critical topics queued | 0 | 2 (R-019, R-040) |
| Research skew | Payment/crypto heavy | Compliance/legal heavy |
| Biggest gap | Operator verification | Market intelligence |
| Time-critical item | None | IMP-101 (June 22, 2026) |

---

## Appendix: New Improvement Proposals

### IMP-139: Prototype disjunctive graph task decomposition for compound survey tasks (v2.0 planning item)

**Module:** M5_auction_engine  
**Effort:** large  
**Priority:** low (v2.0)  
**Description:** Based on R-051 (IMR-LLM paper, ICRA 2026), the right architecture for compound multi-robot survey tasks is: (1) LLM decomposes buyer RFP into an operation set with type, workpiece (survey area), required equipment, and precedence constraints, (2) construct a disjunctive graph representing resource conflicts (same area, same equipment type, same time), (3) deterministic FIFO solver schedules the feasible execution order. This is a v2.0 architectural investment. Investigation item: prototype the LLM decomposition step for a compound task (aerial LiDAR + GPR + progress monitoring on a single 12-acre site) using the existing `rfp_processor.py` as the first stage.  
**Evidence:** docs/research/automated/R-051_imr_llm_multi_robot_task_planning.md  
**Research source:** R-051  
**Proposed date:** 2026-05-01

---

*Synthesis by automated daily research agent. No code files modified.*
