# Robot Activation — Process Summary

A 1-page path from "I have a robot" to "it's live on yakrobot.bid taking paid tasks." The longer, reference-level version lives in [`ROBOT_OPERATOR_ONBOARDING.md`](./ROBOT_OPERATOR_ONBOARDING.md).

## Prerequisites

- **A robot with a programmatic control interface.** The framework wraps whatever you already have — you do **not** need to build your own MCP server first. Any of these counts:
  - **HTTP API** over WiFi (example: ELEGOO Tumbller exposes `/motor/`* endpoints)
  - **Vendor SDK** in any language your plugin can call — `djitellopy` for DJI Tello, Boston Dynamics Spot SDK, DJI Mobile SDK, Skydio Connect, Flyability CooperativeLocalization, etc.
  - **CLI tool** you can shell out to
  - **Serial/USB** to a microcontroller or SBC that accepts commands
  - **ROS / ROS2** topics, or a vendor cloud endpoint
  If your robot is RC-only with no software interface, drop in a cheap microcontroller (ESP32, Raspberry Pi) as a bridge first. A fully closed vendor ecosystem with zero programmatic entry point can't be onboarded.
- **Internet reach from the plugin → robot.** Either the robot is reachable via a public URL (Cloudflare Tunnel, ngrok, direct IP) or it dials out to an MQTT broker, or your plugin runs on the same LAN as the robot. The marketplace calls your plugin's public MCP URL; your plugin calls the robot.
- **A Base mainnet wallet** for USDC payouts. You do **not** need to hold gas yourself — the platform signs your ERC-8004 mint.

## The 5 steps

1. **Pick an equipment type.**
  Survey: `aerial_lidar`, `photogrammetry`, `thermal_camera`, `terrestrial_lidar`, `gpr`, `rtk_gps`, `robotic_total_station`. Ground teleop: `ground_robot`. This determines which tasks the marketplace routes to you.

  **If none of these fit your robot**, ask the platform admin to add a new type before you register. The registration tool rejects unknown equipment types with an `UNKNOWN_EQUIPMENT_TYPE` error — by design, so your operator's denoted category is preserved rather than silently collapsed to a fallback. The admin needs to add (PR to `yakrover-marketplace`):
  - An entry in `SENSOR_TO_CATEGORY` mapping your new type to a task category (existing ones: `env_sensing`, `visual_inspection`, `delivery_ground`, etc.)
  - An entry in `COMMON_MODELS` with the default hardware model string
  - If your robot needs a task category that doesn't exist yet, also add to `VALID_TASK_CATEGORIES` in `auction/core.py` and a matching schema in `auction/delivery_schemas.py`

  Reference: [PR #25](https://github.com/YakRoboticsGarage/yakrover-marketplace/pull/25) added `ground_robot` + `delivery_ground` end-to-end. Plan ~1–2 days for the admin roundtrip.
2. **Front your robot with an MCP server.**
  Use the `[yakrover-8004-mcp](https://github.com/YakRoboticsGarage/yakrover-8004-mcp)` framework. Create a plugin at `src/robots/<your_robot>/` with three files: `__init__.py` (a `RobotPlugin` subclass implementing `bid()` and `execute()`), `client.py` (how you talk to your hardware), `tools.py` (any robot-specific MCP tools you want to expose). The framework automatically wires up `robot_submit_bid`, `robot_execute_task`, and `robot_get_pricing` — you don't implement those yourself.
3. **Host it publicly.**
  Fly.io (recommended, always-on, ~$5/month), or ngrok for testing. Needs a stable HTTPS URL like `https://your-robot.fly.dev/<robot>/mcp`. Set env vars for whatever your `client.py` needs to reach the hardware.
4. **Register via the marketplace MCP.**
  Connect to `https://yakrover-marketplace.fly.dev/mcp` in Claude Code, or use the form at [yakrobot.bid/demo/register](https://yakrobot.bid/demo/). Call `auction_onboard_operator_guided` with:

  | Field              | Example                                    |
  | ------------------ | ------------------------------------------ |
  | `company_name`     | `"Acme Aerial Survey"`                     |
  | `equipment_type`   | `"aerial_lidar"`                           |
  | `location`         | `"Detroit, MI"`                            |
  | `mcp_endpoint_url` | `"https://your-robot.fly.dev/<robot>/mcp"` |
  | `usdc_wallet`      | `"0x…"` (Base mainnet)                     |
  | `chain`            | `"base-mainnet"`                           |

   You get back a `robot_id` like `8453:<n>`. Save it — it's your operator identity.
5. **Request a `live_production` EAS attestation.**
  Without it, you're flagged as test and invisible to real buyers. Ask the platform admin to run `auction_eas_attest(agent_id=<n>, chain_id=8453, fleet_type="live_production")`. 24–48h turnaround.

## Time & cost

- **~1 day** of focused work to get from scratch to live (plugin + deploy + register), assuming your robot already talks to something.
- **$0** registration — platform pays gas.
- **~$5/month** Fly.io for the MCP server.
- **Per-task fees**: ~$0.01 per USDC settlement on Base.

## What you don't have to do

- Run a blockchain node.
- Hold the ERC-8004 token yourself (platform holds it initially, transferable later).
- Implement every MCP tool — only `bid` and `execute` are required.
- Have every advertised capability working on day 1. Use an in-plugin availability map (see the `berlin_tumbller` plugin for a reference) so you can bid only on what's online today, flip capabilities back on as hardware arrives.

## Reference implementation

The `berlin_tumbller` plugin (ground teleop) is the simplest working example:

- Plugin code: `yakrover-8004-mcp/src/robots/berlin_tumbller/`
- Delivery schema: `GROUND_DELIVERY_SCHEMA` in `robot-marketplace/auction/delivery_schemas.py`
- Live deployment: `https://npc-robot-mcp.fly.dev/berlin_tumbller/mcp`
- On-chain record: `robot_id 8453:45452` on [BaseScan](https://basescan.org/)
- Full build notes: `tumbller-esp32s3/docs/MARKETPLACE_REGISTRATION_PLAN.md`

## After you're live

- Marketplace routes matching tasks to your `bid()`; you return price + SLA + confidence.
- Buyer picks a winner; your `execute()` runs the work and returns a delivery payload matching the category's schema.
- USDC settles to your wallet after QA passes.
- Update pricing, sensors, or MCP URL any time with `auction_update_operator_profile`.

## What will bite you (lessons from the first live_production rollout)

These are not in the happy-path, but each one cost real time during the NPC ROBOT rollout. Save yourself the debugging.

- **Don't set `MCP_BEARER_TOKEN` on your operator MCP server** unless you know the marketplace's `FLEET_MCP_TOKEN` value. The marketplace uses a single shared token to call every operator; if yours doesn't match, the server returns 401 and bids silently fail. Match Finland's posture: leave it unset.

- **`sudo cloudflared service install` writes an incomplete plist on macOS.** The generated `/Library/LaunchDaemons/com.cloudflare.cloudflared.plist` references only the binary with no subcommand — cloudflared keeps crashing with `Use cloudflared tunnel run …` and launchd respawns it in a 5 s loop. Fix: manually write the plist with explicit `ProgramArguments` `[binary, "tunnel", "--config", "/etc/cloudflared/config.yml", "run", "<tunnel-name>"]`, and copy your config + credentials into `/etc/cloudflared/`. Reload with `launchctl unload` then `load`.

- **Use a raw IP in the cloudflared `service:` line, not an mDNS `.local` hostname.** `http://berlin-tumbller-01.local:80` works but every request pays ~5 s for mDNS resolution — enough to trip the plugin's default 5 s `httpx` timeout. Raw IP drops latency to ~200 ms. If your router changes IPs, update the config.

- **Marketplace restarts invalidate MCP sessions.** The `MCPRobotAdapter` in the marketplace caches the session id on the adapter instance and (pre-PR #33) never reset it. After any operator-side restart (OOM, redeploy), the next bid call sent a stale session id → server 404 → silent None bid. Fixed in PR #33 — if you see inexplicable `bid_count: 0` after a restart, make sure the marketplace's deploy includes that commit.

- **Unknown `equipment_type` is rejected, not silently normalized.** Post PR #28, `auction_onboard_operator_guided` returns `UNKNOWN_EQUIPMENT_TYPE` if your type isn't in `SENSOR_TO_CATEGORY` / `COMMON_MODELS`. See "Pick an equipment type" above — ask the admin to add your type first.

- **Busy state used to over-hold the robot.** A 1 s execute left the robot "busy" for the full `duration_map` window (30 min for most categories). Fixed in PR #34 — `_busy_until` is now released when the task enters `DELIVERED` / `ABANDONED` / `PROVIDER_CANCELLED`.

- **Real USDC settlement from the MCP is not wired yet (as of 2026-04-22).** An agent calling `auction_post_task` → `auction_confirm_delivery` triggers the in-memory demo ledger and (if configured) a Stripe Connect transfer. The `payment_method: "usdc"` field on Task is accepted but the settlement path doesn't branch on it. If you need real USDC-on-Base from a specific buyer wallet, that's [IMP-109](../research/IMPROVEMENT_BACKLOG.yaml) in the v1.5 roadmap. The `yakrobot.bid/demo/` web UI has a USDC path via a separate flow; the MCP surface does not.

## Help

- Full onboarding reference: `[ROBOT_OPERATOR_ONBOARDING.md](./ROBOT_OPERATOR_ONBOARDING.md)`
- 8004 framework: [https://github.com/YakRoboticsGarage/yakrover-8004-mcp](https://github.com/YakRoboticsGarage/yakrover-8004-mcp)
- Marketplace source: [https://github.com/YakRoboticsGarage/yakrover-marketplace](https://github.com/YakRoboticsGarage/yakrover-marketplace)
- Live demo: [https://yakrobot.bid/demo/](https://yakrobot.bid/demo/)

