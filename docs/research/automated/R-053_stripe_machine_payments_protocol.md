# R-053: Stripe Machine Payments Protocol (MPP) + Agentic Commerce

**Status:** Research complete
**Date:** 2026-04-12
**Sources:**
- [Stripe MPP docs](https://docs.stripe.com/payments/machine/mpp)
- [Stripe machine payments overview](https://docs.stripe.com/payments/machine)
- [Stripe ACP (Agentic Commerce Protocol)](https://docs.stripe.com/agentic-commerce/protocol)
- [MPP announcement](https://stripe.com/blog/machine-payments-protocol)
- [Agentic Commerce Suite announcement](https://stripe.com/blog/agentic-commerce-suite)

**Relevance:** Direct alternative/complement to our current payment architecture. Could replace or augment our manual Stripe PaymentIntent flow for agent-mediated auction payments.

---

## What Stripe Launched (March 2026)

Three related but distinct products:

### 1. Machine Payments Protocol (MPP)
An open protocol co-authored by Stripe and Tempo (a Stripe/Paradigm-incubated L1 blockchain). Enables machine-to-machine payments without human checkout flows.

**How it works:**
1. Agent requests a paid resource via HTTP
2. Server returns `402 Payment Required` with a payment challenge
3. Agent authorizes payment (crypto deposit or Shared Payment Token)
4. Agent retries the request with payment proof
5. Server delivers the resource + receipt

**Two payment paths:**
- **Crypto (Tempo/USDC):** Agent sends USDC to a deposit address. Stripe monitors the blockchain and auto-captures. Minimum: $0.01 USDC.
- **SPT (Shared Payment Tokens):** Agent presents a pre-authorized card/wallet token. Stripe creates a PaymentIntent automatically. Supports card, Link, BNPL.

**Key detail:** Visa contributed to MPP — agents can pay with credit/debit cards via SPT, not just crypto.

### 2. x402 Protocol
HTTP-native payment for USDC on Base and Solana. Uses the `402 Payment Required` HTTP status code. Stripe accepts x402 payments and settles to the merchant's Stripe account.

**This is what we already evaluated in v1.1** (decision AD-TC-4). We concluded x402 is wrong for marketplace settlement (it's pay-to-access, not escrow). MPP has the same limitation.

### 3. Agentic Commerce Protocol (ACP)
A higher-level protocol for AI agents (ChatGPT, etc.) to facilitate checkout on behalf of users. The agent handles the UI, the merchant handles pricing and payment processing.

**Four endpoints:** Create, Update, Complete, Cancel
**Already live:** ChatGPT can buy from Etsy sellers, soon Shopify merchants.

---

## How MPP Maps to the Marketplace

### Current marketplace payment flow:
```
Buyer → Claude (agent) → auction_post_task → robots bid → buyer accepts →
  → buyer authorizes payment (Card/ACH/USDC) →
  → robot executes → delivery verified →
  → payment captured/released to operator
```

### What MPP would change:

**Scenario A: Agent pays per-task (buyer's agent has an SPT)**
```
Buyer's Claude agent → sees winning bid →
  → sends SPT to marketplace →
  → marketplace creates PaymentIntent from SPT →
  → holds funds until delivery →
  → captures to operator's Connect account
```

This replaces our current Stripe PaymentElement (card form) and USDC wallet connection with a **token the agent already has**. The buyer pre-authorizes a spending limit, the agent handles payment within that limit.

**Scenario B: Robot operator gets paid via MPP (operator is a "service")**
```
Marketplace → calls operator's MCP endpoint →
  → endpoint returns 402 with price →
  → marketplace pays via SPT or USDC →
  → operator delivers data →
  → marketplace forwards to buyer
```

This would make the operator's robot a **paid API** — the marketplace pays per-execution. This is architecturally interesting but changes the settlement model: marketplace becomes the buyer to operators, not a broker.

### What MPP does NOT solve for us:

1. **Escrow.** MPP is pay-and-deliver, not hold-and-release. Our marketplace needs to hold buyer funds until delivery is verified. MPP's `402 → pay → receive` is atomic — no escrow step.

2. **Multi-party settlement.** MPP pays one recipient. Our flow pays the operator + (future) platform fee. Stripe Connect with `transfer_data` or `application_fee` handles this. MPP doesn't.

3. **Dispute resolution.** If the robot delivers bad data, the buyer needs a refund path. MPP has no built-in dispute mechanism — it's a one-shot payment.

4. **Construction-scale payments.** MPP is optimized for micropayments ($0.01-$100). Our tasks are $1K-$72K. At that scale, buyers want authorization holds, invoicing, and ACH — not instant micropayment.

---

## Applicability Assessment

| Feature | MPP/x402 | Our Current Flow | Verdict |
|---------|----------|-----------------|---------|
| **Agent-initiated payment** | ✅ Native — agent has SPT or wallet | ❌ Human clicks card form | MPP wins for agent UX |
| **Escrow/hold** | ❌ Pay-and-deliver only | ✅ Manual capture / platform hold | We need escrow |
| **Multi-party split** | ❌ Single recipient | ✅ Connect + application_fee | We need splits |
| **Construction scale ($1K+)** | ⚠️ Designed for micro | ✅ ACH, card holds | Our scale is fine |
| **USDC on Base** | ✅ Via x402 | ✅ Via EIP-3009 | Both work |
| **Card payments** | ✅ Via SPT | ✅ Via PaymentElement | Both work |
| **Dispute/refund** | ❌ None | ⚠️ Manual | Neither is great |
| **Buyer spending limits** | ✅ SPT pre-authorization | ❌ Per-task approval | MPP wins |

---

## Recommendation

### Short term (v1.5): Don't adopt MPP yet.

MPP doesn't solve our core payment challenge (escrow + multi-party settlement). Our current Stripe PaymentIntent + Connect flow handles the construction-scale, hold-and-release pattern correctly. Switching to MPP would lose the escrow capability.

### Medium term (v2.0): Adopt MPP for the agent-side payment initiation.

The buyer's AI agent (Claude) could hold an SPT with pre-authorized spending limits (configured by the Controller persona). When the agent awards a task, it pays via SPT — no human checkout form needed. The marketplace still uses Stripe Connect for the escrow + settlement backend.

**Hybrid flow:**
```
Controller → sets $15K SPT spending limit →
Agent → awards task → sends SPT to marketplace →
Marketplace → creates PaymentIntent from SPT (manual capture) →
  → holds funds in Stripe →
Robot executes → QA passes →
Marketplace → captures → transfers to operator via Connect
```

This gives us agent-initiated payment (MPP front-end) with escrow settlement (Stripe Connect back-end).

### Long term (v3.0+): Evaluate ACP for operator discovery.

ACP is how AI agents discover and buy from merchants. If operators publish their capabilities via ACP, buyer agents could discover survey services directly — the marketplace becomes an ACP-compatible service that agents can checkout from. This is the "agentic commerce" vision where Claude finds and hires a drone operator without a web UI.

---

## Implementation Notes

### If we adopt MPP for agent payment (v2.0):

1. **Enable MPP on Stripe account** — requires signup approval, US-only
2. **Issue SPTs to buyer agents** — via Controller dashboard or API
3. **Accept SPTs in auction_accept_bid** — replace card form with SPT consumption
4. **Keep Connect for settlement** — SPT creates PaymentIntent, we hold + capture + transfer

### Required Stripe API version:
- `2026-03-04.preview` for crypto/MPP features
- Standard API for SPT + PaymentIntent

### Dependencies:
- `mppx` npm package (server-side MPP handler)
- Stripe API key with MPP enabled
- For crypto path: Tempo network integration (optional — we already have Base USDC)

---

## Relationship to Existing Decisions

| Decision | Impact |
|----------|--------|
| **TC-4** (USDC on Base) | x402 on Base is now Stripe-supported. Our EIP-3009 flow could migrate to x402 for Stripe settlement, but we'd lose the direct-to-operator transfer. |
| **FD-1** (Settlement abstraction) | MPP adds a new payment initiation method. Settlement abstraction should support SPT as a funding source alongside card/ACH/USDC. |
| **AD-20** (EAS attestation) | Unrelated — attestation is identity, not payment. |
| **PD-2** (Automated bidding) | MPP enables automated payment too — the agent bids AND pays. Full automation from RFP to settlement. |

---

## Key Takeaway

MPP is the right protocol for **how the agent initiates payment**. It is NOT the right protocol for **how the marketplace settles payment** (that's still Stripe Connect). The two compose well: MPP front-end + Connect back-end = agent-automated, escrowed, multi-party settlement.

Don't adopt now. Design the SPT integration for v2.0 when the Controller persona and spending limits are built.

Sources:
- [Stripe MPP Documentation](https://docs.stripe.com/payments/machine/mpp)
- [Stripe Machine Payments Overview](https://docs.stripe.com/payments/machine)
- [Stripe Agentic Commerce Protocol](https://docs.stripe.com/agentic-commerce/protocol)
- [MPP Announcement Blog](https://stripe.com/blog/machine-payments-protocol)
- [Agentic Commerce Suite](https://stripe.com/blog/agentic-commerce-suite)
- [PYMNTS: Stripe-Backed Protocol](https://www.pymnts.com/news/payment-methods/2026/stripe-backed-protocol-lets-ai-agents-transact-autonomously/)
- [Fortune: Tempo MPP Launch](https://fortune.com/2026/03/18/stripe-tempo-paradigm-mpp-ai-payments-protocol/)
- [Forrester: MPP Micropayments Analysis](https://www.forrester.com/blogs/why-stripes-machine-payments-protocol-signals-a-turning-point-for-micropayments/)
