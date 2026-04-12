# Plan: Remove Platform Fee — Single-Signature Payment

**Date:** 2026-04-07
**Status:** COMPLETE — deployed as demo-5, single-sign confirmed working
**Goal:** 100% of payment goes to operator. One wallet signature. No platform split. Ship as mcp-demo-5.
**Preserves:** mcp-demo-4 untouched until demo-5 is proven.

---

## Why

1. Two-signature UX is confusing — buyer asked "why do I need to sign twice?"
2. Platform fee raises "is it worth it?" questions in investor/GC demos
3. 88/12 split is the primary source of payment complexity (partial execution bugs, resumable state tracking, 3-tx sequences)
4. Production will use 0xSplits or equivalent — demo doesn't need on-chain split

## Architecture Change

```
BEFORE: Buyer → permit/3009 → Relay → Operator (88%) + Platform (12%)
AFTER:  Buyer → single 3009 → Operator (100%)
```

---

## Modules (implement in order, each independently testable)

### Module 1: Worker — Remove platform split from USDC paths
**File:** `chatbot/src/index.js`
**Changes:**
- `handleCommitPayment` (~line 1889): Remove `platform_wallet` from stored commitment. Store only `operator_wallet` + `total_amount`. Remove `platform_amount` calculation.
- `handleExecutePayment` — EIP-3009 path (~line 2080): Remove second `transferWithAuthorization` to platform. Single transfer of full `totalBig` to `operator_wallet`.
- `handleExecutePayment` — Permit fallback path (~line 2150): Remove second `transferFrom` to platform. Single `transferFrom` of full `totalBig` to `operator_wallet`. Remove allowance tracking for platform step.
- `handleRelayUsdc` (~line 1713): Remove platform split. Single `transferFrom` of full amount to `operator_wallet`.
- Remove `platform_wallet` validation (line 1704).
- Response: Remove `platform_amount`, `platform_tx` from all success responses.
- Error debug: Remove `platAmt` from debug responses.
**Test:** curl `/api/execute-payment` with a stored commitment → single tx, full amount to operator.

### Module 2: Worker — Remove platform fee from Stripe paths
**File:** `chatbot/src/index.js`
**Changes:**
- `handleCreateCheckout` (~line 972): Remove `application_fee_amount` from Stripe session creation. Or set to 0.
- `handleCreatePaymentIntent` (~line 1083): Remove `application_fee_amount` from PaymentIntent creation.
- `handleCapturePayment`: No change needed (captures whatever was authorized).
- `showPaymentSuccess` Stripe return: Remove fee calculation from display.
**Test:** Create Stripe test checkout → verify no application fee in Stripe dashboard.

### Module 3: Worker — Update system prompts
**File:** `chatbot/src/index.js`
**Changes:**
- `DEMO_SYSTEM_AUCTION` (~line 557): Remove any mention of "12% commission" or "platform fee".
- Chat system prompt (~line 74, 102): Remove "12% on completed tasks" language.
**Test:** Run auction → verify Claude doesn't mention platform fee.

### Module 4: Frontend — Single signature USDC
**File:** `demo/marketplace/index.html` (copy from demo-4)
**Changes:**
- `payWithUSDC()` EIP-3009 path: Sign ONE `TransferWithAuthorization` for full `totalUnits` to `operatorWallet`. Remove second signature (platform). Remove `platform_nonce`, `platform_v/r/s` from commit body.
- `payWithUSDC()` Permit fallback: Sign ONE permit for full `totalUnits`. Spender = relay. Remove platform split from commit body.
- Remove `PLATFORM_COMMISSION` constant.
- Keep `PLATFORM_WALLET` constant (may be needed for other things later) but don't use it in payment flow.
**Test:** USDC payment → one wallet popup → one signature → done.

### Module 5: Frontend — Remove fee from all UI
**File:** `demo/marketplace/index.html`
**Changes:**
- `renderCommitmentStatus()` (USDC path ~line 1321): Remove "Platform" row. Show only "Amount" and "Operator".
- `showStripeHoldApproved()` (Stripe path ~line 1961): Remove "Platform" row.
- `renderPaymentOptions()`: Remove platform calculation from display.
- `renderReceipt()` — USDC path: Remove "Platform commission" row. Remove "View platform fee" link. Show only "Operator received: $X".
- `renderReceipt()` — Stripe path: Remove "Platform commission" row.
- `showPaymentSuccess()` (Stripe return): Remove fee calculation and display.
- `releasePayment()`: Remove `platform_amount` from receipt data.
- `window._paymentCommitment`: Remove `platform_amount` field.
- `window._stripeHold`: Remove `platform_amount` field.
**Test:** Full demo flow → no mention of "platform", "commission", "fee" anywhere in UI.

### Module 6: Deploy + verify
- Copy `docs/mcp_demo_4/` to `demo/marketplace/`
- Apply Modules 4-5 to demo-5 only
- Apply Modules 1-3 to worker (backward compatible — demo-4 still works because it sends `platform_wallet` but the worker just ignores the platform transfer)
- Deploy worker
- Deploy demo-5 to here.now → link at yakrobot.bid/mcp-demo-5
- Test USDC: single sign → single tx → full amount to operator
- Test Stripe: single charge → no application fee
- Test demo-4 still works (backward compat)

---

## What stays

- `PLATFORM_WALLET` constant in frontend (unused but kept)
- `platform_wallet` field in worker commit storage (ignored if no platform split)
- Stripe Connect destination charges (operator still gets paid via Connect)
- All auction engine logic (unaffected by payment split)
- On-chain feedback (unaffected)
- Robot discovery, execution, QA (unaffected)

## What's removed

| Item | Location | Lines affected |
|------|----------|---------------|
| `PLATFORM_COMMISSION = 0.12` | demo HTML | 1 |
| 88/12 split calculation | worker (4 places) + demo (3 places) | ~20 |
| Second EIP-3009 signature | demo payWithUSDC | ~15 |
| Second transferFrom | worker execute-payment | ~10 |
| Platform amount in UI | demo (6 places) | ~12 |
| "View platform fee" link | demo receipt | 1 |
| application_fee_amount | worker Stripe (2 places) | 2 |
| "12% commission" in prompts | worker system prompts | 2 |

## Production path (0xSplits — documented for later)

When platform fee is reintroduced:
1. Create a 0xSplits split on Base: 88% operator, 12% platform
2. Buyer sends to split address (one signature)
3. Either party calls `distribute()` to forward funds
4. Or use 0xSplits "liquid splits" for auto-distribution
5. Split address stored in robot's on-chain metadata alongside `agentWallet`

See IMP-037 in IMPROVEMENT_BACKLOG.yaml.
