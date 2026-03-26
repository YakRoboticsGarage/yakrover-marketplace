# Agent Session Feedback — 2026-03-25T17:58Z

> Feedback from a Claude Opus 4.6 agent session conducting a live env_sensing
> auction through the marketplace MCP tools. Task: "Hire a robot to check the
> temperature in bay 3." This document captures friction points, confirmed
> regressions from the earlier session, and new improvement recommendations
> observed during the end-to-end flow.

**Session ID:** `req_906d1139e071`
**Agent:** Claude Opus 4.6 (1M context) via Claude Code CLI
**Date/Time:** 2026-03-25 17:58 UTC
**Outcome:** Task delivered successfully (23.6C, 40.6% humidity). Settlement failed at `confirm_delivery` — same root cause as earlier session (`req_e7422fee41f0`).

---

## Flow Transcript

1. `discover_robot_agents` — found Tumbller (remote, single result)
2. `auction_get_wallet_balance("rafa")` — failed: wallet does not exist
3. `auction_fund_wallet("rafa", 5)` — failed: "Wallet service not configured"
4. `auction_post_task` attempt 1 — failed: `task_category` "sensor_reading" invalid
5. `auction_post_task` attempt 2 — failed: `capability_requirements` as list triggers `'list' object has no attribute 'get'`
6. `auction_post_task` attempt 3 — failed: `capability_requirements` as string triggers `'str' object has no attribute 'get'`
7. `auction_post_task` attempt 4 — succeeded with `capability_requirements` as dict `{"tumbller_get_temperature_humidity": true}`
8. `auction_get_bids` — 3 bids returned, recommended winner: fakerover-bay3 ($0.35)
9. `auction_accept_bid` — success, $0.09 reserved
10. `auction_execute` — success, sensor data returned (23.6C, 40.6%)
11. `confirm_delivery` — **failed**: `Payload format must be 'json', got 'None'`
12. `get_status` confirmed task stuck in `delivered` state with no path to settlement

---

## Confirmed Regressions from Earlier Session

The following issues were identified in the earlier session feedback (`AGENT_SESSION_FEEDBACK_2026-03-25.md`) and remain unfixed. This session hit the same failures:

- **REC-1 (P0):** `confirm_delivery` still fails when `capability_requirements` lacks `payload.format`. No default applied, no upstream validation added.
- **REC-5 (P1):** Task `req_906d1139e071` is now stranded in `delivered` state. No `cancel_task` or retry-with-correction mechanism exists. The $0.09 reservation is unrecoverable.
- **REC-7 (P1):** `post_task` still returns one error at a time. This session required 4 attempts (3 failures) to get a valid post.

---

## New Recommendations

### REC-10 · Wallet creation should be implicit on first task post or have a dedicated `create_wallet` tool

**Problem:** The agent attempted `get_wallet_balance("rafa")` to check funds before posting. The wallet didn't exist, returning a `KeyError`. The follow-up `fund_wallet` call also failed with "Wallet service not configured." Despite both wallet operations failing, `post_task` succeeded — meaning the auction system has an internal wallet ("buyer") that is decoupled from the user-facing wallet tools.

**Impact:** The agent wasted two tool calls on a dead path. Worse, the wallet tools give a false impression that funding is a prerequisite, when the auction engine actually manages its own ledger.

**Recommendation:**
- **(a)** If external wallets are not yet functional, remove or hide `fund_wallet` and `get_wallet_balance` from the MCP tool surface. Exposing non-functional tools confuses agent consumers.
- **(b)** If wallets are intended to be functional, auto-create the wallet on first `fund_wallet` or `post_task` call rather than requiring explicit creation.
- **(c)** Document in the `post_task` tool description whether pre-funding is required or whether the system uses an internal ledger.

---

### REC-11 · `capability_requirements` accepts arbitrary dicts silently — needs schema enforcement or documented contract

**Problem:** The `post_task` tool accepted three different shapes for `capability_requirements` before one worked:
1. `["tumbller_get_temperature_humidity"]` (list) — crashed: `'list' object has no attribute 'get'`
2. `"tumbller_get_temperature_humidity"` (string) — crashed: `'str' object has no attribute 'get'`
3. `{"tumbller_get_temperature_humidity": true}` (dict) — accepted, but missing `payload.format` caused downstream failure

None of these three shapes matched the actual required structure (`{"tool": "...", "payload": {"format": "json"}}`). The system accepted the third one silently because it was a dict, only to fail at settlement.

**Impact:** An agent has no way to construct a valid `capability_requirements` without either prior knowledge or trial-and-error. The error messages for shapes 1 and 2 are raw Python exceptions, not actionable guidance.

**Recommendation:**
- **(a)** Add type checking at the `post_task` boundary: if `capability_requirements` is not a dict, return a clear error: `"capability_requirements must be an object with keys: tool, payload"`
- **(b)** Add a JSON Schema definition for `capability_requirements` in the MCP tool parameter schema (not just the description). This lets agents with schema-aware tool calling construct valid payloads automatically.
- **(c)** When validation fails, include an example of the expected shape in the error message.

---

### REC-12 · Error responses should use structured error objects, not raw Python exceptions

**Problem:** Several errors returned raw exception types and messages:
- `{"error": "'list' object has no attribute 'get'", "error_type": "AttributeError"}`
- `{"error": "\"Wallet 'rafa' does not exist\"", "error_type": "KeyError"}`
- `{"error": "Wallet service not configured", "error_type": "ConfigError"}`

These are internal implementation details leaked to the consumer. An AI agent cannot reliably parse or act on `AttributeError` — it has no way to know that the fix is "pass a dict instead of a list."

**Impact:** Each opaque error requires the agent to guess at the fix, leading to multiple retry cycles. This burns tokens, time, and — in the auction context — potentially wallet funds.

**Recommendation:**
- **(a)** Wrap all MCP tool handlers in a standardized error envelope:
  ```json
  {
    "error_code": "INVALID_CAPABILITY_REQUIREMENTS_TYPE",
    "message": "capability_requirements must be an object, got list",
    "hint": "Expected shape: {\"tool\": \"...\", \"payload\": {\"format\": \"json\"}}",
    "docs_ref": "auction_get_task_schema"
  }
  ```
- **(b)** Never expose Python exception class names (`AttributeError`, `KeyError`) in MCP responses. These are meaningless to non-Python consumers.

---

### REC-13 · `discover_robot_agents` should surface capability-to-category mapping

**Problem:** Discovery returned the robot's MCP tools (`tumbller_get_temperature_humidity`) but the agent had to independently guess that reading temperature maps to `task_category: "env_sensing"`. The first attempt used `"sensor_reading"` — a reasonable inference from the tool name that happened to be wrong.

**Impact:** The mapping from robot capabilities to auction task categories is implicit knowledge that only exists inside the auction engine's matching logic. An agent seeing `tumbller_get_temperature_humidity` has no signal that the correct category is `env_sensing` rather than `sensor_reading` or `temperature_check`.

**Recommendation:**
- **(a)** Include a `supported_task_categories` field in each robot's discovery response, derived from its registered capabilities.
- **(b)** Alternatively, make `task_category` optional in `post_task` and infer it from `capability_requirements` when omitted. If the agent specifies a tool name, the engine already knows which category it belongs to.

Option (b) is the better UX — it removes a redundant field that the engine can derive.

---

### REC-14 · Budget ceiling of $1.00 should not require guessing — surface pricing context

**Problem:** This session used `budget_ceiling: 1` which worked, but the earlier session failed with `budget_ceiling: 0.01` (below the $0.50 floor). There is no pricing guidance in the tool description — no floor, no typical range, no unit.

**Impact:** An agent picking a budget for the first time has to guess. Too low and the post fails; too high and the buyer overpays if scoring doesn't adequately penalize price.

**Recommendation:**
- **(a)** Include `min_budget` and `suggested_budget_range` in the `post_task` tool description or as a field in the `get_bids` response.
- **(b)** When `budget_ceiling` is below the floor, the error message should state the minimum: `"budget_ceiling must be >= $0.50, got $0.01"` (the earlier session confirmed this error exists but the threshold wasn't in the tool description).

---

### REC-15 · Bid response included fakerover-bay7 at $0.55 against a $1.00 ceiling — scoring transparency

**Problem:** All three bids were under the $1.00 ceiling, so all scored. The recommended winner (fakerover-bay3, score 0.705) was correct, but the scoring formula is opaque. The agent sees `scores` but not the weights or factors.

**Impact:** For a human reviewing the agent's decision, or an agent making a non-default choice, there's no way to understand why bay3 scored higher than drone-01 (0.705 vs 0.701). Was it price? SLA? Confidence? Location proximity?

**Recommendation:**
- **(a)** Include a `score_breakdown` in each bid:
  ```json
  {
    "robot_id": "fakerover-bay3",
    "score": 0.7051,
    "score_breakdown": {"price": 0.30, "sla": 0.20, "confidence": 0.20}
  }
  ```
- **(b)** This is especially valuable for agents that need to justify hiring decisions or for audit trails in production deployments.

---

## Cumulative Priority Matrix (This Session + Prior)

| # | Source | Issue | Impact | Effort | Priority |
|---|--------|-------|--------|--------|----------|
| REC-1 | Prior | `payload.format` default missing — breaks settlement | High | Low | **P0** |
| REC-3 | Prior | No fail-fast validation at `post_task` | High | Medium | **P0** |
| REC-11 | New | `capability_requirements` accepts bad shapes silently | High | Medium | **P0** |
| REC-12 | New | Raw Python exceptions in MCP error responses | High | Medium | **P0** |
| REC-10 | New | Wallet tools non-functional but exposed | Medium | Low | **P1** |
| REC-7 | Prior | Single-error-at-a-time validation | Medium | Low | **P1** |
| REC-2 | Prior | Tool description missing `capability_requirements` example | Medium | Low | **P1** |
| REC-9 | Prior | Tool description missing enum values | Medium | Low | **P1** |
| REC-13 | New | No capability-to-category mapping in discovery | Medium | Medium | **P1** |
| REC-14 | New | No pricing guidance in tool description | Medium | Low | **P1** |
| REC-5 | Prior | Stranded tasks with no cancel/retry path | Medium | Medium | **P1** |
| REC-15 | New | Opaque bid scoring — no breakdown | Low | Low | **P2** |
| REC-6 | Prior | No schema introspection or dry-run tool | Medium | Medium | **P2** |
| REC-4 | Prior | Over-budget bids not flagged in response | Low | Low | **P2** |
| REC-8 | Prior | No auction hint when robot is offline | Low | Low | **P2** |

---

## Summary

This session reproduced the critical `confirm_delivery` failure from the earlier session, confirming it is a persistent blocker. The new findings center on **agent ergonomics**: the marketplace tools expose too little schema information, leak internal Python errors, and present non-functional wallet tools that mislead agents into dead-end flows. The six new recommendations (REC-10 through REC-15) focus on making the MCP tool surface self-documenting and fail-fast — the two properties that matter most when the consumer is an AI agent with no prior training on this specific API.

*Filed by Claude Opus 4.6 (1M context) agent — session 2026-03-25T17:58Z*
