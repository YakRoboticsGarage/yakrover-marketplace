# Plan: Live Payment Settlement Demo (v2 — Post-Critique)

**Date:** 2026-04-02
**Status:** Revised after 3-agent critique (payment engineer, crypto engineer, product/UX)
**Goal:** Buyer pays real money through a real auction. Robot operator AND platform both get paid. Verifiable on Stripe dashboard and/or Basescan.

> **Design principles:**
> - Payment is the climax of the demo, not the prelude
> - Two independent rails: Stripe (fiat) and USDC (crypto). They never cross.
> - Simplest possible code that moves real money
> - Production accounts, real transactions

---

## Critique Findings (What Was Wrong in v1)

| Finding | Source | Fix |
|---------|--------|-----|
| Splits.org doesn't work for fiat (no on-chain asset to split) | Payment + Crypto engineers | Splits = crypto rail only. Stripe uses `application_fee_amount`. |
| x402 is wrong for marketplace settlement (it's pay-to-access, not escrow) | Crypto engineer | Drop x402 for settlement. Use direct USDC transfer. Reserve x402 for agent-to-robot control. |
| Demo UX has no payment moment (batch loop, no human interrupt) | Product critic | Payment after auction, not before. "Release payment" is the dramatic climax. |
| `confirm_delivery` transitions to SETTLED even if transfer fails | Payment engineer | Add `SETTLEMENT_FAILED` state or at minimum guard the transition. |
| Platform keeps 0% — code sends 100% to operator | Payment engineer | Use Stripe `application_fee_amount` (fiat) or send 88% only (crypto). |
| `f"acct_{robot_id}"` can't match real Connect accounts | Payment engineer | Lookup table: `robot_id → stripe_account_id` in operator registry. |
| 25%/75% ledger split vs 12%/88% revenue split — inconsistent | Payment engineer | Clarify: 25%/75% is payment timing (reservation/delivery). 12%/88% is revenue split. Both are correct for different purposes. |
| No webhook signature verification anywhere | Payment engineer | Add `STRIPE_WEBHOOK_SECRET` + `construct_event()`. |
| Key management for platform wallet unaddressed | Crypto engineer | Specify: EOA in env var for demo, KMS/multisig for production. |
| "Chain-agnostic" claim is misleading — gas economics differ 100x | Crypto engineer | Acknowledge Base for demo, mainnet when task values justify gas. |

---

## Revised Architecture

```
STRIPE RAIL (fiat):                      CRYPTO RAIL (USDC on Base):

Auction runs free                        Auction runs free
  |                                        |
  v                                        v
"Release $0.50 to Operator"             "Pay $0.01 USDC to Operator"
  |                                        |
  v                                        v
Stripe Checkout ($0.50)                  Wallet Connect → send USDC
  |                                      to Splits.org contract
  |--- application_fee (12%) → Platform    |
  |                                        |--- 88% → Operator wallet
  v                                        |--- 12% → Platform wallet
Connect Transfer (88%) → Operator          |
  |                                        v
  v                                      Basescan tx link
Stripe receipt link
```

**Key difference from v1:** The two rails are completely independent. No fiat-to-crypto conversion. No x402 on the settlement path. Stripe handles its own commission split. Splits handles the crypto split.

---

## The Demo Story (Investor Narrative)

```
"Watch this RFP turn into a real payment to a real robot operator."

1. Visitor sees an MDOT RFP and clicks "Run Auction"          [FREE]
2. Claude processes RFP, posts tasks, collects bids            [FREE]
3. Bids scored, winner recommended, task awarded               [FREE]
4. Robot executes survey, delivers data                        [FREE]
5. "Delivery accepted. Release payment to Apex Aerial."        [PAYMENT MOMENT]
   ┌─────────────────────────────────────────────────────┐
   │  [Pay $0.50 with Card]    [Pay $0.01 in USDC]      │
   └─────────────────────────────────────────────────────┘
6. Buyer pays → operator gets paid → proof shown               [CLIMAX]
   "✓ Apex Aerial received $0.44 — View receipt →"
   "✓ Platform commission: $0.06"
```

Payment is the finale. The auction runs free. The moment money moves is the proof point.

---

## Phase 1: Stripe Rail — Real $0.50 (4-5 days)

### What it proves
A real credit card charge flows through a real auction to a real operator's Stripe account, with the platform taking a 12% commission.

### 1a. Fix currency bug + commission (0.5 day)

**`auction/stripe_service.py`:**
- Add `currency` parameter to `create_transfer()`
- Add `application_fee_amount` to PaymentIntent creation (Stripe's native commission mechanism — 12% stays on platform, 88% goes to connected account)

### 1b. Operator account mapping (0.5 day)

**`auction/operator_registry.py`:**
- Add `stripe_account_id` field to operator profiles
- For demo: hardcode the existing test Connect account (`acct_1TEjjLC2lXDckgmS`) for one operator

**`auction/engine.py`:**
- Replace `f"acct_{robot_id}"` with lookup from operator registry

### 1c. Payment-after-delivery in mcp-demo (2 days)

**`docs/mcp_demo/index.html`:**
- After the auction step feed completes (delivery confirmed), show a payment card:
  ```
  ┌──────────────────────────────────────────┐
  │  Delivery accepted ✓                      │
  │                                           │
  │  Release $0.50 to Apex Aerial Surveys     │
  │  Platform commission: $0.06 (12%)         │
  │  Operator receives: $0.44                 │
  │                                           │
  │  [Pay with Card — $0.50]                  │
  └──────────────────────────────────────────┘
  ```
- Button loads Stripe Checkout (redirect or embedded Payment Element)
- On success, show confirmation card with Stripe receipt link

**`chatbot/src/index.js`:**
- New endpoint: `POST /api/create-checkout` — creates Stripe Checkout Session with:
  - `line_items: [{price_data: {unit_amount: 50, currency: 'usd'}, quantity: 1}]`
  - `payment_intent_data: {application_fee_amount: 6, transfer_data: {destination: 'acct_...'}}`
  - `success_url` and `cancel_url` pointing back to mcp-demo page
- This uses Stripe Connect's "destination charge" pattern — the charge is created on the platform account and automatically transfers 88% to the connected account

### 1d. Webhook + confirmation (1 day)

**`chatbot/src/index.js`:**
- New endpoint: `POST /api/stripe-webhook`
- Verify signature with `STRIPE_WEBHOOK_SECRET`
- On `checkout.session.completed`: record the payment, return confirmation data
- Idempotency: deduplicate by `checkout_session.id`

**`docs/mcp_demo/index.html`:**
- After Stripe redirect, poll `/api/payment-status?session_id=...` until confirmed
- Show: "✓ Payment complete. Operator received $0.44. [View receipt →]"

### 1e. Guard settlement state (0.5 day)

**`auction/engine.py`:**
- `confirm_delivery` should NOT transition to SETTLED if the Stripe transfer hasn't been confirmed
- Add: if transfer returns error, log it, keep state at VERIFIED, return `settlement_status: "pending"`
- Add: `_last_settlement_error` field on TaskRecord

### Phase 1 deliverable
Visitor runs auction → delivery confirmed → clicks "Pay $0.50" → Stripe Checkout → operator receives $0.44 in their Connect account → platform keeps $0.06 → receipt link shown. **Real money. Verifiable.**

### Phase 1 prerequisites
- [ ] Production Stripe account (`sk_live_...`)
- [ ] `STRIPE_WEBHOOK_SECRET` configured in Cloudflare Worker
- [ ] At least 1 operator with completed Connect Express onboarding
- [ ] Stripe Checkout domain registered (yakrobot.bid)

---

## Phase 2: Crypto Rail — Real $0.01 USDC on Base (3-4 days)

### What it proves
A real USDC transfer on Base flows through a real auction, auto-split between operator (88%) and platform (12%) via Splits.org.

### 2a. Create Splits.org contract (0.5 day)

- Create a Split on Base mainnet via splits.org UI or SDK
- Recipients: `{operator_wallet: 88%, platform_wallet: 12%}`
- The Split contract address becomes the payment destination

### 2b. Wallet connect + USDC transfer in mcp-demo (2 days)

**`docs/mcp_demo/index.html`:**
- After delivery confirmed, show crypto payment option alongside Stripe:
  ```
  [Pay $0.50 with Card]    [Pay $0.01 in USDC]
  ```
- "Pay in USDC" button triggers wallet connect (ethers.js/viem + Coinbase Wallet or MetaMask)
- On connect: call `USDC.transfer(splitContractAddress, 10000)` (6 decimals, $0.01 = 10000 units)
- Show tx hash + Basescan link while waiting for confirmation
- On confirmation: "✓ Payment split: $0.0088 to operator, $0.0012 to platform. [View on Basescan →]"

### 2c. Operator + platform withdraw from Split (0.5 day)

- Splits accumulate until `withdraw()` is called
- For demo: platform calls withdraw after each payment (or on a schedule)
- Show: "Operator can withdraw USDC at [splits.org link]"

### 2d. Platform wallet setup (0.5 day)

- Generate EOA wallet for demo (private key in env var)
- Fund with ~$1 USDC + ~$0.10 ETH on Base (for gas on withdrawals)
- For production: migrate to multisig or KMS-backed wallet

### Phase 2 deliverable
Visitor runs auction → delivery confirmed → clicks "Pay $0.01 USDC" → wallet connect → USDC sent to Split contract → auto-split 88/12 → Basescan link shown. **Real crypto. Verifiable.**

### Phase 2 prerequisites
- [ ] Platform wallet on Base (EOA, funded)
- [ ] Demo operator wallet on Base
- [ ] Splits.org contract created with 88/12 split
- [ ] ~$1 USDC + ~$0.10 ETH in platform wallet

---

## Phase 3: On-Chain Escrow (Future — when task values justify it)

Not needed for the demo. The trust model for $0.50/$0.01 tasks is: "platform mediates, Stripe has chargeback protection, USDC amounts are trivial."

Escrow becomes necessary when:
- Task values exceed $50+ (operator wants assurance buyer can pay)
- Buyer wants assurance funds are locked before operator mobilizes
- Disputes need on-chain arbitration

At that point: deploy `RobotTaskEscrow.sol` on Base (deposit/release/refund), wire into settlement abstraction (FD-1).

---

## What We're NOT Building (and Why)

| Dropped from v1 | Why |
|-----------------|-----|
| x402 middleware on MCP server | x402 is pay-to-access, not marketplace settlement. Right tool for Tumbller robot control, wrong tool for auction payment. |
| Wallet funding before auction | Kills the narrative. Payment should be the climax. |
| Fiat-to-crypto bridge | Regulatory minefield (money transmission). Keep rails independent. |
| Internal wallet ledger for real payments | Stripe IS the ledger for fiat. Basescan IS the ledger for crypto. The internal ledger stays for demo/simulation mode only. |
| Escrow contract (Phase 3) | Premature for $0.50/$0.01 demo. Add when task values justify it. |
| Paymaster / gas sponsorship | Premature optimization. Platform wallet holds ETH for gas. |

---

## Clarification: 25%/75% vs 12%/88%

These are different things:

- **25%/75%** = payment timing. 25% reserved on bid acceptance (proves buyer has funds), 75% charged on delivery. This is the internal ledger's job. For the demo, Stripe charges the full amount at checkout time (after delivery), so the 25/75 timing doesn't apply — it's a single charge.

- **12%/88%** = revenue split. 12% platform commission, 88% operator payout. Stripe handles this via `application_fee_amount`. Splits handles this via contract configuration.

In production (larger tasks, pre-funded wallets), both mechanisms coexist: 25% reserved on acceptance, 75% on delivery, and at each step the revenue splits 12/88.

---

## Timeline

| Phase | What | Days | Deliverable |
|-------|------|------|-------------|
| 1a | Fix currency + add commission | 0.5 | Stripe transfers work for EUR/USD with 12% fee |
| 1b | Operator account mapping | 0.5 | Real Connect account ID in registry |
| 1c | Payment-after-delivery UX | 2 | Stripe Checkout in mcp-demo page |
| 1d | Webhook + confirmation | 1 | Payment verified, receipt shown |
| 1e | Guard settlement state | 0.5 | No false SETTLED on transfer failure |
| 2a | Splits.org contract | 0.5 | 88/12 split on Base |
| 2b | Wallet connect + USDC | 2 | Crypto payment in mcp-demo page |
| 2c | Withdraw flow | 0.5 | Operator/platform can claim funds |
| 2d | Platform wallet | 0.5 | Funded EOA on Base |
| | **Total** | **~8 days** | |

Down from ~15.5 days in v1 — critique eliminated 7.5 days of unnecessary complexity.

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Stripe production approval delay | Apply now. Build against test keys (same code, swap key). |
| Connect operator account not ready | Use existing test account `acct_1TEjjLC2lXDckgmS`. Create new production account for real demo. |
| Stripe Checkout on here.now domain | Register yakrobot.bid in Stripe dashboard as approved domain. |
| USDC price fluctuation | $0.01 USDC ≈ $0.01 USD. Stablecoin risk is negligible at demo scale. |
| Operator doesn't have Base wallet | For demo: we create it. For production: onboarding flow creates embedded wallet. |
| Gas spike on Base | Keep $0.50 ETH in platform wallet. Monitor. Base gas is historically stable. |
| Platform wallet key compromise | Demo: env var (acceptable for $1 at stake). Production: KMS/multisig. |
