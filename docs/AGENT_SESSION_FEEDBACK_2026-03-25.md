# Agent Session Feedback — 2026-03-25T17:19Z

> Feedback from a Claude Opus 4.6 agent session conducting a live env_sensing
> auction through the marketplace MCP tools. Task: "Check the temperature in
> Bay 3." This document captures friction, failure modes, and improvement
> recommendations observed during the end-to-end flow.

**Session ID:** `req_e7422fee41f0` (failed at confirm_delivery), `req_d9e4ff1a9851` (completed)
**Agent:** Claude Opus 4.6 (1M context) via Claude Code CLI
**Date:** 2026-03-25
**Outcome:** Task completed on second attempt after correcting `capability_requirements` schema

---

## Summary of Flow

1. Discovered robots via `discover_robot_agents` — found Tumbller (remote, offline)
2. Attempted direct MCP call to robot endpoint — ngrok tunnel offline (ERR_NGROK_3200)
3. Pivoted to auction marketplace — posted task via `auction_post_task`
4. Hit three errors before successful post (budget floor, category enum, capability_requirements format)
5. Collected bids, accepted recommended winner (fakerover-bay3, $0.35)
6. Executed task — received sensor data (23.2°C, 40.8% humidity)
7. **`confirm_delivery` failed** — `Payload format must be 'json', got 'None'`
8. Root-caused to missing `payload.format` in `capability_requirements`
9. Re-ran full auction with corrected spec — settled successfully on second pass

---

## Recommendations

### REC-1 · `capability_requirements` needs a documented schema and defaults

**Problem:** The `capability_requirements` field accepts an arbitrary dict, but `confirm_delivery` later validates `capability_requirements["payload"]["format"]` and `capability_requirements["payload"]["fields"]`. There is no documentation, type hint, or example showing what shape this dict should have. An agent posting a task has no way to know that omitting `payload.format` will cause settlement to fail five steps later.

**What happened:** First task posted with `{"tool": "tumbller_get_temperature_humidity"}` — a reasonable guess. This passed `post_task` validation but silently created a time bomb that detonated at `confirm_delivery`.

**Recommendation:** Either:
- **(a) Default `payload.format` to `"json"` when not provided** — this is always true in v0.1 per the comment on line 791 of engine.py. The check on line 792 should treat `None` as `"json"` rather than failing.
- **(b) Validate the `payload` sub-schema at post time** in `Task.__post_init__()` or `post_task()`, so the error surfaces immediately instead of after payment reservation and execution.
- **(c) Add a `capability_requirements` schema reference** to the `auction_post_task` tool description, with an example.

Option (a) is the smallest fix. Option (b) is the most robust. Both should ship.

---

### REC-2 · `post_task` tool description should include the capability_requirements shape

**Problem:** The tool docstring says: *"Accepts a task specification dict with keys: description, task_category, capability_requirements, budget_ceiling, sla_seconds."* — but gives no guidance on what `capability_requirements` should contain internally. Compare this with `task_category`, which at least produces a clear error listing valid values.

**Recommendation:** Expand the tool description to include an example `task_spec`:
```json
{
  "description": "Read temperature in Bay 3",
  "task_category": "env_sensing",
  "capability_requirements": {
    "tool": "tumbller_get_temperature_humidity",
    "payload": {"format": "json", "fields": ["temperature_celsius", "humidity_percent"]}
  },
  "budget_ceiling": 0.50,
  "sla_seconds": 120
}
```
This eliminates the guesswork entirely. MCP tool descriptions are the primary interface for AI agents — they should be self-contained.

---

### REC-3 · Fail-fast validation at `post_task` for the full task lifecycle

**Problem:** The current validation in `post_task` checks `budget_ceiling` and `task_category` but nothing else. Errors in `capability_requirements` structure, SLA values, or payload spec are only discovered mid-lifecycle — after bids have been collected, a bid accepted, payment reserved, and execution completed. This wastes compute, wallet balance, and robot availability.

**Recommendation:** Add a `validate_task_spec()` function called at `post_task` time that checks:
1. `payload.format` is `"json"` (or a supported format)
2. `payload.fields` is a non-empty list of strings (if provided)
3. `sla_seconds` is positive and within a reasonable range
4. `budget_ceiling` type coercion (currently fails opaquely if passed as string)

This follows the principle: **every field that will be validated downstream should be validated upstream.**

---

### REC-4 · Over-budget bids should be excluded from `get_bids` response or clearly marked

**Problem:** `fakerover-bay7` bid $0.55 against a $0.50 budget ceiling. The scoring function correctly excludes it (`score_bids` filters `price > budget_ceiling`), but the bid still appears in the `bids` array returned to the agent with no explicit disqualification flag. An agent must cross-reference the `scores` dict (which omits over-budget bids) with the `bids` list to figure out why a bid has no score.

**Recommendation:** Either:
- **(a)** Add an `"eligible": false, "reason": "over_budget"` field to disqualified bids in the response.
- **(b)** Split the response into `eligible_bids` and `disqualified_bids` arrays.
- **(c)** Simply omit over-budget bids from the response entirely.

Option (a) is the most informative for an agent consumer.

---

### REC-5 · `confirm_delivery` and `reject_delivery` should be callable without re-posting

**Problem:** When `confirm_delivery` failed on the first task (`req_e7422fee41f0`), the task was stuck in `DELIVERED` state. There was no way to fix the `capability_requirements` retroactively, so the entire auction had to be re-run from scratch — new post, new bids, new execution, new payment reservation. The original $0.09 reservation was effectively lost.

**Recommendation:**
- **(a)** If `confirm_delivery` fails due to a spec mismatch (not a data quality issue), allow the agent to retry with corrected parameters, or fall back to a manual override: `confirm_delivery(request_id, override_validation=True)`.
- **(b)** Alternatively, provide an `auction_cancel_task` tool that refunds the reservation when the failure is on the buyer's side (malformed spec, not robot fault).

---

### REC-6 · Add a `auction_get_task_schema` or `auction_dry_run` tool

**Problem:** An AI agent interacting with the marketplace for the first time has to learn the correct `task_spec` shape through trial and error. This session required 4 attempts at `post_task` before success (budget too low, wrong category, list vs dict, missing payload spec).

**Recommendation:** Add one of:
- `auction_get_task_schema()` — returns the expected JSON schema for `task_spec`, including valid `task_category` values, `capability_requirements` structure, and constraints.
- `auction_dry_run(task_spec)` — validates the full spec without posting, returning all errors at once rather than failing on the first one.

Either tool would let an agent self-correct in a single round-trip instead of iterating.

---

### REC-7 · Error messages from `post_task` should return all validation failures, not just the first

**Problem:** Each call to `post_task` raised a single `ValueError`. The agent had to fix one issue, re-call, hit the next error, fix that, re-call, and so on. Four serial round-trips for four independent validation errors.

**Recommendation:** Collect all validation errors in `Task.__post_init__()` (or a dedicated validator) and return them together:
```json
{
  "error": "Task validation failed",
  "errors": [
    "budget_ceiling must be >= $0.50, got $0.01",
    "task_category must be one of [...], got 'sensor_reading'",
    "capability_requirements.payload.format is required"
  ]
}
```

---

### REC-8 · The `discover_robot_agents` → auction handoff needs a smoother bridge

**Problem:** Discovery showed the Tumbller robot with its tools (`tumbller_get_temperature_humidity`), but the robot was offline (ngrok tunnel down). The agent then had to independently decide to pivot to the auction system. There was no indication from the discovery response that the auction marketplace exists or that it's the fallback path for offline robots.

**Recommendation:** When a discovered robot's endpoint is offline or `local_endpoint` is null, include a hint in the response:
```json
{
  "robot_id": "...",
  "local_endpoint": null,
  "hint": "Robot is not available for direct control. Use auction_post_task to hire a robot for this capability."
}
```

---

### REC-9 · MCP tool descriptions should list valid enum values inline

**Problem:** `task_category` accepts only 5 values, but the agent only learns this from the error message after a failed call. The tool description says just `task_category` with no enumeration.

**Recommendation:** Include valid values directly in the tool description:
```
task_category: one of "env_sensing", "visual_inspection", "mapping", "delivery_ground", "aerial_survey"
```

This is especially important for AI agent consumers where the tool description is the only documentation available at call time.

---

## Priority Matrix

| # | Impact | Effort | Priority |
|---|--------|--------|----------|
| REC-1 | High — breaks settlement silently | Low (default or validate) | **P0** |
| REC-3 | High — wasted resources on bad specs | Medium | **P0** |
| REC-7 | Medium — agent iteration overhead | Low | **P1** |
| REC-2 | Medium — agent usability | Low (docstring edit) | **P1** |
| REC-9 | Medium — agent usability | Low (docstring edit) | **P1** |
| REC-5 | Medium — stranded tasks, lost funds | Medium | **P1** |
| REC-4 | Low — cosmetic, agent can work around | Low | **P2** |
| REC-6 | Medium — first-use experience | Medium | **P2** |
| REC-8 | Low — UX polish | Low | **P2** |

---

*Filed by Claude Opus 4.6 agent — session 2026-03-25T17:19Z*
