# Critique: Operator Registration & Demo Engine

**Date:** 2026-04-10
**Context:** v1.4 operator registration is live. The Tumbller has been successfully hired and delivered temperature/humidity data through the demo. This critique evaluates the current state against the real execution path.

---

## The Execution Path That Works

The demo has a proven end-to-end path:

```
Buyer types RFP → Claude parses → Task posted → Robots bid → Winner selected
→ Claude calls auction_execute → MCPRobotAdapter calls robot MCP tools
→ Robot moves + reads sensors → DeliveryPayload returned → QA validates
→ Buyer approves → Payment settles
```

This path works for the Tumbller and FakeRovers because they have **running MCP servers** (on Fly.io at `yakrover.online`) that respond to `tumbller_move`, `tumbller_get_temperature_humidity`, `fakerover_move`, etc.

---

## Critique 1: Registered Operators Can't Execute

**The gap:** An operator registers via the form, their robot is minted on-chain, and it joins the bidding fleet. It can win an auction. But when `auction_execute` is called, the robot's `execute()` method runs `ConstructionMockRobot.execute()` — which returns **pre-fabricated mock survey data** from local JSON files. No real robot action happens.

**Why this matters:** The buyer sees "Delivery Received" with data that came from `auction/data/sample_deliverables/`, not from the operator's actual equipment. The payment settles for work that wasn't done. The operator gets paid for mock data.

**Root cause:** `RuntimeRegisteredRobot` inherits from `ConstructionMockRobot`, which has a local `execute()` that generates fake deliverables. There's no bridge from a form-registered robot to an actual MCP endpoint.

**What would fix it:** The registration form collects the robot's name, equipment, and sensors — but not its **MCP endpoint URL**. A real operator would need to:
1. Run their own robot MCP server (using `yakrover-8004-mcp` or their own implementation)
2. Register the MCP endpoint in the IPFS agent card (`services[].endpoint`)
3. The marketplace would then create an `MCPRobotAdapter` (not a `RuntimeRegisteredRobot`) that calls the operator's real MCP tools

**Current workaround:** The demo works because the FakeRover fleet and Tumbller have pre-deployed MCP servers. Form-registered robots are in-memory mock objects that can bid but can't really execute.

**Recommendation:** Add an optional "MCP Endpoint URL" field to the registration form. If provided, the server creates an `MCPRobotAdapter` instead of `RuntimeRegisteredRobot`. If not provided, the robot works in demo mode (mock execution). This is the bridge between "registered identity" and "operational robot."

---

## Critique 2: The Registration Flow Doesn't Explain What Happens Next

**The gap:** After registration, the confirmation card shows the on-chain identity, agent ID, and 8004scan link. It says "ACTIVE — BIDDING ENABLED." But there's no guidance on:
- How the operator's robot will bid (it's automatic, based on `bid_pct`)
- How execution works (the buyer initiates it, not the operator)
- What the operator needs to do (currently: nothing — it's all automated)
- How to connect a real robot MCP server

**Why this matters:** A real operator registering a real drone would expect to know: "What do I do when I win a task?" The answer today is "nothing — the demo auto-executes with mock data." That's fine for a demo but confusing as a product experience.

**Recommendation:** Add a "What's Next" section to the confirmation card:
- "Your robot will automatically bid on matching tasks"
- "To connect real hardware: run your MCP server and update your agent card"
- Link to the Claude Code / MCP connection instructions
- "Try it: go back and click Hire Operator to see your robot bid"

---

## Critique 3: Bid Engine Is One-Size-Fits-All

**The gap:** Every robot uses the same bidding logic: `price = budget_ceiling × bid_pct`. The `bid_pct` slider (70-95%) is the only differentiation. There's no consideration of:
- Task complexity (a 12-acre aerial survey vs. a single room temperature reading)
- Distance to site (a Detroit operator bidding on a Phoenix task)
- Equipment match quality (the robot has LiDAR but the task also wants GPR)
- Time of day / availability

**Why this matters for the demo:** It's fine — the demo shows competitive bidding with different prices. The scoring weights (price 40%, SLA 25%, confidence 20%, reputation 15%) produce meaningful differentiation.

**Why this matters for production:** Real operators price by the acre, by the day, or by deliverable type. A flat percentage of budget ceiling doesn't model real construction survey pricing. The `min_bid_cents` field helps set a floor, but the pricing model needs to evolve.

**Not a demo blocker.** The current model demonstrates the auction mechanism. Real pricing is a v2.0 concern.

---

## Critique 4: MCPRobotAdapter Hardcodes Tool Names

**The gap:** `MCPRobotAdapter.execute()` (line 277-318) hardcodes tool name selection:
- If robot name contains `"tumbller"` → use `tumbller_move` + `tumbller_get_temperature_humidity`
- Else → use `fakerover_move` + `fakerover_get_temperature_humidity`

**Why this matters:** A newly registered robot with custom sensors (e.g., `temperature_and_humidity`) has no tool mapping. If it were connected via a real MCP endpoint, the adapter wouldn't know which tools to call. The tool names are hardcoded, not discovered from the robot's agent card.

**What the IPFS agent card already provides:** `mcpTools[]` — an array of tool names the robot supports. The adapter could use this instead of hardcoding.

**Recommendation:** For v1.5, the adapter should:
1. Read `mcpTools` from the discovered robot's agent card
2. Match task requirements to available tools (e.g., task needs `temperature` → find a tool with "temperature" in its name or description)
3. Fall back to the hardcoded mapping for known robot types

This is the path from "works for Tumbller and FakeRover" to "works for any robot."

---

## Critique 5: QA Validation Is Schema-Only

**The gap:** The `qa_check()` in `confirm_delivery` validates the delivery data against the task's `delivery_schema` — checking that required fields exist, types match, and values are within min/max bounds. It does NOT verify:
- Data came from the robot that won (no signature on delivery)
- Readings are from the correct location (no GPS verification)
- Timestamps are within the execution window
- Sensor accuracy meets spec

**Why this is fine for the demo:** The schema check demonstrates the QA concept. A PASS/FAIL badge appears on the delivery card. The buyer can "Release Anyway" on failure.

**Why this matters for production:** An operator could return fabricated data that passes schema validation. The signed telemetry (v2.0 roadmap) and delivery cross-verification (v2.5 roadmap) address this, but they're not in the current demo.

**Not a demo blocker.** The roadmap already has this planned.

---

## Critique 6: Payment Settlement Is Disconnected from Execution

**The gap:** The payment flow and the execution flow are independent UI phases. The buyer:
1. Authorizes payment (Dispatch phase — card/ACH/USDC)
2. Sees execution happen (Execute phase — robot works, delivery received)
3. Releases payment (Execute phase — "Release Payment" button)

But there's no programmatic link between "robot delivered data" and "payment is released." The buyer manually clicks "Release Payment." If the buyer doesn't click, the auto-accept timer (3600s) eventually releases it.

**Why this is fine for the demo:** The manual release shows the buyer is in control. The auto-accept timer prevents deadlock.

**Why this matters for production:** At scale, buyers won't manually release every payment. The QA PASS should auto-release (with a configurable delay for dispute). The current model is correct for high-value tasks ($1K+) where buyers want to review, but needs auto-release for routine tasks.

---

## Critique 7: Fleet Discovery Runs Once Then Caches

**The gap:** `discover_and_swap_fleet()` runs on the first `auction_post_task` or `auction_process_rfp` call, then sets `_discovery_done = True` and never runs again (unless a fleet filter toggle resets it). A newly registered robot (via the form) is hot-added to the fleet immediately. But a robot registered by someone else (on-chain via their own agent0-sdk) won't appear until the server restarts or a filter toggle forces re-discovery.

**Why this is fine for the demo:** The demo is single-user. The operator registers and immediately bids.

**Why this matters for production:** A multi-user marketplace needs periodic re-discovery (e.g., every 5 minutes) or a webhook/event listener for new ERC-8004 registrations.

---

## Critique 8: The Demo Has Two Invisible Assumptions

**Assumption 1: The MCP server is always on.** The marketplace MCP server runs on Fly.io with `min_machines_running = 1`. The FakeRover fleet runs on a separate Fly.io app (`yakrover-fleet`). If either goes down, auctions fail silently. The demo page shows "Discovering..." but doesn't explain if no robots are found because the server is down vs. no robots exist.

**Assumption 2: Claude orchestrates everything.** The buyer doesn't directly interact with the auction engine — Claude does. If the Anthropic API is down or rate-limited, the entire demo fails. The demo has no fallback for API unavailability.

**These are acceptable for a demo.** But they should be documented in the demo's help/FAQ.

---

## Summary: What's Working vs. What's Theater

| Component | Real | Theater | Notes |
|---|---|---|---|
| **On-chain registration** | Real | — | ERC-8004 mint + metadata on Base mainnet |
| **IPFS agent card** | Real | — | Pinata upload, agent card JSON with tools/endpoints |
| **Robot discovery** | Real | — | Subgraph query, liveness probe, fleet swap |
| **Bidding** | Partially real | `bid_pct` model | Real scoring, but pricing model is simplified |
| **Tumbller execution** | Real | — | Actual `tumbller_move` + sensor reading via MCP |
| **FakeRover execution** | — | Simulated | Runs on Fly.io simulator, not real hardware |
| **Form-registered robot execution** | — | Mock | Returns pre-fab data, no real MCP call |
| **QA validation** | Real | — | Schema check works, but no data authenticity verification |
| **Card payment** | Real | — | Stripe authorize/capture with real test keys |
| **ACH payment** | Real | — | Stripe us_bank_account, real debit |
| **USDC payment** | Real | — | EIP-3009 on Base mainnet, real USDC |
| **Operator gets paid** | Partially real | — | Stripe Connect transfer works, USDC goes to wallet |

---

## Top 5 Recommendations (Priority Order)

1. **Add MCP endpoint URL to registration form.** This is the single change that turns form-registered robots from mock objects into real operators. If the endpoint is reachable, create an `MCPRobotAdapter`. If not, fall back to mock.

2. **Add "What's Next" guidance to confirmation card.** Tell the operator what happens after registration — automated bidding, how to connect real hardware, how to test.

3. **Discover tools from agent card, not hardcoded names.** Read `mcpTools[]` from IPFS to determine what tools to call during execution.

4. **Periodic fleet re-discovery.** Run `discover_and_swap_fleet()` every 5 minutes, not just on first request. New robots appear without server restart.

5. **Show execution source in delivery card.** Tell the buyer whether the data came from a real robot (MCPRobotAdapter) or mock execution (RuntimeRegisteredRobot). Transparency builds trust.
