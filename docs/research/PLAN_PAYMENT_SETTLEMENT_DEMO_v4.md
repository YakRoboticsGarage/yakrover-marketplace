# Plan: Live Payment Settlement Demo (v4 — Implementation Status)

**Date:** 2026-04-05 (v1.1 milestone 2)
**Status:** USDC payment working end-to-end on **Base mainnet** with real ERC-8004 robot. Stripe working in test mode. Two-phase demo with correct user journey.
**Supersedes:** v3
**Demo:** https://yakrobot.bid/mcp-demo-2/
**Goal:** Real money through a real robot auction. Buyer pays, operator and platform both get paid.
**Milestone tags:** `v1.1-milestone-payment-e2e` (Sepolia), `v1.1-milestone-base-mainnet` (mainnet + UX)

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

### Step 4: Payment — WORKING (both Stripe test + USDC on Base Sepolia)

**USDC (crypto) — CONFIRMED WORKING 2026-04-05:**
- Two-phase commit-on-hire: buyer signs ERC-2612 permit on award (no money moves), buyer clicks Release after delivery + QA (money moves)
- Worker endpoint `POST /api/commit-payment` stores signed permit in KV
- Worker endpoint `POST /api/execute-payment` submits permit + 2x transferFrom on-chain
- 88% to operator wallet, 12% to platform wallet
- Relay wallet (`0x4b59...0d9`) pays gas (~$0.005 on Base)
- Tested on Base Sepolia with real USDC, Rabby wallet
- Bugs fixed during milestone: missing `balanceOf` in ABI, blocking httpx calls in async handlers, mock fleet calling missing simulator

**Stripe (fiat) — WORKING (test mode):**
- Worker endpoint `POST /api/create-checkout` creates Stripe Checkout Session
- Uses destination charges: `application_fee_amount` (12%) stays on platform, 88% transfers to operator Connect account
- Worker endpoint `GET /api/payment-status` polls session status
- Worker endpoint `POST /api/stripe-webhook` handles `checkout.session.completed`
- **Remaining:** production Stripe keys + operator Stripe Connect onboarding

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

### For USDC path ($0.01) — GASLESS:
1. [x] ~~Add ethers.js to demo page for wallet connect~~ — DONE
2. [x] ~~USDC transfer call~~ — DONE (ERC-2612 permit relay, platform pays gas)
3. [x] ~~Show block explorer tx links~~ — DONE
4. [x] ~~Platform wallet configured~~ — DONE (`0xe33356d0d16c107eac7da1fc7263350cbdb548e5`)
5. [x] ~~Relay wallet configured~~ — DONE (`0x4b5974229f96ac5987d6e31065d73d6fd8e130d9`)
6. [x] ~~Relay wallet funded~~ — DONE (0.05 ETH Sepolia, 0.04 ETH Base Sepolia, 0.01 ETH mainnet, 0.01 ETH Base mainnet)
7. [x] ~~Worker deployed with RELAY_PRIVATE_KEY~~ — DONE
8. [x] ~~Gasless flow~~ — DONE (buyer signs EIP-712 permit, no ETH needed)
9. [x] ~~Multi-wallet support~~ — DONE (Rabby, MetaMask, Coinbase Wallet via window.ethereum)
10. [x] ~~Multi-chain support~~ — DONE (Base mainnet, Ethereum mainnet, Base Sepolia, Eth Sepolia)
11. [ ] Buyer needs Sepolia USDC for testing (get from faucet.circle.com)

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
| 6 | Delivery verification | IPFS upload + CID + schema-driven QA. Built. | 2026-04-02 |
| 7 | x402 | Not used for marketplace settlement. Reserved for agent-to-robot control. | 2026-04-02 |
| 8 | Discovery method | Direct subgraph + RPC fallback from browser. No server dependency. | 2026-04-02 |
| 9 | Fiat-to-USDC bridge | Research topic R-024. Not built — keep rails separate. | 2026-04-02 |
| 10 | Delivery QA | Schema-driven: task spec includes `delivery_schema`, robot self-checks, QA validates same schema. No surprises. | 2026-04-05 |
| 11 | Payment timing | Commit-on-hire: permit signed on award, executed on delivery acceptance. No upfront charge. | 2026-04-05 |
| 12 | 25/75 split | Removed. Full payment on delivery only. Escrow deferred to high-value tasks. | 2026-04-05 |

---

## What Else Was Built (2026-04-02)

### IPFS Delivery (Step 3)
- Worker endpoint `POST /api/upload-delivery` uploads JSON to Pinata, returns IPFS CID
- Demo auto-uploads sample sensor data (3 waypoints, temp/humidity) after auction
- Buyer sees real IPFS link to verify data before releasing payment
- **Needs:** `PINATA_JWT` worker secret

### USDC Payment (Step 4)
- ethers.js wallet connect (MetaMask / Coinbase Wallet)
- Auto-detects chain, prompts switch if wrong
- Two USDC transfers: 88% to operator wallet, 12% to platform wallet
- Both tx hashes shown with block explorer links
- USDC addresses configured per chain (Base mainnet, Base Sepolia, Eth Sepolia)
- Platform wallet: `0xe33356d0d16c107eac7da1fc7263350cbdb548e5`

### Feedback Loop (Step 5)
- Star rating + comment after payment (both Stripe and USDC flows)
- Worker endpoint `POST /api/auction-feedback` stores in KV + creates GitHub issue
- MCP tool `auction_submit_feedback` for agent-submitted feedback
- GitHub issues labeled `feedback` + `auction` + role
- Daily research agent reads feedback issues, creates improvement proposals, closes processed issues
- `GITHUB_TOKEN` worker secret: CONFIGURED ✓ (issue #2 created successfully)

### Robot Operator Onboarding
- Complete guide at `docs/onboarding/ROBOT_OPERATOR_ONBOARDING.md`
- 3 MCP tools spec: `robot_submit_bid`, `robot_execute_task`, `robot_get_pricing`
- On-chain metadata additions, wallet verification, Stripe Connect setup
- Testing instructions with curl examples
- Sent to 8004 team for implementation

### Automated Research + Docs Sync
- Daily research agent (9am Berlin): picks topics, does web research, writes findings, spawns new topics
- Now reads GitHub feedback issues and incorporates into research/proposals
- Weekly self-critique (R-META-001) reviews all research + feedback
- Daily docs-sync agent (7pm Berlin): updates stats across all admin docs
- Both send Telegram notifications via GitHub Action pipeline

---

## What's Done vs What's Remaining

### Done
| What | Status |
|------|--------|
| Browser robot discovery (subgraph + getAgentWallet RPC + fallback) | ✅ Live |
| Ethereum mainnet + Base + Sepolia in discovery chains | ✅ Live |
| Auction via MCP server + Claude tool_use | ✅ Live (needs tunnel) |
| Discovered robot injected into auction prompt | ✅ Live |
| IPFS delivery upload (Pinata via worker) | ✅ Live (PINATA_JWT configured) |
| Gasless USDC (ERC-2612 permit relay) | ✅ Live |
| Commit-on-hire (permit on award, execute on delivery) | ✅ Live |
| Multi-wallet (Rabby, MetaMask, Coinbase Wallet) | ✅ Live |
| Multi-chain (Eth mainnet, Base, Sepolia) | ✅ Live |
| Relay wallet funded on all chains | ✅ Live |
| Stripe Checkout (test mode, $1.00, 88/12 split) | ✅ Live |
| Schema-driven delivery QA | ✅ Live |
| 4-level buyer-configurable QA (none → schema → standards → PLS) | ✅ Live |
| Feedback loop (demo → KV + GitHub issue → research agent) | ✅ Live |
| Platform USDC wallet | ✅ 0xe333...8e5 |
| All worker secrets configured | ✅ ANTHROPIC, GITHUB, RELAY, PINATA, STRIPE (test) |

### Current phase: waiting on 8004 team
| What | Blocker |
|------|---------|
| **Robot MCP tools** (`robot_submit_bid`, `robot_execute_task`) | Anuraj — PR #5 plan reviewed |
| **Robot registration on mainnet** (Eth or Base) | Anuraj — multi-chain Stage 6 |
| **End-to-end test**: real bid → real execution → real sensor data → IPFS → QA → USDC payment | Blocked on above two |

### Next phase: after USDC + robot execution confirmed working
| What | Notes |
|------|-------|
| Stripe production (`sk_live_`) | Replace test key with live key |
| Operator Stripe Connect onboarding | Anuraj or robot operator completes real KYC |
| Stripe Connect ID in robot agent card | Currently hardcoded `acct_1TEjjLC2lXDckgmS` in demo |
| Stripe payment confirmation to operator | Robot doesn't currently verify Stripe payment |
| Stripe webhook for status tracking | `STRIPE_WEBHOOK_SECRET` ready, endpoint built, needs registration |

### Future
| What | Notes |
|------|-------|
| Escrow contract on Base/Ethereum | On-chain hold/release for high-value tasks (>$10K) |
| Splits.org for multi-operator distribution | Production-scale revenue splitting |
| Fiat-to-USDC checkout | Research topic R-024 | TBD |
| Splits.org integration | Production-scale multi-operator distribution | 2-3 |
