# Skill Architecture Plan v2 — Yak Robotics Marketplace

**Date:** 2026-04-16
**Status:** Draft v2 (post-critique)
**Goal:** Design the agent integration layer for the robot marketplace, targeting Anthropic official plugin directory.

---

## Multi-Agent Critique Summary

Three perspectives critiqued v1's 3-skill proposal (hire-robot, onboard-operator, demand-signal). Their verdicts diverged sharply, which is the point.

### Buyer Critique

**"hire-robot is three skills pretending to be one."**

The buyer has four distinct intents that map to different sessions and mental states:

1. **Scope** — "I have a problem, help me figure out what I need" (novice buyer, RFP holder)
2. **Post** — "Here's my spec, put it out for bids" (expert buyer, repeat buyer)
3. **Award** — "Show me the bids, I want to pick someone" (comes back hours/days later)
4. **Track** — "What's happening with my job? Is it done? Is it good?" (monitoring + verification)

Plus a fifth for repeat buyers: **Reorder** — "Same as last week, different date."

The demand signal is not a buyer action — it's a byproduct of `scope` finding no match. Capture it where it happens, don't make the buyer do extra work.

**Proposed: 5 buyer-side skills + keep onboard-operator separate = 6 total.**

### Operator Critique

**"Onboarding is dead after day 1. Where's day 2-365?"**

The operator needs:
- **Onboard** (day 1 wizard) — profile, equipment, credentials, payment
- **Dashboard** (daily driver) — active bids, completed tasks, earnings, fleet status, demand signals, market rates
- **Alerts** (proactive) — credential expiry, maintenance intervals, demand spikes, bid outcomes, payouts

Demand signals are not a standalone skill — they're a data layer consumed by the operator dashboard ("show me unmet demand in my area" is a dashboard query, not a separate workflow).

**Proposed: 3 operator-side skills + buyer skills = 8-9 total.**

### Platform/Technical Critique

**"Do not build skills. Build better tools."**

The contrarian case:
- Every accepted plugin in Anthropic's directory (Stripe, GitHub, Playwright) is **MCP-only, zero skills**. Skills are not required for acceptance.
- With 39 tools, a skill becomes a brittle orchestration layer that drifts as tools change. The model is better at ad-hoc tool composition than following a rigid script.
- Skills are Claude Code-specific. MCP tools work everywhere (Cursor, ChatGPT, OpenAI agents). Every hour on skills benefits one client. Every hour on tool descriptions benefits all clients.
- Skills have a nonzero context floor cost (~500-800 tokens each, loaded every conversation). Tools deferred via ToolSearch cost near-zero until invoked.
- Tool responses can embed orchestration hints ("No robots found. Use `log_unmet_demand` to notify operators of market gaps.") — this is runtime guidance available to every MCP client, not a stale prompt in one client.

**Proposed: 0 skills. Invest in tool descriptions, tool response messages, and a `marketplace_help` tool.**

---

## Synthesis: Where the Critiques Agree

Despite different conclusions (6 skills / 9 skills / 0 skills), all three agree on:

1. **Demand signal is a data layer, not a skill.** It's a byproduct of failed searches, consumed by operators. Build the MCP tools (`log_unmet_demand`, `get_demand_signals`), surface them in tool responses, don't create a skill for it.

2. **The original 3-skill split was wrong.** It mapped to internal marketplace concepts (buy/sell/signal), not user intents.

3. **Tool quality is the highest-leverage investment.** Whether you build skills or not, the 39 MCP tools need better descriptions, clearer schemas, and orchestration hints in their responses.

4. **Onboarding is architecturally different from daily use.** Even the 0-skills advocate would benefit from this distinction at the MCP tool level.

---

## Revised Architecture: Tools-First, Skills-Light

### Layer 1: MCP Tools (Universal, All Clients)

**This is the primary investment.** Every MCP client (Claude, Cursor, ChatGPT, OpenAI agents) benefits.

#### Tool Description Quality Standard

Every tool gets a 2-3 sentence description following Springett's dictionary discipline:
- **What it does** (one sentence)
- **When to use it** (one sentence)
- **What to call next** (one sentence, optional)

Example:
```
auction_post_task:
  "Post a structured task to the marketplace for robot operators to bid on.
   Use after the buyer has confirmed a task specification with category,
   budget, location, and capability requirements. After posting, use
   auction_get_bids to retrieve ranked bids."
```

#### Tool Response Orchestration

When a tool returns results, embed next-step guidance in the response:

```json
{
  "state": "bidding",
  "bid_count": 5,
  "recommended_winner": "robot_042",
  "_next_steps": [
    "Use auction_review_bids for detailed comparison",
    "Use auction_award_with_confirmation to select a winner"
  ]
}
```

When a search fails:
```json
{
  "state": "no_match",
  "reason": "No robots with GPR capability within 200km of specified location",
  "_next_steps": [
    "Use auction_log_unmet_demand to notify operators of this gap",
    "Try broadening the search radius or relaxing sensor requirements"
  ]
}
```

This is the Springett principle: world physics, not actor guidance. The orchestration knowledge lives in the tool responses where it is contextual, runtime, and universal.

#### New MCP Tools

| Tool | Purpose | Called by |
|------|---------|----------|
| `auction_log_unmet_demand` | Log a failed search as market signal | Any client, on no-match |
| `auction_get_demand_signals` | Query unmet demand by region/capability | Operators checking market |
| `auction_marketplace_help` | Return structured guide of all capabilities | Any client, on first interaction |
| `auction_my_tasks` | Buyer: list my posted/active/completed tasks | Buyer dashboard |
| `auction_my_bids` | Operator: list my active/won/lost bids | Operator dashboard |
| `auction_my_earnings` | Operator: earnings summary by period | Operator dashboard |
| `auction_market_rates` | Anonymized aggregate pricing by task type and region | Operator pricing |

#### Tool Vocabulary Audit

Current 39 tools have dictionary inflation in three areas:

| Cluster | Current tools | Recommendation |
|---------|--------------|----------------|
| Bid acceptance | `accept_bid`, `accept_and_execute`, `award_with_confirmation` | Keep all three — they serve genuinely different workflows (auto-accept, immediate dispatch, confirmation gate). But descriptions must clearly differentiate when to use each. |
| Operator onboarding | `onboard_operator`, `onboard_operator_guided`, `register_operator` | Consolidate to 2: `register_operator` (programmatic) and `onboard_operator_guided` (interactive). Drop `onboard_operator` — it's the same as register. |
| Status queries | `get_status`, `get_bids`, `review_bids`, `list_tasks`, `get_task_feed` | Keep all — different scopes (single task vs all tasks vs feed). Descriptions must clarify. |

### Layer 2: Plugin Packaging (Anthropic Directory)

Minimum viable plugin for directory submission:

```
yakrover/
  .claude-plugin/
    plugin.json
  .mcp.json
  README.md
```

That's it. No skills. This matches the pattern of every accepted external plugin (Stripe, GitHub, Playwright, Linear, Supabase).

**plugin.json:**
```json
{
  "name": "yakrover",
  "description": "Robot task auction marketplace. Post construction survey tasks, receive bids from certified robot operators, and settle payments. Supports 18 task categories including aerial LiDAR, GPR subsurface scanning, bridge inspection, and thermal imaging. 100+ robots on testnet, 1 physical robot on mainnet.",
  "version": "1.0.0",
  "author": {
    "name": "Yak Robotics Garage",
    "email": "contact@yakrobot.bid"
  },
  "homepage": "https://yakrobot.bid",
  "repository": "https://github.com/YakRoboticsGarage/yakrover-marketplace"
}
```

**.mcp.json:**
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

### Layer 3: Skills (Claude Code-Specific, Optional)

If skills are built at all, they should be **value-adds on top of already-functional tools**, not the primary orchestration layer. The model should be able to run the full buyer and operator flows using just the MCP tools. Skills add guided workflows for users who want hand-holding.

**If we build skills, build exactly two:**

#### `yak` (single buyer-facing skill)

Not `hire-robot`, not 5 separate buyer skills. One skill with a broad trigger:

```yaml
---
name: yak
description: >
  Robot task auction marketplace. Use when someone needs a drone survey,
  LiDAR scan, bridge inspection, GPR subsurface scan, thermal inspection,
  construction monitoring, or any physical data collection. Also trigger on
  "hire a robot", "find a drone operator", "I need a survey", "post a task",
  "check my bids", "what's the status of my job", or "reorder last survey".
---
```

The body handles branching internally based on user intent:
- "I need a survey" → scope and post flow
- "Show me my bids" → status/award flow
- "Same as last week" → reorder flow
- "What can you do?" → calls `auction_marketplace_help`

This avoids trigger competition between multiple skills and keeps the context floor to one skill's cost (~500-800 tokens).

#### `yak-operator` (single operator-facing skill)

```yaml
---
name: yak-operator
description: >
  Register and manage a robot operator account on the Yak Robotics
  marketplace. Use when someone wants to register a drone, list robots for
  hire, check their bids and earnings, update equipment, or see what tasks
  buyers are requesting in their area.
---
```

Handles onboarding (day 1) and daily operations (day 2+) with internal branching. New operator → guided registration. Returning operator → dashboard view.

### Layer 4: Knowledge Objects (References)

Domain knowledge stored as structured YAML in `references/` directories, following the thejaymo.net Knowledge Object pattern:

- `TASK_CATEGORIES.yaml.md` — 18 categories with required sensors, deliverable formats, QA criteria
- `EQUIPMENT_PROFILES.yaml.md` — Robot types, sensor capabilities, coverage specs
- `REGULATORY_REQUIREMENTS.yaml.md` — FAA Part 107, state PLS rules, insurance minimums
- `SURVEY_STANDARDS.yaml.md` — ASPRS accuracy classes, USGS density requirements, CRS codes

These are loaded by skills when needed (not always in context) and are also useful as MCP resources.

---

## Development Sequence (Revised)

| Phase | Deliverable | Effort | Impact |
|-------|------------|--------|--------|
| **1** | Tool description audit — rewrite all 39 tool descriptions to quality standard | 1 session | High (universal) |
| **2** | Tool response orchestration — add `_next_steps` to all tool responses | 1-2 sessions | High (universal) |
| **3** | New MCP tools: `log_unmet_demand`, `get_demand_signals`, `marketplace_help`, `my_tasks`, `my_bids`, `my_earnings`, `market_rates` | 2-3 sessions | High |
| **4** | Plugin packaging: plugin.json + .mcp.json + README | 0.5 session | Medium (directory submission) |
| **5** | Submit to Anthropic directory (MCP-only, no skills) | 0.5 session | High |
| **6** | Optional: `yak` + `yak-operator` skills | 1-2 sessions | Medium (Claude Code only) |
| **7** | Optional: Knowledge Object references | 1 session | Low-Medium |
| **8** | Eval suite (if skills built) | 1 session | Medium |

Note the inversion from v1: tools first (phases 1-3), directory submission early (phase 5), skills last and optional (phase 6). This is the key architectural decision.

---

## Key Decisions

### Decided

1. **Demand signal is a data layer, not a skill.** Build `log_unmet_demand` and `get_demand_signals` as MCP tools. Surface them in tool responses on no-match.

2. **Tool quality is the primary investment.** Rewrite descriptions, add response orchestration hints. This benefits all MCP clients.

3. **Plugin submission is MCP-only.** Match the pattern of accepted plugins. No skills required for directory acceptance.

### Open

1. **Should we build the two optional skills?** Arguments for: better Claude Code UX, guided flows for non-technical buyers. Arguments against: maintenance burden, Claude Code-only benefit, tools should be self-sufficient.

2. **Should `_next_steps` be a formal convention or ad-hoc?** Could define it as a standard field in all auction engine responses. Or keep it informal in response text.

3. **Should Knowledge Object references live in the plugin or in the MCP server as resources?** MCP supports resources natively. A `resources/task-categories` URI that returns structured YAML would be universal. Plugin references are Claude Code-only.

---

## References

- [Springett skill-creator](https://github.com/bglek/skill-creator-springett) — Hard Worlds framework
- [Knowledge Objects](https://github.com/tehjaymo/thejaymo.net/tree/main/Objects) — YAML ontology pattern
- [here-now skill](https://here.now/docs) — Reference implementation
- [Anthropic Plugin Directory](https://github.com/anthropics/claude-plugins-official) — Submission target
- [R-053: MCP/Skills/Plugins Research](../research/automated/R-053_mcp_skills_plugins_agent_integration.md)
- [v1 Architecture Plan](./SKILL_ARCHITECTURE_PLAN.md) — Superseded by this document
