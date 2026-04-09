# Plan: Operator Sign-Up and Registration (v1.4)

**Date:** 2026-04-09
**Status:** Plan — ready for review
**Phase:** v1.4
**Personas:** Alex (independent operator), Controller (AP manager)
**Gate for v1.5:** At least 1 operator registered on-chain and bidding on tasks

---

## Summary

Add operator registration to the live demo at yakrobot.bid/demo. A "Register Robot" button sits alongside the existing "Hire Operator" button. The operator fills a form. On submit, the server registers the robot on-chain (ERC-8004 on Base mainnet + Base Sepolia), uploads its agent card to IPFS, and adds it to the bidding fleet. The robot is real — it appears on 8004scan.io and survives server restarts.

---

## What happens when the operator clicks "Register Robot"

### The on-chain registration sequence

The operator fills a form. On submit, the server executes this exact sequence using the `agent0-sdk`:

```
1. SDK(chainId=8453, rpcUrl, signer=SIGNER_PVT_KEY, ipfs="pinata", pinataJwt=PINATA_JWT)
2. agent = sdk.createAgent(name, description, image="")           # in-memory
3. agent.setMCP(mcp_endpoint, auto_fetch=False)                   # in-memory
4. mcp_ep.meta["mcpTools"] = [tool_names]                         # in-memory
5. mcp_ep.meta["fleetEndpoint"] = fleet_url                       # in-memory
6. agent.setTrust(reputation=True)                                # in-memory
7. agent.setActive(True)                                          # in-memory
8. agent.setMetadata({category, robot_type, fleet_provider, ...}) # in-memory
9. agent.registerIPFS()                                           # TWO TRANSACTIONS:
   ├── Tx 1: identity_registry.register("", [{key,value},...])    # mint token + set metadata
   ├── IPFS upload: pinata v3 API → returns CID                   # upload agent card JSON
   └── Tx 2: identity_registry.setAgentURI(agentId, "ipfs://CID")# set token URI
10. wait_mined(timeout=120)                                       # blocks until both txs confirmed
```

**Result:** Robot has an on-chain identity (e.g. `8453:42`), an IPFS agent card with MCP endpoint and tool list, and on-chain metadata (category, robot_type, fleet_provider, sensors, pricing). Visible on 8004scan.io within seconds of tx confirmation.

### Both chains

Registration runs twice — once on Base mainnet (chain 8453) and once on Base Sepolia (chain 11155111). The demo frontend's `discoverRobots()` already queries both chains via The Graph subgraph. The operator gets two agent IDs.

### Then: join the bidding fleet

After on-chain registration, the server also creates an in-memory `ConstructionMockRobot` from the form data and hot-adds it to `engine.robots`. This makes the robot immediately biddable without waiting for subgraph indexing (which can take 1-2 minutes). On the next server restart, the marketplace re-discovers the robot from the subgraph automatically.

---

## User Journey: Alex Registers

### Step 1 — Entry

Alex visits yakrobot.bid/demo and sees two buttons in the sidebar:
- **Hire Operator** (existing — runs the buyer auction flow)
- **Register Robot** (new — opens the operator registration flow)

### Step 2 — Fill the form

Single form. No multi-step wizard.

| Field | Type | Required | Maps to | Notes |
|---|---|---|---|---|
| Robot Name | text | yes | `RobotMetadata.name` | e.g. "Acme Survey Drone" |
| Description | textarea | yes | `RobotMetadata.description` | What the robot does |
| Company / Operator | text | yes | Operator profile `company_name` | Legal business name |
| Contact Email | email | yes | Operator profile + Stripe onboarding | |
| Location | text | yes | `coverage_area.base` | e.g. "Detroit, MI" |
| Equipment Type | select | yes | `BiddingTerms.accepted_task_types` → on-chain `task_categories` | `aerial_lidar`, `terrestrial_lidar`, `photogrammetry`, `gpr`, `rtk_gps`, `thermal_camera`, `robotic_total_station` |
| Model | text | yes | MCP endpoint metadata | e.g. "DJI Matrice 350 RTK + Zenmuse L2" |
| Minimum Bid ($) | number | yes | `BiddingTerms.min_price_cents` | Converted to cents |
| Bid Aggressiveness | range 70-95% | yes | `ConstructionMockRobot._bid_pct` | How aggressively to bid vs. budget ceiling |

### Step 3 — Click "Register & Activate"

The UI shows a progress sequence:

```
Registering on Base mainnet...          ✓ Agent ID: 8453:42
Uploading agent card to IPFS...         ✓ ipfs://QmXxxx
Registering on Base Sepolia...          ✓ Agent ID: 11155111:43
Joining bidding fleet...                ✓ Fleet size: 11 robots
```

Each line appears as the corresponding step completes. Total time: ~30-60 seconds (two on-chain transactions per chain, IPFS upload).

### Step 4 — Confirmation

Success card showing:
- Robot name and on-chain agent IDs (both chains, linked to 8004scan.io)
- IPFS agent card link
- Equipment and eligible task types
- Status: **ACTIVE — BIDDING ENABLED**
- "Your robot will bid on the next matching task posted through Hire Operator."

Below:
- **"Add Credentials"** (collapsed — optional Part 107, COI, PLS upload)
- **"Return to Demo"** button

### Step 5 — Test it

Click "Hire Operator" → post a task requiring the registered robot's sensors → the new robot appears in bid results alongside the existing fleet.

---

## Technical Plan

### New backend endpoint: `POST /api/tool/auction_register_robot_onchain`

This is the core new code. A single MCP tool that:

1. Creates an operator profile (via existing `OperatorRegistry`)
2. Registers the robot on-chain on both Base mainnet and Base Sepolia (via `agent0-sdk`)
3. Creates an in-memory fleet robot for immediate bidding

```python
@mcp.tool()
def auction_register_robot_onchain(
    name: str,
    description: str,
    company_name: str,
    contact_email: str,
    location: str,
    equipment_type: str,
    model: str,
    min_bid_cents: int = 50,
    bid_pct: float = 0.80,
) -> dict:
    """Register a robot on-chain (ERC-8004) and add to bidding fleet."""

    # --- 1. Operator profile (existing registry) ---
    op_id = engine._operator_registry.register(
        company_name=company_name,
        contact_name=company_name,
        contact_email=contact_email,
        location=location,
    )
    engine._operator_registry.add_equipment(op_id, equipment_type, model)

    # --- 2. On-chain registration (both chains) ---
    results = {}
    for chain in ["base-mainnet", "base-sepolia"]:
        sdk = SDK(
            chainId=CHAIN_CONFIG[chain]["chain_id"],
            rpcUrl=CHAIN_CONFIG[chain]["rpc"],
            signer=os.environ["SIGNER_PVT_KEY"],
            ipfs="pinata",
            pinataJwt=os.environ["PINATA_JWT"],
        )

        agent = sdk.createAgent(name=name, description=description, image="")
        agent.setMCP(MCP_ENDPOINT, auto_fetch=False)

        mcp_ep = next(ep for ep in agent.registration_file.endpoints
                       if ep.type == EndpointType.MCP)
        mcp_ep.meta["mcpTools"] = MARKETPLACE_TOOL_NAMES
        mcp_ep.meta["fleetEndpoint"] = FLEET_ENDPOINT

        agent.setTrust(reputation=True)
        agent.setActive(True)
        agent.setX402Support(False)

        # Map equipment_type to task_categories
        sensor_map = {
            "aerial_lidar": "env_sensing",
            "terrestrial_lidar": "env_sensing",
            "photogrammetry": "visual_inspection",
            "gpr": "env_sensing",
            "rtk_gps": "env_sensing",
            "thermal_camera": "visual_inspection",
            "robotic_total_station": "env_sensing",
        }

        agent.setMetadata({
            "category": "robot",
            "robot_type": "survey_platform",
            "fleet_provider": "yakrover",
            "fleet_domain": "yakrobot.bid",
            "min_bid_price": str(min_bid_cents),
            "accepted_currencies": "usd,usdc",
            "task_categories": sensor_map.get(equipment_type, "env_sensing"),
        })

        tx = agent.registerIPFS()
        result = tx.wait_mined(timeout=120)
        results[chain] = {
            "agent_id": result.agentId,
            "agent_uri": result.agentURI,
        }

    # --- 3. Immediate fleet join (in-memory) ---
    from auction.mock_fleet import ConstructionMockRobot
    sensors = [equipment_type]
    robot = ConstructionMockRobot(
        robot_id=op_id,
        name=company_name,
        sensors=sensors,
        capability_metadata={
            "sensors": sensors,
            "mobility_type": "aerial" if "aerial" in equipment_type else "ground",
            "equipment": [{"type": equipment_type, "model": model}],
            "coverage_area": {"base": location},
        },
        reputation_metadata={"completion_rate": 0.95},
        signing_key=f"reg_{op_id}",
        bid_pct=bid_pct,
        sla_seconds=3600,
        ai_confidence=0.85,
    )
    engine.robots.append(robot)
    engine._robots_by_id[op_id] = robot

    return {
        "operator_id": op_id,
        "status": "active",
        "name": name,
        "company": company_name,
        "equipment": {"type": equipment_type, "model": model},
        "sensors": sensors,
        "chains": results,
        "fleet_size": len(engine.robots),
        "message": f"{name} registered on-chain and added to fleet. {len(engine.robots)} robots active.",
    }
```

### Chain configuration

```python
CHAIN_CONFIG = {
    "base-mainnet": {"chain_id": 8453, "rpc": "https://mainnet.base.org"},
    "base-sepolia": {"chain_id": 84532, "rpc": "https://sepolia.base.org"},
}
```

### Required environment variables

| Variable | Purpose | Already set? |
|---|---|---|
| `SIGNER_PVT_KEY` | Signs on-chain transactions (platform wallet) | Needed — the platform signs on behalf of operators |
| `PINATA_JWT` | IPFS upload via Pinata v3 API | Needed |
| `STRIPE_CONNECT_ACCOUNT_ID` | Optional — adds to on-chain metadata | Already exists in some configs |

The platform wallet pays gas (~$0.005 per registration on Base, $0.01 total for both chains). This is negligible.

### Required dependency

The `agent0-sdk` package must be available in the marketplace server's Python environment. Check if it's already in `pyproject.toml` or needs adding.

### Frontend Changes (docs/mcp_demo_5/index.html)

**1. Sidebar button** — "Register Robot" below "Hire Operator"

**2. New phase view** — `id="phase-register"` with form and progress/confirmation sub-states

**3. Form** — fields per the user journey table above

**4. Progress display** — show each registration step as it completes (mainnet tx, IPFS, sepolia tx, fleet join)

**5. After registration** — append the new robot to `discoveredRobots` array so it appears in the Active Operators sidebar immediately

**6. API call** — single POST to `/api/tool/auction_register_robot_onchain` via tunnel URL. Long timeout (120s) because on-chain transactions take time.

### No Worker Changes Required

All calls go directly to the MCP server REST API. The worker is not involved.

---

## UI Wireframe

```
┌──────────────────────────────────────────────────────────────┐
│  SIDEBAR                  │  MAIN AREA                       │
│                           │                                  │
│  [Hire Operator]          │  Register Your Robot             │
│  [Register Robot] ◄─new   │                                  │
│                           │  Robot Name                      │
│                           │  [Acme Survey Drone           ]  │
│                           │                                  │
│                           │  Description                     │
│                           │  [DJI M350 RTK with Zenmuse L2  │
│                           │   for aerial LiDAR surveys    ]  │
│                           │                                  │
│                           │  Company          Email          │
│                           │  [Acme Survey  ]  [alex@acme  ] │
│                           │                                  │
│                           │  Location         Equipment      │
│                           │  [Detroit, MI ]   [aerial_lidar▼]│
│                           │                                  │
│                           │  Model                           │
│                           │  [DJI Matrice 350 RTK + L2    ]  │
│                           │                                  │
│                           │  Min Bid ($)      Aggressiveness │
│                           │  [0.50       ]    [====●====] 80%│
│                           │                                  │
│                           │  [Register & Activate]           │
└──────────────────────────────────────────────────────────────┘

During registration (30-60 seconds):

│  Registering on Base mainnet...          ✓ Agent 8453:42     │
│  Uploading agent card to IPFS...         ✓ ipfs://QmXxxx     │
│  Registering on Base Sepolia...          ✓ Agent 84532:43    │
│  Joining bidding fleet...                ✓ 11 robots active  │

After registration:

│  ✓ Robot Registered On-Chain                                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Acme Survey Drone                                     │   │
│  │ Acme Survey Co. · Detroit, MI                         │   │
│  │                                                       │   │
│  │ Equipment: DJI M350 RTK + L2 (aerial_lidar)          │   │
│  │ Bids at: 80% of budget ceiling                        │   │
│  │                                                       │   │
│  │ Base mainnet:  8453:42    ↗ 8004scan.io               │   │
│  │ Base Sepolia:  84532:43   ↗ 8004scan.io               │   │
│  │ IPFS:          ipfs://QmXxxx  ↗ gateway               │   │
│  │                                                       │   │
│  │ Status: ACTIVE — BIDDING ENABLED                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ▸ Add Credentials (optional)                                │
│  [Return to Demo]                                            │
```

---

## End-to-end test scenario

1. Click "Register Robot"
2. Fill form: Acme Survey Drone, aerial_lidar, DJI M350 RTK + L2, $0.50 min bid, 80%
3. Click "Register & Activate" → watch progress (4 steps, ~30-60 seconds)
4. Confirmation card with agent IDs on both chains. Verify on 8004scan.io.
5. Click "Return to Demo"
6. Click "Hire Operator" → post an aerial LiDAR survey task
7. **Acme Survey Drone appears in the bid results** alongside the Michigan fleet
8. Acme can win the auction, proceed through payment and delivery
9. Restart the MCP server → Acme is re-discovered from the subgraph automatically

---

## Acceptance Criteria

1. "Register Robot" button visible in sidebar alongside "Hire Operator"
2. Single-form registration triggers real on-chain transactions on Base mainnet and Base Sepolia
3. Robot appears on 8004scan.io with correct metadata (category=robot, fleet_provider=yakrover, task_categories, min_bid_price)
4. IPFS agent card contains correct MCP endpoint, tool list, and fleet endpoint
5. After activation, the robot bids on the next matching task
6. Robot appears in Active Operators sidebar (via subgraph discovery or immediate client-side append)
7. Robot survives server restart — re-discovered from subgraph
8. Buyer auction flow is completely unaffected
9. Mode A (platform signs): works with no wallet, token owned by deployer address
10. Mode B (operator wallet): operator provides address, token ownership transferred after mint
11. Mode C (MCP agent): Claude Code can call `auction_register_robot_onchain` and register a robot via conversation. MCP connection snippet shown in UI with copy button.
12. Mobile responsive

---

## Effort Estimate

| Component | Scope |
|---|---|
| `auction_register_robot_onchain` tool | ~80 lines Python. Calls agent0-sdk + creates fleet robot. |
| `agent0-sdk` integration | Verify it's in the Python env. Add chain config constants. |
| Registration phase view (HTML/CSS) | ~150 lines. Single form + progress + confirmation. |
| Registration JS (API call, progress display, state) | ~120 lines. Single fetch with long timeout + step rendering. |
| Sidebar integration (show registered robot) | ~30 lines. Append to `discoveredRobots`. |
| Testing | Register → verify on 8004scan.io → post task → verify bid. |

---

## Risks

1. **Transaction failure.** Base mainnet tx could fail (insufficient gas, nonce collision). Mitigation: catch and show error with retry button. The registration is idempotent — re-running with the same name creates a new agent (ERC-8004 allows multiple agents per signer).

2. **Subgraph indexing delay.** After on-chain registration, the subgraph may take 1-2 minutes to index the new agent. Mitigation: the in-memory fleet robot provides immediate bidding while the subgraph catches up. On next server restart, subgraph discovery takes over.

3. **Platform wallet gas depletion.** Each registration costs ~$0.01 across both chains. At scale this needs monitoring. For demo with <100 registrations, negligible.

4. **IPFS pinning.** If Pinata is down, Tx 1 (on-chain mint) succeeds but Tx 2 (set URI) may reference an unreachable CID. The robot would be on-chain but without a readable agent card. Mitigation: retry IPFS upload before Tx 2.

---

## Wallet Custody Model

### The question

When an operator registers a robot, who holds the private key that owns the on-chain ERC-8004 identity? This determines custody, portability, and how much crypto the operator needs to understand.

### Current state

One platform key (`SIGNER_PVT_KEY`) owns all registered robots — FakeRover-Berlin-01/02/03, Tumbller, Tello. The operator has no key, no wallet, no on-chain ownership. This is the same deployer wallet used for the Berlin FakeRovers.

### v1.4: Three registration paths

The registration form offers two paths. The operator chooses.

**Mode A — Platform registers (default)**

```
Operator fills form → Platform deployer wallet mints ERC-8004 token → Platform owns it
```

- Operator needs: nothing crypto-related. Just the form fields.
- The deployer wallet (same key that registered Berlin FakeRovers) signs both transactions and pays gas.
- The operator is registering a new FakeRover with their own choice of metadata (name, description, sensors, pricing). The on-chain identity belongs to the platform.
- Ownership can be transferred later via `agent.transfer(operatorAddress)` when the operator obtains a wallet.
- UI note on confirmation: "Registered under YAK Robotics platform wallet. Ownership transfer available on request."

**Mode B — Operator signs with own wallet (optional)**

```
Operator connects wallet (MetaMask, Coinbase Wallet, etc.)
→ Operator's wallet signs the registration tx → Operator owns the token
→ Platform relay wallet pays gas (or operator pays their own gas)
```

- Operator needs: a browser wallet (MetaMask, Coinbase Wallet, or any injected provider).
- The form includes a "Connect Wallet" button that calls `window.ethereum.request({method: 'eth_requestAccounts'})`.
- If connected, the registration uses the operator's address as the signer. The minted token is owned by the operator from the start.
- Gas: two options presented in the UI:
  - "Platform pays gas" — the server submits the tx using the relay wallet, but sets the operator's address as owner via a two-step mint+transfer (or the operator signs a meta-transaction).
  - "I'll pay gas" — the frontend builds the tx and the operator signs directly via their wallet. Simpler but requires the operator to have ETH on Base.
- For the demo, "Platform pays gas" + operator-owned token is the cleanest UX. Implementation: platform mints with deployer key, then immediately calls `agent.transfer(operatorAddress)`. Two extra transactions per registration (~$0.005 additional gas).

**Mode C — Register via AI agent (Claude Code / MCP client)**

```
Operator pastes MCP connection command into Claude Code
→ Tells Claude "register my drone" in natural language
→ Claude calls auction_register_robot_onchain with the right parameters
→ Same on-chain registration, same fleet join, invoked via agent instead of form
```

- Operator needs: Claude Code (or any MCP client) installed in their terminal.
- No form to fill. The operator describes their robot in natural language. Claude extracts the fields and calls the tool.
- This is the native agent path — the same MCP server and tools that the buyer side uses.
- The operator can also manage their robot post-registration: check status, update metadata, upload credentials — all via conversation.

Example session:
```
$ claude mcp add --transport http yakrover https://mcp.yakrover.online/mcp

> Register my survey drone. I have a DJI Matrice 350 RTK with
> Zenmuse L2 LiDAR, based in Detroit MI. Company is Acme Survey Co.,
> email alex@acmesurvey.com. Minimum bid $500.

Claude: I'll register your robot on-chain. This will create an ERC-8004
identity on Base mainnet and Base Sepolia...

[calls auction_register_robot_onchain with extracted parameters]

Your robot is registered:
- Base mainnet: Agent 8453:42 (8004scan.io link)
- Base Sepolia: Agent 84532:43
- Fleet status: Active, bidding enabled
- Sensors: aerial_lidar
- Equipment: DJI Matrice 350 RTK + Zenmuse L2
```

### Frontend: three entry paths

The demo page offers all three paths. The form is the primary UI. The MCP path is a secondary option for technical operators.

```
How would you like to register?

  ● Fill out the form below (recommended)
    Register directly in the browser. No tools needed.

  ○ Connect your own wallet
    Use MetaMask or Coinbase Wallet. You own the on-chain identity.
    [Connect Wallet]  Status: Not connected

  ○ Register via Claude Code
    Connect your AI agent to the marketplace MCP server and register
    via conversation. Copy the command below into your terminal:

    ┌──────────────────────────────────────────────────────────┐
    │ claude mcp add --transport http yakrover                 │
    │   https://mcp.yakrover.online/mcp                        │
    │                                                    [Copy]│
    └──────────────────────────────────────────────────────────┘

    Then tell Claude: "Register my survey robot" and describe
    your equipment.
```

Selecting "Register via Claude Code" collapses the form and shows the MCP connection snippet with a copy button. No backend work needed — the `auction_register_robot_onchain` tool is already exposed via MCP at `/mcp`.

### Frontend: signing mode selector (form path)

```
How should this robot be registered?

  ● Register under platform wallet (recommended)
    No wallet needed. Platform manages the on-chain identity.

  ○ Register with my own wallet
    Connect MetaMask or Coinbase Wallet. You own the on-chain identity.
    [Connect Wallet]  Status: Not connected
```

Default is platform wallet. The "own wallet" option expands to show a Connect Wallet button and wallet status. When connected, the submit flow changes to use the operator's address.

### Backend: Mode A implementation (platform signs)

No change from the existing plan. The `auction_register_robot_onchain` tool uses `SIGNER_PVT_KEY` to sign. The minted token is owned by the platform deployer address.

### Backend: Mode B implementation (operator signs)

Two sub-options, in order of preference:

**B1 — Platform mints, then transfers (simpler, server-side only):**

The server mints the token using the deployer key (same as Mode A), then immediately calls `agent.transfer(operator_address)`. The operator provides their address via the form. No client-side signing required — the operator just needs to prove they control the address (or we trust the form input for now).

```python
# After registerIPFS() completes:
if operator_address:
    sdk.web3_client.transact_contract(
        sdk.identity_registry,
        "transferFrom",
        deployer_address,     # from
        operator_address,     # to
        agent_id_int,         # tokenId
    )
```

Cost: 2 extra transactions per chain (~$0.01 total). Token ends up owned by the operator.

**B2 — Operator signs directly via frontend (full self-custody):**

The frontend builds the `register()` calldata, the operator signs via MetaMask, and submits the tx themselves. This requires:
- ethers.js contract interaction in the frontend (already loaded: `ethers` is on the page for USDC flows)
- The ERC-8004 IdentityRegistry ABI (only the `register` and `setAgentURI` functions)
- The operator to have ETH on Base for gas
- A separate server endpoint to handle the IPFS upload (operator can't call Pinata directly without the JWT)

Flow:
1. Frontend collects form data, POSTs to server for IPFS upload only → server returns CID
2. Frontend builds `register(agentURI, metadata[])` tx → operator signs via MetaMask → tx 1
3. Frontend builds `setAgentURI(agentId, "ipfs://CID")` tx → operator signs → tx 2
4. Frontend reports completion to server → server adds to fleet

More work but gives true self-custody. The operator pays their own gas.

**Recommendation for v1.4:** Implement B1 (platform mints + transfer). It's 10 lines of additional Python, no frontend signing complexity, and the operator ends up with real ownership. B2 (full self-custody with MetaMask signing) can be added later — it's additive, not a rewrite.

### Production path (v1.5+)

**Embedded wallets via Coinbase Smart Wallet or Privy.** The operator signs up with email, gets a wallet they never see (MPC-sharded or enclave-stored key), owns their token. No MetaMask required. The platform relay wallet sponsors gas via a paymaster.

This was already flagged in `PLAN_PAYMENT_SETTLEMENT_DEMO.md`: "Operator can't receive USDC → Provide operator onboarding that creates Base wallet via CDP embedded wallets." The v1.4 on-chain tokens are transferable, so nothing minted now is throwaway — tokens can be transferred to embedded wallets when the production onboarding is built.

### Summary

| Mode | Who signs | Who owns token | Operator needs | When |
|---|---|---|---|---|
| A — Platform (default) | Deployer wallet | Platform | Nothing — fill form in browser | v1.4 |
| B — Operator wallet | Deployer wallet, then transfer | Operator | Wallet address (MetaMask, Coinbase Wallet) | v1.4 |
| C — AI agent (MCP) | Deployer wallet | Platform (transfer available) | Claude Code or MCP client in terminal | v1.4 |
| D — Embedded wallet | Privy/CDP wallet | Operator (via email login) | Email address | v1.5+ |

---

## Decisions resolved

1. **Real on-chain registration.** Both Base mainnet and Base Sepolia. No mock path.
2. **Three registration paths.** Form in browser (default), own wallet (optional), or via Claude Code / MCP client. All paths call the same `auction_register_robot_onchain` tool.
3. **Operators register new FakeRovers.** The robot runs on the existing FakeRover infrastructure. The operator chooses their own metadata (name, description, sensors, pricing).
4. **Immediate bidding via in-memory fleet robot.** Don't wait for subgraph. Hot-add to engine on registration.
5. **Compliance is optional.** Part 107, COI, PLS shown as collapsed "Add Credentials" section. Not required for bidding.
6. **Single tool, multiple entry points.** The backend is one MCP tool. The form, wallet flow, and agent path are all frontends to the same call.
7. **Ownership is transferable.** Tokens minted under the platform wallet can be transferred to operator wallets later. Nothing is throwaway.
8. **FakeRover- prefix enforced for demo.** All registered robot names are prefixed with `FakeRover-` so the subgraph discovery (which filters by `fleet_provider=yakrover`) finds them alongside the existing Berlin FakeRovers.

---

## Future: MCP Connection Verification (Robot Liveness)

How the platform verifies an actual MCP connection to a physical robot. Phased approach from simple to rigorous.

### Level 1 — Liveness probe (v1.4, already exists)

The marketplace calls `adapter.is_reachable(timeout=15.0)` on the robot's MCP endpoint during fleet discovery. Proves the endpoint is up. Does not prove a physical robot is behind it.

Used today in `mcp_server.py` during `discover_and_swap_fleet()`. Robots that fail the probe are dropped from the fleet.

### Level 2 — Capability attestation (v1.5)

Ask the robot to prove it has the sensors it claims by calling a standardized challenge tool.

**Implementation:** Add a `robot_health_check` MCP tool standard. The robot returns:
- Live sensor readings (temperature, humidity, GPS coordinates, battery level)
- Hardware serial number (if available from firmware)
- Uptime and last-calibration timestamp

The platform compares the response against registered metadata. If the robot claims `aerial_lidar` but cannot return a point density reading or GPS fix, the capability claim is downgraded.

Record the attestation: "last verified: 2026-04-09, sensors confirmed: aerial_lidar, rtk_gps, battery: 87%."

**Effort:** ~1 day. Requires a `robot_health_check` tool on each robot plugin. FakeRover already has `fakerover_is_online` — extend it.

### Level 3 — Signed telemetry (v2.0)

Robot signs GPS coordinates + timestamps + sensor readings with its ERC-8004 signer key during task execution. The platform verifies the signature chain after delivery.

**What this proves:** The data was produced by the registered robot (not copied from another source). The GPS track matches the task boundary polygon. The timestamps fall within the task execution window.

**Requirements:**
- Robot firmware must implement EIP-712 signing of telemetry payloads
- The same signer key used for on-chain registration signs the telemetry
- Platform stores and verifies the signature chain as part of delivery QA

**Effort:** Significant — requires changes to every robot plugin. The signing primitives exist (ERC-8004 signer key is already used for bid signing), but telemetry signing is a new contract between robot and platform.

### Level 4 — Delivery cross-verification (v2.5+)

Post-delivery verification that the data came from the claimed location and equipment:

- **GPS track vs. boundary polygon:** Compare robot-reported flight path with the task's survey area. Flag if coverage is <80% of the boundary.
- **EXIF/metadata verification:** LAS files contain CRS, point density, scanner model. GeoTIFF files contain GPS coordinates and camera model. Verify these match the registered equipment.
- **Hardware serial matching:** DJI flight logs embed the drone's serial number. Verify it matches the serial registered in the operator profile.

**Depends on:** R-009 (LAS/LAZ validation via PDAL), delivery_schema QA system, equipment serial number field in operator registration.

### Summary

| Level | What | Proves | Phase | Effort |
|---|---|---|---|---|
| 1 — Liveness | Ping MCP endpoint | Endpoint is up | v1.4 (done) | 0 |
| 2 — Attestation | Challenge tool returns live readings | Robot has claimed sensors | v1.5 | ~1 day |
| 3 — Signed telemetry | Robot signs data with ERC-8004 key | Data came from this robot | v2.0 | Weeks |
| 4 — Cross-verification | Compare delivery vs. task boundary | Data is from the right location | v2.5+ | Weeks |
