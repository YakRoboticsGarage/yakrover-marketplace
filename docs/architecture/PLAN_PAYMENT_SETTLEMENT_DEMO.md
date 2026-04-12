# Plan: Live Payment Settlement Demo

**Date:** 2026-04-02
**Status:** Draft for review
**Goal:** Add real-money payment settlement to yakrobot.bid/mcp-demo — both Stripe (fiat) and USDC on Ethereum mainnet (crypto), production environment, minimum viable amounts.

> **Design principles (from founder):**
> - Keep it simple — successfully transact real money through a real auction
> - Prefer Ethereum mainnet over L2s where possible
> - Use Splits (splits.org) for platform/operator revenue splitting
> - Price demo tasks in cents ($0.50 Stripe, $0.01 crypto)
> - Use production-registered robots if available (currently on Sepolia via ERC-8004)
> - Both rails must be production, not test mode

---

## Context

The current demo at yakrobot.bid/mcp-demo runs a full auction lifecycle (RFP → bid → award → execute → deliver) but payment is simulated. The internal wallet ledger tracks 25%/75% splits but no real money moves. This plan adds real settlement to close the loop.

### What exists today
- **Stripe Service** (`auction/stripe_service.py`) — PaymentIntent, Connect transfers, stub/live dual mode. Tested live 2026-03-25 with EUR transfers.
- **Wallet Ledger** (`auction/wallet.py`) — thread-safe debit/credit, 25%/75% split, full audit trail.
- **Settlement Abstraction** (`auction/settlement.py`) — Protocol interface designed, no implementations.
- **x402 Protocol Spec** (`yakrover-protocols/04-yakrover-payments/`) — specification only, no code.
- **Bug:** `create_transfer()` hardcodes `currency="usd"` — fails for EUR accounts.

### Demo pricing
- **Stripe tasks:** $0.50 (Stripe's hard minimum for charges)
- **Crypto tasks:** $0.01 USDC (well above Base gas costs of ~$0.007)
- All amounts are production/real money — no test mode

---

## Architecture

```
Buyer (browser)
  |
  |-- Stripe Checkout ($0.50) -----> Stripe PaymentIntent
  |                                    |
  |-- Coinbase Onramp ($0.01 USDC) -> USDC on Base
  |                                    |
  v                                    v
Wallet Ledger (internal)          On-chain balance
  |                                    |
  v                                    v
Auction Engine (existing)         Auction Engine (existing)
  |                                    |
  |-- accept_bid: 25% reserve         |-- accept_bid: USDC approve+hold
  |-- confirm_delivery: 75% + payout  |-- confirm_delivery: USDC release
  |                                    |
  v                                    v
Stripe Transfer (operator)        USDC transfer (operator wallet)
```

---

## Phase 1: Stripe Rail — Real $0.50 Settlement (3-4 days)

### 1a. Fix currency bug
**File:** `auction/stripe_service.py`
**Change:** Add `currency` parameter to `create_transfer()`, default to platform currency.
**Effort:** 30 minutes.

### 1b. Stripe Checkout integration for buyer wallet funding
**What:** Embed Stripe Checkout (or Payment Element) in the mcp-demo page so buyers can fund their wallet with a real card.
**Flow:**
1. Buyer clicks "Fund Wallet — $0.50"
2. Frontend calls worker → worker creates PaymentIntent ($0.50, `automatic_payment_methods`)
3. Stripe Checkout UI collects card → confirms payment
4. Webhook fires → worker credits wallet via MCP server
5. Buyer sees "$0.50 available" in demo

**Files:**
- `chatbot/src/index.js` — new `POST /api/create-payment-intent` endpoint
- `docs/mcp_demo/index.html` — Stripe.js embed, "Fund Wallet" button
- `mcp_server.py` — webhook endpoint for `payment_intent.succeeded`

**Stripe resources needed:**
- Production API key (`sk_live_...`) — switch from test mode
- Webhook endpoint registered in Stripe dashboard
- Stripe.js loaded in mcp-demo page

**Effort:** 2 days.

### 1c. Real operator payout on delivery confirmation
**What:** When `confirm_delivery` fires, the existing `create_transfer()` sends real money to operator's Connect account.
**Requirements:**
- At least one operator with completed Stripe Connect Express onboarding
- Platform Stripe balance > $0.50 (auto-funded by buyer's payment)
- Operator's `acct_...` stored in operator profile or mapped from `robot_id`

**Current gap:** `engine.confirm_delivery()` calls `stripe_service.create_transfer(destination=f"acct_{robot_id}")` — this constructs the account ID from robot_id, which won't match real Connect accounts. Need a lookup table: `robot_id → stripe_account_id`.

**Files:**
- `auction/engine.py` — look up real Stripe account from operator registry instead of constructing it
- `auction/operator_registry.py` — add `stripe_account_id` field to operator profiles

**Effort:** 1 day.

### 1d. Webhook handler for payment confirmation
**What:** Verify PaymentIntent succeeded before crediting wallet. Currently the ledger credits immediately (design issue noted in audit).
**Flow:**
1. Stripe sends `payment_intent.succeeded` to webhook endpoint
2. Handler verifies signature, extracts `metadata.wallet_id`
3. Credits wallet ledger (move credit from 1b here instead of immediate)

**Files:**
- `mcp_server.py` or `chatbot/src/index.js` — webhook handler
- `auction/wallet.py` — add `pending_topup` / `confirm_topup` states

**Effort:** 1 day.

### Phase 1 deliverable
Buyer visits mcp-demo → funds wallet with $0.50 via Stripe → runs auction → operator gets paid $0.50 via Stripe Connect transfer. Real money, production.

---

## Phase 2: Crypto Rail — Real $0.01 USDC Settlement (4-5 days)

### 2a. Choose approach

Three viable options, in order of simplicity:

**Option A: Direct USDC transfer (simplest)**
- Buyer sends USDC directly to operator wallet on Base
- No escrow contract — trust model relies on platform
- ~20 lines of JS (viem/ethers)
- Gas: ~$0.007 per transfer
- Pro: ships in hours. Con: no escrow protection.

**Option B: x402 pay-per-request (agent-native)**
- Protect the `auction_accept_bid` MCP endpoint with x402
- Agent's wallet auto-pays $0.01 USDC to access the endpoint
- Server verifies via Coinbase facilitator
- ~45 lines Python (FastAPI middleware)
- Pro: designed for agent payments. Con: buyer needs USDC wallet.
- x402 Python SDK: `pip install "x402[fastapi]"` (v2.5.0, production-ready, 75M+ tx settled)

**Option C: Simple escrow contract on Base (proper marketplace)**
- Deploy `RobotTaskEscrow.sol` on Base
- `deposit()` → buyer locks USDC in contract
- `release()` → platform releases to operator on delivery confirmation
- `refund()` → returns to buyer on rejection/timeout
- ~80 lines Solidity + deployment script
- Gas: ~$0.05-$0.10 per escrow cycle (5-10% of $1 — acceptable for demo, drops to <1% at $50+ task values)
- Pro: real escrow, matches pitch claims. Con: needs contract audit, more code.

**Recommendation:** Start with **Option B (x402)** because:
- It's production-ready (Coinbase SDK, 75M+ transactions)
- It aligns with the agent-native positioning (AI agents pay for robot services)
- The `yakrover-protocols` repo already has the spec
- It works for the demo ($0.01 per request) and scales to production
- Then add **Option C (escrow)** as Phase 3 for full marketplace integrity

### 2b. x402 integration on MCP server
**What:** Add x402 middleware to `mcp_server.py` so the `auction_accept_bid` endpoint requires USDC payment.
**Flow:**
1. Agent calls `POST /api/tool/auction_accept_bid`
2. Server returns `402 Payment Required` with USDC payment instructions (amount, recipient, chain)
3. Agent's wallet signs a USDC permit/transfer
4. Agent resends request with `PAYMENT-SIGNATURE` header
5. Server forwards to Coinbase facilitator for verification
6. Facilitator settles USDC on Base
7. Server processes the bid acceptance
8. On delivery confirmation: platform transfers USDC to operator wallet

**Files:**
- `mcp_server.py` — add x402 middleware on payment-required endpoints
- `auction/settlement.py` — implement `BaseX402Settlement` class
- New: `auction/x402_config.py` — x402 configuration (facilitator URL, recipient wallet, chain)

**Dependencies:**
- `pip install "x402[fastapi]"` — x402 Python SDK
- Coinbase Developer Platform account (free tier: 1,000 tx/month)
- Platform wallet on Base (receives USDC payments)
- Operator wallets on Base (receive USDC payouts)

**Environment variables:**
```
X402_RECIPIENT_WALLET=0x...     # Platform wallet on Base
X402_FACILITATOR_URL=https://x402.org/facilitator  # Coinbase facilitator
BASE_RPC_URL=https://mainnet.base.org
OPERATOR_WALLET_ADDRESS=0x...   # Demo operator wallet
```

**Effort:** 3-4 days.

### 2c. Buyer wallet funding (USDC)
**What:** Buyer needs USDC on Base to pay. Two options:
- **Coinbase Onramp** (embedded in page) — buyer pays with card, gets USDC. Zero fee for USDC on Base.
- **Manual funding** — buyer already has USDC in MetaMask/Coinbase Wallet.

For the demo, start with manual funding (simpler). Add Coinbase Onramp later for general audience.

**Effort:** 1 day for manual, +2 days for Onramp embed.

### Phase 2 deliverable
Agent calls MCP server → x402 middleware requires $0.01 USDC → agent wallet pays on Base → auction proceeds → operator receives USDC on delivery confirmation. Real crypto, production Base mainnet.

---

## Phase 3: Escrow Contract (Future, 5-7 days)

### 3a. Deploy RobotTaskEscrow.sol on Base
**What:** Simple escrow contract for USDC on Base.
**Functions:**
- `deposit(bytes32 commitmentHash, uint256 amount)` — buyer locks USDC
- `release(bytes32 commitmentHash, address operator)` — platform releases to operator
- `refund(bytes32 commitmentHash)` — returns to buyer
- `getDeposit(bytes32 commitmentHash)` — view deposit status

**Design decisions:**
- Uses commitment hash (FD-4) not raw request_id
- Platform address is the only authorized caller for release/refund (admin role)
- USDC only (no ETH, no other tokens)
- No time-locked auto-refund in v1 (platform triggers manually)

**Testing:** Deploy on Base Sepolia first (free testnet USDC from faucet.circle.com), then Base mainnet.

**Effort:** 3-4 days (contract + tests + deployment).

### 3b. Wire escrow into settlement abstraction
**What:** Implement `EscrowSettlement` class that:
1. On `accept_bid`: calls `escrow.deposit(commitmentHash, amount)`
2. On `confirm_delivery`: calls `escrow.release(commitmentHash, operatorWallet)`
3. On `reject_delivery`: calls `escrow.refund(commitmentHash)`

**Effort:** 2-3 days.

### Phase 3 deliverable
Full escrow-backed settlement: buyer's USDC locked in smart contract on bid acceptance, released to operator on delivery, or refunded on rejection. Matches pitch deck claims.

---

## Demo UX Flow (Post-Implementation)

```
yakrobot.bid/mcp-demo
  |
  [Choose payment method]
  |
  ├── "Pay with Card ($0.50)"
  │     └── Stripe Checkout → wallet funded → auction runs → operator paid via Stripe
  │
  └── "Pay with USDC ($0.01)"
        └── Connect wallet → USDC on Base → x402 payment → auction runs → operator paid in USDC
  |
  [Live auction feed shows each step]
  |
  [Settlement confirmation with tx hash / Stripe transfer ID]
```

---

## Existing Code Reuse

| Component | Exists In | Reusable? |
|-----------|-----------|-----------|
| Stripe PaymentIntent | `auction/stripe_service.py` | Yes — just needs currency fix |
| Stripe Connect Transfer | `auction/stripe_service.py` | Yes — working, tested live |
| Wallet Ledger (25/75) | `auction/wallet.py` | Yes — production-ready |
| Settlement Interface | `auction/settlement.py` | Yes — implement against it |
| x402 Protocol Spec | `yakrover-protocols/04-yakrover-payments/` | Yes — use as implementation guide |
| Wallet generation | `yakrover-8004-mcp/src/core/wallet.py` | Partially — good for operator wallet creation |
| Escrow mock | `auction/tests/scenarios/service_mocks/` | Yes — defines the interface to implement |

---

## Environment & Accounts Needed

### Stripe (Phase 1)
- [ ] Production Stripe account (upgrade from test mode)
- [ ] Webhook endpoint registered in Stripe dashboard
- [ ] At least 1 operator with completed Connect Express onboarding
- [ ] `STRIPE_SECRET_KEY` (live key) in Cloudflare Worker secrets

### Crypto (Phase 2)
- [ ] Platform wallet on Base (holds received USDC, sends operator payouts)
- [ ] Coinbase Developer Platform account (x402 facilitator, free tier)
- [ ] Demo operator wallet on Base
- [ ] `BASE_RPC_URL`, `X402_RECIPIENT_WALLET`, `OPERATOR_WALLET_ADDRESS` env vars
- [ ] Small USDC + ETH balance in platform wallet (for gas on payouts)

### Contract (Phase 3)
- [ ] Base Sepolia testnet USDC (from faucet.circle.com)
- [ ] Contract deployment wallet (needs ETH for gas)
- [ ] Hardhat or Foundry for contract development + testing

---

## Timeline

| Phase | What | Days | Deliverable |
|-------|------|------|-------------|
| **1a** | Fix currency bug | 0.5 | Transfer works for EUR + USD |
| **1b** | Stripe Checkout in mcp-demo | 2 | Buyer funds wallet with real card |
| **1c** | Real operator payout | 1 | Operator receives real Stripe transfer |
| **1d** | Webhook handler | 1 | Payment confirmed before wallet credited |
| **2a** | x402 middleware on MCP server | 3 | Agent pays $0.01 USDC per bid acceptance |
| **2b** | USDC operator payout | 1 | Operator receives USDC on Base |
| **2c** | Buyer USDC funding | 1 | Manual wallet funding for demo |
| **3a** | Escrow contract (Base Sepolia → mainnet) | 4 | On-chain USDC escrow |
| **3b** | Wire into settlement abstraction | 2 | Engine uses escrow for crypto tasks |
| | **Total** | **~15.5 days** | |

### Suggested order
1. Phase 1a (quick fix, unblocks everything)
2. Phase 1b + 1c (Stripe demo works end-to-end)
3. Phase 1d (hardens Stripe flow)
4. Phase 2a + 2b (crypto demo works)
5. Phase 2c (better buyer UX)
6. Phase 3 (escrow, when ready for investor demo)

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Stripe production approval takes time | Start application now; use test mode with real card numbers in the meantime |
| x402 facilitator downtime | Self-host facilitator as backup (x402 SDK supports it) |
| Gas price spike on Base | Use Circle Paymaster (pay gas in USDC) as fallback |
| Smart contract bug | Deploy on Sepolia first; keep amounts tiny ($0.01-$1); get informal review before mainnet |
| Buyer doesn't have USDC | Phase 2c (Coinbase Onramp) solves this; initially demo to crypto-native audience |
| Operator can't receive USDC | Provide operator onboarding that creates Base wallet via CDP embedded wallets |
| Double-spend / replay on x402 | x402 facilitator handles this; uses nonces per specification |

---

## Splits.org Integration (Revenue Splitting)

**What:** Splits (splits.org) provides audited, open-source smart contracts for on-chain revenue distribution. Zero protocol fees — only gas costs.

**How it fits:** After a task settles, payment flows through a Split contract that auto-distributes:
- 88% → operator wallet
- 12% → platform wallet (commission)

**Technical details:**
- Deployed on Ethereum mainnet, Base, Optimism, Polygon, Arbitrum + 8 more chains
- Supports ETH and all ERC-20s (including USDC)
- SDK available: `@0xsplits/splits-sdk` (TypeScript), React SDK, API
- Contract types: Split (continuous distribution), Waterfall (expenses first), Swapper (auto-convert to stablecoins)
- No fees, ever — runs at gas cost only

**For the demo:**
1. Create a Split contract on Ethereum mainnet: `{operator: 88%, platform: 12%}`
2. When buyer pays, USDC goes to the Split address
3. Split auto-distributes on `withdraw()` — operator gets 88%, platform gets 12%
4. Fully transparent, auditable on-chain

**Advantage over custom escrow:** Splits is already audited and deployed. We don't need to write or audit our own payment distribution contract. The escrow hold/release logic stays in our engine; Splits handles the split itself.

---

## Ethereum Mainnet vs Base

**Preference:** Ethereum mainnet for production. Reasons:
- Stronger credibility signal (mainnet = "real")
- ERC-8004 robots registered on Sepolia → migrate to mainnet
- Splits deployed on Ethereum mainnet
- Institutional credibility for GC/investor demos

**Cost comparison for $0.01 USDC transaction:**
| Chain | Gas per transfer | % of $0.01 | % of $50 task |
|-------|-----------------|------------|---------------|
| Ethereum mainnet | ~$0.50-$2.00 | 5,000-20,000% | 1-4% |
| Base | ~$0.007 | 70% | 0.01% |

**Reality:** Ethereum mainnet gas makes $0.01 transactions impractical (gas > value). Two options:
1. **Demo on mainnet with higher amounts** — $5-$10 tasks where gas is <10% overhead
2. **Demo on Base for micro, mainnet for larger** — dual-chain, more complex
3. **Use Base for demo, plan mainnet migration for production** — pragmatic

**Recommendation:** Use **Base for the live demo** (gas-efficient for small amounts), but design the architecture so it works on **Ethereum mainnet for production** tasks ($1K+). The Splits SDK and x402 both support both chains — the only difference is the RPC URL and chain ID.

---

## Production Robots (ERC-8004)

Robots are currently registered on **Ethereum Sepolia** via ERC-8004 (`yakrover-8004-mcp`). For the live demo:

**Option A:** Keep robots on Sepolia, do payment on Base mainnet. The robot identity and the payment chain don't need to be the same network.

**Option B:** Register demo robot on Ethereum mainnet via ERC-8004. Cost: ~$5-$15 in gas for the NFT mint. Benefit: robot has a real mainnet identity.

**Option C:** Register on Base mainnet (if ERC-8004 registry is deployed there). Keeps everything on one chain.

**Recommendation:** Option A for the demo (simplest — don't move robots). Option B for the investor demo (mainnet robot + mainnet payment = strongest signal).

---

## Decisions (Resolved 2026-04-02)

| # | Decision | Resolution | Rationale |
|---|----------|-----------|-----------|
| 1 | **Stripe mode** | Production (`sk_live_...`) | Goal is real money. Build against test mode while Stripe review runs, swap key on approval. |
| 2 | **Crypto chain** | Base for demo, Ethereum mainnet for production | Gas makes micro-tx impractical on mainnet. Architecture is chain-agnostic (RPC URL + chain ID config). Swap when moving to investor demo. |
| 3 | **Payment split** | Splits.org | Audited, zero fees, deployed on Base + mainnet. 88% operator / 12% platform. No reason to build custom. |
| 4 | **Robot identity** | Keep on Sepolia for now. Robot owners registering on Base production in parallel. | Robot identity chain and payment chain are independent. One migration when ready for mainnet. |
| 5 | **Escrow approach** | x402 (payment) + Splits (distribution) first. Custom escrow contract as Phase 3. | Ship the value flow piping first, add on-chain escrow hold/release when needed. |
