# Plan: ACH Bank Transfer + Payment Method Translation

**Date:** 2026-04-08
**Status:** IMPLEMENTING
**Depends on:** Stripe test keys (have), operator Stripe Connect account (have: `acct_1TEjjLC2lXDckgmS`)
**Related:** FD-1 (settlement abstraction), PLAN_PAYMENT_SETTLEMENT_DEMO_v4.md
**Reviewed:** Agent critique identified ACH/capture incompatibility — plan revised

---

## Core Insight: Payment Method Translation

The marketplace sits between two preferences:

```
Buyer pays how they want    →    Marketplace translates    →    Operator gets paid how they want
(card, ACH, crypto)              (settlement layer)             (USDC, bank deposit, etc.)
```

The buyer should never need to know or care how the operator prefers to be paid. The operator should never need to accept a payment rail they don't want. The marketplace absorbs the translation cost and complexity.

### Translation Matrix (what the marketplace must support)

| Buyer pays with | Operator wants USDC | Operator wants bank deposit |
|----------------|--------------------|-----------------------------|
| **Card** | Stripe collects → Coinbase Onramp or Circle mint → USDC to operator wallet | Stripe Connect destination charge → operator bank |
| **ACH** | Stripe collects → same offramp → USDC to operator wallet | Stripe Connect transfer after settlement → operator bank |
| **USDC** | Direct transfer (current flow) | USDC → Circle offramp or Coinbase Commerce → operator bank |

**For v1.2 demo:** Translation is not needed yet. Stripe (card/ACH) goes to operator's Stripe Connect account. USDC goes to operator's on-chain wallet. The buyer picks one of the methods the operator accepts. Translation is a v1.5+ feature when we have enough operators to see real preference mismatches.

---

## Critical Design Constraint: ACH Has No Hold

**ACH does not support authorize/capture.** Unlike cards where `capture_method: manual` creates a real hold on the buyer's funds, ACH debits are initiated immediately on confirmation. There is no intermediate "authorized" state.

This means the three payment methods have fundamentally different hold mechanisms:

| Method | Hold mechanism | Release trigger | Settlement |
|--------|---------------|----------------|------------|
| **Card** | Stripe `capture_method: manual` (real bank hold) | `/api/capture-payment` captures the authorized amount | Instant to operator |
| **ACH** | Platform-level hold (Stripe collects into platform, holds until task complete) | `/api/transfer-to-operator` creates Stripe transfer after delivery | 2-4 days for ACH to settle, then transfer |
| **USDC** | EIP-3009 signed authorization (buyer signs, relay executes later) | `/api/execute-payment` submits on-chain transfer | Instant |

### ACH flow (revised)

```
1. Buyer selects "Bank Transfer" → Stripe Payment Element with us_bank_account only
2. Financial Connections verifies bank account (instant)
3. Buyer confirms → Stripe initiates ACH debit (money starts moving to platform)
4. PaymentIntent status: "processing" (2-4 business days in production, instant in test)
5. Robot executes task → delivery → QA
6. Webhook: payment_intent.succeeded → funds available on platform
7. Buyer clicks "Release Payment" → platform transfers to operator's Connect account
8. Receipt shown
```

In test mode, step 4 resolves instantly, so the demo flow feels identical to card.

---

## ACH User Journey

### Who uses ACH?

GCs paying for tasks over $3,000. Corporate procurement typically requires bank transfer for anything above a credit card threshold ($2,500-$5,000 at most firms). This is the dominant payment method for construction survey work.

### Economic motivation

| Task amount | Card fee (2.9% + $0.30) | ACH fee (0.8%, cap $5) | Savings |
|------------|-------------------------|------------------------|---------|
| $1,000 | $29.30 | $5.00 | $24.30 |
| $5,000 | $145.30 | $5.00 | $140.30 |
| $50,000 | $1,450.30 | $5.00 | $1,445.30 |

At construction scale, ACH saves the buyer over $1,400 on a $50K task.

### Risk: ACH returns (bounced payments)

ACH payments can be returned up to 60 days after. If the buyer's bank account has insufficient funds, the marketplace learns about it days after the debit.

**Mitigations:**
- Financial Connections with `balances` permission — check account balance before initiating debit
- For tasks >$10K in production, require pre-verified bank account before auction entry
- Platform absorbs return risk for tasks under $5K (cost of doing business)
- For demo: test mode always succeeds, no return risk

---

## Technical Implementation

### Module 1: Worker — New ACH PaymentIntent endpoint

**File:** `chatbot/src/index.js`

Add `POST /api/create-ach-intent` (separate from card PI to keep flows clean):

```javascript
async function handleCreateAchIntent(request, env, cors) {
  // Creates a PaymentIntent with:
  //   payment_method_types: ['us_bank_account']
  //   capture_method: omitted (default 'automatic' — ACH debits immediately)
  //   payment_method_options.us_bank_account.financial_connections.permissions: ['payment_method', 'balances']
  //   payment_method_options.us_bank_account.verification_method: 'instant'
  //   metadata: { request_id, operator_name, operator_account_id }
  // Returns: { client_secret, payment_intent_id, amount_cents }
  // Note: No transfer_data[destination] — platform collects, transfers later
}
```

Why separate from card: card uses `capture_method: manual` + `transfer_data[destination]`. ACH uses automatic capture + platform-level hold + separate transfer. Mixing them in one endpoint creates confusing conditional logic.

### Module 2: Worker — Transfer-to-operator endpoint

**File:** `chatbot/src/index.js`

Add `POST /api/transfer-to-operator`:

```javascript
async function handleTransferToOperator(request, env, cors) {
  // Called after delivery verified + buyer clicks "Release Payment"
  // 1. Verify PaymentIntent status is 'succeeded' (ACH settled)
  // 2. Create Stripe Transfer to operator's Connect account
  //    POST /v1/transfers { amount, currency, destination: operator_account_id }
  // 3. Return { transfer_id, amount, status }
}
```

### Module 3: Worker — Webhook endpoint for ACH lifecycle

**File:** `chatbot/src/index.js`

Add `POST /api/stripe-webhook`:

```javascript
async function handleStripeWebhook(request, env) {
  // Verify Stripe signature (STRIPE_WEBHOOK_SECRET)
  // Handle events:
  //   payment_intent.processing → ACH debit initiated (store status in KV)
  //   payment_intent.succeeded  → ACH settled, funds available (update KV)
  //   payment_intent.payment_failed → ACH return/NSF (update KV, alert)
}
```

For the demo (test mode), webhooks fire instantly. For production, this is how we learn ACH has settled.

### Module 4: Worker — Route new endpoints

Add to request router:
- `POST /api/create-ach-intent` → `handleCreateAchIntent`
- `POST /api/transfer-to-operator` → `handleTransferToOperator`
- `POST /api/stripe-webhook` → `handleStripeWebhook`

### Module 5: Frontend — Payment method selector in Dispatch phase

**File:** `demo/marketplace/index.html`

Replace the current single payment button in `renderPaymentOptions()` with three method buttons:

```
┌──────────────────────────────────────────────────┐
│  Authorize Payment                                │
│                                                   │
│  ┌──────────────┐ ┌────────────────┐ ┌─────────┐│
│  │     Card     │ │ Bank Transfer  │ │  USDC   ││
│  │    $4,200    │ │     $4,200     │ │  4,200  ││
│  └──────────────┘ └────────────────┘ └─────────┘│
│                                                   │
│  Secure payment processing by Stripe              │
└──────────────────────────────────────────────────┘
```

- **Card** → existing `payWithStripe()` (manual capture PI)
- **Bank Transfer** → new `payWithACH()` (ACH PI via `/api/create-ach-intent`)
- **USDC** → existing `payWithUSDC()` (EIP-3009)

Do not show fee breakdowns to the buyer. Show a clean total.

### Module 6: Frontend — ACH payment function

Add `payWithACH()`:

```javascript
async function payWithACH(amountCents, operatorAccountId) {
  // 1. POST /api/create-ach-intent
  // 2. Mount Payment Element (us_bank_account only)
  // 3. confirmPayment() — Financial Connections flow opens
  // 4. On success: PI status = 'processing' (test mode: instant)
  // 5. Store payment_intent_id, show "Bank transfer initiated"
  // 6. Trigger robot execution
}
```

### Module 7: Frontend — Release Payment handles all three methods

The "Release Payment" button already exists. Update it to detect payment method:

```javascript
if (window._paymentMethod === 'usdc') {
  // existing: POST /api/execute-payment
} else if (window._paymentMethod === 'ach') {
  // new: POST /api/transfer-to-operator
} else {
  // existing: POST /api/capture-payment (card)
}
```

### Module 8: Frontend — Method-specific status text

| Phase | Card | ACH | USDC |
|-------|------|-----|------|
| After authorization | "Card authorized. Hold active." | "Bank transfer initiated. Processing." | "USDC authorization signed." |
| During execution | "Payment hold active — operator executing" | "Payment processing — operator executing" | "Payment authorized — operator executing" |
| After release | "Payment captured." | "Payment transferred to operator." | "USDC transferred to operator." |

---

## Implementation order

1. Worker: `handleCreateAchIntent` endpoint
2. Worker: `handleTransferToOperator` endpoint
3. Worker: `handleStripeWebhook` endpoint (basic — KV status tracking)
4. Worker: Route all three new endpoints
5. Worker: Deploy
6. Frontend: Payment method selector (Card / Bank Transfer / USDC) in Dispatch phase
7. Frontend: `payWithACH()` function
8. Frontend: "Release Payment" branching for ACH
9. Frontend: Method-specific status text
10. Frontend: Deploy
11. Test: Card flow still works
12. Test: ACH flow with test credentials (routing `110000000`, account `000123456789`)
13. Test: USDC flow still works

---

## What stays unchanged

- USDC flow (commit/release) — untouched
- Card flow (authorize/capture) — untouched
- `/api/capture-payment` — still used for card only
- `/api/execute-payment` — still used for USDC only
- Auction engine, MCP server, robot execution — all untouched

## What's new

| Endpoint | Purpose |
|----------|---------|
| `POST /api/create-ach-intent` | ACH PaymentIntent (automatic capture, instant verification) |
| `POST /api/transfer-to-operator` | Platform → operator transfer after ACH settles |
| `POST /api/stripe-webhook` | ACH lifecycle events (processing, succeeded, failed) |

---

## Stripe test credentials for ACH

| Field | Test value |
|-------|-----------|
| Routing number | `110000000` |
| Account number | `000123456789` |
| Account type | Checking |

Stripe test mode simulates instant verification (no micro-deposits) and instant settlement (no 2-4 day wait).

---

## What this does NOT include (deferred to v1.5+)

1. **Fiat-to-crypto translation** — Buyer pays ACH, operator receives USDC. Requires Coinbase Onramp or Circle Payments API. Research topic R-024.
2. **Crypto-to-fiat translation** — Buyer pays USDC, operator receives bank deposit. Requires Circle offramp.
3. **Escrow for ACH returns** — For tasks >$10K, the 60-day ACH return window means the platform carries risk. The `RobotTaskEscrow.sol` contract (FD-1, v1.5) handles this.
4. **Invoice/Net-30 terms** — Large GCs may want invoice terms. Stripe Invoicing feature.
5. **Pre-auction bank verification** — Verify buyer's bank account during registration, not during payment.
6. **ACH return handling** — `payment_intent.payment_failed` webhook needs dispute resolution flow.

---

## Operator payout preference (metadata, for production)

Each operator's preferred payout method is readable from their on-chain metadata:

| Metadata key | Example value | Meaning |
|-------------|--------------|---------|
| `agentWallet` | `0x99a5...E136` | USDC wallet on Base |
| `stripe_connect_id` | `acct_1TEjjLC2...` | Stripe Connect account (receives card/ACH payouts) |
| `payout_preference` | `usdc` or `fiat` or `both` | What the operator prefers |
| `accepted_currencies` | `usd,usdc` | What the operator accepts |

For now, both Berlin robots accept both (`accepted_currencies: usd,usdc`) and have both a wallet and a Stripe Connect account. No translation needed — the buyer's choice determines the rail.
