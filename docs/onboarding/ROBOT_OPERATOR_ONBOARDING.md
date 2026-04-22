# Operator Onboarding Guide

Register your robot on the marketplace so it can discover tasks, bid on them, execute work, and get paid. Takes about 5 minutes.

> **Writing your own plugin?** Read [`ROBOT_ACTIVATION_SUMMARY.md`](./ROBOT_ACTIVATION_SUMMARY.md) first — it's a 1-page developer-facing summary of the full path from hardware to live operator, with concrete references to the framework, the reference plugin, and the admin workflow for new equipment types.

---

## How It Works

```
1. REGISTER    You tell us about your equipment. We create an on-chain identity.
2. DISCOVER    Buyers post survey tasks. Your robot shows up as a qualified bidder.
3. BID         Your robot automatically evaluates tasks and submits competitive bids.
4. EXECUTE     You win a task → your robot performs the work → delivers results.
5. GET PAID    Buyer verifies delivery → payment released (card, bank transfer, or USDC).
```

You handle steps 1 and 4. The marketplace handles everything else.

---

## Two Ways to Register

### Option A: Talk to Claude (recommended)

Connect to the marketplace MCP server and describe your setup in plain English:

```bash
# Connect Claude Code to the marketplace
claude mcp add-json yakrover '{"type":"http","url":"https://yakrover-marketplace.fly.dev/mcp"}' && claude
```

Then tell Claude what you have (prefix with "Use yakrover" so Claude knows which tools to use):

> "Use yakrover to register my drone for survey work. I'm Acme Aerial, based in Detroit, Michigan. I have a Matrice 350 with a LiDAR sensor."

Claude will ask a few follow-up questions, fill in sensible defaults for pricing and bidding, and register your robot. The whole process takes about 2 minutes.

**To update your profile later**, just tell Claude:

> "Update my robot's minimum bid to $1.00" or "Change my location to Ann Arbor, MI"

### Option B: Use the Web Form

Go to [yakrobot.bid/demo](https://yakrobot.bid/demo/) → click **Register Robot** → fill out the 3-step form.

**Step 1 — Who you are:** Company name, location, robot name, description.

**Step 2 — What you have:** Select your sensor type, pick your platform model, optionally enter your robot's MCP server URL.

**Step 3 — How you bid:** Set your minimum price (default $0.50), bid aggressiveness (default 80%), and payment preferences.

Click **Register & Activate**. Takes 30-60 seconds to register on-chain.

---

## What You Need (Minimum)

| Information | Example | Why |
|-------------|---------|-----|
| Company name | "Acme Aerial Survey" | Displayed to buyers |
| Equipment type | One of: `aerial_lidar`, `photogrammetry`, `thermal_camera`, `terrestrial_lidar`, `gpr`, `rtk_gps`, `robotic_total_station`, `ground_robot` | Determines which tasks you're eligible for. **Unknown types are rejected with `UNKNOWN_EQUIPMENT_TYPE`** — ask the platform admin to add a new type before registering (they update `SENSOR_TO_CATEGORY` + `COMMON_MODELS`). |
| Location | "Detroit, MI" | Geographic matching — you only see tasks within your service area |

Everything else has smart defaults:

| Field | Default | Can customize |
|-------|---------|---------------|
| Robot name | Generated from company + equipment | Yes |
| Platform model | Common model for your sensor type | Yes |
| Minimum bid | $0.50 | Yes |
| Bid aggressiveness | 80% of buyer's budget | Yes (70-95%) |
| Service radius | 100 km | Yes |
| Network | Base mainnet (production) | Yes |

---

## What Happens With Minimal Registration

If you provide just your company name, equipment type, and location, the platform fills in everything else. Here's exactly what gets created:

**On-chain identity (ERC-8004 on Base mainnet):**
- A unique token is minted — this is your robot's permanent identity on the registry
- An IPFS agent card is published with your equipment info, capabilities, and pricing
- The platform signs and pays for the transaction — no wallet or crypto needed from you
- The platform owns the token initially; ownership can be transferred to your wallet later

**Robot MCP connection:**
- Without an MCP endpoint URL, your robot points to the **platform's shared simulator** (`fleet.yakrover.online/fakerover/mcp`)
- This means your robot can bid on tasks and "execute" them with simulated data — useful for testing the full flow end to end
- Simulated execution returns realistic-looking delivery data (point clouds, scans, readings) but it's not real survey output
- To execute real tasks, provide your own MCP server URL during registration or update it later

**Wallet and payments:**
- Without a USDC wallet, payments are **held by the platform** until you provide a destination
- Without a Stripe Connect account, card/bank payments are unavailable — USDC only
- You can add both at any time after registration

**Test vs. production registration:**
- If you register without a working MCP endpoint (i.e. no real hardware connected), your robot is flagged as `is_test = true` on-chain
- Test robots appear in the demo fleet but are **not visible to production buyers**
- Once you connect real hardware and the platform verifies it, your robot can be promoted to production status

**Marketplace visibility and attestation:**
- Registration alone does not make your robot visible in the marketplace
- The **platform issues an EAS (Ethereum Attestation Service) attestation** classifying your robot as `demo_fleet` (test/demo) or `live_production` (real operator)
- The marketplace filters robots by attestation — only attested robots appear in buyer search results
- For `demo_fleet`: the platform runs `auction_eas_attest` against your `agent_id`; typically same-day.
- For `live_production`: the platform verifies the MCP endpoint is reachable, the wallet is real, and the operator identity is legitimate, then runs `auction_eas_attest` with `fleet_type="live_production"`. Can be same-day for known operators; allow up to 24–48h for first-time registrations while the reviewer checks the setup.

**Bidding:**
- Once attested, your robot starts bidding automatically using the default strategy (80% of buyer's budget, $0.50 floor)
- Bidding is automatic — the marketplace calls your robot's `robot_submit_bid` tool whenever a matching task is posted
- You don't need to do anything for bids to happen

**In short:** With 3 fields you get a registered robot on-chain. Without real hardware, it's flagged as a test robot and uses simulated execution. Once the platform attests your registration, your robot appears in the marketplace and starts receiving bids. To go live with real survey data, connect your own MCP server and add a payment destination.

---

## After Registration

Your robot is registered on-chain but needs platform attestation before it appears in the marketplace. Here's what to do while you wait:

### Connect Real Hardware (optional for demo)

If you have a robot MCP server running, provide the URL during registration or update it later. Without it, your robot uses simulated execution — fine for testing, but won't produce real survey data.

Use the [8004 robot framework](https://github.com/YakRoboticsGarage/yakrover-8004-mcp): create a plugin package at `src/robots/<your_robot>/` with three files — `__init__.py` (subclass `RobotPlugin`, implement `bid()` and `execute()`), `client.py` (how you talk to your hardware — HTTP, SDK, serial, ROS, whatever), and `tools.py` (any robot-specific MCP tools). The framework **automatically** wires up `robot_submit_bid`, `robot_execute_task`, and `robot_get_pricing` for you — no need to implement them directly.

**Host it somewhere public.** Fly.io (~$5/month for a single-robot deployment) or ngrok for testing. You need a stable HTTPS URL — that's what you paste into `mcp_endpoint_url` at registration.

**Partial-hardware readiness.** If your robot has, say, a LiDAR working but the thermal camera isn't wired yet, use a simple `availability.json` file that your plugin's `bid()` method reads on each call. Advertise all your intended capabilities at registration, flip the offline ones to `{"available": false}` in the JSON, and your `bid()` returns `None` (declining) for tasks that need them. Flip them back on once the hardware lands — no redeploy needed. The `berlin_tumbller` plugin is a worked reference for this pattern.

**Reference plugin.** [`src/robots/berlin_tumbller/`](https://github.com/YakRoboticsGarage/yakrover-8004-mcp/tree/main/src/robots/berlin_tumbller) is the simplest working example — ground teleop robot on Base mainnet, ~200 LOC including availability map, pricing formula, and rate limiter.

### Add Credentials (recommended)

These aren't required for demo bidding but will be required for production:

- **FAA Part 107** — Required for commercial drone operations
- **Insurance COI** (ACORD 25) — General liability coverage
- **PLS License** — Required for survey work in most states

Upload via Claude: *"Upload my Part 107 certificate"* → provide the file.

### Set Up Payments (optional)

- **USDC:** Provide your Base wallet address during registration → payments go directly to your wallet
- **Card/Bank:** Provide your Stripe Connect account ID → platform handles payouts
- **Neither:** Payments held by the platform until you configure a destination

---

## Updating Your Profile

### Via Claude

> "Change my minimum bid to $2.00"
> "Update my service radius to 200 km"
> "Add a Stripe Connect account: acct_1ABC123"
> "Change my MCP endpoint to https://my-robot.example.com/mcp"

### What You Can Change

| Field | How |
|-------|-----|
| Company name | Claude or re-register |
| Location | Claude (`auction_update_operator_profile`) |
| Equipment model | Claude |
| Minimum bid | Claude |
| Bid aggressiveness | Claude |
| MCP endpoint | Claude |
| Service radius | Claude |
| Payment destinations | Claude |

On-chain metadata (name, description, sensors) requires IPFS re-upload — tell Claude and it will note the change for the next sync.

---

## How Bidding Works

When a buyer posts a task that matches your equipment:

1. The marketplace checks: Do you have the right sensors? Are you within range? Are you available?
2. Your robot evaluates the task and submits a bid (price + timeline + confidence)
3. Bids are scored: 40% price, 25% speed, 20% confidence, 15% reputation
4. Buyer reviews the top bids and picks a winner
5. Your robot executes the task and delivers results
6. Payment releases after delivery is verified

**Bid aggressiveness** controls how much of the buyer's budget you bid. At 80%, if the buyer's budget is $1,000, you bid $800. Lower = more competitive. Higher = more profit per task.

**Custom pricing.** If the default aggressiveness model doesn't fit — e.g. you charge per motor command, per scanned square meter, or per photo — your plugin's `bid()` method can return any price it wants. The framework's `BiddingTerms` settings (min_price_cents, rate_per_minute_cents) are used by the default `robot_get_pricing` response, but your custom `bid()` can compute price from task parameters however it likes. See the `berlin_tumbller` plugin's pricing formula for a per-command example.

---

## Testing Your Setup

1. Visit [yakrobot.bid/demo](https://yakrobot.bid/demo/)
2. Your robot should appear in the sidebar fleet list (once attested)
3. Select an RFP preset matching your equipment type from the dropdown — presets exist for each task category, including `delivery_ground` ("Teleop — NPC ROBOT Berlin Tumbller"), `env_sensing`, `subsurface_scan`, `topo_survey`, etc. If no preset matches your category, choose **"Other (specify below)"** and paste your own RFP text.
4. Run the auction → your robot should appear in the bid results if the task matches your capabilities and availability map.
5. Accept the bid → your robot executes → delivery data appears (validated against the category's delivery schema).

---

## Questions?

- **Marketplace:** [yakrobot.bid/demo](https://yakrobot.bid/demo/)
- **Robot framework:** [yakrover-8004-mcp](https://github.com/YakRoboticsGarage/yakrover-8004-mcp)
- **Issues:** [GitHub Issues](https://github.com/YakRoboticsGarage/yakrover-marketplace/issues)
