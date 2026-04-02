# Plan: Live Payment Settlement Demo (v4 — Implementation Status)

**Date:** 2026-04-02
**Status:** Partially built, partially blocked
**Supersedes:** v3
**Demo:** https://yakrobot.bid/mcp-demo-2/
**Goal:** Real money through a real robot auction. Buyer pays, operator and platform both get paid.

---

## What's Built (mcp-demo-2, live now)

### Step 1: Robot Discovery — DONE
- Direct subgraph query from browser (no server needed)
- Queries ERC-8004 registry for `fleet_provider: yakrover`
- Searches Base mainnet first, falls back to Sepolia
- Reads wallet address via on-chain `getAgentWallet()` RPC call
- Shows each robot's chain, active status, MCP tools, wallet badge
- Links to block explorer for verification
- **Current result:** Tumbller (Sepolia, agent #989, wallet `0x99a5...E136`) found

### Step 2: Auction — DONE (via MCP server)
- Pre-filled RFP matches Tumbller capabilities (env monitoring, temp/humidity)
- Claude tool_use loop runs full auction lifecycle
- Requires MCP server + tunnel (existing infrastructure)

### Step 3: Delivery Verification — PARTIAL
- UI shows delivery step with explanation of IPFS verification flow
- Accept/Reject buttons present
- **Not built:** actual IPFS upload by robot, CID verification, on-chain delivery record

### Step 4: Payment — BUILT (Stripe), BLOCKED (USDC)

**Stripe (fiat):**
- Worker endpoint `POST /api/create-checkout` creates Stripe Checkout Session
- Uses destination charges: `application_fee_amount` (12%) stays on platform, 88% transfers to operator Connect account
- Worker endpoint `GET /api/payment-status` polls session status
- Worker endpoint `POST /api/stripe-webhook` handles `checkout.session.completed`
- **Blocked on:** production Stripe keys + operator Stripe Connect onboarding

**USDC (crypto):**
- Wallet address read from on-chain `getAgentWallet()` — ready to receive
- Payment button enabled when wallet found
- **Blocked on:** browser wallet connect code (ethers.js/viem USDC transfer)

---

## Key Discovery: On-Chain Wallet Already Works

The ERC-8004 contract has `getAgentWallet(agentId)` returning a real address. The Tumbller's wallet (`0x99a55d71682807fde9c81e0984aBdd2C7AcCE136`) is set and readable via a single RPC call from the browser. No additional operator registration is needed for USDC payments — the robot is already ready to receive funds.

This simplifies the payment flow significantly:
- **No separate operator registry for payment** — read from on-chain
- **No Splits.org needed for demo** — send directly to robot wallet, platform keeps remainder
- **Wallet verification is trustless** — anyone can call `getAgentWallet(989)` and verify

---

## What's Blocking End-to-End

### For Stripe path ($0.50):
1. [ ] Production Stripe account with `sk_live_...` key
2. [ ] One operator completes Stripe Connect Express onboarding → gets `acct_...`
3. [ ] Add `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` as Cloudflare Worker secrets
4. [ ] Register webhook URL in Stripe dashboard
5. [ ] Redeploy worker (`wrangler deploy`)

### For USDC path ($0.01):
1. [ ] Add ethers.js/viem to demo page for wallet connect
2. [ ] USDC transfer call: `USDC.transfer(robotWallet, 10000)` (6 decimals)
3. [ ] Show Basescan/Etherscan tx link after transfer
4. [ ] Platform commission: either send 88% to robot + 12% to platform wallet, or use Splits
5. [ ] Robot wallet needs USDC on the same chain it's registered on (currently Sepolia — testnet USDC only)

### For real production:
1. [ ] Robot registered on Base mainnet (not Sepolia) with `fleet_provider: yakrover`
2. [ ] Robot wallet funded or ready to receive USDC on Base
3. [ ] RFP and auction configured for Base-registered robot capabilities

---

## Architecture (What We Learned)

```
Browser (yakrobot.bid/mcp-demo-2)
  |
  |-- [1] Subgraph query → discover robots (fleet_provider: yakrover)
  |-- [1] eth_call getAgentWallet(id) → read robot wallet address
  |
  |-- [2] POST /api/demo (worker → MCP server) → run auction
  |
  |-- [3] Show delivery verification UI
  |
  |-- [4a] POST /api/create-checkout (worker → Stripe API)
  |         → Stripe Checkout → application_fee 12% → Connect transfer 88%
  |
  |-- [4b] Wallet connect → USDC.transfer(robotWallet, amount)
  |         → direct on-chain payment → Basescan proof
  |
  v
  Confirmation: receipt link (Stripe) or tx hash (Base)
```

**No custom smart contracts needed for the demo.** The ERC-8004 identity registry is the only contract involved — and it's already deployed.

---

## Decisions (Resolved)

| # | Decision | Resolution | Date |
|---|----------|-----------|------|
| 1 | Stripe mode | Production (`sk_live_...`) | 2026-04-02 |
| 2 | Crypto chain | Base for production. Sepolia for current demo. | 2026-04-02 |
| 3 | Revenue split | Stripe `application_fee_amount` for fiat. Direct transfer for crypto demo (Splits.org for production scale). | 2026-04-02 |
| 4 | Robot identity | Read from ERC-8004 on-chain. `fleet_provider: yakrover` filter. | 2026-04-02 |
| 5 | Robot wallet | Read via `getAgentWallet()` on-chain RPC. No separate registry. | 2026-04-02 |
| 6 | Delivery verification | IPFS upload + CID. Not built yet — placeholder UI in demo. | 2026-04-02 |
| 7 | x402 | Not used for marketplace settlement. Reserved for agent-to-robot control. | 2026-04-02 |
| 8 | Discovery method | Direct subgraph + RPC from browser. No server dependency. | 2026-04-02 |
| 9 | Fiat-to-USDC bridge | Research topic R-024. Not built — keep rails separate. | 2026-04-02 |

---

## Remaining Work

| Phase | What | Days | Status |
|-------|------|------|--------|
| **Stripe activation** | Add production keys, webhook, deploy worker | 0.5 | Blocked on Stripe account |
| **Operator Connect onboarding** | One operator completes Stripe Express | 0.5 | Blocked on operator |
| **USDC wallet connect** | Add ethers.js, USDC transfer call | 1-2 | Ready to build |
| **IPFS delivery** | Robot uploads data, demo shows CID | 2-3 | Needs robot-side work |
| **Base mainnet registration** | Register robot on Base with yakrover metadata | 0.5 | 8004 team |
| **Escrow contract** | On-chain hold/release for larger tasks | 5-7 | Future (v1.1 Phase 3) |
