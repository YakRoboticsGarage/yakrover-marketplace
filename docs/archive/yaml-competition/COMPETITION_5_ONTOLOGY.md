# Competition Entry 5: Ontology Purist Critique

**Role:** Ontology Purist (Competitor 5 of 5)
**Date:** 2026-03-29
**Input:** PRODUCT_DSL.yaml (1509 lines), thejaymo.net Knowledge Object patterns, Architect/Strategist/Engineer debate docs

---

## Verdict

The YAML is impressively comprehensive as a human-readable document. As a machine-parseable ontology, it has **six structural defects** that prevent an LLM from reliably traversing it, and **four thejaymo patterns** that remain unapplied despite the prior analysis recommending them.

---

## 1. Schema Consistency Failures

**ID format is not uniform.** The file uses three incompatible ID schemes simultaneously: (a) typed IDs `persona:marco`, `equipment:dji_m350`; (b) bare prefixed IDs `PD-1`, `FD-4`; (c) untyped slugs `layer_0_regulatory`, `F-1`. A parser encountering `decision: PD-1` cannot determine from syntax alone whether this is a `decision:PD-1` ref or a bare string. The `features: [F-1, F-2, ...]` list on line 1245 references IDs that are never defined anywhere in the file -- they are ghost references to FEATURE_REQUIREMENTS_v15.md with no anchor in this ontology.

**`source` field is overloaded.** It appears as: a string (`source: docs/DECISIONS.md`), a list of objects (`sources: [{path: ...}]`), and a section-level attribute on container nodes (`bet_chain.source`). An agent cannot reliably extract provenance without three separate parsing strategies for the same semantic concept.

**`decision` field is sometimes a string, sometimes a list.** Compare `decision: PD-1` (line 775) with `decision: [FD-1, FD-4, TC-4]` (line 938). Same key name, two types. This is a YAML validity issue -- a strict schema cannot express "string or list of strings" cleanly, and it forces every consumer to handle both.

---

## 2. Cross-Reference Integrity

**Dangling references found:**
- `features: [F-1, F-2, ..., F-12]` in phase:v1.5 -- no `feature:` entities exist in the file.
- `skill:rfp_to_robot_spec` and `skill:rfp_to_site_recon` are referenced in journey stages (line 342) using a `skill:` prefix, but defined under `architecture.skills` with `id: skill:rfp_to_robot_spec`. The path to resolve them is `architecture.skills[?id==skill:rfp_to_robot_spec]`, which is a search, not a lookup.
- `architecture:auction_engine` and `architecture:settlement` appear as actors in journey stages, but component IDs use the `component:` prefix. The journey uses an ad hoc `architecture:` prefix that matches nothing.
- `equipment:dji_m350` and `equipment:spot` appear as journey actors (lines 354-356), mixing entity types with the journey's actor model (which elsewhere uses personas).

**Resolution rule is undefined.** The file declares `cross_reference_syntax: "domain:slug"` but never specifies HOW to resolve a reference. Is `persona:marco` resolved by scanning all lists for an `id` field match? By dotted path? The Engineer's debate doc proposed `$ref` with dotted paths -- this was not adopted.

---

## 3. Completeness Asymmetry

**Deeply specified:** bet_chain (7 bets with full evidence/falsification), legal (contracts, insurance, Michigan specifics, moats vs. overhead distinction), supply_side equipment catalog (9 items with detailed specs), settlement modes (4-mode matrix), state machines (2 full graphs).

**Thinly sketched:** MCP tools (`existing` is a name-only list with no input/output schemas -- the Engineer's debate doc proposed full JSON Schema for each tool, none adopted), personas Sarah/Alex/Diane/mine_surveyor/bridge_pm (one-line JTBD strings vs. Marco's rich profile), journeys B/C (outcome-only, no stages), execution stack layers (no `inputs`/`outputs` fields despite Engineer proposing them), API surface (entirely absent).

**The imbalance matters.** An LLM querying "can I bid on this task with my equipment?" cannot answer it because `mcp_tools.existing` lacks input schemas and `task_templates` (proposed by Engineer) do not exist.

---

## 4. Machine-Readability Gaps

**Untyped string values where enums are needed.** `gap_severity: high_for_remote` (line 997) vs. `gap_severity: high` (line 1006) -- is `high_for_remote` a valid enum value or a comment masquerading as data? `automation_level: none | partial | full` is implied but never declared. `status: built | next | future` likewise. Without a `types:` block declaring closed enums, every value is an open string.

**Nested quantitative data trapped in prose strings.** `tam_usd: "$8B/yr US construction surveying"` is a string containing a number, a unit, a time period, and a geographic scope. An agent cannot compare TAM values or do arithmetic. Same for `price_usd: "~$13,600-$14,800 (drone only)"` -- range + qualifier in a string.

**The glossary is a flat string map, not a structured map.** Each term maps to a single string. The thejaymo pattern uses `definition` + `note` (distinguishing borrowed vs. coined terms, scope of usage). Our glossary cannot be filtered or enriched.

---

## 5. Thejaymo Delta -- What Is Still Missing

The prior analysis (ANALYSIS_YAML_REFERENCE_THEJAYMO.md) recommended 8 changes. Four were adopted: `usage` block, `executive_summary`, `glossary`, `mantra`/`essence`. Four were not:

1. **`gravity_effect` is only on 4 of 7 bets.** `bet:construction_wedge_works`, `bet:mining_expansion`, `bet:infra_expansion` lack it. The pattern was supposed to be universal per the analysis -- "add `gravity_effect` to each bet." Partial adoption is worse than none because a consumer cannot rely on the field's presence.

2. **`implied_critiques` on unknowns.** Recommendation 7 said to add what each unknown implies about the current design. Not adopted. Each unknown has `mitigation` but not what it critiques -- a model cannot reason about design pressure.

3. **Glossary lacks `note` field.** The analysis specifically recommended `definition` + `note` per thejaymo's pattern. The glossary uses bare strings, losing the borrowed-vs-coined distinction and scope metadata.

4. **No `talisman_taxonomy` / self-classification of sections.** thejaymo classifies each object as Analytical, Reference, Procedural, or Narrative. Our file has one `usage.type` for the whole document but does not classify individual sections. The `architecture` section is a Reference; `bet_chain` is Analytical; `journeys` is Narrative. Classifying them would let an agent load only relevant sections.

---

## 6. Redundancy and Overlap

- **Payment split appears three times:** `architecture.settlement.payment_split` (line 967), `pol:payment_split` (line 1441), and implicitly in the journey outcome (line 358: "$3,600 total"). Which is canonical?
- **Scoring weights appear twice:** `cap:filter_then_score.scoring_weights` (line 790) and `pol:scoring_weights` (line 1429). Same data, different locations.
- **Wallet-never-negative rule appears twice:** `inv:wallet_non_negative` (line 1384) and in the glossary/CLAUDE.md ecosystem. The invariant is correct to live in `constitutional`, but the duplication with CLAUDE.md means drift risk.
- **`no_direct_competitor: true`** (line 90) and `direct_competitors: none` (line 409) say the same thing in two sections.
- **Sensor data lives in both `supply_side.equipment_catalog`** (sensor items like `equipment:zenmuse_l2`) and `transfer_map.sensors_that_transfer` (sensor names like "LiDAR"). The transfer map should reference equipment IDs, not prose names.

---

## 7. Missing Ontological Relationships

- **Equipment-to-task matching chain is broken.** The Engineer proposed `task -> sensor -> equipment -> operator`. The file has equipment and sensors but no `task_templates` entity, no `operator` entity (personas are buyers, not operators -- `persona:alex` is the only operator and has no equipment field), and no explicit sensor-to-equipment compatibility links (only `compatible_platforms` on two sensors).
- **Decisions have no `impacts` backlinks.** The Architect proposed `impacts: [component:auction-engine]` on each decision. Decisions are referenced FROM components (`decisions: [PD-1, PD-2]`) but not the reverse. An agent asking "what does FD-4 affect?" must scan the entire file.
- **Unknowns do not link to bets they threaten.** `unknown:flight_planning_api` blocks launch, but which bet does it threaten? Probably `bet:agent_mediation_adds_value`, but this relationship is implicit.
- **Phases do not link to unknowns they must resolve.** The Strategist proposed `unknowns_resolved` per phase. The file has `resolve_by: phase:v2.0` on unknowns but no reverse index on phases.

---

## 8. Concrete Fixes (Priority Order)

1. **Normalize all IDs to `domain:slug` format.** Convert `PD-1` to `decision:PD-1`, `F-1` to `feature:F-1`, `layer_0_regulatory` to `layer:0_regulatory`. One syntax, one resolver.
2. **Add a `types:` block** declaring all enums (`status`, `gap_severity`, `automation_level`, `role`, `strategic_function`) as closed sets.
3. **Make `decision` always a list.** `decisions: [PD-1]` not `decision: PD-1`. One key name, one type.
4. **Make `source` always a list of `{path, section?}` objects.** Kill the string variant.
5. **Add `gravity_effect` to all 7 bets, or remove it from the schema.** Partial fields are parser traps.
6. **Add `threatens: [bet:X]` to each unknown** and `resolves: [unknown:X]` to each phase.
7. **Define feature entities** or remove the `features: [F-1, ...]` references. Ghost refs are ontology debt.
8. **Restructure glossary entries** as `{definition: ..., note: ..., borrowed: bool}` per thejaymo pattern.

---

*Ontology is not decoration. Every inconsistency in ID format, every overloaded field type, every dangling reference is a fork in the road where an LLM must guess instead of resolve. The file is 80% of the way to being machine-traversable. The last 20% is the part that matters.*
