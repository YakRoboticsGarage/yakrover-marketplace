# Skill Architecture Plan — Yak Robotics Marketplace

**Date:** 2026-04-16
**Status:** Draft
**Goal:** Design and build production-quality Claude Code skills for the robot marketplace, targeting registration in the Anthropic official plugin directory (`anthropics/claude-plugins-official`).

---

## 1. Design Frameworks

This plan synthesizes three frameworks:

### A. Springett Hard Worlds (skill-creator-springett)

Core principle: **Build the bump, not the sign.** Constraints should be world physics (enforced by scripts/schemas), not actor guidance (prose instructions Claude might forget).

- **World physics:** Validation, budget ceilings, SLA deadlines, sensor matching — enforced by the MCP server's `auction_validate_task_specs`, not by SKILL.md prose.
- **Room structure:** The vocabulary of available tools, file locations, and context in scope. The SKILL.md defines what Claude can see and reach.
- **Actor guidance:** Judgment calls, user interaction patterns, tone. This is what SKILL.md prose is for.

Failure diagnostics (ontological hardness):
- **Lexical:** Can Claude find the right tool? Are 39 tool names unambiguous?
- **Interface:** Right tool, wrong arguments? Are schemas clear?
- **World:** Did the action produce the right state? Is the state inspectable?
- **Temporal:** Did Claude lose track of what already happened?

### B. Knowledge Objects (thejaymo.net)

Domain knowledge should be structured as reusable YAML artifacts with:
- Thesis stack (primary/secondary/tertiary claims)
- Argument maps with evidence and logic paths
- Provenance chain (author, source, license)
- Machine-readable salience (models reason over structure, not just text)

Application: Equipment capability profiles, survey methodology standards, and regulatory requirements should be Knowledge Objects in the `references/` directory, not inline prose.

### C. here-now Reference Implementation

The best-in-class skill we've observed. Key patterns to adopt:

| Pattern | here-now | Yak Robotics equivalent |
|---------|----------|------------------------|
| **One script does the work** | `scripts/publish.sh` (351 lines) | `scripts/hire-robot.sh` or MCP calls directly |
| **SKILL.md is the guide, not the engine** | 273 lines of instructions, script does execution | SKILL.md orchestrates MCP tool calls |
| **References for advanced ops** | `references/REFERENCE.md` (767 lines) | `references/TASK_CATEGORIES.md`, `references/EQUIPMENT_PROFILES.md` |
| **State management** | `.herenow/state.json` tracks published sites | Auction state lives server-side (SQLite), no local state needed |
| **Credential handling** | `~/.herenow/credentials` with clear priority chain | MCP bearer token or no auth (public demo) |
| **Description triggers on natural language** | "publish this", "host this", "deploy this" | "hire a robot", "survey this site", "I need a drone" |
| **Versioned** | `Skill version: 1.8.3` | Version in SKILL.md frontmatter |
| **What to tell the user** section | Explicit guidance on what to communicate | Same — what to show after auction completes |

---

## 2. Skill Inventory

### Existing Skills (`.claude/skills/`)

| Skill | Purpose | Status |
|-------|---------|--------|
| `rfp-to-robot-spec` | Parse RFP into structured task specs | Functional |
| `rfp-to-site-recon` | Generate site recon from RFP data | Functional |
| `bond-verification` | Verify payment bonds against Treasury Circular 570 | Functional |
| `legal-terms-compare` | Compare survey subcontract terms | Functional |

### New Skills to Build

| Skill | Purpose | Priority | Complexity |
|-------|---------|----------|------------|
| `hire-robot` | End-to-end: describe need → post task → review bids → award → execute → verify delivery | **P0** | High |
| `onboard-operator` | Register operator: profile → equipment → credentials → payment → activation | **P0** | Medium |
| `demand-signal` | When no robot can fulfill a request, broadcast the unmet demand to an operator-facing feed | **P1** | Medium |

### Why These Three

**`hire-robot`** is the buyer journey. It's what the memo promises: "an AI agent can post a task, receive ranked bids from 100 robots, and settle payment in a single session." This skill turns 39 raw tools into that experience.

**`onboard-operator`** is the supply side. Without operators registering real robots, the marketplace has no supply. This skill guides the 3-step registration (Profile → Equipment → Payment & Bidding) that currently only works through the demo UI.

**`demand-signal`** addresses the cold-start problem. When a buyer requests a capability that no registered robot can fulfill (e.g., "GPR subsurface scan in rural Montana"), the skill should:
1. Log the unmet request with location, capability requirements, and budget range
2. Broadcast to an operator-facing feed (MCP resource or API endpoint)
3. Allow operators to see real demand data and invest in equipment accordingly
4. Close the loop: when an operator registers a matching robot, notify the original requester

This turns failed auctions into market intelligence — the marketplace equivalent of "customers searched for X but we don't carry it."

---

## 3. Skill Design: `hire-robot`

### SKILL.md Structure (following here-now pattern)

```
hire-robot/
  SKILL.md                          # 200-300 lines, orchestration guide
  references/
    TASK_CATEGORIES.md              # 18 categories with descriptions
    EQUIPMENT_PROFILES.md           # Robot types, sensors, capabilities
    PAYMENT_METHODS.md              # Card, ACH, USDC — what to expect
  evals/
    evals.json                      # 3-5 test scenarios
```

### Frontmatter

```yaml
---
name: hire-robot
description: >
  Hire a robot for a physical-world task through the Yak Robotics auction
  marketplace. Use when the user needs a drone survey, LiDAR scan, bridge
  inspection, GPR subsurface scan, thermal inspection, construction monitoring,
  or any physical data collection task. Also trigger on "I need a survey",
  "find me a drone operator", "get a quote for site inspection", "hire a
  robot", "run an auction", or "post a task".
---
```

### Flow (Staged Commitment per Springett)

**Stage 1 — Understand the Need** (no tools called yet)
- Parse user's natural language request
- Identify task category, location, budget range, timeline
- If ambiguous, ask clarifying questions
- Present the structured task spec for user confirmation before proceeding

**Stage 2 — Post Task & Collect Bids** (tools: `auction_post_task`, `auction_get_bids`)
- Post the confirmed task spec
- Wait for bids (SLA-dependent, typically seconds in demo)
- Present ranked bids with scoring breakdown
- Recommend the top bid with reasoning

**Stage 3 — Award & Execute** (tools: `auction_award_with_confirmation`, `auction_accept_and_execute`)
- User confirms the winner
- Execute the task
- Monitor execution status

**Stage 4 — Verify & Settle** (tools: `auction_confirm_delivery`, `auction_track_execution`)
- Receive delivery data
- Run QA checks
- Present results to user
- Trigger settlement

**Stage 5 — No Match Handling** (tools: `auction_get_task_feed` + demand signal)
- If no robots can fulfill the request, explain why
- Log the unmet demand (location, capability, budget)
- Suggest alternative task categories if applicable
- Inform user that operators will be notified of the demand

### What to Tell the User (per here-now pattern)

- After posting: show task ID, category, budget, number of eligible robots
- After bids: show top 3 bids with price, SLA, robot name, equipment
- After award: show winner, agreed price, estimated delivery time
- After delivery: show QA result, key data points, settlement status
- On failure: explain what went wrong, what the user can do

---

## 4. Skill Design: `onboard-operator`

### Structure

```
onboard-operator/
  SKILL.md
  references/
    EQUIPMENT_TYPES.md              # Supported equipment with sensor mappings
    CREDENTIAL_REQUIREMENTS.md      # FAA Part 107, insurance, PLS
    STRIPE_CONNECT_GUIDE.md         # Payment onboarding steps
  evals/
    evals.json
```

### Flow

**Stage 1 — Profile** (tool: `auction_onboard_operator_guided`)
- Company name, contact, location, coverage area
- Equipment type and model
- Minimum bid pricing

**Stage 2 — Equipment & Credentials**
- Add equipment with sensor capabilities
- Upload FAA Part 107 certification
- Upload insurance COI
- Optional: PLS license, SAM registration

**Stage 3 — Payment & Activation** (tools: `auction_activate_operator`, Stripe Connect)
- Connect Stripe account for payouts
- Set pricing preferences
- Activate for bidding

---

## 5. Skill Design: `demand-signal`

### Concept

This is not a user-facing skill in the traditional sense. It's a system behavior triggered when `hire-robot` fails to find a match. The skill:

1. Captures the unmet request as structured data:
   ```json
   {
     "request_id": "...",
     "task_category": "subsurface_scan",
     "location": {"lat": 42.29, "lng": -85.59, "description": "Rural Montana"},
     "capability_requirements": {"sensors_required": ["gpr"]},
     "budget_range": "$2,000-$5,000",
     "timestamp": "2026-04-16T...",
     "status": "unmet"
   }
   ```

2. Writes to an operator-facing feed (new MCP tool: `auction_get_demand_signals`)

3. Operators running `onboard-operator` or checking the marketplace see: "3 requests for GPR scanning in Montana in the last 30 days, average budget $3,500. No operators within 200km."

4. When a matching operator registers, the system can notify the original requester (if they opted in).

### Implementation

- New MCP tool: `auction_log_unmet_demand` (called by hire-robot on no-match)
- New MCP tool: `auction_get_demand_signals` (called by operators or analytics)
- Storage: SQLite table `unmet_demands` in `SyncTaskStore`
- Frontend: Add to demo marketplace sidebar or separate dashboard

---

## 6. Tool Vocabulary Audit (Springett Dictionary Discipline)

Current 39 tools — potential dictionary inflation:

| Tool cluster | Tools | Issue? |
|-------------|-------|--------|
| Bid flow | `auction_accept_bid`, `auction_accept_and_execute`, `auction_award_with_confirmation` | 3 tools for one concept. Skill should guide which to use when. |
| Task posting | `auction_post_task`, `auction_validate_task_specs`, `auction_process_rfp` | Clear: validate → post, or rfp → post. OK. |
| Status | `auction_get_status`, `auction_get_bids`, `auction_review_bids`, `auction_list_tasks`, `auction_get_task_feed` | 5 query tools. Some overlap. |
| Operator | `auction_onboard_operator`, `auction_onboard_operator_guided`, `auction_register_operator`, `auction_activate_operator`, `auction_update_operator_profile` | 5 tools. `_guided` vs non-guided is the Springett "two verbs for one action" antipattern. |

**Recommendation:** Skills should curate which tools to use. Don't expose all 39 — the skill picks the right 5-8 for its flow. Deferred loading handles the rest.

---

## 7. Plugin Packaging for Anthropic Directory

### Minimum Viable Submission

```
yakrover/
  .claude-plugin/
    plugin.json
  .mcp.json                         # Points to hosted MCP server
  skills/
    hire-robot/
      SKILL.md
      references/
        TASK_CATEGORIES.md
        EQUIPMENT_PROFILES.md
    onboard-operator/
      SKILL.md
      references/
        EQUIPMENT_TYPES.md
        CREDENTIAL_REQUIREMENTS.md
  README.md
```

### plugin.json

```json
{
  "name": "yakrover",
  "description": "Robot task auction marketplace. Hire survey robots, post construction tasks, run auctions, and settle payments via MCP. Use when someone needs a drone survey, LiDAR scan, bridge inspection, or any physical data collection.",
  "version": "1.0.0",
  "author": {
    "name": "Yak Robotics Garage",
    "email": "contact@yakrobot.bid"
  },
  "homepage": "https://yakrobot.bid",
  "repository": "https://github.com/YakRoboticsGarage/yakrover-marketplace"
}
```

### .mcp.json

```json
{
  "mcpServers": {
    "yakrover": {
      "type": "http",
      "url": "https://yakrover-marketplace.fly.dev/mcp"
    }
  }
}
```

### Submission Path

1. Build and test `hire-robot` and `onboard-operator` skills
2. Run evals using skill-creator-springett framework
3. Package as plugin with `.claude-plugin/plugin.json` + `.mcp.json`
4. Test install: `claude plugin install yakrover --plugin-dir ./yakrover`
5. Submit via https://clau.de/plugin-directory-submission
6. Pass Anthropic quality/security review

### Precedent

Accepted external plugins (Playwright, Supabase, Linear, GitHub) are all:
- Established companies/projects with public repos
- Functional MCP servers or tool integrations
- Clean metadata (plugin.json with name, description, author)
- Some have Skills, most are MCP-only

YakRover with Skills + MCP would be above-average quality for the directory.

---

## 8. Development Sequence

| Phase | Deliverable | Effort |
|-------|------------|--------|
| **1** | `hire-robot/SKILL.md` + references | 1-2 sessions |
| **2** | `onboard-operator/SKILL.md` + references | 1 session |
| **3** | Eval suite for both skills (evals.json) | 1 session |
| **4** | Plugin packaging + local testing | 0.5 session |
| **5** | `demand-signal` design + new MCP tools | 1-2 sessions |
| **6** | Submit to Anthropic directory | 0.5 session |

### Key Decisions Needed

1. **Should `hire-robot` handle payment inline or defer?** Currently settlement is functional but the buyer flow through Stripe/USDC is complex. The skill could stop at "task awarded" and link to the demo UI for payment.

2. **Should `demand-signal` be a separate skill or built into `hire-robot`?** Architecturally it's cleaner as a system behavior within `hire-robot` (no-match → log demand). The operator-facing query could be in `onboard-operator`.

3. **Should we submit to Anthropic directory before or after production robots?** The 100-robot test fleet with simulated execution is functional. The skill works. But "simulated execution" may affect Anthropic's quality assessment. Counter-argument: Stripe MCP, GitHub MCP, etc. are all live services — our test fleet is live on Base Sepolia with real ERC-8004 registrations.

---

## References

- [Springett skill-creator](https://github.com/bglek/skill-creator-springett)
- [Knowledge Objects](https://github.com/tehjaymo/thejaymo.net/tree/main/Objects)
- [here-now skill](https://here.now/docs) — reference implementation
- [Anthropic Plugin Directory](https://github.com/anthropics/claude-plugins-official)
- [Plugin Submission Form](https://clau.de/plugin-directory-submission)
- [R-053: MCP/Skills/Plugins Research](../research/automated/R-053_mcp_skills_plugins_agent_integration.md)
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Claude Code Plugins Docs](https://code.claude.com/docs/en/plugins)
