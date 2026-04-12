# Debate: YAML Schema Critique (Strategist)

**Role:** Product Strategist
**Date:** 2026-03-29
**Responding to:** `PLAN_YAML_DSL_SYNTHESIS.md` proposed 8 domains

---

## Overall Assessment

The architect's 8 domains are a reasonable taxonomy of *topics*. But a taxonomy of topics is a documentation outline, not a strategic model. The YAML DSL needs to capture the *logic* of the product -- why things depend on each other, what we're betting on, and what breaks if we're wrong. The proposed domains would produce a flat encyclopedia organized by category. We need a directed graph organized by consequence.

Three specific failures of the current 8 domains:

1. **No distinction between facts and bets.** "Construction is our wedge" and "LiDAR transfers to lunar" live in the same bucket as "Stripe handles fiat payments." One is a falsifiable bet; the other is an implementation detail. The YAML must separate these or it becomes useless for decision-making.

2. **No causal relationships between domains.** The entire product strategy is a chain of BECAUSE statements: construction wedge BECAUSE sensor overlap to lunar; RFQ auction BECAUSE global robot latency; payment bonds BECAUSE construction industry norms; agent mediation BECAUSE raw point clouds are not deliverables. The 8 domains silo these into separate boxes and the causal chain disappears.

3. **No concept of what we don't know.** The research docs are full of explicit unknowns and gap analyses (flight planning API, autonomous navigation in unstructured terrain, regulatory uncertainty around autonomous drone operations). These unknowns are not second-class citizens -- they are the highest-leverage items in the model. If we don't track them structurally, they vanish.

---

## Domain-by-Domain Critique

### 1. Vision & Thesis
**Problem:** Too vague. "North star" and "core assumptions" are different things. The north star is stable ("robots bid on physical tasks"); the assumptions are volatile ("construction is the right wedge"). Mixing them into one domain makes it impossible to tell what is load-bearing versus aspirational.

**Recommendation:** Split into `identity` (what the product IS, stable) and `bets` (what we BELIEVE, falsifiable).

### 2. User Profiles & Journeys
**Problem:** This is fine as a domain, but it buries the most strategic insight: the *handoff topology* between actors. Marco -> Claude agent -> auction engine -> robot operator -> robot -> agent verification -> Marco. The journey is a pipeline. The YAML should capture the pipeline stages, not just the personas.

**Recommendation:** Rename to `actors_and_flows`. Model actors as nodes and flows as edges. Include AI agents as first-class actors, not appendages of human users.

### 3. Product Architecture
**Problem:** Confuses logical architecture (what the product does) with implementation architecture (MCP, CLI, web). The YAML should describe product capabilities and their relationships. Implementation details belong in a separate, narrower spec.

**Recommendation:** Split into `capabilities` (what the system does, described functionally) and leave implementation to code-level docs. The YAML is a product model, not a system design doc.

### 4. Market & Competitive
**Problem:** "Landscape, affordances, partnerships, geography" is a grab bag. The competitive landscape research is clear: no direct competitor exists. That single finding matters more than a detailed matrix. What the YAML needs to capture is the *strategic positioning logic* -- why the open gap exists and what could close it.

**Recommendation:** Merge into `environment` -- external conditions (market, competitors, partners, regulation) that constrain or enable the product. Model each as a condition with a confidence level and an expiration date.

### 5. Legal & Governance
**Problem:** Scoped correctly, but missing the key strategic insight: legal structure is not a compliance checkbox, it is a *competitive moat*. The payment bond verification flow, the PE-stamped deliverables, the MCL 129.201 compliance -- these are barriers to entry that protect the wedge. The YAML should flag which legal requirements are moats versus overhead.

**Recommendation:** Keep, but add a `strategic_function` field to each legal requirement (moat, compliance, risk_mitigation, trust_building).

### 6. Technical Platform
**Problem:** "Blockchain, sensors, equipment, autonomy gaps" jams four unrelated things together. Blockchain is an implementation choice for identity/payment. Sensors are domain-specific capabilities tied to wedge selection. Equipment is supply-side inventory. Autonomy gaps are risks. These need different treatment.

**Recommendation:** Dissolve this domain. Sensors and equipment go into `supply_side`. Blockchain goes into implementation docs. Autonomy gaps go into `unknowns`.

### 7. Roadmap & GTM
**Problem:** Roadmap and GTM are different things. The roadmap is a sequence of capability unlocks. GTM is a market entry strategy (who to sell to first, through what channel, with what message). They interact but shouldn't be flattened.

**Recommendation:** Split. Roadmap becomes `sequence` (ordered phases with dependencies and gates). GTM becomes part of `environment` or gets its own `entry_strategy` key.

### 8. Constitutional Controls
**Problem:** Good instinct, wrong framing. "Safety, mediation, conflict resolution, agent governance" -- these are constraints on system behavior. But they're mixed between hard constraints (safety: a robot must not fly over people) and soft policies (mediation: disputed deliverables go to re-bid). The YAML should distinguish invariants from policies.

**Recommendation:** Rename to `constraints`. Split into `invariants` (things that must NEVER be violated, regardless of context) and `policies` (things that CAN be adjusted based on context, market, or phase).

---

## What's Missing Entirely

### A. The Bet Chain
The entire product thesis is a chain of dependent bets:

```
construction_wedge_works
  BECAUSE survey_bottleneck_is_real
  BECAUSE robot_supply_exists_in_target_geos
  BECAUSE agent_mediation_adds_value_over_booking_portal
  WHICH_ENABLES lunar_transfer
    BECAUSE sensor_stack_overlaps
    BECAUSE unstructured_terrain_workflows_transfer
    BECAUSE NASA_commercial_demand_exists
```

If `survey_bottleneck_is_real` turns out to be false, everything downstream collapses. The YAML must model this dependency chain explicitly or we lose the ability to reason about strategic risk.

### B. The Unknowns Register
The research docs are admirably honest about what is not yet known:
- No flight planning API in the MCP tool set (Gap 1, execution gaps)
- Autonomous navigation over unstructured terrain is unsolved at the required reliability
- Regulatory status of fully autonomous commercial drone ops is ambiguous
- Whether operators will adopt automated bid engines or resist
- Whether payment bond verification scales beyond Michigan

These are not footnotes. Each unknown is a risk with a severity, a mitigation plan, and a deadline by which it must be resolved or the strategy changes.

### C. The Transfer Map
The wedge-to-lunar transfer is the most important strategic claim in the entire product. But it is asserted, not modeled. Which specific sensors transfer? Which workflows transfer? Which ones DON'T? What new capabilities does lunar require that construction doesn't exercise? The YAML should have an explicit transfer matrix.

### D. Supply-Side Economics
The 8 domains are almost entirely demand-side. Where are the robot operators? What does their onboarding look like? What is their unit economics? The operator onboarding research exists (`RESEARCH_OPERATOR_ONBOARDING_CONSTRUCTION.md`) but has no domain in the schema. A marketplace fails if either side is thin. Supply deserves its own root key.

---

## Proposed Root Keys

Here is an alternative schema. 11 root keys instead of 8, organized by strategic function rather than topic category.

```yaml
# === STABLE IDENTITY ===
identity:
  # What the product IS. Changes rarely.
  # Name, one-line description, core mechanism (auction),
  # category (marketplace), non-negotiable properties.

# === FALSIFIABLE BETS ===
bets:
  # What we BELIEVE but could be wrong about.
  # Each bet has: claim, evidence_for, evidence_against,
  # confidence (0-1), depends_on (other bets),
  # falsified_by (observable condition that kills the bet),
  # last_validated date.
  #
  # Example:
  #   construction_wedge:
  #     claim: "Construction site surveying is the right first market"
  #     confidence: 0.8
  #     depends_on: [survey_bottleneck_real, robot_supply_exists]
  #     falsified_by: "No operator signs up in target geo within 90 days of launch"
  #     enables: [lunar_transfer, mining_expansion, infra_expansion]

# === UNKNOWNS ===
unknowns:
  # Things we explicitly do not know.
  # Each unknown has: question, severity (blocks_launch, degrades_experience,
  # limits_scale), mitigation_plan, resolve_by_date, owner.
  #
  # This is NOT a backlog. It is a risk register for strategic gaps.

# === ACTORS AND FLOWS ===
actors:
  # Every entity that participates: human personas, AI agents,
  # robots, operators, platform services, external systems.
  # Each actor has: role, capabilities, constraints, economic_model.

flows:
  # Named pipelines that connect actors.
  # Each flow has: trigger, stages (ordered list of actor actions),
  # happy_path, failure_modes, current_gaps.
  #
  # Example:
  #   pre_bid_survey:
  #     trigger: "Marco uploads RFP scope"
  #     stages:
  #       - actor: marco_agent
  #         action: parse_rfp_and_post_task
  #       - actor: auction_engine
  #         action: open_rfq_and_collect_bids
  #       - actor: robot_operators
  #         action: automated_bid_submission
  #       ...

# === CAPABILITIES ===
capabilities:
  # What the system can DO, described functionally.
  # Each capability has: description, required_by (which flows),
  # current_status (built, partial, missing), phase_available.
  # Implementation details are references (file paths, not inline code).

# === SUPPLY SIDE ===
supply:
  # Robot operators, equipment, sensors, geographic coverage.
  # Unit economics for operators. Onboarding requirements.
  # Fleet composition targets by phase.
  # This is the domain the architect's schema forgot entirely.

# === ENVIRONMENT ===
environment:
  # External conditions the product operates within.
  # Sub-keys: market (TAM, segments), competitors (with threat_level),
  # partners (with dependency_risk), regulation (by jurisdiction),
  # technology_landscape (emerging infra we depend on: ERC-8004, x402, MCP).
  # Each item has: status, confidence, last_checked, expires.

# === CONSTRAINTS ===
constraints:
  invariants:
    # MUST NEVER be violated. Safety, legal hard requirements,
    # cryptographic commitments. These survive across all phases.
  policies:
    # CAN be adjusted. Payment splits, scoring weights,
    # insurance minimums, approval thresholds.
    # Each policy has: current_value, rationale, adjustable_by.
  decisions:
    # References to DECISIONS.md entries (AD-X, PD-X, FD-X, etc.)
    # with their current status and any pending reconsideration.

# === SEQUENCE ===
sequence:
  # Ordered phases with explicit gates between them.
  # Each phase has: name, objective, entry_criteria, exit_criteria,
  # capabilities_unlocked, bets_validated, unknowns_resolved.
  # Gates are conditions, not dates. "Phase 2 starts when
  # 5 operators complete onboarding" not "Phase 2 starts Q3."

# === TRANSFERS ===
transfers:
  # Explicit mapping of what transfers between markets.
  # construction_to_lunar:
  #   sensors_transfer: [lidar, rtk_gps, photogrammetry, imu]
  #   sensors_new: [radiation_hardened_electronics, ...]
  #   workflows_transfer: [terrain_mapping, progress_monitoring]
  #   workflows_new: [regolith_analysis, reduced_gravity_nav]
  #   assumptions: [...]
  # construction_to_mining:
  #   ...

# === META ===
meta:
  # Schema version, last_updated, source_documents (with file paths),
  # generation_method, contributors.
```

---

## Key Design Principles for the Schema

1. **Bets are first-class objects.** Every strategic claim has an explicit confidence, dependency chain, and falsification condition. This is the single most important thing the YAML can do that documentation cannot.

2. **Unknowns are tracked, not hidden.** A missing flight planning API is not a backlog ticket -- it is a strategic blocker that determines whether the auction model works for autonomous execution. Track it at the schema level.

3. **Relationships are edges, not implied.** "Construction wedge enables lunar transfer" is not a sentence in a Vision section. It is a `depends_on` / `enables` link between two bet objects. The YAML must be traversable.

4. **Facts and beliefs are separated.** "Stripe handles fiat payments" is a fact (it either does or it doesn't). "Payment bond verification is a competitive moat" is a belief. They get different treatment, different confidence scores, and different update cadences.

5. **The supply side exists.** A marketplace YAML that only models the demand side is modeling half a marketplace. Operators, their economics, their onboarding friction, and their geographic distribution deserve a root key.

6. **Phases are gated by conditions, not dates.** The roadmap should describe what must be TRUE for the next phase to begin, not when we hope it begins. Condition-gated phases are testable; date-gated phases are wishes.

---

## What I Would Cut

- **Product Architecture as a root key.** Implementation details do not belong in a strategic YAML. Capabilities (what the system does) belong; architecture (how it does it) belongs in code and design docs.
- **Constitutional Controls as a separate domain.** This is really two things: invariants (hard safety constraints) and policies (adjustable governance rules). Neither needs its own root key -- they fit under `constraints`.
- **Market & Competitive as a standalone domain.** Competitive intelligence is important but has a shelf life of weeks. It belongs in `environment` with an expiration date, not as a permanent structural domain.

---

## Summary

The architect's 8 domains answer the question "what categories of information exist?" The strategist's 11 root keys answer the question "what is the logic of this product and where could it break?" A YAML DSL should be the latter. It should be a model you can query: "show me every bet with confidence below 0.5," "what breaks if operator onboarding takes 3x longer than expected," "which capabilities must be built before Phase 2 gate." The current 8 domains cannot answer any of those questions. The proposed schema can.
