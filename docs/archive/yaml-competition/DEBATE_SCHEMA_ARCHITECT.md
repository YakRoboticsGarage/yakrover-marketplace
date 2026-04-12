# Schema Architect Proposal: YAML DSL Top-Level Ontology

**Author:** Systems Architect (Agent 1 of 3)
**Date:** 2026-03-29
**Input:** PLAN_YAML_DSL_SYNTHESIS.md, ROADMAP_v4.md, DECISIONS.md, SYNTHESIS_JTBD_WEDGE_PROPOSAL.md

---

## Design Principles

1. **Entities are nouns, not documents.** The YAML models *things* (personas, robots, decisions, phases) -- not the research files they came from. Source provenance is metadata, not structure.
2. **IDs are the spine.** Every entity gets a typed ID (`PD-4`, `persona:marco`, `phase:v1.5`). Cross-references use these IDs, never prose descriptions. This makes the file machine-queryable.
3. **Two-level rule.** Root keys are domains. Second level is always a list of typed entities or a map of named scalars. No deeper nesting in the skeleton -- depth lives in the fill phase.
4. **YAML is the index, not the encyclopedia.** Long-form rationale stays in markdown docs. The YAML links to them via `source:` fields. If a value exceeds ~3 lines, it belongs in a doc, not inline.

---

## Proposed Root Keys (8 domains)

```yaml
# ============================================================
# yakrover-marketplace.yaml — Ontological Map of the Product
# ============================================================

meta:
  name: "Robot Task Auction Marketplace"
  version: "1.0"                          # schema version, not product version
  updated: "2026-03-29"
  sources:                                # provenance index
    - path: docs/DECISIONS.md
    - path: docs/ROADMAP_v4.md
    - path: docs/research/SYNTHESIS_JTBD_WEDGE_PROPOSAL.md
    # ... all 30+ source docs listed here

# 1. VISION — north star, thesis, positioning
vision:
  thesis: "AI agents post tasks, physical robots bid, winners get paid"
  wedge_market: "construction-site-surveying"  # from JTBD analysis
  moat: "network-effects + sensor-to-deliverable AI pipeline"
  assumptions:                            # falsifiable claims
    - id: assumption:time-over-cost
      claim: "Buyer pain is scheduling speed, not unit cost"
      evidence: [source:SYNTHESIS_JTBD_WEDGE_PROPOSAL]

# 2. PERSONAS — every named user, including agents
personas:
  - id: persona:marco
    name: "Marco Reyes"
    role: buyer
    phase: phase:v1.5
    jtbd:                                 # jobs-to-be-done list
      - situation: "3 bids overlap in spring letting season"
        motivation: "get survey data before Thursday deadline"
        outcome: "accurate earthwork quantities in HeavyBid"
  - id: persona:sarah
    role: buyer
    phase: phase:v1.0
  - id: persona:claude-agent
    role: agent
    phase: phase:v1.0

# 3. DECISIONS — canonical, mirrors DECISIONS.md structure
decisions:
  - id: PD-1
    domain: product                       # product | technical | foundational | privacy | lunar
    title: "Auction Mechanism: RFQ"
    summary: "Open indefinitely, agent controls close"
    source: docs/DECISIONS.md#PD-1
    impacts: [component:auction-engine]   # what this decision constrains
  - id: FD-1
    domain: foundational
    title: "Settlement Abstraction"
    impacts: [component:payment, component:escrow]

# 4. ARCHITECTURE — components, interfaces, tech choices
architecture:
  components:
    - id: component:auction-engine
      path: auction/engine.py
      depends_on: [component:store, component:signing]
      decisions: [PD-1, PD-2, PD-3]      # back-references
    - id: component:payment
      path: auction/stripe_service.py
      decisions: [PD-4, TC-2, FD-1]
    - id: component:escrow
      path: contracts/RobotTaskEscrow.sol
      decisions: [FD-4, FD-5]
  protocols:
    - id: protocol:erc-8004
      role: "robot identity + bid signing"
    - id: protocol:x402
      role: "USDC payment rail (v1.5)"

# 5. MARKET — competitive landscape, TAM, partnerships
market:
  tam: "$8B/yr US construction surveying"
  wedge_tam: "$1.2B/yr pre-bid surveys"
  verticals:                              # ordered by score
    - id: vertical:construction
      score: 4.25
      phase: phase:v1.5
    - id: vertical:mining
      score: 3.95
      phase: phase:v2.5
    - id: vertical:infrastructure
      score: 3.65
      phase: phase:v3.0

# 6. LEGAL — contracts, bonds, compliance, disputes
legal:
  contract_model: "platform-mediated, no direct buyer-operator privity"
  payment_bonds:
    required_above: "$35K task value"
    source: docs/research/RESEARCH_PAYMENT_BOND_VERIFICATION.md
  dispute_resolution:
    v1: "agent self-verifies (PD-5)"
    v2: "oracle-assisted verification"
  compliance:
    - jurisdiction: US
      constraints: ["state surveyor licensing", "FAA Part 107 for drones"]

# 7. ROADMAP — phases, milestones, persona-phase mapping
roadmap:
  phases:
    - id: phase:v1.0
      status: built
      label: "Warehouse + Fiat"
      personas: [persona:sarah]
      stats: { tests: 151, mcp_tools: 15, loc: 11400 }
    - id: phase:v1.5
      status: next
      label: "Crypto Rail + Construction Wedge"
      personas: [persona:marco]
      decisions: [FD-1, FD-4, FD-5, PP-2]
    - id: phase:v4.0
      status: future
      label: "Lunar Operations"
      personas: [persona:kenji]

# 8. GOVERNANCE — safety, mediation, agent constraints
governance:
  agent_constraints:
    - "Agent may not override operator pricing"
    - "Agent must verify delivery before releasing payment"
  safety:
    autonomy_gaps:
      source: docs/research/ANALYSIS_AUTONOMOUS_EXECUTION_GAPS.md
    sensor_requirements:
      source: docs/research/RESEARCH_ROBOTS_AND_SENSORS.md
  constitutional_rules:                   # hard limits, never relaxed
    - "Wallet balances must never go negative"
    - "Bids are signed and non-repudiable from day one (PD-3)"
```

---

## Cross-Reference Design

All cross-references use **typed ID strings**. The format is `domain:slug` (e.g., `persona:marco`, `component:payment`, `phase:v1.5`). Decisions use their existing IDs (`PD-1`, `FD-4`) since those are already canonical in DECISIONS.md.

References appear as:
- **Single:** `phase: phase:v1.5`
- **List:** `decisions: [PD-1, PD-2, FD-1]`
- **Source link:** `source: docs/research/RESEARCH_PAYMENT_BOND_VERIFICATION.md`

This means a tool can answer "what does PD-4 affect?" by scanning all `decisions:` arrays, or "what ships in v1.5?" by scanning all `phase:` fields.

## What Stays Outside the YAML

| In YAML | In Markdown (linked via `source:`) |
|---------|-------------------------------------|
| Entity ID, name, 1-line summary | Full rationale, research methodology |
| Cross-references to other entities | Narrative user journeys |
| Quantitative facts (TAM, scores) | Qualitative analysis, interview notes |
| Status, phase assignment | Detailed implementation specs |
| Constitutional rules (1 line each) | Legal research, case law citations |

## The 8 Parallel Extraction Domains

Each domain maps 1:1 to a root key (excluding `meta`, which is structural):

| # | Domain | Root Key | Primary Sources |
|---|--------|----------|-----------------|
| 1 | Vision & Thesis | `vision` | SYNTHESIS_JTBD_WEDGE_PROPOSAL, SCOPE |
| 2 | Personas & Journeys | `personas` | USER_JOURNEY_CONSTRUCTION, ROADMAP_v4 (user map) |
| 3 | Decisions & Constraints | `decisions` | DECISIONS.md (canonical) |
| 4 | Architecture & Tech | `architecture` | CLAUDE.md, FEATURE_REQUIREMENTS_v15, source code |
| 5 | Market & Competitive | `market` | RESEARCH_WEDGE_INDUSTRY_ANALYSIS, JTBD scoring |
| 6 | Legal & Compliance | `legal` | RESEARCH_LEGAL_FRAMEWORK, RESEARCH_PAYMENT_BOND |
| 7 | Roadmap & GTM | `roadmap` | ROADMAP_v4, DEVELOPMENT_STRATEGY |
| 8 | Governance & Safety | `governance` | ANALYSIS_AUTONOMOUS_EXECUTION_GAPS, RESEARCH_ROBOTS_AND_SENSORS |

## Why This Structure

**IDs as spine, not nesting.** Deep nesting creates coupling -- if you nest personas inside phases, you can't ask "show me all buyers" without traversing every phase. Flat entity lists with ID cross-references give you both directions for free.

**8 domains = 8 agents.** Each domain has clear boundaries and a distinct set of source documents. An extraction agent for "legal" never needs to read auction engine source code. An agent for "architecture" never needs to parse TAM numbers. Clean separation means parallel execution without merge conflicts.

**Decisions are first-class.** Most product specs bury decisions in prose. Here, every decision is an addressable entity that other entities point to. This means you can trace from "why does the escrow work this way?" directly to FD-4, and from FD-4 to every component it constrains.
