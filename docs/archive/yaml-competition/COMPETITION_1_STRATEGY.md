# Competition Entry 1: Strategy Critic

**Competitor:** Strategy Critic (deepest strategic gaps)
**Date:** 2026-03-29
**Files reviewed:** PRODUCT_DSL.yaml, demo/index.html, ROADMAP_v4.md, USER_JOURNEY_CONSTRUCTION_v01.md, thejaymo.net Knowledge Objects, YakRoboticsGarage org repos

---

## Top 5 Improvements (ranked by impact)

### 1. The YAML has no demand-side validation mechanism -- the biggest bet is untested

The entire bet chain rests on `bet:survey_bottleneck_real` (confidence 0.85), but the YAML contains zero structure for tracking demand-side signal. No `validation_experiments` section, no customer discovery log, no conversion funnel metrics. The `falsified_by` fields are good exit criteria but there is no `validated_by` counterpart showing what positive evidence looks like at each stage. The thejaymo Knowledge Object pattern uses `gravity_effect` to steer model attention -- the PRODUCT_DSL uses it decoratively on a few bets but never on the demand gap. Add a `validation_register` that tracks experiments, results, and confidence updates over time. Without this, the YAML is a plan that cannot learn.

### 2. The demo shows a product the YAML does not describe -- the RFP-to-task decomposition flow is invisible

The demo's core flow is: upload MDOT RFP PDF, extract requirements, decompose into 3 biddable tasks (2 robot + 1 manual), verify payment bond, run parallel auctions, review awards. This is the actual product experience. But the YAML's `journeys` section describes Marco typing "I need topo for SR-89A" to Claude -- a completely different interaction model. The demo shows a web UI with steps (Upload, Extract, Verify, Bid, Review, Award). The YAML has no `interaction_modes` distinguishing agent-mediated vs. direct-web-UI vs. API. The demo also shows "47 operators online, 312 robots, 4 states" and "14,283 tasks completed this week" -- aspirational numbers with no corresponding YAML metrics target or growth model. The YAML and demo are telling two different stories.

### 3. No competitive response playbook -- Fabric/OpenMind with $20M is the existential threat

The competitive landscape lists threats but has no `response_playbook`. Fabric (ROBO token, $20M Pantera round, robot economy protocol on Base) is rated HIGH threat. If Fabric ships a marketplace frontend, they have the same chain (Base), deeper crypto-native distribution, and token incentives for operator bootstrapping. The YAML needs a `competitive_moats` section that is distinct from `legal:moats`. Legal compliance (bond verification, PLS licensing) is a moat against generic platforms but not against a well-funded competitor who can replicate it. The real moats are: (a) operator network density in specific geos, (b) construction-domain task decomposition intelligence, (c) deliverable format validation pipeline. None of these are called out as strategic moats in the YAML.

### 4. The 1M-robot / lunar path has a credibility gap the YAML acknowledges but does not close

`bet:lunar_transfer` has the lowest confidence (0.6) and `depends_on` construction + mining, but the transfer map only covers sensor and workflow transfer. It completely ignores the business model transfer. Who pays for lunar surveys? NASA contracts are cost-plus, not reverse-auction. JAXA procurement is government-to-government. The auction mechanism that works for Marco (private GC with $15K discretionary spend) has no analog in space agency procurement. The YAML needs a `lunar_business_model` section that addresses: (a) who is the buyer, (b) what procurement vehicle do they use, (c) how does a reverse auction fit into a cost-plus/firm-fixed-price regime. Without this, the lunar story is a sensor-transfer narrative, not a business-transfer narrative.

### 5. The YAML lacks a `self_description` / talisman-type block that the thejaymo pattern demands

The thejaymo Knowledge Object pattern treats documents as active reasoning artifacts with explicit `gravity_effect`, `talisman_taxonomy`, and `likely_effects` on model behavior. The PRODUCT_DSL has a `usage` block with a generic `gravity_effect` but does not classify itself as a talisman type, does not declare its likely effects on agent reasoning, and does not specify what it should NOT be used for (negative gravity). The `executive_summary.sources` list 19 documents but provides no guidance on when to defer to them vs. this file. Add a `talisman_metadata` block that declares: type (Reference + Analytical hybrid), intended effects, anti-patterns, and staleness policy.

---

## Additional Findings

**Missing from YAML, present in demo:**
- The demo shows a "Buy a Robot" screen with tiered equipment recommendations (not in YAML journeys)
- The demo shows an "Agent Link" flow where users connect Claude/ChatGPT via API key (no YAML entity)
- The demo shows a live activity feed with SSE events (no YAML architecture component)
- The demo shows robot detail panels with reviews, legal info, and hire CTAs (richer than YAML's equipment catalog)

**Missing from both YAML and demo:**
- Dispute resolution flow (acknowledged as excluded, but no design-only stub)
- Data quality SLA -- what happens when deliverables fail QC? The demo ends at "task complete"
- Operator churn modeling -- what keeps operators on the platform after first payout?

**YakRoboticsGarage org signal:**
- 14 repos exist including `tumbller-8004-mcp`, `tello-8004-mcp`, `yakrover-8004-mcp` -- real ERC-8004 implementations
- `cryptobotics-whitepaper` repo exists but the YAML never references it
- The org has real hardware (tumbller, tello, yakrover) but none appear in the demo's robot catalog, which shows only survey equipment. The YAML should bridge these with a `prototype_fleet` section

---

## Specific YAML Additions (with exact YAML snippets to add)

```yaml
# After bet_chain section:
validation_register:
  experiments:
    - id: exp:gc_discovery_interviews
      bet_tested: bet:survey_bottleneck_real
      method: "Interview 20 senior estimators at ENR Top 400 regional firms"
      success_signal: "12+ cite scheduling as top-3 pain"
      status: not_started
      confidence_delta: "+0.10 if positive, -0.30 if negative"
    - id: exp:operator_signup_60day
      bet_tested: bet:robot_supply_exists
      method: "Launch operator registration in AZ/NV/NM"
      success_signal: "5+ operators register within 60 days"
      status: not_started

# After competitive_landscape section:
competitive_moats:
  durable:
    - id: moat:geo_operator_density
      description: "Operator network density in target metros -- hard to replicate without demand"
      defensibility: high
      timeline_to_build: "6-12 months"
    - id: moat:construction_domain_intelligence
      description: "RFP-to-task decomposition, deliverable format validation, agency-specific compliance"
      defensibility: high
    - id: moat:legal_compliance_stack
      description: "Bond verification, COI parsing, PLS validation, DBE tracking"
      defensibility: medium
      note: "Replicable with effort but requires domain expertise"
  response_playbook:
    fabric_ships_marketplace:
      trigger: "Fabric launches task marketplace on Base"
      response: "Accelerate construction-domain features they cannot match; legal stack is 6-month head start"
    rentahuman_adds_robots:
      trigger: "RentAHuman adds robot operators to their 600K worker network"
      response: "They lack sensor-specific matching and deliverable pipelines; compete on quality not quantity"

# After transfer_map section:
lunar_business_model:
  gravity_effect: "The lunar narrative is only credible if the business model transfers, not just the sensors."
  open_questions:
    - "NASA CLPS contracts are firm-fixed-price to payload providers, not reverse-auction"
    - "Who is the buyer: NASA directly, CLPS payload provider, or commercial lunar company?"
    - "Auction mechanism may need adaptation: pre-qualified pool + task order, not open RFQ"
  procurement_vehicles:
    - {name: "CLPS", type: firm_fixed_price, buyer: NASA, relevance: "Task orders to pre-qualified providers"}
    - {name: "Artemis support", type: cost_plus, buyer: NASA, relevance: "Survey work as subcontract"}
    - {name: "Commercial lunar", type: negotiated, buyer: "ispace/Astrobotic/Intuitive Machines", relevance: "Most auction-compatible"}

# Replace usage block:
talisman_metadata:
  type: "Reference + Analytical hybrid"
  gravity_effect: "Treat as authoritative source of entities, relationships, bets, and architecture. Defer to this over individual research docs when they conflict."
  likely_effects:
    - "Anchors agent reasoning to construction-survey wedge strategy"
    - "Prevents scope creep into verticals not yet on roadmap"
    - "Biases toward auction-based thinking for all problems"
  anti_patterns:
    - "Do NOT use this file to generate marketing copy -- it is internal strategy"
    - "Do NOT treat confidence scores as fixed -- they must be updated by validation_register"
  staleness_policy:
    max_age_days: 30
    refresh_trigger: "Any bet confidence changes by > 0.15 or a phase gate is crossed"
```
