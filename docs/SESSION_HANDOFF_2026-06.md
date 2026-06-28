# Session Handoff — 2026-06 (teleop demo end-to-end)

Context for the next agent picking up the live demo at
[yakrobot.bid/demo](https://yakrobot.bid/demo/). This session debugged and fixed the
live teleop + sensing auction flow end to end. Everything below is on branch
**`fix/teleop-qa-delivery`** (not yet merged to `main` or opened as a PR).

## What shipped (committed on `fix/teleop-qa-delivery`)

| Commit | What |
|--------|------|
| `eac9cc1` | **Teleop ground-delivery fix.** Adapter now sends a motor-command sequence to teleop robots (default for `delivery_ground`; explicit `parameters.commands` still wins); stops fabricating a fake sensor payload when the robot returns no `delivery_data` (raises `RobotExecutionError` instead); `engine.execute()` gained an `except` that transitions IN_PROGRESS→ABANDONED cleanly. Files: `auction/mcp_robot_adapter.py`, `auction/engine.py`, `auction/tests/test_mcp_robot_adapter.py`. |
| `47090a0` | **QA-failure payload surfacing.** `confirm_delivery` raises `QADeliveryError` (a `ValueError` subclass) carrying the QA result + delivered payload; `auction_confirm_delivery` returns `{qa_failed, settled:false, qa, delivery}` instead of a bare error, so the demo can show the delivery card and offer "Release Anyway." No frontend change needed. Also swept in pre-existing `monocular_camera`/`rgb_camera` entries in `mcp_tools.py` (COMMON_MODELS, SENSOR_TO_CATEGORY). Files: `auction/engine.py`, `auction/mcp_tools.py`, `auction/tests/test_engine.py`, `auction/tests/test_mcp_contracts.py`. |
| `b14b8c9` | **monocular_camera sensor support** — completes the above: canonical sensor + aliases in `auction/sensor_registry.py`. Supports live `PiZero-Robot-01`. |

All three are **deployed** to `yakrover-marketplace` (Fly) and verified live: teleop runs end to
end (QA PASS, real `commands_executed` log). Active test suite: ~300 passing (the 3
`auction/tests/_archive/test_construction_tasks.py` failures are pre-existing/unrelated).

## Current production fleet reality (CLAUDE.md's "1 live_production" is stale)

EAS `live_production` attested robots on Base mainnet (chain 8453), as discovered live:

| Robot | agent_id | Capability | Eligible RFP | Status (2026-06) |
|-------|----------|------------|--------------|------------------|
| **Tumbller-Finland-01** | 38947 | temp + humidity (`tumbller_get_temperature_humidity`) | **Server Room Climate Check** (the only sensing RFP it fits) | **OFFLINE** — ngrok tunnel `mikel-pluckless-correctively.ngrok-free.dev` returns ERR_NGROK_3200 |
| **NPC ROBOT (Berlin)** | 45452 | teleop, no sensor | Teleop / `delivery_ground` | online (`npc-robot-mcp.fly.dev`) |
| **PiZero-Robot-01** | 54049 | monocular_camera | visual_inspection | on ngrok tunnel (intermittent) |

`FakeRover-Finland-01` (38801) is NOT attested (`live_production`), so it does not appear in
"Production only." Working demo matrix: **Production only → Teleop task**, **Demo fleet →
sensing tasks (Climate Check, GPR, LiDAR, …)**.

## Open issues (added to IMPROVEMENT_BACKLOG.yaml this session)

- **IMP-135** (high) — discovery probes the whole fleet *before* applying the EAS/fleet-type
  filter → production-only auctions probe ~120 robots and hang. Filter-before-probe.
- **IMP-136** (high) — discovery runs on the request path and blocks `/health` → repeated
  server wedges/outages; machine is 512 MB and has been OOM-killed. Cache off request path +
  bump memory / always-on.
- **IMP-137** (med) — no fail-fast on zero eligible/reachable robots → demo hangs on "Running".
- **IMP-138** (med) — offline robots silently excluded with no buyer-visible reachability badge.
- **IMP-139** (med) — demo "Override deadline" forces `sla_seconds=5`, which aborts real-robot
  execution (teleop ~15-20s). Scope the override per preset.

IMP-135/136 are the root cause of the demo "going dark"/hanging and should be done together.

## Ops runbook

- **Fly auth in a sandboxed shell** (CLI not logged in by default):
  `FLY_ACCESS_TOKEN=$(grep '^access_token:' ~/.fly/config.yml | sed 's/access_token: *//' | tr -d '"')`
- **Revive a wedged MCP server** (health `000` / demo dark):
  `fly machine restart 48e43def153638 -a yakrover-marketplace` (returns slowly because
  discovery runs on boot; verify with `fly checks list` → `passing` and
  `curl https://mcp.yakrover.online/health`).
- **Deploy MCP server:** `fly deploy -a yakrover-marketplace` from repo root. Note: deploys from
  the working tree. (Claude Code's auto-mode blocks this as a production deploy — the user runs it.)
- **Worker** (`yakrobot-api`, Cloudflare) calls the Anthropic API for demo orchestration;
  a 500/529 from Anthropic surfaces as **"AI service unavailable"** (`worker/src/index.js:804`).
  That's an upstream LLM incident, not a worker bug. `/api/demo` is rate-limited 5/day/IP.
- **Topology:** demo HTML on here.now → worker (`yakrobot-api.rafaeldf2.workers.dev`) →
  MCP server (`mcp.yakrover.online`, Fly app `yakrover-marketplace`, machine `48e43def153638`).

## Next steps

1. Open a PR for `fix/teleop-qa-delivery` (or merge) — three commits, all green.
2. Tackle IMP-135 + IMP-136 together (removes the recurring hang/outage).
3. Bring Tumbller-Finland-01's tunnel back online if Climate-Check-in-production should win.
