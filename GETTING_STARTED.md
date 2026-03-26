# Getting Started — Robot Task Auction

A step-by-step guide to running your first robot task auction with real Stripe payments.

**Time required:** ~15 minutes
**What you'll need:** A computer with Python 3.13+, a free Stripe account, and a terminal

---

## What this does

You'll run a simulated robot marketplace where:
- You post a task ("measure the temperature in Bay 3")
- Three robots evaluate the task — one gets filtered out (wrong sensors), two compete
- The best robot wins based on price, speed, reliability, and confidence — not just cheapest
- The winning robot reads a real (simulated) temperature sensor
- Your Stripe account processes the payment (test mode — no real money)

By the end, you'll see real PaymentIntents and Transfers in your Stripe dashboard.

---

## Step 1 — Get the code

```bash
git clone <this-repo-url>
cd yakrover-auction-explorer
```

Install dependencies (this uses [uv](https://docs.astral.sh/uv/), a fast Python package manager):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
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

Open a terminal and start the simulated robot. This pretends to be a small rover with a temperature and humidity sensor:

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
cd yakrover-auction-explorer
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

**Scenario 1 — Happy Path**
Three robots are discovered. A drone is filtered out (no temperature sensor). Two rovers bid — one at $0.35 (closer, more reliable), one at $0.55 (farther, less experienced). The scoring function picks the best value, not just the cheapest. The winner reads the sensor. You see:

```
[SCORE   ] fakerover-bay3: 0.8751
[SCORE   ] fakerover-bay7: 0.7819
[STATE   ] ... | bidding -> bid_accepted | winner: fakerover-bay3 @ $0.35
[RESULT  ]   Temperature: 22.1C
[RESULT  ]   Humidity: 44.9%
```

**Scenario 2 — No Capable Robots**
A task asks for a welding robot. All three robots are filtered out. No bids, no charge.

**Scenario 3 — Cheapest Doesn't Win**
Two robots bid: one cheap but slow and unreliable ($0.40), one pricier but fast and proven ($0.60). The expensive robot wins because the scoring weights reliability, not just price.

**Scenario 4 — Robot Times Out**
A faulty robot wins the bid but never delivers. After the SLA deadline, it's automatically abandoned. The reservation fee is refunded. The task re-pools and a good robot completes it.

**Scenario 5 — Bad Payload**
A robot delivers garbage data (null temperature, negative humidity). The verification catches it, rejects the delivery, refunds the buyer, and re-pools to a good robot.

At the end you'll see a summary:

```
[WALLET  ] Final buyer balance: $13.80
[REPUTATION] fakerover-bay3: completed=3, completion_rate=1.00
[REPUTATION] badpayload-robot: completed=0, rejection_rate=1.00
[REPUTATION] timeout-robot: completed=0, completion_rate=0.00
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

**4. Transfer funds to the operator:**
```python
transfer = stripe.Transfer.create(
    amount=35,             # EUR 0.35 in cents
    currency="eur",
    destination=account.id,
    metadata={"request_id": "your-task-uuid", "robot_id": "fakerover-bay3"},
)
print(transfer.id)  # e.g. tr_xxx
```

---

## Step 5 — Check your Stripe dashboard

If you ran with a real Stripe test key, go to [dashboard.stripe.com/test/payments](https://dashboard.stripe.com/test/payments). You'll see:

- **A PaymentIntent** for the wallet top-up ($5.00)
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
| Robot sensor reading | **Real** — the simulator produces drifting temperature/humidity values |
| Auction scoring | **Real** — four-factor weighted algorithm, mathematically verified |
| Bid signing | **Real** — HMAC-SHA256 cryptographic signatures (Ed25519 available via env var) |
| State machine | **Real** — 11 states with enforced transitions |
| Wallet tracking | **Real** — every debit, credit, and refund is tracked to the cent |
| Reputation | **Real** — computed from actual task outcomes |
| Stripe payments | **Real** (test mode) — actual API calls, visible in Stripe dashboard |
| Robot hardware | **Simulated** — the fakerover simulator stands in for a physical robot |
| On-chain discovery | **Available** — ERC-8004 discovery bridge exists but the demo uses mock robots |

---

## Troubleshooting

**"Is the fakerover simulator running?"**
Scenario 1 needs the simulator at `localhost:8080`. Start it per Step 3.

**"ModuleNotFoundError: No module named 'auction'"**
Make sure you're running from the `yakrover-auction-explorer` directory with `PYTHONPATH=.` set.

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
cd yakrover-8004-mcp
PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py
```

You'll see the fleet endpoint and auction tools listed. Optional flags:

```bash
# With Stripe (test mode):
STRIPE_SECRET_KEY=sk_test_xxx PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py

# With persistent SQLite:
AUCTION_DB_PATH=./auction.db PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py

# Specific robot plugins only:
PYTHONPATH=src:marketplace uv run python marketplace/serve_with_auction.py --robots fakerover
```

**Connect Claude Code:**

```bash
claude mcp add --transport http fleet http://localhost:8000/fleet/mcp
```

**Then talk naturally:**

- "Check the temperature in Bay 3"
- "What robots are available?"
- "Fund my wallet with $5"

The simplest path is `auction_quick_hire` — it posts a task, collects bids, picks the best robot, executes, and confirms delivery in a single call. The agent will use it automatically for straightforward requests.

For fine-grained control, the individual tools (`auction_post_task`, `auction_get_bids`, `auction_accept_bid`, `auction_execute`, `auction_confirm_delivery`) let you inspect and intervene at each step.

---

## Demo to Production

The demo uses mock robots and Stripe test mode. Here is what changes for production — and what stays the same.

**What stays the same:**
- The auction engine, scoring, state machine, wallet ledger, and MCP tool interface are identical
- The 15 MCP tools work the same way whether robots are simulated or real
- Agent conversations are the same — "Check the temperature in Bay 3" works in demo and production

**What changes:**

| Component | Demo | Production |
|-----------|------|------------|
| **Robots** | `mock_fleet.py` — 5 simulated robots | Real robots discovered via ERC-8004 on-chain registry (`discovery_bridge.py`) |
| **Hosting** | `localhost:8000` | Cloud server with `--ngrok` or a public URL |
| **Stripe keys** | `sk_test_xxx` — test mode, no real money | `sk_live_xxx` — real charges and payouts |
| **Card onboarding** | Manual `.env` setup | Stripe Shared Payment Tokens (SPTs) — agent-initiated card linking |
| **Operator payouts** | Stub or test transfers | Stripe Connect Express — operators complete hosted KYB onboarding (~2 min) |
| **Agent connection** | `claude mcp add ... http://localhost:8000/fleet/mcp` | `claude mcp add ... https://your-public-url/fleet/mcp` |

**Production checklist:**
1. Register robots on ERC-8004 Sepolia (or mainnet) — each robot gets an on-chain identity
2. Deploy the MCP server to a cloud host with a stable public URL (or use `--ngrok` with a static domain)
3. Set `STRIPE_SECRET_KEY` to a live key and `AUCTION_DB_PATH` for persistent state
4. Onboard operators via `auction_onboard_operator` — they complete Stripe Connect Express KYB
5. Fund buyer wallets via `auction_fund_wallet` with real card payments
6. Connect AI agents to the public fleet endpoint

---

## Next steps

- **Connect real robots** — Register a robot on ERC-8004 Sepolia and use the discovery bridge to include it in auctions. See `auction/discovery_bridge.py`.
- **Use as an MCP server** — Run `serve_with_auction.py` and connect Claude Code. The 15 auction tools are available via natural conversation. See the "Running as an MCP Server" section above.
- **Add crypto payments** — The x402/USDC path is on the roadmap. See `docs/ROADMAP.md`.
- **Read the architecture** — `docs/DECISIONS.md` has every design decision. `docs/USER_JOURNEY.md` tells the full product story.
