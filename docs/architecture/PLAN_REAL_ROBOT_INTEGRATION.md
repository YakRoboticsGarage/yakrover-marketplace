# Plan: Real Robot Integration (Option B — MCP Endpoint Bridge)

**Date:** 2026-04-06
**Goal:** Replace mock fleet with real on-chain robots that bid and execute via MCP endpoints.
**Status:** COMPLETE — all 7 steps done, end-to-end verified

---

## Architecture

```
Browser ──discovers──> Subgraph (Berlin-01, 02, 03 on Base mainnet)
Browser ──auction────> Worker ──tools──> Marketplace MCP Server
                                              │
                                              ├─ MCPRobotAdapter(Berlin-01)
                                              │     └── POST {robot_mcp_url}/robot_submit_bid
                                              │     └── POST {robot_mcp_url}/robot_execute_task
                                              ├─ MCPRobotAdapter(Berlin-02)
                                              └─ MCPRobotAdapter(Berlin-03)
                                                        │
                                                        ▼
                                              Robot MCP Server (yakrover-8004-mcp)
                                                        │
                                                        ▼
                                              Fakerover Simulator (:8080)
```

## Registered Robots (Base mainnet)

| Robot | Agent ID | Wallet | MCP Endpoint |
|-------|----------|--------|--------------|
| FakeRover-Finland-01 | 8453:38801 | 0x99a5...E136 | placeholder (Anuraj) |
| FakeRover-Berlin-01 | 8453:38918 | 0xC69B...d57 | placeholder → needs update |
| FakeRover-Berlin-02 | 8453:38919 | 0xC69B...d57 | placeholder → needs update |
| FakeRover-Berlin-03 | 8453:38921 | 0xC69B...d57 | placeholder → needs update |

---

## Steps

### Step 1: Start fakerover simulator
- [x] **Status:** DONE
- **What:** `cd yakrover-8004-mcp && PYTHONPATH=src uv run python -m robots.fakerover.simulator`
- **Runs on:** localhost:8080
- **Provides:** `/sensor/ht` → `{"temperature": 22.5, "humidity": 45.0}`
- **Verify:** `curl http://localhost:8080/sensor/ht`

### Step 2: Start robot MCP server
- [x] **Status:** DONE
- **What:** `cd yakrover-8004-mcp && PYTHONPATH=src uv run python scripts/serve.py --robots fakerover`
- **Runs on:** localhost:8000
- **MCP endpoint:** `/fakerover/mcp` (Streamable HTTP, requires session)
- **6 tools:** `fakerover_move`, `fakerover_is_online`, `fakerover_get_temperature_humidity`, `robot_submit_bid`, `robot_execute_task`, `robot_get_pricing`
- **Depends on:** Step 1 (simulator must be running)

#### Verified API Format

**robot_submit_bid** — flat args (not nested task_spec):
```
Input: { task_description, task_category, budget_ceiling, sla_seconds, capability_requirements }
Output: { willing_to_bid, price, currency, sla_commitment_seconds, confidence, capabilities_offered, notes }
```

**robot_execute_task:**
```
Input: { task_id, task_description, parameters }
Output: { success, delivery_data: { readings, summary, robot_id, robot_name, duration_seconds } }
```

### Step 3: Tunnel the robot MCP server
- [x] **Status:** DONE — `https://tel-advice-allowed-rocky.trycloudflare.com`
- **What:** `cloudflared tunnel --url http://localhost:8000`
- **Gives:** Public URL like `https://xxx.trycloudflare.com`
- **Verify:** `curl https://xxx.trycloudflare.com/health`

### Step 4: Update Berlin robots' on-chain MCP endpoint
- [x] **Status:** DONE — all 3 updated, subgraph confirmed
- **What:** Update the 3 Berlin registrations with the real tunnel URL
- **How:** `uv run python scripts/update_agent.py fakerover 8453:38918 --chain base-mainnet` (x3)
- **Blocker:** Need to verify if `update_agent.py` supports cloudflared URLs or only ngrok
- **Alternative:** If update_agent.py only uses NGROK_DOMAIN, may need to modify it or update .env
- **Verify:** Query subgraph, check `mcpEndpoint` field matches tunnel URL
- **Depends on:** Step 3 (need the tunnel URL first)

### Step 5: Build MCPRobotAdapter in marketplace
- [x] **Status:** DONE — `auction/mcp_robot_adapter.py`
- **What:** New class in `robot-marketplace/auction/` that calls robot MCP endpoints
- **Interface:** Same as MockRobot — `robot_id`, `capability_metadata`, `bid_engine(task)`, `execute(task)`
- **Implementation:**
  - `bid_engine(task)` → HTTP POST to `{mcp_url}/robot_submit_bid` with task spec
  - `execute(task)` → HTTP POST to `{mcp_url}/robot_execute_task` with task params
  - Parse response into `Bid` and `DeliveryPayload` dataclasses
- **File:** `auction/mcp_robot_adapter.py` (new) or extend `auction/discovery_bridge.py`
- **Depends on:** Need to verify exact request/response format of Anuraj's MCP tools (Step 2)

### Step 6: Marketplace discovers and loads real robots
- [x] **Status:** DONE — `mcp_server.py` queries subgraph at startup, fleet=14 (10 mock + 4 on-chain)
- **What:** Modify `mcp_server.py` startup to query subgraph, create MCPRobotAdapters
- **Flow:**
  1. Query subgraph for `fleet_provider: yakrover` on Base mainnet
  2. For each robot with valid `mcpEndpoint` in metadata, create MCPRobotAdapter
  3. Add to fleet: `fleet = create_full_fleet() + discovered_adapters`
  4. Or: replace mock fleet entirely with discovered robots
- **File:** `mcp_server.py` (modify `build_engine()`)
- **Depends on:** Step 5 (adapter must exist)

### Step 7: Test end-to-end
- [x] **Status:** DONE — Berlin-01 bid ($0.50), executed via MCP, returned 3 waypoints of sensor data
- **Terminals needed:**
  1. Fakerover simulator (port 8080)
  2. Robot MCP server (port 8000)
  3. Cloudflared → robot server
  4. Marketplace MCP server (port 8001)
  5. Cloudflared → marketplace server
- **Test:** Demo page → Run Auction → Berlin robots bid → winner selected → execute → real sensor data
- **Verify:** Feed shows Berlin robot names, delivery data comes from simulator

---

## Unknowns to Resolve

1. **Robot MCP server port** — What port does `serve.py` default to?
2. **update_agent.py + cloudflared** — Does it support non-ngrok URLs?
3. **Robot MCP tool request format** — What does `robot_submit_bid` expect as input? What does it return?
4. **Robot MCP tool response format** — What does `robot_execute_task` return? Does it match `DeliveryPayload`?
5. **Auth** — Does the robot MCP server require `MCP_BEARER_TOKEN`? If so, how does the marketplace authenticate?

## Decision: Keep mock fleet as fallback?

If the robot MCP server is down, the auction should still work with mock fleet. Options:
- **A)** Always include mock fleet + discovered robots (merged fleet)
- **B)** Only use discovered robots when available, fall back to mock fleet
- **C)** Replace mock fleet entirely (auction fails if robot server is down)

Recommend: **B** — try discovered robots first, fall back to mock fleet if none respond.

---

## Open: Stripe Payments to Robot Operators

**Current state (2026-04-06):** Stripe payments go to a hardcoded platform Connect account (`acct_1TEjjLC2lXDckgmS`), not to the robot's operator. USDC payments correctly go to the robot's on-chain `agentWallet`. The Stripe path works for the demo (card charged, authorize/capture flow) but the robot operator doesn't receive the Stripe payout.

**Why:** ERC-8004 on-chain metadata stores `agentWallet` (crypto address) but has no field for `stripe_connect_id`. The marketplace has no way to look up which Stripe Connect account belongs to which robot.

**Options for later:**
1. **On-chain metadata:** Add `stripe_connect_id` to the ERC-8004 agent metadata. Robot operators register their Stripe Connect Express account alongside their wallet. The marketplace reads it from the subgraph like it reads `agentWallet`.
2. **Off-chain registry:** Marketplace maintains a mapping of `robot_id → stripe_connect_id` in its own database. Operators register their Stripe account via a separate onboarding flow.
3. **Stripe Connect onboarding link:** Marketplace generates a Stripe Connect onboarding URL for each robot operator. After completion, the Connect account ID is stored and associated with the robot.

**Recommendation:** Option 1 (on-chain) is most aligned with the decentralized architecture. Requires coordination with 8004 team to add the metadata field to the registration flow. Option 2 is faster to implement but adds a centralized dependency.

---

## Open: Stable Tunnel URLs (Priority)

**Current state (2026-04-06):** Both the marketplace MCP server and robot MCP server use free `trycloudflare.com` tunnels that generate a random URL each time they start. This means:
- On-chain robot MCP endpoints go stale whenever the tunnel restarts (requires `update_agent.py` + on-chain tx + gas + subgraph re-indexing)
- Demo page requires manually pasting the marketplace tunnel URL each session
- Can't send a demo link to someone and have it "just work"

**Impact:** Every demo session requires 5+ minutes of setup (start simulators, start servers, start tunnels, update on-chain registrations, paste URLs). A stable URL makes the demo instantly runnable.

**Options:**
1. **Cloudflare named tunnel (free):** Create a Cloudflare account, set up a named tunnel with a fixed subdomain (e.g., `mcp.yakrobot.bid`, `fleet.yakrobot.bid`). Free tier supports this. Requires one-time `cloudflared tunnel create` + DNS CNAME setup.
2. **ngrok static domain (free tier):** ngrok gives one free static domain per account (e.g., `xxx.ngrok-free.dev`). The 8004 repo already supports `NGROK_DOMAIN`. Requires ngrok account.
3. **Dedicated server:** Deploy both servers to a VPS (Fly.io, Railway, Render) with a stable hostname. Most reliable but adds hosting cost.
4. **Hybrid:** Named Cloudflare tunnel for marketplace (it's our infra), ngrok for robot fleet (operator's infra — each operator runs their own ngrok/tunnel).

**Recommendation:** Option 1 (Cloudflare named tunnel) for the marketplace MCP server — we already use Cloudflare (Workers, yakrobot.bid DNS). Option 4 hybrid for robot fleet — operators should manage their own endpoints.

**Two stable URLs needed:**
| Service | Current | Target |
|---------|---------|--------|
| Marketplace MCP server | `random.trycloudflare.com` (changes daily) | `mcp.yakrobot.bid` (permanent) |
| Robot fleet MCP server | `random.trycloudflare.com` (changes daily) | `fleet.yakrobot.bid` or ngrok static domain |

**Setup for Cloudflare named tunnel:**
```bash
# One-time setup
cloudflared tunnel create yakrobot-mcp
cloudflared tunnel route dns yakrobot-mcp mcp.yakrobot.bid

# Then run with:
cloudflared tunnel run --url http://localhost:8001 yakrobot-mcp
# URL is always: https://mcp.yakrobot.bid
```
