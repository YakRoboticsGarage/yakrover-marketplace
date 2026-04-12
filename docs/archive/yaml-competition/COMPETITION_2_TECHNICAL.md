# Competition Entry 2 — Technical Architect Critique

**Competitor:** 2 (Technical Architect)
**Date:** 2026-03-29
**Target:** `docs/research/PRODUCT_DSL.yaml` v1.1

---

## 1. MCP Tool Surface Is Incomplete

The YAML lists 15 existing MCP tools but only names 10 (`post_task`, `submit_bid`, `accept_bid`, `auction_execute`, `confirm_delivery`, `reject_delivery`, `cancel_task`, `auction_get_status`, `auction_quick_hire`, `auction_fund_wallet`). Five tools are unaccounted for. Worse, `mcp_tools.existing` lacks parameter signatures, return types, and error codes (AD-15 defines structured errors, but the YAML never specifies which `error_code` values each tool can emit). The planned tools (`plan_flight`, `validate_capture`, `file_laanc`) have descriptions but no input/output schemas. An LLM reading this file cannot generate a correct tool call.

**Fix:** Every MCP tool needs `parameters`, `returns`, and `errors` fields. The 5 missing tools must be enumerated.

## 2. State Machine Has Silent Gaps

The `task_lifecycle` state machine (line 1044) defines a `rejected` state in DM-6 and AD-8 but the YAML state machine transitions jump from `delivered` directly to `in_progress` on rejection (`poster_rejects -> request_redelivery`). This contradicts AD-8 which shows `REJECTED -> RE_POOLED -> BIDDING`. The `re_pooled` state exists in DM-6 but is absent from `state_machines.task_lifecycle.states`. Similarly, `expired` is in DM-6 but never appears in transitions.

The `award_confirmation` sub-machine (line 1076) is disconnected from the task lifecycle -- there is no explicit join point showing how `awarded` maps to `bid_accepted` or `in_progress` in the main machine. Two state machines that share a lifecycle but lack a composition model is an implementation trap.

**Fix:** Add `re_pooled` and `expired` as explicit states. Define a `compose` or `embed` relationship between the two machines.

## 3. Settlement Interface Missing `refund` Semantics

`settlement.interface.methods` lists `[settle, verify, batch_settle, refund]` but the YAML never defines `refund` behavior. FEATURE_REQUIREMENTS_v15 describes the 25/75 split with "returned to buyer on timeout/failure" for the escrow, but the settlement abstraction has no refund mode, no partial-refund logic, and no timeout-triggered refund. The `SettlementReceipt` dataclass (from F-5) has no `refund_reason` or `refunded_amount` field.

This matters because the escrow contract (F-2) has buyer-return-on-timeout logic that must flow through the settlement interface, not bypass it. If `refund` is an afterthought, Mode 3/4 (batched/DTN) refunds become impossible -- you cannot claw back a settlement that is queued in a DTN bundle already in transit to the Moon.

**Fix:** Define `refund(receipt, reason, amount) -> RefundReceipt` with explicit semantics for each mode. Add `REFUND_REQUESTED` to the settlement receipt lifecycle.

## 4. Cross-Repo Coherence Is Absent

The YAML references `yakrover-8004-mcp` zero times. The `discovery_bridge.py` component wraps ERC-8004, but the YAML never specifies which MCP tools from the yakrover-8004-mcp repo are consumed, what agent card fields the marketplace reads, or how the external repo's tool surface maps to the marketplace's auction flow. The `src/core/server.py` fleet MCP server and the external yakrover-8004-mcp server are two separate MCP endpoints that an agent must coordinate -- the YAML does not model this multi-server topology.

Similarly, the two skills (`rfp-to-robot-spec`, `rfp-to-site-recon`) live in `.claude/skills/` but the YAML `skills` section (line 1098) treats them as opaque boxes with `inputs` and `outputs`. It does not capture the reference files they load (`michigan-standards.md`, `aashto-federal-standards.md`, `robot-sensor-mapping.md`, `public-data-sources.md`), the validation scripts they invoke, or the examples directory structure. A new developer reading only the YAML would not know these skills have 7 example RFP files or that `validate_task_spec.py` exists.

**Fix:** Add a `repos` section mapping external repos to consumed interfaces. Expand `skills` with `references`, `validation_scripts`, and `examples` fields.

## 5. Execution Stack Layers Lack Interface Contracts

The 6-layer execution stack (lines 982-1042) names each layer and its automation level but never defines the data contract between layers. Layer 2 (Mission Planning) says `inputs_from: [skill:rfp_to_site_recon, skill:rfp_to_robot_spec]` -- but what specific fields? The site recon skill outputs a `boundary_polygon`, `airspace_class`, `max_altitude_agl_ft`, and `obstacles_within_1nm`. Which of those does `plan_flight` consume? What format does it expect the boundary in (WKT? GeoJSON? Both)?

Layer 4 (In-Field QC) has `checks: [point_density_vs_spec, coverage_completeness, gsd_achieved, accuracy_estimate]` but these are bare strings with no schema. What is the pass/fail threshold for `point_density_vs_spec`? The task spec's `accuracy_required.vertical_ft` from the rfp-to-robot-spec skill should flow into this check, but the YAML does not trace that data path.

**Fix:** Define `layer_contract: {inputs: [...], outputs: [...], passes_to: layer_N}` for each layer. Trace data lineage from skill output through execution stack to deliverable.

## 6. Demo-to-Architecture Drift

The live demo (`demo/index.html`) presents a search-driven UX with robot cards, live feed, and inline auction flow. The YAML `architecture` section has no `frontend` component, no mention of the demo's robot card schema (name, location, capabilities, price range, rating), and no mapping between the demo's simulated feed events and the actual MCP tool calls they represent. The demo shows `$0.25-$5.00` pricing in its schema.org markup -- far below the $0.50 minimum (TC-1) and entirely disconnected from the $1,500-$5,000 construction survey pricing in the YAML's operator economics.

**Fix:** Add a `frontend` component to `architecture.components`. Reconcile demo pricing with TC-1 and construction economics.

## 7. Constitutional Section Misses Runtime Enforcement

The `constitutional` section (line 1381) lists 8 invariants and 8 policies but provides `enforced_at` as a bare string (`wallet_ledger`, `api_layer`, `settlement_layer`, `code_review`). There is no mapping from enforcement point to actual code path, no test ID, and no CI gate. `inv:no_wallet_in_api` says `enforced_at: api_layer` but does not reference the grep-all-tool-outputs test mentioned in F-7's acceptance criteria. Invariants without automated enforcement are documentation, not guarantees.

**Fix:** Add `test_id` and `ci_gate` fields to each invariant. Link to specific test files in `auction/tests/`.

## 8. Knowledge Object Patterns Underutilized

The YAML references thejaymo.net Knowledge Object patterns in its header but barely applies them. True Knowledge Objects have: typed relationships between objects (not just `source` backlinks), versioned provenance chains (who said what, when, with what confidence), and composability (objects reference each other by stable ID with semantic predicates like `contradicts`, `supersedes`, `depends_on`). The YAML uses `source` fields as flat path references. The `bet_chain` section comes closest with `depends_on` and `enables`, but entities like `persona`, `equipment`, and `component` have no inter-object relationships beyond co-occurrence in a list.

**Fix:** Add a `relationships` block to the schema supporting typed edges: `{from: X, to: Y, type: depends_on|contradicts|implements|consumes|produces}`. This enables graph queries like "what breaks if we remove ERC-8004?"

## 9. Scoring Model Not Versioned for Vertical Expansion

The YAML defines one set of scoring weights (price 40%, SLA 25%, confidence 20%, reputation 15%) for construction and a separate lunar set. But the mining vertical (phase v2.5) and infrastructure vertical (phase v3.0) have different priorities -- bridge inspections weight certification compliance and form factor availability over price. The YAML has no `scoring_profile_per_vertical` mechanism, which means the auction engine will use construction-optimized weights for bridge inspection bids.

**Fix:** Add `scoring_profiles` keyed by vertical ID, with weight overrides and vertical-specific scoring factors (e.g., `nbi_certification_match` for infrastructure).

---

## Summary

| # | Gap | Severity | Affects |
|---|-----|----------|---------|
| 1 | MCP tools lack schemas | HIGH | Agent integration, code generation |
| 2 | State machine inconsistencies | HIGH | Implementation correctness |
| 3 | Refund semantics undefined | HIGH | Settlement, escrow, DTN |
| 4 | Cross-repo coherence absent | MEDIUM | Multi-repo development |
| 5 | Execution stack lacks contracts | MEDIUM | Skill-to-robot data flow |
| 6 | Demo-architecture drift | LOW | Product consistency |
| 7 | Invariants lack enforcement links | MEDIUM | CI/CD, runtime safety |
| 8 | Knowledge Object patterns shallow | LOW | Graph queries, impact analysis |
| 9 | Scoring not vertical-aware | MEDIUM | Market expansion |
