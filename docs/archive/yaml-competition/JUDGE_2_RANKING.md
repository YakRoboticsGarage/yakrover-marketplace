# Judge 2 Ranking — Practical Impact Weight

**Judge:** 2 of 3
**Lens:** Practical impact on the YAML (what actually changes the file and moves the product forward)
**Date:** 2026-03-29

---

## Scoring Criteria

| Weight | Criterion |
|--------|-----------|
| 40% | Practical impact on the YAML — do the recommendations change real behavior? |
| 30% | Novelty of critique — did this surface something non-obvious? |
| 20% | Quality of YAML snippets — can you paste them in and ship? |
| 10% | thejaymo alignment — does it respect the Knowledge Object pattern? |

---

## Rankings

### 1st Place: Entry 4 — Legal & Compliance Critic (Score: 88/100)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Practical impact | 38/40 | Retainage, lien waivers, money transmission, dispute states — these are not nice-to-haves, they are legal requirements. Missing any one could halt a real deployment. |
| Novelty | 25/30 | E&O tail coverage risk, TxDOT Form 1560-CSS rejection of ACORD, and the escrow-as-money-transmitter trap are findings that require domain expertise to surface. |
| YAML snippets | 15/20 | Proposed state machine additions and entity structures are clear but not copy-paste ready. |
| thejaymo | 10/10 | Treats legal compliance as enforceable states rather than decorative badges — exactly the "active reasoning artifact" ethos. |

### 2nd Place: Entry 2 — Technical Architect (Score: 84/100)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Practical impact | 36/40 | MCP tool schemas, state machine gaps, and refund semantics are blocking issues for any developer trying to build from this YAML. The re_pooled/expired state omission is a real bug. |
| Novelty | 24/30 | Settlement refund semantics for DTN bundles (you cannot claw back a payment in transit to the Moon) is the single most creative finding across all entries. |
| YAML snippets | 16/20 | Clear fix descriptions with field names. Could be more concrete with actual YAML blocks. |
| thejaymo | 8/10 | Knowledge Object pattern critique (typed relationships, composability) is on-point but brief. |

### 3rd Place: Entry 1 — Strategy Critic (Score: 82/100)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Practical impact | 34/40 | The validation_register concept is the single highest-leverage addition proposed by any entry — it turns a static plan into a learning system. Competitive moats section is immediately useful. |
| Novelty | 22/30 | Lunar business model gap (NASA is cost-plus, not reverse-auction) is sharp. But the demo-YAML mismatch observation overlaps heavily with entries 2 and 3. |
| YAML snippets | 18/20 | Best snippets of all five entries. The validation_register, competitive_moats, and lunar_business_model blocks are copy-paste ready with real experiment designs. |
| thejaymo | 8/10 | talisman_metadata block is a direct, well-formed application of the pattern. |

### 4th Place: Entry 3 — UX Critic (Score: 76/100)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Practical impact | 30/40 | Journey parity for operators and agents is valid but additive (more YAML) rather than corrective (fixing wrong YAML). Feedback integration is process improvement, not structural. |
| Novelty | 22/30 | Manual-flagged tasks as a first-class concept is the standout find. The controller persona gap is real. Agent spending limits as a policy node is practical. |
| YAML snippets | 14/20 | Recommendations are directional ("add a section") rather than concrete YAML. No paste-ready blocks. |
| thejaymo | 10/10 | Directly invokes the "conceptual warnings, limits, or risks" principle for agent failure modes. |

### 5th Place: Entry 5 — Ontology Purist (Score: 74/100)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Practical impact | 26/40 | ID normalization and type declarations improve machine readability but do not change product behavior. The fixes are valuable for tooling, not for users or operators. |
| Novelty | 26/30 | Highest novelty score. The redundancy audit (payment split in 3 places, scoring weights in 2), the ghost reference inventory (F-1 through F-12), and the "partial adoption is worse than none" argument on gravity_effect are all unique and precise. |
| YAML snippets | 14/20 | Priority-ordered fix list is clear but provides no actual YAML. |
| thejaymo | 8/10 | Best diagnosis of the thejaymo delta (4 of 8 recommendations adopted), but the fixes proposed are schema hygiene, not Knowledge Object enrichment. |

---

## Unique Gems Per Entry

### Entry 1 — Strategy Critic
- **validation_register with confidence_delta**: No other entry proposed a mechanism for the YAML to update its own confidence scores based on experiment outcomes. This is the difference between a plan and a learning system.
- **Lunar business model gap**: Only entry to note that NASA procurement (cost-plus, firm-fixed-price) has no analog to reverse auctions, making the lunar narrative a sensor story but not a business story.

### Entry 2 — Technical Architect
- **DTN refund impossibility**: Only entry to identify that batched/DTN settlement modes make refunds physically impossible once a bundle is in transit. This is a protocol-level constraint that must shape the escrow design.
- **Multi-MCP-server topology**: Only entry to flag that yakrover-8004-mcp and the marketplace fleet server are two separate MCP endpoints requiring agent coordination, with no YAML model for this.

### Entry 3 — UX Critic
- **Manual-flagged tasks as differentiator**: The demo's "Task 3 requires a human" triage is the product's smartest moment, and only Entry 3 noticed it has zero YAML representation.
- **Controller persona missing entirely**: The person who uploads bonds, sets insurance defaults, and manages the company account has no persona entry. No other entry caught this role gap.

### Entry 4 — Legal & Compliance Critic
- **Escrow-triggers-money-transmitter**: Only entry to identify that moving from Stripe to a platform-controlled escrow account likely converts the platform into a money transmitter under state law, requiring 49+ licenses.
- **E&O tail coverage as platform risk**: Only entry to flag that claims-made E&O policies create downstream liability if an operator drops coverage after project completion. No YAML field enforces tail coverage.

### Entry 5 — Ontology Purist
- **Ghost references (F-1 through F-12)**: Only entry to identify that feature IDs in the phase listing point to nothing inside the YAML — pure ontology debt that breaks any automated traversal.
- **Redundancy inventory**: Only entry to systematically catalog where the same data lives in multiple YAML locations (payment split x3, scoring weights x2, no-competitor x2), creating drift risk.

---

## Final Notes

Entry 4 (Legal) ranks first under practical impact because its gaps carry real legal liability — missing retainage, unmodeled money transmission, absent dispute states. These are not design preferences; they are compliance obligations that block deployment. Entry 5 (Ontology) ranks last not because it is wrong — it is the most technically precise entry — but because schema normalization does not change whether the product ships legally or works correctly. The strongest overall portfolio would merge Entry 4's legal state machines, Entry 2's technical contracts, and Entry 1's validation_register into a single YAML revision.
