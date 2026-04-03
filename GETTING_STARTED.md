# Getting Started — Robot Task Auction Marketplace

A step-by-step guide to running your first robot task auction with real Stripe payments. The marketplace targets **construction site surveying** as its wedge market — tasks range from $1,000 pre-bid topo surveys to $72,000+ full-project monitoring contracts.

**Time required:** ~15 minutes
**What you'll need:** A computer with Python 3.13+, a free Stripe account, and a terminal

---

## What this does

You'll run a simulated robot marketplace where:
- You post a task ("pre-bid topographic survey, SR-89A milepost 340-342, 12 acres")
- Operators evaluate the task — one gets filtered out (insufficient accuracy), two compete
- The best operator wins based on price, speed, reliability, and confidence — not just cheapest
- The winning operator executes the survey and delivers processed data (LandXML, DXF, CSV)
- Your Stripe account processes the payment (test mode — no real money)

By the end, you'll see real PaymentIntents and Transfers in your Stripe dashboard.

---

## Step 1 — Get the code

```bash
git clone https://github.com/YakRoboticsGarage/yakrover-marketplace.git
cd yakrover-marketplace
```

Install dependencies (this uses [uv](https://docs.astral.sh/uv/), a fast Python package manager):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync --all-extras
```

Verify it worked:

```bash
uv run python -m pytest auction/tests/ -q
```

You should see `151 passed` across 10 test files. If so, everything is installed correctly.

---

## Step 2 — Set up a Stripe account (free, 5 minutes)

1. Go to [dashboard.stripe.com/register](https://dashboard.stripe.com/register) and create an account. You don't need to activate it — test mode works immediately.

2. Once logged in, make sure you're in **test mode** (toggle in the top-right corner of the dashboard — it should say "Test mode" with an orange badge).

3. Go to [dashboard.stripe.com/test/apikeys](https://dashboard.stripe.com/test/apikeys) and copy your **Secret key**. It starts with `sk_test_`.

4. Enable **Stripe Connect** at [dashboard.stripe.com/connect](https://dashboard.stripe.com/connect). This is required for operator payouts (transfers to robot operator accounts). Click through the setup — no business verification needed for test mode.

5. Create a `.env` file in the project root (or copy `.env.example`):

```bash
echo 'STRIPE_SECRET_KEY=sk_test_PASTE_YOUR_KEY_HERE' > .env
```

**Currency note:** If your Stripe account is based in Germany (DE) or another EU country, all charges and transfers must use **EUR**, not USD. The Stripe API will reject USD charges on DE-based accounts. The demo code uses EUR by default.

That's it for Stripe. No credit card, no business verification — test mode is instant.

---

## Step 3 — Start the robot simulator

Open a terminal and start the simulated robot fleet. In production, these would be real survey drones (DJI Matrice 350 RTK) and ground robots (Boston Dynamics Spot with GPR), but for development the simulator stands in:

```bash
cd ../yakrover-8004-mcp
PYTHONPATH=src uv run python -m robots.fakerover.simulator
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8080
```

Leave this running. Open a **second terminal** for the next step.

---

## Step 4 — Run the auction demo

In your second terminal:

```bash
cd yakrover-marketplace
PYTHONPATH=. uv run python auction/demo.py
```

If your `.env` file has the Stripe key, you'll see:

```
[CONFIG  ] Stripe mode: live (test)
```

If you didn't set up Stripe, you'll see `Stripe mode: stub` — everything still works, payments are just logged instead of hitting Stripe.

---

## What you'll see

The demo runs 5 scenarios automatically:

**Scenario 1 — Happy Path (Site Survey)**
Three operators are discovered. One is filtered out (8 cm accuracy does not meet the 5 cm requirement). Two compete — one at $2,200 (stronger reputation, 47 completed surveys), one at $2,600 (fewer completions). The scoring function picks the best value, not just the cheapest. The winner executes the survey. You see:

```
[SCORE   ] skyview-mapping: 0.8751
[SCORE   ] desert-hawk-geo: 0.7819
[STATE   ] ... | bidding -> bid_accepted | winner: skyview-mapping @ $2,200
[RESULT  ]   Survey: 12-acre LiDAR topo complete
[RESULT  ]   Deliverables: LandXML, DXF, CSV cross-sections
```

**Scenario 2 — No Capable Robots**
A task asks for subsurface GPR in a region with no registered operators. All operators are filtered out. No bids, no charge.

**Scenario 3 — Cheapest Doesn't Win**
Two operators bid: one cheap but slow and less experienced ($1,400), one pricier but fast and proven ($2,200). The expensive operator wins because the scoring weights reliability, not just price.

**Scenario 4 — Operator Times Out**
A faulty operator wins the bid but never delivers. After the SLA deadline, it's automatically abandoned. The reservation fee is refunded. The task re-pools and a good operator completes it.

**Scenario 5 — Bad Payload**
An operator delivers unusable data (wrong coordinate system, insufficient point density). The verification catches it, rejects the delivery, refunds the buyer, and re-pools to a good operator.

At the end you'll see a summary:

```
[WALLET  ] Final buyer balance: $4,200.00
[REPUTATION] skyview-mapping: completed=3, completion_rate=1.00
[REPUTATION] badpayload-operator: completed=0, rejection_rate=1.00
[REPUTATION] timeout-operator: completed=0, completion_rate=0.00
```

---

## Step 5a — Enable Stripe Connect (for operator payouts)

If you want to test real transfers to robot operator accounts, you need Stripe Connect enabled:

1. Go to [dashboard.stripe.com/connect](https://dashboard.stripe.com/connect) and enable Connect.
2. The demo can then create **Connect Express** accounts for operators. Each account needs two capabilities: `card_payments` and `transfers` (US-based accounts require both).
3. After creating a Connect account, you must generate an **AccountLink** — this gives the operator a URL to complete Stripe's hosted onboarding (KYB).
4. Capabilities go through `inactive` -> `pending` -> `active`. In test mode this may take a few seconds after the operator completes onboarding.

Once an operator account is active, the platform can transfer funds to it.

---

## Step 5b — Testing with real Stripe transfers

To make a real (test-mode) transfer end-to-end:

**1. Fund the platform balance** (required before any transfer):
```python
import stripe
stripe.api_key = "sk_test_YOUR_KEY"

# tok_bypassPending instantly adds funds to available balance (test mode only)
charge = stripe.Charge.create(
    amount=1000,       # EUR 10.00 in cents
    currency="eur",    # Use EUR for DE-based accounts, not USD
    source="tok_bypassPending",
    description="Fund platform balance for testing",
)
print(charge.id)  # e.g. ch_xxx
```

> **Why not Topup?** `stripe.Topup.create()` does not work for DE-based accounts with USD. Use `Charge.create(source='tok_bypassPending')` instead.

**2. Create a Connect Express account for the operator:**
```python
account = stripe.Account.create(
    type="express",
    country="US",
    capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}},
)
print(account.id)  # e.g. acct_xxx
```

**3. Generate an onboarding link:**
```python
link = stripe.AccountLink.create(
    account=account.id,
    refresh_url="https://example.com/reauth",
    return_url="https://example.com/return",
    type="account_onboarding",
)
print(link.url)  # Open this in a browser to complete onboarding
```

**4. Transfer funds to the operator (construction-scale example):**
```python
transfer = stripe.Transfer.create(
    amount=220000,         # EUR 2,200.00 in cents (aerial LiDAR survey)
    currency="eur",
    destination=account.id,
    metadata={"request_id": "your-task-uuid", "robot_id": "skyview-mapping"},
)
print(transfer.id)  # e.g. tr_xxx
```

---

## Step 5 — Check your Stripe dashboard

If you ran with a real Stripe test key, go to [dashboard.stripe.com/test/payments](https://dashboard.stripe.com/test/payments). You'll see:

- **A PaymentIntent** for the wallet top-up (e.g., $5,000 credit bundle for construction tasks)
- **Transfers** for each settled task (each with `request_id` and `robot_id` in the metadata)

Click any transfer to see the metadata — this is the audit trail connecting the Stripe payment back to the specific robot and task.

---

## Step 6 — Persist tasks to a file (optional)

By default, task state lives in memory and disappears when the demo ends. To keep it:

```bash
AUCTION_DB_PATH=./auction.db PYTHONPATH=. uv run python auction/demo.py
```

After the demo, inspect the database:

```bash
sqlite3 auction.db ".tables"
# Output: bids  ledger_entries  reputation_records  tasks  wallet_balances

sqlite3 auction.db "SELECT request_id, state FROM tasks;"
```

---

## What's real and what's simulated

| Component | Status |
|-----------|--------|
| Survey data generation | **Real** — the simulator produces synthetic survey deliverables (in production: LiDAR point clouds, GPR data, photogrammetry) |
| Auction scoring | **Real** — four-factor weighted algorithm, mathematically verified |
| Bid signing | **Real** — HMAC-SHA256 cryptographic signatures (Ed25519 available via env var) |
| State machine | **Real** — 11 states with enforced transitions |
| Wallet tracking | **Real** — every debit, credit, and refund is tracked to the cent |
| Reputation | **Real** — computed from actual task outcomes |
| Stripe payments | **Real** (test mode) — actual API calls, visible in Stripe dashboard |
| Robot/operator hardware | **Simulated** — the fakerover simulator stands in for physical survey drones and ground robots |
| On-chain discovery | **Available** — ERC-8004 discovery bridge exists but the demo uses mock robots |

---

## Troubleshooting

**"Is the fakerover simulator running?"**
Scenario 1 needs the simulator at `localhost:8080`. Start it per Step 3.

**"ModuleNotFoundError: No module named 'auction'"**
Make sure you're running from the `yakrover-marketplace` directory with `PYTHONPATH=.` set.

**"Stripe mode: stub" even though I set the key**
The key must be in a `.env` file in the project root, or set as an environment variable:
```bash
STRIPE_SECRET_KEY=sk_test_xxx PYTHONPATH=. uv run python auction/demo.py
```

**Tests fail**
Run `uv sync` to make sure all dependencies are installed. Then `uv run python -m pytest auction/tests/ -v --tb=short` to see which test fails and why.

**Stripe: "InvalidRequestError: Topups are not supported"**
DE-based (Germany) Stripe accounts cannot use `stripe.Topup.create()` with USD. Use `stripe.Charge.create(source='tok_bypassPending', currency='eur')` to fund your platform balance instead.

**Stripe: "InvalidRequestError: Must use EUR for charges"**
Your Stripe account's country determines the default currency. DE-based accounts must use `currency='eur'`, not `'usd'`. Update any hardcoded `'usd'` references to `'eur'`.

**Stripe: "Transfer amount exceeds available balance"**
The platform's available balance must be funded before making transfers to Connect accounts. In test mode, use `stripe.Charge.create(source='tok_bypassPending', currency='eur', amount=1000)` to add funds.

**Stripe Connect: Capabilities stuck on "inactive"**
After creating a Connect Express account, the operator must complete onboarding via the AccountLink URL. Capabilities go `inactive` -> `pending` -> `active`. In test mode, this happens within seconds after onboarding. Check status with `stripe.Account.retrieve(acct_id)`.

**"dotenv not loading / STRIPE_SECRET_KEY not found"**
Make sure your script includes `from dotenv import load_dotenv; load_dotenv()` before accessing `os.getenv('STRIPE_SECRET_KEY')`. The `.env` file must be in the project root.

---

## Running as an MCP Server

The demo script is great for seeing the auction in action, but the real way to use the marketplace is as an MCP server that any AI agent can talk to naturally.

**Start the server:**

```bash
cd yakrover-marketplace
PYTHONPATH=. uv run python serve_with_auction.py
```

You'll see the fleet endpoint and auction tools listed. Optional flags:

```bash
# With Stripe (test mode):
STRIPE_SECRET_KEY=sk_test_xxx PYTHONPATH=. uv run python serve_with_auction.py

# With persistent SQLite:
AUCTION_DB_PATH=./auction.db PYTHONPATH=. uv run python serve_with_auction.py
```

**Connect Claude Code:**

```bash
claude mcp add-json yak-robotics '{"type":"http","url":"http://localhost:8001/fleet/mcp"}'
```

**Then talk naturally:**

- "I need a pre-bid topo survey for SR-89A milepost 340-342, 12 acres"
- "What operators are available for aerial LiDAR in Phoenix?"
- "Fund my wallet with $5,000"

The simplest path is `auction_quick_hire` — it posts a task, collects bids, picks the best operator, executes, and confirms delivery in a single call. The agent will use it automatically for straightforward requests.

For fine-grained control, the individual tools (`auction_post_task`, `auction_get_bids`, `auction_accept_bid`, `auction_execute`, `auction_confirm_delivery`) let you inspect and intervene at each step.

---

## Demo to Production

The demo uses mock robots and Stripe test mode. Here is what changes for production — and what stays the same.

**What stays the same:**
- The auction engine, scoring, state machine, wallet ledger, and MCP tool interface are identical
- The 15 MCP tools work the same way whether operators are simulated or real
- Agent conversations are the same — "I need a topo survey for SR-89A" works in demo and production

**What changes:**

| Component | Demo | Production |
|-----------|------|------------|
| **Operators** | `mock_fleet.py` — simulated operators | Real drone/robot operators discovered via ERC-8004 on-chain registry (`discovery_bridge.py`) |
| **Survey data** | Synthetic deliverables | Real LiDAR point clouds, GPR data, photogrammetry |
| **Hosting** | `localhost:8001` | Cloud server with a public URL |
| **Stripe keys** | `sk_test_xxx` — test mode, no real money | `sk_live_xxx` — real charges and payouts ($1K-$72K+ construction tasks) |
| **Payment method** | Manual `.env` setup | Payment bonds (public projects), escrow (private), or prepaid credits |
| **Operator payouts** | Stub or test transfers | Stripe Connect Express — operators complete hosted KYB onboarding (~2 min) |
| **Agent connection** | `claude mcp add-json yak-robotics '{"type":"http","url":"http://localhost:8001/fleet/mcp"}'` | Same command with public URL |

**Production checklist:**
1. Register robots on ERC-8004 Sepolia (or mainnet) — each robot gets an on-chain identity
2. Deploy the MCP server to a cloud host with a stable public URL (or use `--ngrok` with a static domain)
3. Set `STRIPE_SECRET_KEY` to a live key and `AUCTION_DB_PATH` for persistent state
4. Onboard operators via `auction_onboard_operator` — they complete Stripe Connect Express KYB
5. Fund buyer wallets via `auction_fund_wallet` with real card payments
6. Connect AI agents to the public fleet endpoint

---

## Next steps

- **Connect real operators** — Register a robot on ERC-8004 Sepolia and use the discovery bridge to include it in auctions. See `auction/discovery_bridge.py`.
- **Use as an MCP server** — Run `serve_with_auction.py` and connect Claude Code. The 15 auction tools are available via natural conversation. See the "Running as an MCP Server" section above.
- **Add crypto payments** — The x402/USDC path is on the roadmap. See `docs/ROADMAP_v4.md`.
- **Read the architecture** — `docs/DECISIONS.md` has every design decision. `docs/USER_JOURNEY_CONSTRUCTION_v01.md` tells Marco's full story — pre-bid survey for a highway project.
- **Explore the product** — `docs/research/PRODUCT_DSL_v2.yaml` is the entire product in one file (2,617 lines).
