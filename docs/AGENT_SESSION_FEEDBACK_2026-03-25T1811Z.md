# Agent Session Feedback — 2026-03-25T18:11Z

> Feedback from a Claude Opus 4.6 agent session conducting a live env_sensing
> auction through the marketplace MCP tools. Task: "Hire a robot to check the
> temperature in bay 3." This document captures friction points, confirmed fixes
> from prior sessions, and new improvement recommendations observed during the
> end-to-end flow.

**Session ID:** `req_147cb22886ef`
**Agent:** Claude Opus 4.6 (1M context) via Claude Code CLI
**Date/Time:** 2026-03-25 18:11 UTC
**Outcome:** Task completed end-to-end in a single pass. No retries needed. Settlement succeeded.

---

## Flow Transcript

1. `auction_get_wallet_balance("default")` — failed: `WALLET_NOT_FOUND`, hint returned: use wallet_id `"buyer"`
2. `discover_robot_agents()` and `auction_get_wallet_balance("buyer")` — ran in parallel; found Tumbller (remote), wallet balance $10.00
3. `auction_post_task` — succeeded on first attempt (used example from tool description)
4. `auction_get_bids` — 3 bids returned with `eligible`, `disqualification_reason`, and `score_breakdown` fields
5. `auction_accept_bid("fakerover-bay3")` — success, $0.09 reserved
6. `auction_get_status` — state `bid_accepted`, delivery null, no indication of next step
7. `auction_get_status` (again, after 5s wait) — same result, still no delivery
8. Agent discovered `auction_execute` tool via ToolSearch — this tool was not referenced anywhere in prior responses
9. `auction_execute` — success, sensor data returned (23.6C, 41% humidity)
10. `auction_confirm_delivery` — success, settled, $0.35 transferred to operator

**Total tool calls:** 10 (including 2 wasted on status polling before discovering `execute`)
**Total wall time:** ~45 seconds of agent reasoning + tool execution

---

## Confirmed Fixes from Prior Sessions

The following issues from earlier feedback documents (`AGENT_SESSION_FEEDBACK_2026-03-25.md`, `AGENT_SESSION_FEEDBACK_2026-03-25T1758Z.md`) appear to be resolved:

| Prior REC | Status | Evidence |
|-----------|--------|----------|
| REC-1 (P0) | **Fixed** | `confirm_delivery` succeeded without `payload.format` errors. The default-to-json behavior is working. |
| REC-2 (P1) | **Fixed** | `post_task` tool description now includes a full example `task_spec` with `capability_requirements` shape. Agent posted successfully on first attempt. |
| REC-4 (P2) | **Fixed** | Over-budget bid (`fakerover-bay7`, $0.55 vs $0.50 ceiling) now includes `"eligible": false, "disqualification_reason": "over_budget ($0.55 > $0.5)"`. |
| REC-9 (P1) | **Fixed** | `task_category` enum values are listed in the tool description. |
| REC-12 (P0) | **Partial** | Wallet error now uses structured `error_code`/`message`/`hint` format. Not verified for all error paths. |
| REC-15 (P2) | **Fixed** | Each bid now includes `score_breakdown` with `price`, `sla`, `confidence`, `reputation` components. |

These fixes represent significant progress. The first-attempt success rate for `post_task` went from 25% (1 in 4 attempts in prior sessions) to 100% in this session.

---

## New Recommendations

### REC-16 · The `accept_bid` → `execute` handoff is invisible to the agent

**Problem:** After calling `accept_bid`, the auction enters state `bid_accepted`. The response and status contain no indication that the agent must call `auction_execute` to dispatch the task. The agent's natural assumption is that accepting a bid triggers execution automatically — the user journey document describes this as seamless. Instead, the agent must independently discover a tool (`auction_execute`) that was never referenced in any prior tool response.

**What happened:** The agent polled `get_status` twice, waited 5 seconds, and then had to search the tool registry to find `auction_execute`. Two tool calls and 5 seconds of wall time were wasted.

**Recommendation:**
- **(a) Include a `next_action` field in the `accept_bid` response:**
  ```json
  {
    "state": "bid_accepted",
    "next_action": "Call auction_execute(request_id) to dispatch the task to the winning robot.",
    "next_tool": "auction_execute"
  }
  ```
- **(b) Alternatively, merge `accept_bid` and `execute` into a single step.** From the buyer's perspective, accepting a bid and dispatching execution are the same intent. A separate `execute` call only makes sense if there's a reason to accept a bid but delay execution — and no such use case exists in the current scope (v0.1–v1.0).
- **(c) At minimum, mention `auction_execute` in the `accept_bid` tool description** as the expected next step.

Option (b) is the cleanest UX. Option (a) is the smallest fix.

---

### REC-17 · Wallet ID requires guessing — no default or enumeration

**Problem:** The agent called `get_wallet_balance("default")` as a reasonable first guess. The error returned `WALLET_NOT_FOUND` with a hint to use `"buyer"`. This worked, but the correct wallet ID is not documented in any tool description and cannot be discovered without a failed call.

**What happened:** One wasted tool call to learn the wallet ID.

**Recommendation:**
- **(a) Default the `wallet_id` parameter** to `"buyer"` when not provided. The `get_wallet_balance` tool should work with zero arguments for the common case.
- **(b) Add a `list_wallets` tool** or include valid wallet IDs in the `get_wallet_balance` tool description.
- **(c) At minimum, document the default wallet ID** in the tool description: `"wallet_id: Wallet to query. Use 'buyer' for the default buyer wallet."`

Option (a) eliminates the friction entirely.

---

### REC-18 · State machine transitions should hint at available actions

**Problem:** The `get_status` response for state `bid_accepted` includes detailed information about the winning bid, payment reservations, and timer status — but no indication of what actions are available or expected. The agent must already know the full state machine to proceed.

**What happened:** The agent called `get_status` to figure out why nothing was happening after `accept_bid`, and the response provided no guidance.

**Recommendation:** Add an `available_actions` field to the `get_status` response:
```json
{
  "state": "bid_accepted",
  "available_actions": ["auction_execute", "auction_cancel_task"],
  "hint": "Call auction_execute to dispatch the task to the winning robot."
}
```

This pattern is especially valuable for AI agent consumers who cannot read source code to understand state machine transitions. Each state should declare what tools are callable next.

---

### REC-19 · The full lifecycle requires too many tool calls for simple tasks

**Problem:** A simple sensor reading required 10 tool calls across 7 distinct tools: `get_wallet_balance` → `discover_robot_agents` → `post_task` → `get_bids` → `accept_bid` → `execute` → `confirm_delivery`. For the "Sarah asks for a temperature reading" use case described in USER_JOURNEY.md, this is 7 steps of protocol overhead for 1 sensor value.

**Impact:** Each tool call costs agent reasoning time, token budget, and user patience. The 42-second vision in the user journey becomes difficult when the agent must navigate 7 sequential tool calls with no parallelization possible (each depends on the prior result).

**Recommendation:** Add a high-level convenience tool for the common case:
```
auction_quick_hire(task_spec) → { sensor_data, cost, robot_id }
```
This tool would internally run: post → wait for bids → auto-accept recommended winner → execute → auto-confirm if data matches spec → return result. The existing granular tools remain available for agents that want fine-grained control (custom bid selection, manual confirmation, etc.).

**Scope note:** This fits within v0.5/v1.0 as a UX layer on top of the existing engine. The granular tools are the right foundation — the convenience tool is syntactic sugar for the 80% case.

---

### REC-20 · `auto_accept_timer_active` appears in status but behavior is undocumented

**Problem:** The `get_status` response includes `"auto_accept_timer_active": true, "auto_accept_seconds": 3600`. The agent has no documentation on what this means: Does delivery auto-confirm after 3600 seconds? Does the task auto-cancel? What happens if the agent neither confirms nor rejects?

**Impact:** An agent that encounters this field cannot make an informed decision about whether to act urgently on confirmation or let the timer handle it. If auto-accept silently settles payment, the agent loses its opportunity to reject bad data.

**Recommendation:**
- **(a) Document the timer behavior in the `confirm_delivery` or `get_status` tool description:** "If `confirm_delivery` is not called within `auto_accept_seconds`, the delivery is automatically accepted and payment is settled."
- **(b) Include the timer deadline as an ISO timestamp** (not just a duration) so the agent knows exactly when auto-accept triggers: `"auto_accept_deadline": "2026-03-25T19:11:24Z"`

---

### REC-21 · `eligible_robots: 3` in `post_task` response doesn't match discovery count

**Problem:** `discover_robot_agents` returned 1 robot (Tumbller). `post_task` returned `"eligible_robots": 3`. The agent cannot reconcile these numbers — are there robots the auction engine knows about that aren't on-chain? Are the mock fleet robots included?

**Impact:** Minor, but it undermines trust in the system. An agent or human reviewing the flow sees inconsistent robot counts between discovery and auction. In production, this would raise questions about which robots are bidding and why they weren't visible in discovery.

**Recommendation:**
- **(a) Include the list of eligible robot IDs** in the `post_task` response, not just a count:
  ```json
  {
    "eligible_robots": ["fakerover-bay3", "fakerover-bay7", "mock-drone-01"],
    "filtered_robots": 0
  }
  ```
- **(b) Note in the response or docs that the auction engine includes simulated/mock robots** not present in the on-chain registry, so the agent understands the discrepancy.

---

## Regression Check

| Prior REC | Status |
|-----------|--------|
| REC-3 (P0) — Fail-fast validation at post_task | **Not tested** — this session's spec was valid on first attempt, so validation coverage was not exercised |
| REC-5 (P1) — Stranded tasks, no cancel/retry | **Not tested** — no failure occurred |
| REC-7 (P1) — Single-error-at-a-time validation | **Not tested** — spec was valid on first attempt |
| REC-6 (P2) — Schema introspection tool | **Present** — `auction_get_task_schema` exists in tool registry (not called this session since `post_task` description was sufficient) |
| REC-8 (P2) — Auction hint when robot offline | **Not tested** — Tumbller showed as remote but no offline scenario occurred |
| REC-10 (P1) — Wallet tools non-functional | **Partial** — `get_wallet_balance("buyer")` works; `fund_wallet` not tested |
| REC-11 (P0) — capability_requirements accepts bad shapes | **Not tested** — spec was correct on first attempt |
| REC-13 (P1) — Capability-to-category mapping | **Not tested** — agent used correct category from tool description example |
| REC-14 (P1) — No pricing guidance | **Partial** — tool description now shows `$0.50` in example; no explicit min/range documented |

---

## Priority Matrix (New Recommendations)

| # | Impact | Effort | Priority |
|---|--------|--------|----------|
| REC-16 | High — agent cannot proceed without discovering a hidden tool | Low (add next_action to response, or merge tools) | **P0** |
| REC-18 | High — agents need state-aware guidance at every step | Medium (add available_actions to all states) | **P1** |
| REC-19 | High — 7 sequential tool calls for 1 sensor reading | Medium (new convenience tool wrapping existing engine) | **P1** |
| REC-17 | Medium — wasted tool call on every new session | Low (default parameter or doc fix) | **P1** |
| REC-20 | Medium — undocumented financial auto-settlement | Low (doc update) | **P1** |
| REC-21 | Low — cosmetic inconsistency, erodes trust | Low (include robot IDs in response) | **P2** |

---

## Session Comparison

| Metric | Session 1 (17:19Z) | Session 2 (17:58Z) | Session 3 (18:11Z) |
|--------|-------------------|--------------------|--------------------|
| `post_task` attempts | 4 | 4 | **1** |
| `confirm_delivery` success | No (stuck) | No (stuck) | **Yes** |
| End-to-end completion | 2nd auction | Never | **1st auction** |
| Total tool calls | ~15 | ~14 | **10** |
| Wasted tool calls | ~8 | ~10 | **3** |

The module is maturing. The critical blockers from prior sessions (REC-1, REC-2, REC-4) are fixed. The remaining friction is in agent navigation — knowing which tool to call next and reducing the number of steps for simple tasks.

---

*Filed by Claude Opus 4.6 (1M context) agent — session 2026-03-25T18:11Z*
