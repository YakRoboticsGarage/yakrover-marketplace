# Frontend Design Sprint: Robot Marketplace Web Interface

**Date:** 2026-03-27
**Status:** Draft
**Depends on:** v1.0 (built), v1.5 (in progress)
**Companion docs:** `USER_JOURNEY_MARKETPLACE_v01.md`, `ROADMAP_v2.md`, `FEATURE_REQUIREMENTS_v15.md`

---

## Problem Statement

The current marketplace exists only as a set of MCP tools (`auction_post_task`, `auction_quick_hire`, etc.) consumed by AI agents. Sarah's journey works — but only if she already has Claude configured with the marketplace MCP server, an API key pasted by her IT admin, and a pre-funded wallet. This creates three problems a web frontend solves:

1. **Discovery is impossible.** There is no public surface for a new user to find the marketplace, understand what robots are available, or see what tasks cost. The marketplace is invisible to anyone who hasn't already been onboarded.

2. **Onboarding requires IT involvement.** Sarah's journey begins with an IT admin configuring API keys and buying credit bundles. A web frontend can reduce this to: type what you want, connect Claude, connect payment — in that order, with zero IT involvement for the first task.

3. **The marketplace is not agent-discoverable.** Other AI agents (not just Claude with a pre-configured MCP) cannot find or use the marketplace. A web frontend with structured data (schema.org, MCP endpoint metadata, `.well-known/mcp.json`) makes the marketplace discoverable by any agent that can browse the web.

4. **There is no social proof.** Potential users cannot see that real robots are completing real tasks. A live feed of robot activity provides the trust signal that "this thing works" before anyone commits to posting a task.

---

## User Stories

### Human User Story (Sarah v2 — Web-Native)

Sarah is the same facilities manager from the v0.1 journey. But this time, she doesn't have an IT admin who set things up. She found the marketplace herself.

**1. Landing (0 seconds)**
Sarah searches "robot sensor reading service" and lands on the marketplace homepage. She sees:
- A large search bar: **"What do you need?"**
- Below it, a live ticker strip showing recent robot activity: `Ground Rover A completed humidity reading in Helsinki — $0.35 — 42s ago` scrolling alongside `3 robots available near you`
- No login button in the hero. No sign-up wall. The page loads fast and feels alive.

**2. Intent Capture (10 seconds)**
Sarah types: "Temperature and humidity reading in my warehouse, Bay 3"
She presses Enter. The site immediately:
- Stores her raw intent string in the backend (anonymous, no account needed)
- Shows a structured preview: **Task: Sensor Reading / Sensors: temperature, humidity / Location: needs clarification / Estimated cost: $0.25–$0.80 / Estimated time: 30s–3min**
- Below the preview: "To get an exact quote and start the auction, connect your AI assistant."

She has invested 10 seconds and zero credentials. Her intent is captured. She can see this is real.

**3. Claude Connection (30 seconds)**
Sarah clicks "Connect Claude." An OAuth popup opens. She signs in with her Anthropic account (or her company's Claude Enterprise account). Claude now has permission to:
- Structure her natural-language request into a formal task spec (sensor requirements, accuracy thresholds, data format)
- Act as her agent during the auction
- Receive and present results

The page updates with Claude's structured version of her request:
```
Task Spec (structured by Claude):
  - Sensors: temperature (±0.5°C), humidity (±2% RH)
  - Location: Warehouse Bay 3 (needs facility ID — Claude asks Sarah)
  - Max budget: $2.00
  - Deadline: 15 minutes
  - Data format: JSON {temperature_c, humidity_pct, timestamp}
```
Sarah confirms the spec looks right.

**4. Payment Connection (45 seconds)**
Now — and only now — the site asks for payment. Sarah sees two options:
- **Stripe:** "Pay with card" — she enters her corporate Amex. One-click via Stripe Checkout.
- **USDC:** "Pay with crypto" — she connects a wallet (WalletConnect/Coinbase Wallet). Funds on Base.

Sarah chooses Stripe. She enters her card. The site creates a $25 credit bundle (minimum top-up), same as the v0.1 IT-admin flow but self-service. Her card is charged once: `YAK ROBOTICS MARKETPLACE $25.00`.

**5. Auction Live (50 seconds)**
The auction starts automatically. Sarah sees a live view:
- **Status bar:** "Finding robots near Bay 3..."
- **Robot cards appear:** Robot A (Bay 3, 0m away, $0.35, 98% confidence), Robot B (Bay 5, 80m away, $0.55, 91% confidence)
- **Scoring breakdown visible:** Price 40%, Speed 25%, Confidence 20%, Track Record 15%
- **Winner highlighted:** Robot A wins. "Executing now..."
- A progress indicator shows the robot reading its sensor.

**6. Result (92 seconds total)**
The page shows:
```
Bay 3: 22.8°C, 47.3% humidity
Measured by Ground Rover A — 42 seconds — $0.35
Your balance: $24.65
```
Below the result:
- **"Hire again"** button (pre-fills the same task spec)
- **"Add this marketplace to Claude"** button — one click to install the MCP server in Sarah's Claude environment so next time she can just ask Claude directly, no website needed
- **"Download data"** — JSON export of the reading
- **"View receipt"** — Stripe receipt with task ID

**7. Return Visit**
Next time Sarah needs a reading, she has two paths:
- **Web:** Returns to the site, already logged in, types a new request. No re-authentication.
- **Claude direct:** Because she clicked "Add to Claude," her Claude can now use `auction_quick_hire` directly. She never visits the website again — the site's job was to get her onboarded.

---

### AI Agent User Story (Claude as Buyer Agent)

An AI agent (Claude, GPT, or any MCP-capable agent) discovers and uses the marketplace programmatically.

**1. Discovery**
The agent fetches `https://marketplace.yakrobotics.com/.well-known/mcp.json` and finds:
```json
{
  "name": "yak-robotics-marketplace",
  "description": "Robot task auction marketplace — post tasks, robots bid, best one wins",
  "version": "1.5.0",
  "tools": [
    {"name": "auction_post_task", "description": "Post a task for robot bidding"},
    {"name": "auction_quick_hire", "description": "One-call: post, bid, execute, deliver"},
    {"name": "auction_get_status", "description": "Check task status"},
    {"name": "auction_fund_wallet", "description": "Add funds to marketplace wallet"}
  ],
  "auth": {
    "type": "oauth2",
    "authorization_url": "https://marketplace.yakrobotics.com/oauth/authorize",
    "token_url": "https://marketplace.yakrobotics.com/oauth/token",
    "scopes": ["task:post", "task:read", "wallet:read", "wallet:fund"]
  },
  "endpoints": {
    "mcp_sse": "https://marketplace.yakrobotics.com/mcp/sse",
    "mcp_streamable_http": "https://marketplace.yakrobotics.com/mcp/"
  }
}
```

**2. Authentication**
The agent initiates OAuth on behalf of its user. If the user has previously authorized the marketplace (e.g., via the web flow), the agent reuses the existing token. No re-consent needed.

**3. Task Posting**
The agent calls `auction_post_task` with a structured task spec. No natural-language translation needed — the agent already speaks the schema. The agent can also call `auction_quick_hire` for simple tasks.

**4. Monitoring**
The agent subscribes to the SSE endpoint for real-time auction updates (bids arriving, winner selected, execution progress, delivery confirmation).

**5. Payment**
The agent uses the wallet balance already funded by the user. If balance is insufficient, the agent can prompt the user to top up via the web interface or call `auction_fund_wallet` with a pre-authorized payment method.

**6. Result**
The agent receives structured JSON from `auction_confirm_delivery` and presents it to the user in whatever format the user's context requires — chat message, spreadsheet, report, etc.

---

### Operator/Robot Story

Robot operators (like YakRobotics) register their robots and configure pricing. Their robots then appear in the live feed and compete for tasks.

**1. Registration**
Operator visits the operator dashboard (`/operator`). They:
- Create an account and connect a bank account (Stripe Connect Express) or USDC wallet for payouts
- Register each robot: name, location, sensor capabilities, photos, ERC-8004 agent card
- Configure pricing rules: base price per sensor type, distance multiplier, battery discount

**2. Live Feed Presence**
Once registered and online, the robot appears in the homepage ticker:
- `Ground Rover A — Helsinki Warehouse District — temp, humidity, air quality — from $0.25`
- Status: Online (green), Busy (amber), Offline (gray)
- Robots with higher reputation scores appear more prominently

**3. Bidding and Execution**
Robots bid automatically via pre-configured pricing logic — no manual operator involvement. The operator monitors a dashboard showing:
- Active tasks, bid win/loss rate, revenue, robot health
- Alert rules for robot offline, low battery, failed tasks

**4. Payout**
After each successful delivery, payment transfers to the operator's connected account. The operator dashboard shows per-task revenue and a monthly summary. Payout method (Stripe or USDC) is independent of the buyer's payment method — the settlement abstraction (`SettlementInterface`) handles routing.

---

## Design Decisions

### DD-1: Progressive Disclosure (Intent Before Identity)

**Decision:** The user journey follows a strict funnel: **explore -> intend -> authenticate -> pay -> auction -> result**. Authentication and payment are deferred to the latest possible moment.

**Rationale:**
- Sarah's v0.1 journey requires IT-admin setup before she can even ask a question. This inverts the funnel — commitment before exploration.
- Research shows >60% drop-off when sign-up precedes value demonstration.
- Recording anonymous intent first gives us data on what people want (even if they never complete the funnel) and gives the user a taste of the product before asking for anything.

**Implementation:**
- Landing page is fully functional without authentication: search bar works, feed is live, intent is captured in the backend with a session cookie + anonymous ID.
- OAuth gate appears only after intent is structured and the user sees an estimated cost.
- Payment gate appears only after Claude has structured the request and the user has confirmed the task spec.
- Session state persists through the funnel so no data is lost at each gate.

---

### DD-2: Agent-Readable Markup (Schema.org, MCP Endpoint Discovery)

**Decision:** Every page renders both human-visible HTML and machine-readable structured data. The site is an MCP server, not just a website.

**Rationale:**
- The founder's principle: "The website must be agent-readable, not just human-readable."
- AI agents increasingly browse the web. If an agent lands on the marketplace, it should be able to discover the MCP endpoint and start using it programmatically without human intervention.
- Schema.org markup improves SEO (Google understands what the marketplace offers) and agent discovery simultaneously.

**Implementation:**
- `/.well-known/mcp.json` — MCP server metadata, tool list, auth endpoints (see AI Agent user story above)
- Every robot listing includes `schema.org/Product` + `schema.org/Offer` structured data
- Every task result includes `schema.org/Service` + `schema.org/Invoice` structured data
- HTML uses semantic elements: `<article>` for robot cards, `<form>` for task posting, `<output>` for results, `aria-live` for real-time updates
- JSON-LD in `<head>` for the landing page describing the marketplace as a `schema.org/WebApplication`
- OpenAPI spec at `/api/openapi.json` for non-MCP API consumers

---

### DD-3: Payment Connection Architecture (Stripe Connect, Wallet Connect, x402)

**Decision:** Support two payment rails from launch, with the settlement abstraction routing between them transparently.

**Fiat (Stripe):**
- Stripe Checkout for initial credit bundle purchase (Stripe handles PCI compliance)
- `StripeService` (existing in `auction/stripe_service.py`) creates the checkout session
- Stripe Connect Express for operator payouts (existing)
- Stripe Elements embedded in the payment step for returning users (saved card)

**Crypto (USDC on Base):**
- WalletConnect modal for wallet connection (MetaMask, Coinbase Wallet, Rainbow, etc.)
- USDC deposit to platform wallet address on Base (F-3 from v1.5)
- x402 middleware verifies payment on `accept_bid()` (F-1 from v1.5)
- `RobotTaskEscrow.sol` holds USDC during execution (F-2 from v1.5)

**Routing:**
- User chooses `"stripe"` or `"usdc"` during payment connection
- `"auto"` mode (default for returning users) selects based on which funding source has balance
- `SettlementInterface` (F-5) dispatches to `StripeSettlement` or `BaseX402Settlement`
- Operators receive payouts regardless of buyer's payment method

---

### DD-4: Real-Time Robot Feed (WebSocket/SSE for Live Robot Availability)

**Decision:** The homepage ticker and auction live view use Server-Sent Events (SSE) for real-time updates. WebSocket is reserved for bidirectional communication (future chat/negotiation features).

**Rationale:**
- SSE is simpler, uses HTTP (works through proxies/CDNs), auto-reconnects, and is sufficient for the server-to-client push pattern we need.
- The existing MCP server already supports SSE transport (`mcp_sse` endpoint). Reuse the same infrastructure.
- WebSocket adds complexity (custom ping/pong, connection management, no CDN caching) with no benefit for a read-heavy feed.

**Implementation:**
- `/api/feed/events` — SSE endpoint for the homepage ticker. Events: `robot_online`, `robot_offline`, `task_completed`, `task_posted`, `bid_placed`
- `/api/auction/{request_id}/events` — SSE endpoint for a specific auction's live updates. Events: `bid_received`, `bid_scored`, `winner_selected`, `execution_started`, `delivery_confirmed`
- Feed data sourced from `AuctionEngine` (in `auction/engine.py`) event hooks
- Client reconnects with `Last-Event-ID` for seamless recovery
- Initial page load includes last 20 feed items as static HTML (no JS required for first paint)

---

### DD-5: MCP Integration Button ("Add to Claude")

**Decision:** After a user completes their first task via the web, prominently offer a one-click button to add the marketplace MCP server to their Claude environment.

**Rationale:**
- The web frontend is an onboarding funnel, not the primary interface. The goal is to get users into the MCP flow where Claude handles everything directly.
- After the user has seen the marketplace work (live result, real cost, real speed), they have maximum motivation to integrate it into their daily workflow.
- This is the founder's explicit requirement: "a button/mockup to 'Add this MCP to your Claude environment' after first use."

**Implementation:**
- The button generates a Claude Desktop configuration snippet:
```json
{
  "mcpServers": {
    "yak-robotics-marketplace": {
      "url": "https://marketplace.yakrobotics.com/mcp/sse",
      "auth": {
        "type": "oauth2",
        "client_id": "<user-specific>",
        "scopes": ["task:post", "task:read", "wallet:read"]
      }
    }
  }
}
```
- One-click copy to clipboard, with instructions for Claude Desktop, Claude Code, and API usage
- For Claude Desktop: deep link to `claude://mcp/install?config=<base64-encoded-config>` (if supported)
- For API users: show the bearer token and SSE endpoint
- Track conversion: how many web users become MCP users (this is the key metric for the frontend's success)

---

## Wireframes (ASCII)

### Landing Page

```
┌─────────────────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════════════════╗  │
│  ║  YAK ROBOTICS                              [Operator Login]  ║  │
│  ╚═══════════════════════════════════════════════════════════════╝  │
│                                                                     │
│                                                                     │
│                    What do you need?                                 │
│         ┌───────────────────────────────────────────┐               │
│         │ Temperature reading in my warehouse...    │  [Go →]       │
│         └───────────────────────────────────────────┘               │
│                                                                     │
│         Examples: "Humidity check Bay 3" · "Photo of loading dock"  │
│                   "Air quality survey" · "Inventory count aisle 7"  │
│                                                                     │
│  ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──  │
│                                                                     │
│  LIVE ROBOT FEED                                          [pause]   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ● Rover-A completed humidity reading · Helsinki · $0.35    │←  │
│  │   42s ago                                                    │   │
│  │ ● Rover-B came online · Helsinki · temp, humidity, air     │   │
│  │   2m ago                                                     │   │
│  │ ○ Drone-C completed aerial photo · Espoo · $1.20           │   │
│  │   5m ago                                                     │   │
│  │ ● Rover-A won auction · Bay 3 sensor reading · $0.35      │   │
│  │   6m ago                                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──  │
│                                                                     │
│  AVAILABLE ROBOTS (3 online now)                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ 🤖 Rover-A   │ │ 🤖 Rover-B   │ │ 🤖 Drone-C   │               │
│  │ Bay 3        │ │ Bay 5        │ │ Building 2   │               │
│  │ temp/humid   │ │ temp/humid   │ │ camera       │               │
│  │ from $0.25   │ │ from $0.30   │ │ from $0.80   │               │
│  │ ★★★★★ (142) │ │ ★★★★☆ (89)  │ │ ★★★☆☆ (23)  │               │
│  │ ● ONLINE     │ │ ● ONLINE     │ │ ● ONLINE     │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Powered by the Robot Task Auction Protocol                   │   │
│  │ MCP Endpoint: marketplace.yakrobotics.com/mcp/              │   │
│  │ API Docs: /api/openapi.json · Status: All Systems Online    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- No login/signup in the hero area. "Operator Login" is small, top-right, for robot operators only.
- Search bar is the dominant element. Auto-suggest shows common task types.
- Live feed updates via SSE. Initial render is static HTML with last 20 events.
- Robot cards use structured data (`schema.org/Product`) for agent discovery.
- Footer includes MCP endpoint URL — agents reading the page can find it.

---

### Intent Capture

```
┌─────────────────────────────────────────────────────────────────────┐
│  YAK ROBOTICS                                    [Operator Login]   │
│                                                                     │
│  YOUR REQUEST                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ "Temperature and humidity reading in my warehouse, Bay 3"   │   │
│  │                                                   [Edit ✎]  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  WE UNDERSTOOD                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Task Type:      Sensor Reading                             │   │
│  │  Sensors:        Temperature, Humidity                      │   │
│  │  Location:       Warehouse Bay 3 (needs facility ID)        │   │
│  │  Est. Cost:      $0.25 — $0.80                              │   │
│  │  Est. Time:      30 seconds — 3 minutes                     │   │
│  │  Robots nearby:  3 online                                   │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  To get an exact quote, we need your AI assistant to        │   │
│  │  structure this into a precise task specification.           │   │
│  │                                                              │   │
│  │           ┌──────────────────────────┐                      │   │
│  │           │   Connect Claude   →     │                      │   │
│  │           └──────────────────────────┘                      │   │
│  │                                                              │   │
│  │  Claude will:                                               │   │
│  │  · Clarify any missing details (like your facility ID)      │   │
│  │  · Set accuracy thresholds and data format                  │   │
│  │  · Manage the auction on your behalf                        │   │
│  │  · Present your results                                     │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ── LIVE FEED (scrolling) ──────────────────────────────────────   │
│  ● Rover-A completed humidity reading · $0.35 · 42s ago           │
└─────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- The site does a best-effort parse of the natural language input using a lightweight classifier (not Claude yet — Claude comes after auth).
- Cost/time estimates are based on recent auction data for similar tasks.
- "3 online" links to the robot cards on the landing page.
- The intent + preliminary parse are stored server-side with the anonymous session ID.
- The live feed continues at the bottom — the page stays alive.

---

### Authentication Gate

```
┌─────────────────────────────────────────────────────────────────────┐
│  YAK ROBOTICS                                    [Operator Login]   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  CONNECT YOUR AI ASSISTANT                                    │ │
│  │                                                                │ │
│  │  ┌────────────────────────────────────────────────────────┐   │ │
│  │  │                                                        │   │ │
│  │  │  ┌──────────────────────────────────────┐              │   │ │
│  │  │  │  ◆  Sign in with Claude              │              │   │ │
│  │  │  └──────────────────────────────────────┘              │   │ │
│  │  │                                                        │   │ │
│  │  │  ┌──────────────────────────────────────┐              │   │ │
│  │  │  │  ◇  Sign in with API key             │              │   │ │
│  │  │  └──────────────────────────────────────┘              │   │ │
│  │  │                                                        │   │ │
│  │  └────────────────────────────────────────────────────────┘   │ │
│  │                                                                │ │
│  │  "Sign in with Claude" opens Anthropic OAuth.                 │ │
│  │  Your assistant gets permission to post tasks and              │ │
│  │  manage auctions on your behalf.                              │ │
│  │                                                                │ │
│  │  Already have an MCP API key?                                 │ │
│  │  Paste it above for instant access.                           │ │
│  │                                                                │ │
│  │  ────────────────────────────────────────────                 │ │
│  │  YOUR REQUEST (saved):                                        │ │
│  │  "Temperature and humidity reading, Bay 3"                    │ │
│  │  Est. $0.25–$0.80 · 3 robots available                       │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Two auth paths: OAuth (for Claude users) and API key (for developers/IT-admin pre-configured setups).
- The user's original intent is shown at the bottom as a reminder — "this is what you're here for."
- After OAuth, Claude immediately structures the request (this happens server-side) and the user is redirected to the payment step with the structured spec visible.

---

### Payment Connection

```
┌─────────────────────────────────────────────────────────────────────┐
│  YAK ROBOTICS                          Logged in as: Sarah M.  [⚙] │
│                                                                     │
│  TASK READY — CONNECT PAYMENT TO START AUCTION                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  TASK SPEC (structured by Claude)                           │   │
│  │                                                              │   │
│  │  Task:        Sensor reading — temperature + humidity       │   │
│  │  Location:    Helsinki Warehouse, Bay 3 (Facility #HEL-03) │   │
│  │  Accuracy:    Temperature ±0.5°C, Humidity ±2% RH          │   │
│  │  Format:      JSON {temperature_c, humidity_pct, timestamp} │   │
│  │  Max budget:  $2.00                                         │   │
│  │  Deadline:    15 minutes                                    │   │
│  │                                                    [Edit]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  CHOOSE PAYMENT METHOD                                              │
│  ┌──────────────────────────┐  ┌──────────────────────────┐       │
│  │                          │  │                          │       │
│  │   💳 Pay with Card      │  │   ⬡ Pay with USDC       │       │
│  │                          │  │     (on Base)            │       │
│  │   Stripe · Visa, Amex,  │  │                          │       │
│  │   Mastercard             │  │   Connect wallet via     │       │
│  │                          │  │   WalletConnect          │       │
│  │   Min top-up: $25        │  │                          │       │
│  │   (covers ~70 readings)  │  │   Min deposit: $5 USDC  │       │
│  │                          │  │                          │       │
│  └──────────────────────────┘  └──────────────────────────┘       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Already have a balance?                                     │   │
│  │  If your admin pre-funded your account, you're all set.      │   │
│  │  Balance: checking...                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Task spec is fully visible so the user knows exactly what they're paying for.
- Credit bundle model: $25 minimum top-up for fiat, $5 minimum for USDC. This avoids per-task card charges for sub-dollar tasks.
- If the user already has a balance (admin pre-funded), they skip this step entirely.
- Stripe Checkout handles PCI compliance — no card data touches our servers.
- After payment, the auction starts automatically (no extra "Start" button).

---

### Auction Live View

```
┌─────────────────────────────────────────────────────────────────────┐
│  YAK ROBOTICS                                     Balance: $24.65   │
│                                                                     │
│  AUCTION LIVE — Task #t_8f3a2b                                      │
│  Temperature + humidity reading · Bay 3 · Max $2.00                 │
│                                                                     │
│  STATUS: ████████████░░░░░░░░░░░░░░ Collecting bids (4s)           │
│                                                                     │
│  ELIGIBLE ROBOTS                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  ┌─ ROBOT A ─────────────────────────────────────────────┐  │   │
│  │  │  Ground Rover · Bay 3 (0m away) · Battery 87%        │  │   │
│  │  │  ┌──────────────────────────────────────────────────┐ │  │   │
│  │  │  │  BID: $0.35 · Est. 3 min · Confidence 98%       │ │  │   │
│  │  │  │                                                  │ │  │   │
│  │  │  │  Score breakdown:                                │ │  │   │
│  │  │  │  Price ████████░░ 40%  →  9.1/10               │ │  │   │
│  │  │  │  Speed ████████░░ 25%  →  8.5/10               │ │  │   │
│  │  │  │  Conf. █████████░ 20%  →  9.8/10               │ │  │   │
│  │  │  │  Track ████████░░ 15%  →  8.9/10               │ │  │   │
│  │  │  │  ─────────────────────                          │ │  │   │
│  │  │  │  TOTAL: 9.08          ★ WINNING                 │ │  │   │
│  │  │  └──────────────────────────────────────────────────┘ │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌─ ROBOT B ─────────────────────────────────────────────┐  │   │
│  │  │  Ground Rover · Bay 5 (80m away) · Battery 71%       │  │   │
│  │  │  BID: $0.55 · Est. 5 min · Confidence 91%            │  │   │
│  │  │  TOTAL: 7.62                                          │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌─ ROBOT C ─────────────────────────────────────────────┐  │   │
│  │  │  Aerial Drone · Building 2                            │  │   │
│  │  │  FILTERED: No temperature sensor                      │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  TIMELINE                                                           │
│  ○ 9:14:00  Task posted                                            │
│  ○ 9:14:01  3 robots discovered, 1 filtered                       │
│  ○ 9:14:05  2 bids received                                       │
│  ● 9:14:06  Robot A wins ($0.35)  ← you are here                  │
│  ○ ──:──:── Executing...                                           │
│  ○ ──:──:── Delivery                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Real-time updates via SSE from `/api/auction/{request_id}/events`.
- Score breakdown uses the same four-factor formula from `score_bids()` in `auction/core.py`: price 40%, speed 25%, confidence 20%, track record 15%.
- Filtered robots shown with the reason (transparency builds trust).
- Timeline updates live as each event fires.
- Once winner is selected, the view transitions to an execution progress indicator.

---

### Result View

```
┌─────────────────────────────────────────────────────────────────────┐
│  YAK ROBOTICS                                     Balance: $24.65   │
│                                                                     │
│  TASK COMPLETE ✓                                   Task #t_8f3a2b   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │        Temperature:   22.8 °C                               │   │
│  │        Humidity:      47.3 %                                │   │
│  │                                                              │   │
│  │        Measured by:   Ground Rover A                        │   │
│  │        Location:      Warehouse Bay 3, Helsinki             │   │
│  │        Time:          42 seconds                            │   │
│  │        Cost:          $0.35                                 │   │
│  │        Timestamp:     2026-03-27 09:14:42 UTC               │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │
│  │ Hire Again   │  │ Download     │  │ View Receipt         │     │
│  │              │  │ JSON         │  │                      │     │
│  └──────────────┘  └──────────────┘  └──────────────────────┘     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  NEVER VISIT THIS WEBSITE AGAIN                             │   │
│  │  (in the best way possible)                                 │   │
│  │                                                              │   │
│  │  Add this marketplace to your Claude environment and         │   │
│  │  just ask Claude directly next time.                        │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │  + Add to Claude Desktop                               │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │  + Add to Claude Code (CLI)                            │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │  Copy API Key (for other agents)                       │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  COST BREAKDOWN                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Task cost:           $0.35                                 │   │
│  │  Platform fee:        $0.00 (seed phase — free)             │   │
│  │  Total charged:       $0.35                                 │   │
│  │  Previous balance:    $25.00                                │   │
│  │  New balance:         $24.65                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  AUCTION SUMMARY                                                    │
│  Robots discovered: 3 · Eligible: 2 · Bids: 2 · Winner: Rover A   │
│  Auction duration: 6s · Execution: 32s · Total: 42s               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- "NEVER VISIT THIS WEBSITE AGAIN" is the key call-to-action. The website is a funnel to MCP adoption. If users keep coming back to the website, the product has failed to onboard them properly.
- "Hire Again" pre-fills the same task spec for repeat readings.
- JSON download provides the raw structured data (useful for reports, spreadsheets, integrations).
- Receipt links to Stripe receipt (fiat) or Base block explorer (USDC).
- Cost breakdown shows seed-phase zero platform fee explicitly — transparency builds trust and sets expectations for future fee introduction.

---

## Technical Architecture

### Frontend Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Framework** | Next.js 15 (App Router) | SSR for SEO and first-paint speed. Server Components for the landing page (no JS needed for initial render). Client Components for interactive elements (search, auction view). |
| **Language** | TypeScript | Type safety, especially for the structured task spec and auction event types. |
| **Styling** | Tailwind CSS | Utility-first, fast iteration, small bundle. No design system needed at this stage. |
| **Real-time** | Native EventSource (SSE) | Built-in browser API. No library needed. Reconnect logic in a custom hook (~30 lines). |
| **Payment UI** | Stripe.js + Stripe Elements | PCI-compliant card capture. Stripe handles all sensitive data. |
| **Wallet** | WalletConnect v2 + wagmi | Standard wallet connection for USDC on Base. wagmi provides React hooks for wallet state. |
| **Auth** | NextAuth.js (Auth.js v5) | OAuth provider for Claude/Anthropic. API key auth for programmatic access. |
| **State** | React Server Components + `use` hook | Minimal client state. Server components fetch data directly. Client components use SSE for real-time updates. URL state for task/auction IDs. |
| **Deployment** | Vercel (or Cloudflare Workers) | Edge deployment for low latency. Serverless functions for API routes that proxy to the auction engine. |

### Backend API

The frontend talks to the existing auction engine via a thin API layer. No new auction logic in the frontend — it is a presentation layer only.

```
┌─────────────────────────────────────────────────────────┐
│  Next.js Frontend (Vercel)                              │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Server       │ │ Client       │ │ API Routes     │  │
│  │ Components   │ │ Components   │ │ /api/*         │  │
│  │ (SSR, SEO)   │ │ (Interactive)│ │ (proxy)        │  │
│  └──────┬───────┘ └──────┬───────┘ └───────┬────────┘  │
│         │                │                  │           │
└─────────┼────────────────┼──────────────────┼───────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│  Auction Engine API (Python / FastAPI)                   │
│                                                          │
│  POST /api/tasks         → engine.post_task()            │
│  GET  /api/tasks/:id     → engine.get_status()           │
│  POST /api/tasks/:id/accept → engine.accept_bid()        │
│  POST /api/tasks/:id/confirm → engine.confirm_delivery() │
│  GET  /api/tasks/:id/events → SSE auction updates        │
│  GET  /api/feed/events   → SSE global feed               │
│  POST /api/wallet/fund   → wallet.credit()               │
│  GET  /api/wallet/balance → wallet.get_balance()         │
│  GET  /api/robots        → discovery_bridge.discover()   │
│  POST /api/auth/token    → OAuth token exchange           │
│  GET  /api/mcp/sse       → MCP SSE transport             │
│  POST /api/mcp/          → MCP Streamable HTTP           │
│                                                          │
│  Components used:                                        │
│  · AuctionEngine (auction/engine.py)                     │
│  · WalletLedger (auction/wallet.py)                      │
│  · StripeService (auction/stripe_service.py)             │
│  · ReputationTracker (auction/reputation.py)             │
│  · SyncTaskStore (auction/store.py)                      │
│  · discovery_bridge (auction/discovery_bridge.py)        │
│  · SettlementInterface (v1.5, auction/settlement.py)     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** The API layer exposes REST endpoints that map 1:1 to existing `AuctionEngine` methods. The 15 MCP tools in `auction/mcp_tools.py` remain the canonical interface for agents. The REST API is for the web frontend only.

### MCP Endpoint

The marketplace is both a website and an MCP server. They share the same backend.

```
Agent discovers: GET /.well-known/mcp.json
                      ↓
Agent connects: SSE  /mcp/sse
           or:  HTTP /mcp/   (Streamable HTTP transport)
                      ↓
Agent authenticates: OAuth2 bearer token
                      ↓
Agent calls tools:  auction_post_task
                    auction_quick_hire
                    auction_get_bids
                    auction_accept_bid
                    auction_execute
                    auction_accept_and_execute
                    auction_confirm_delivery
                    auction_reject_delivery
                    auction_cancel_task
                    auction_get_task_schema
                    auction_get_status
                    auction_fund_wallet
                    auction_get_wallet_balance
                    auction_onboard_operator
                    auction_get_operator_status
```

The `.well-known/mcp.json` file is served by the Next.js frontend as a static route. It points to the Python backend's MCP transport endpoints. This means an agent that visits the website's domain automatically discovers the MCP server — no separate discovery step needed.

### Authentication Flow

```
                    Human (web)                    Agent (MCP)
                        │                              │
                        ▼                              ▼
              ┌──────────────────┐          ┌──────────────────┐
              │ Anthropic OAuth  │          │ OAuth2 or        │
              │ (Sign in with    │          │ Bearer Token     │
              │  Claude)         │          │ (from .well-     │
              │                  │          │  known/mcp.json) │
              └────────┬─────────┘          └────────┬─────────┘
                       │                             │
                       ▼                             ▼
              ┌──────────────────────────────────────────────┐
              │           Platform Auth Layer                  │
              │                                                │
              │  OAuth tokens ──→ session (web) or             │
              │                   bearer token (API/MCP)       │
              │                                                │
              │  Scopes:                                       │
              │  · task:post    — post tasks, manage auctions  │
              │  · task:read    — view task status and results  │
              │  · wallet:read  — view balance                 │
              │  · wallet:fund  — add funds                    │
              │  · operator:*   — robot management (operators) │
              └──────────────────────────────────────────────┘
```

**Notes:**
- "Sign in with Claude" uses Anthropic's OAuth provider. This is the same identity Sarah uses for Claude Desktop/API.
- API key auth (bearer token) is available for developer/IT-admin use cases and agents.
- Scopes control what the token can do. A scoped-down token (task:read only) can be shared with monitoring dashboards.
- The web session and the MCP bearer token share the same underlying user identity — a user who logs in via the web can seamlessly transition to MCP.

### Real-Time Data

```
┌─ Browser ──────────────────────────────┐
│                                        │
│  EventSource('/api/feed/events')       │────── Global feed (landing page)
│                                        │
│  EventSource('/api/auction/:id/events')│────── Auction-specific (live view)
│                                        │
└────────────────────────────────────────┘
                    │
                    ▼
┌─ API Server ───────────────────────────┐
│                                        │
│  SSE Publisher                         │
│  · Listens to AuctionEngine events     │
│  · Publishes to connected clients      │
│  · Event types:                        │
│    - robot_online / robot_offline      │
│    - task_posted                       │
│    - bid_received                      │
│    - bid_scored                        │
│    - winner_selected                   │
│    - execution_started                 │
│    - delivery_confirmed               │
│    - delivery_rejected                 │
│    - task_cancelled                    │
│    - task_reposted (failure recovery)  │
│                                        │
│  · Each event includes:                │
│    - event ID (for Last-Event-ID)      │
│    - timestamp                         │
│    - JSON payload                      │
│                                        │
└────────────────────────────────────────┘
```

**Implementation detail:** The `AuctionEngine` in `auction/engine.py` already manages state transitions (posted -> bidding -> accepted -> executing -> delivered). Each transition emits an event. The SSE publisher wraps these transitions and pushes them to connected clients. This requires adding an event callback hook to `AuctionEngine` — a small change to the existing code.

---

## Roadmap

### Phase 0: Static Landing + Intent Capture (1 week)

**Goal:** A live URL that captures user intent and shows robot activity. No auth, no payment, no auction.

**Deliverables:**
- Next.js project scaffolded with Tailwind CSS, deployed to Vercel
- Landing page with search bar, example prompts, and static robot cards
- `/api/intent` endpoint — stores raw search text + anonymous session ID in SQLite (via `SyncTaskStore` or a new lightweight table)
- Mock feed ticker with realistic but pre-recorded data (replays real v1.0 demo data on a loop)
- `/.well-known/mcp.json` — static file pointing to the future MCP endpoint (returns 503 for now)
- `schema.org/WebApplication` JSON-LD in `<head>`
- Responsive layout (mobile-first)
- Lighthouse score > 90 (performance, accessibility, SEO)

**Backend changes needed:** None. Phase 0 is frontend-only with a mock API.

**Success metric:** The URL is live. Someone can type "temperature reading" and the site saves it. The feed feels alive.

---

### Phase 1: Claude Integration + Structured Requests (2 weeks)

**Goal:** Users can type a request, connect Claude, and see a structured task spec. No payment or auction yet.

**Deliverables:**
- Anthropic OAuth integration via NextAuth.js — "Sign in with Claude" button
- After auth, the raw intent is sent to Claude for structuring (via Claude API with a system prompt that knows the `auction_get_task_schema()` format)
- Structured task spec displayed to the user with edit capability
- `/api/tasks` endpoint — creates a task in `AuctionEngine` via `post_task()` (task is created but not funded/started)
- SSE endpoint for the global feed — connects to `AuctionEngine` events (live data replaces mock data)
- Robot discovery: `/api/robots` calls `discovery_bridge.discover()` and renders real robot cards
- Intent-to-task conversion analytics: how many intents become structured specs

**Backend changes needed:**
- Add HTTP event callback to `AuctionEngine` for SSE publishing
- Expose `post_task()` and `get_status()` via REST (in addition to existing MCP tools)
- Ensure `discovery_bridge.py` returns robot data suitable for card rendering (name, location, capabilities, reputation score, online status)

**Success metric:** A user can type a request, sign in with Claude, see a structured spec, and see real robots listed. The feed shows real activity.

---

### Phase 2: Payment + Live Auction (2 weeks)

**Goal:** End-to-end: type request, connect Claude, pay, watch auction, get result. Real money (Stripe test mode or Base Sepolia USDC).

**Deliverables:**
- Stripe Checkout integration for credit bundle purchase (`StripeService.create_checkout_session()`)
- WalletConnect + wagmi for USDC wallet connection
- Payment step in the funnel (after Claude structures the request)
- Auction live view with SSE updates — bids, scoring, winner, execution, delivery
- Result view with data display, JSON download, receipt link
- "Hire Again" button (pre-fills task spec)
- Balance display in header (refreshes after each task)
- Wallet funding page for returning users
- Error states: no robots available (Journey B), robot fails mid-task (Journey C), insufficient balance

**Backend changes needed (depends on v1.5):**
- F-4: Payment method selection at task posting (`payment_method` field)
- F-1: x402 middleware on `accept_bid()` for USDC path
- F-5: `SettlementInterface` routing between Stripe and Base x402
- REST endpoints for `accept_bid()`, `confirm_delivery()`, `fund_wallet()`, `get_wallet_balance()`

**Success metric:** A user completes the full journey from "What do you need?" to seeing a sensor reading, with real payment. Both fiat and USDC paths work.

---

### Phase 3: Agent-Readable + MCP Discovery (1 week)

**Goal:** The website is fully agent-readable. The "Add to Claude" button works. Agents can discover and use the marketplace by visiting the URL.

**Deliverables:**
- `/.well-known/mcp.json` returns live MCP server metadata (tools, auth, endpoints)
- MCP SSE and Streamable HTTP transports exposed at `/mcp/sse` and `/mcp/` (proxied to Python MCP server)
- Schema.org structured data on all pages: robot cards (`Product`), task results (`Service`), auction results (`Offer`)
- "Add to Claude Desktop" button — generates config JSON, copies to clipboard
- "Add to Claude Code" button — generates `claude mcp add` command
- "Copy API Key" button — generates a scoped bearer token
- OpenAPI spec at `/api/openapi.json`
- Conversion tracking: web user -> MCP user
- Operator dashboard: robot registration, pricing config, revenue/payout view, robot health monitoring

**Backend changes needed:**
- MCP transport endpoints need CORS headers for cross-origin agent access
- OAuth token generation for "Add to Claude" flow
- Scoped token creation endpoint

**Success metric:** An AI agent can fetch `/.well-known/mcp.json`, connect to the MCP endpoint, authenticate, and complete a task — all programmatically, no human in the loop after initial OAuth consent.

---

## Dependencies on v1.1.1/v1.5

| Frontend Phase | Backend Dependency | v1.5 Feature | Status |
|---|---|---|---|
| Phase 0 | None | — | Can start immediately |
| Phase 1 | `AuctionEngine` event hooks for SSE | Not in v1.5 scope (new) | Needs ~1 day of backend work |
| Phase 1 | REST API layer on top of `AuctionEngine` | Not in v1.5 scope (new) | Needs ~2 days of backend work |
| Phase 1 | `discovery_bridge.py` returning card-renderable data | Partially exists | Minor enrichment needed |
| Phase 2 | Payment method selection at task posting | F-4 (Must) | Blocked until v1.5 F-4 ships |
| Phase 2 | x402 middleware for USDC payment | F-1 (Must) | Blocked until v1.5 F-1 ships |
| Phase 2 | Settlement abstraction interface | F-5 (Must) | Blocked until v1.5 F-5 ships |
| Phase 2 | Wallet top-up with USDC | F-3 (Must) | Blocked until v1.5 F-3 ships |
| Phase 3 | MCP transport (SSE + Streamable HTTP) | Exists in fleet server (`src/core/server.py`) | Needs to be exposed via public URL |
| Phase 3 | OAuth token generation | Not in v1.5 scope (new) | Needs ~1 day of backend work |

**Critical path:** Phase 0 can start immediately (parallel with v1.5 development). Phase 1 needs minor backend additions. Phase 2 is blocked on v1.5 crypto rail features (F-1, F-3, F-4, F-5). Phase 3 needs the MCP transport to be publicly accessible.

**Recommended approach:** Start Phase 0 now. Start Phase 1 backend work (event hooks, REST API) in parallel with v1.5. Phase 2 starts when v1.5 F-1/F-3/F-4/F-5 ship. Phase 3 follows immediately.

---

## Considerations

### Privacy (Diane's Story)

Diane's privacy requirements (encrypted task specs, TEE-based matching, viewer keys) affect the frontend in v2.0+:

- **Task posting UI must support `privacy: true` toggle** — when enabled, the task spec is encrypted client-side before submission. The UI should indicate "This task spec will be encrypted. Only the winning robot will see the full details."
- **Result view must support viewer keys** — Diane's CFO can view task metadata with a viewer key. The frontend needs a "shared audit view" that decrypts metadata for authorized viewers.
- **Robot cards must not leak private task data** — when a robot completes a private task, the feed shows "Rover-A completed a task — $0.35" without task details.
- **No frontend changes needed for v1.5** — the privacy-aware foundation (F-6 commitment hash, F-7 hidden wallet addresses, F-9 encrypted at rest) is all backend. The frontend only needs to avoid displaying wallet addresses in robot cards (which it wouldn't do anyway — robot cards use `robot_id` and capability descriptions).

### Lunar (Kenji's Story)

Kenji's lunar tasks have fundamentally different timing (minutes, not seconds) and status patterns:

- **Auction live view must handle long bid windows** — 30-120 seconds for DTN round-trip, not 6 seconds. The UI should show "Waiting for bids via deep-space relay — this takes longer than Earth tasks" with a progress indicator calibrated to the expected window.
- **Task status must support "in transit" states** — task spec sent to Moon, awaiting rover response, rover executing (checkpoint updates), data returning to Earth.
- **Result view must handle partial results** — checkpoint-and-resume means partial data may be available before the full task completes. The UI should show incremental results.
- **No lunar-specific frontend work in Phase 0-3** — the web frontend launches for Earth tasks only. Lunar UI adaptations are a Phase 4+ concern. However, the component architecture should avoid hardcoding Earth-speed assumptions (e.g., no "this should take seconds" copy baked into components — use dynamic timing estimates from the task spec).

### Mobile-First vs Desktop

**Decision: Mobile-first, desktop-enhanced.**

- The landing page (search bar + feed) works perfectly on mobile. It's a search engine UX.
- The auction live view is richer on desktop (score breakdown, timeline) but degrades gracefully to a simpler "bid → winner → result" flow on mobile.
- The operator dashboard is desktop-only (complex tables, fleet management). Operators are not managing robots from their phones.
- Tailwind CSS responsive utilities handle the breakpoints. No separate mobile codebase.

### Accessibility

- Semantic HTML throughout: `<main>`, `<nav>`, `<article>`, `<form>`, `<output>`
- `aria-live="polite"` on the feed ticker and auction status updates (screen readers announce changes)
- `aria-live="assertive"` on auction winner announcement and delivery confirmation
- All interactive elements keyboard-navigable (tab order, Enter/Space activation)
- Color contrast meets WCAG AA. Score breakdown uses both color and text labels (not color alone).
- Reduced motion: `prefers-reduced-motion` disables feed ticker animation, replaces with static list

### SEO and Discoverability

- Server-side rendering (Next.js SSR) ensures search engines see full page content
- `schema.org/WebApplication` JSON-LD on the landing page
- `schema.org/Product` on each robot card (discoverable as a service listing)
- `<meta>` tags for Open Graph (social sharing: "Robot marketplace — hire a robot in 42 seconds")
- Dynamic `<title>` and `<meta description>` for task result pages (shareable URLs)
- `/.well-known/mcp.json` for agent discovery (non-standard but emerging convention)
- `/robots.txt` allows crawling of all public pages; blocks `/api/` endpoints
- `/sitemap.xml` generated from robot listings and completed task pages
