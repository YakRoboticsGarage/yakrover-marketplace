# Competition Entry 3: UX Critic
## Gap Analysis Between YAML DSL and Actual User Experience

**Competitor:** 3 of 5 | **Role:** User Experience Critic
**Date:** 2026-03-29 | **Schema version reviewed:** PRODUCT_DSL.yaml v1.1
**Artifacts cross-referenced:** demo/index.html, 21 feedback files, USER_JOURNEY_CONSTRUCTION_v01.md, RESEARCH_OPERATOR_ONBOARDING_CONSTRUCTION.md, thejaymo.net Knowledge Object patterns

---

### 1. Journey Gaps: Demo Screens the YAML Does Not Model

The demo contains 10+ distinct screens. The YAML `journeys` section models only 4 journeys (pre_bid_survey, no_robots_available, weather_hold, reject_recovery). Missing from the YAML entirely:

- **Operator onboarding screen** (`s-operator`, `s-buyrobot`): The demo has a full "Become a Survey Operator" flow with 3 equipment tiers, cert requirements, and CTA. The YAML has `supply_side.onboarding` but no journey stages modeling what the operator actually clicks through.
- **Agent link flow** (`s-agentlink`): The demo has a multi-step agent connection screen (choose Claude/GPT, get API key, configure MCP, verify). No YAML journey covers this. The `persona:claude_agent` has capabilities listed but no onboarding journey.
- **Robot explorer** (`s-explorer`): Full search, filter-by-type, profile drilldown. Not modeled in any YAML journey or capability.
- **Live feed** (`s-feed`): Tabs, expandable items, activity detail. No YAML analog.
- **Payment verification** (`s-pay`): The demo shows a bond upload + verification screen. The YAML mentions `legal:payment_bond_verification` as a moat but has no journey stage for the controller uploading the bond certificate.
- **Contract signing** (`signingCard`): The demo has a "Sign & Activate Services" step with execution commitment animation. The YAML `award_confirmation` state machine jumps from `award_confirmed` to `agreement_pending` without modeling what the user sees.

**Recommendation:** Add a `demo_screens` section to the YAML that maps each screen ID to its journey stage, or extend `journeys` to include operator, agent, and explorer flows as first-class journeys.

---

### 2. Persona Gaps: Operator Journey Is Skeletal

The buyer journey (Marco) is modeled with 10 detailed stages, timing, actors, and failure modes. The operator journey (Alex) is a single YAML entry with a one-line JTBD: "Onboard robot, earn revenue, see demand heatmap." Meanwhile, the research document `RESEARCH_OPERATOR_ONBOARDING_CONSTRUCTION.md` contains 236 lines of detailed operator economics, failure modes, equipment tiers, and a 6-step recommended demo flow. Almost none of this depth is reflected in the YAML journey structure.

The demo itself has more operator content than the YAML suggests -- equipment tiers, cert requirements, "Already have equipment?" CTA, firm registration link, demand signals. The YAML should model a `journey:operator_onboarding` with the same stage-actor-action format used for Marco.

The **controller persona** is entirely absent from the YAML. The user journey describes the controller setting up the company account, choosing payment method, connecting the AI assistant, and setting insurance defaults. This is a distinct user with distinct screens who appears in the demo (bond upload) but has no persona entry.

---

### 3. Agent-as-User: Claude Has Capabilities but No Journey

`persona:claude_agent` lists 5 capabilities but has no journey of its own. The YAML treats the agent as a tool within Marco's journey rather than a user with its own onboarding, configuration, and failure modes. Gaps:

- **Agent onboarding:** The demo has `s-agentlink` with API key generation, MCP config snippet, and tool verification. No YAML journey models this.
- **Agent failure modes:** What happens when Claude misparses an RFP? When it decomposes incorrectly? When it recommends a filtered-out bidder? The user journey mentions Claude "handled all of that" but the YAML has no error-recovery stages for agent actions.
- **Agent spending limits:** The journey mentions "$5,000 per task, auto-approving anything under $500." The YAML has no policy node for agent authorization thresholds.
- **Agent-to-agent interaction:** The competitive landscape mentions Fetch.ai (3M+ agents, agent-to-agent negotiation). The YAML does not model scenarios where a buyer's agent interacts with an operator's agent.

Following thejaymo.net's Knowledge Object principle of preserving "conceptual warnings, limits, or risks" -- the YAML should add an `agent_journey` with explicit failure modes and authorization boundaries.

---

### 4. Demo-YAML Mismatch: Concrete Divergences

| Demo shows | YAML says | Gap |
|---|---|---|
| MDOT I-94 Drainage Tunnel RFQ (Detroit, $205K, 3 tasks) | Marco's journey is SR-89A Sedona (12 acres, $3,600, 2 tasks) | Demo and YAML tell different stories -- different project, state, scale, budget |
| Task 3 flagged "MANUAL -- requires human tunnel survey manager" | No YAML concept of manual-flagged tasks | The smart triage of robot-vs-human tasks is a major UX moment with no DSL representation |
| Reject button on award review with known dead-end (FEEDBACK_REJECT_DEAD_END.md) | `award_confirmation` state machine includes reject -> next_bidder flow | YAML models the ideal; demo implements the broken version. No YAML field tracks implementation status of journey steps |
| "47 operators online, 312 robots, 4 states" | YAML geographies list 3 primary states + 1 secondary | Demo says 4 states; YAML says 3+1 |
| Equipment Tier 3 at $160K-$210K (including Spot + BLK ARC) | YAML `supply_side.economics.tier_3` says "$60K-$90K" | Demo and YAML disagree on tier 3 pricing because demo includes Spot ($100K+) while YAML tier 3 is drone-only multi-sensor |
| "Sign & Activate Services" with execution commitment animation | No YAML capability or state for contract signing UX | The signing ceremony is a trust-building moment absent from the ontology |

---

### 5. Feedback Integration: 21 Files, Mostly Unreferenced

The `docs/feedback/` directory contains 21 files spanning product critiques, UX audits, engineering reviews, mobile assessments, and founder directives. The YAML `sources` list references 19 research documents but **zero feedback files**. Critical feedback patterns that should be in the YAML but are not:

- **"I don't know what to do with this"** (FEEDBACK_SENIOR_PM_MARKET_FOCUS.md): Led to the entire construction wedge pivot. Should be cited as the origin of `bet:construction_wedge_works`.
- **Reject flow dead end** (FEEDBACK_REJECT_DEAD_END.md): Documents a UX blocker filed 2026-03-29. The YAML `journey:reject_recovery` models the ideal flow but does not reference this known-broken implementation.
- **"Six screens is too many"** (CRITIQUE_PRODUCT.md): The demo still has 6+ steps. No YAML `policy` or `design_constraint` captures screen-count targets.
- **"No back navigation anywhere"** (CRITIQUE_UX_DESIGN.md): A fundamental interaction gap documented in feedback, not represented in YAML journeys.
- **Founder-requested changes** (FEEDBACK_V4_FOUNDER.md): 8 specific change requests, some implemented, some not. No YAML tracking of implementation status.

**Recommendation:** Add a `feedback_synthesis` section to the YAML that maps each feedback theme to the YAML node it affects, with status (addressed/pending/deferred).

---

### 6. Pain Points from Research Not Captured in YAML

The operator onboarding research identifies the #1 failure mode for drone businesses as **client acquisition, not technical capability**. The YAML `supply_side.onboarding.bottleneck` captures this in one line but does not connect it to any journey stage or marketplace feature that solves it. The demo's "demand heatmap" concept (mentioned in research, shown nowhere in demo, referenced once in YAML under Alex's JTBD) is the answer but has no journey, no screen, no capability node.

The user journey research documents **recurring task patterns** (monthly progress monitoring becoming 14 flights over the project lifecycle). The YAML has no `journey:recurring_task` modeling the re-engagement loop. This is the retention mechanism and it is invisible in the ontology.

The legal research identifies **prompt payment compliance** (MCL 125.1561, 10-day requirement, 1.5%/mo penalty) as both a moat and an operator trust signal. The YAML captures it under `michigan_specifics` but no journey stage shows an operator seeing "Payment guaranteed within 10 days per Michigan law" -- the exact trust signal that would convert a skeptical operator.

---

### Summary: Five Structural Recommendations

1. **Add journey parity for operators and agents.** The YAML has 10 stages for Marco and 0 for Alex or Claude's onboarding. Model both with the same stage-actor-action format.
2. **Map demo screens to YAML nodes.** Create a `demo_screen_map` that links each `s-*` screen ID to its journey stage, capability, and persona. This makes demo-YAML drift visible.
3. **Integrate feedback as first-class evidence.** Add feedback files to the YAML `sources` list with synthesis tags (addressed, pending, deferred). Currently 21 files exist in a vacuum.
4. **Model manual-flagged tasks.** The demo's smartest UX moment -- "Task 3 requires a human, sent to specialist vendors" -- has no YAML representation. This is a differentiator worth naming.
5. **Add an `implementation_status` field to journey stages.** The YAML models ideal flows; the demo implements partial flows with known dead ends. Without status tracking, the YAML becomes aspirational fiction rather than an operational map.
