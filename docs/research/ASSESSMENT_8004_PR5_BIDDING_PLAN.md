# Assessment: yakrover-8004-mcp PR #5 — Bidding Marketplace Plan

**Date:** 2026-04-04
**PR:** https://github.com/YakRoboticsGarage/yakrover-8004-mcp/pull/5
**Author:** Anuraj R
**Document:** `docs/BIDDING_MARKETPLACE_PLAN.md` (691 lines, 6 stages)

---

## Summary

Anuraj proposes a full implementation plan for the robot side of the marketplace integration. The plan creates an `src/auction/` package inside yakrover-8004-mcp with its own `AuctionEngine`, models, MCP tools, and Stripe payment handler — plus multi-chain support and per-robot bidding terms.

---

## What Aligns Well With Our Marketplace

### 1. The three MCP tools match our protocol spec exactly
`robot_submit_bid`, `robot_execute_task`, `robot_get_pricing` — same names, same input/output shapes as our spec in yakrover-protocols#15. The schemas are compatible. This is the most important alignment.

### 2. The flow diagram matches
His overview flow (DISCOVER → BID → AWARD → EXECUTE → DELIVER → VERIFY → PAY) matches our plan v4 exactly. He correctly identifies that his repo owns steps 2 and 4, and the marketplace owns the rest.

### 3. BiddingTerms dataclass is well-designed
`min_price_cents`, `rate_per_minute_cents`, `accepted_task_types`, `max_concurrent_tasks`, `requires_approval` — all useful for the marketplace to read during discovery. Storing them in the IPFS agent card (not on-chain KV) is the right call — cheaper to update, richer structure.

### 4. Delivery format matches
His `execute()` return format matches what our IPFS upload expects: `{success, delivery_data: {readings, summary, robot_id, robot_name, duration_seconds}}`. The marketplace wraps this in the `yakrover/delivery/v1` envelope.

### 5. Multi-chain support (Stage 6) is excellent
Adding `--chain` flag to all scripts with a central `chains.py` config is clean engineering. Supports eth-sepolia, eth-mainnet, base-sepolia, base-mainnet. This unblocks Base registration immediately, which is what we need for the demo.

### 6. Plugin bid implementations are practical
Tumbller bids on `env_sensing` (has temp/humidity), FakeRover already has `bid()`, Tello bids on `camera` tasks. Good separation of concerns.

---

## What Needs Discussion

### 1. Duplicate AuctionEngine — the biggest architectural question

His plan creates `src/auction/engine.py` inside yakrover-8004-mcp with its own `AuctionEngine` class. We already have `auction/engine.py` in yakrover-marketplace with a full state machine (1,464 lines, 11 states, 35 MCP tools, 251 tests).

**His engine** is fleet-level orchestration — fans out bid requests to all local plugins, tracks auction state, handles Stripe checkout. It's designed for LLM clients connected directly to the fleet server (Claude Desktop talking to `/fleet/mcp`).

**Our engine** is marketplace-level orchestration — discovers robots via subgraph, scores bids with 4-factor weighting, manages payment settlement, event logging, deliverable QA, feedback.

**The question:** Do we need two engines, or should the fleet server delegate to the marketplace engine?

**Assessment:** Two engines serving two use cases is actually fine:
- **Fleet engine** (his): "I'm connected to this fleet gateway, let me run a quick auction among the robots behind this server." Local, fast, no blockchain involved.
- **Marketplace engine** (ours): "I discovered robots across the network via ERC-8004, let me run a global auction." Cross-fleet, on-chain, IPFS delivery, Stripe/USDC settlement.

The fleet engine is a subset of the marketplace engine. The risk is **divergence** — if the two engines have different bid schemas, state machines, or payment flows, they become hard to maintain. The mitigation is the shared protocol spec (yakrover-protocols#15).

**Recommendation:** Proceed with two engines, but ensure the fleet engine's bid/execute interfaces match the marketplace protocol spec exactly. The fleet engine doesn't need scoring, settlement, or QA — it's a lighter-weight local orchestrator.

### 2. Stripe payment on the robot side — should this exist?

His plan puts `StripePaymentHandler` in yakrover-8004-mcp (`src/auction/payments.py`). This creates Stripe Checkout sessions on the fleet server and handles webhooks.

**Our marketplace already does this** — the Cloudflare Worker has `/api/create-checkout` with `application_fee_amount` (12% commission) and destination charges to operator Connect accounts.

**The conflict:** If the fleet server creates its own Stripe sessions, the platform commission (12%) won't be applied. The buyer pays the fleet directly, bypassing the marketplace.

**Assessment:** This is the right approach for the fleet-direct use case (LLM client → fleet server, no marketplace in between). But for marketplace-mediated auctions, the marketplace must create the Stripe session (with commission).

**Recommendation:** His Stripe handler should be for fleet-direct use only. When the marketplace mediates, it handles payment. The fleet server should check whether the task came from the marketplace (has a `request_id` from our engine) and skip its own payment flow if so.

### 3. `task_category` mapping — "sensor_reading" vs "env_sensing"

His plan uses `sensor_reading` and `camera` as v1 task types, mapping to our `env_sensing` and `visual_inspection`. The mapping is documented but it's a translation layer that could cause bugs.

**Recommendation:** Use our marketplace categories directly (`env_sensing`, `visual_inspection`) as the canonical names. The fleet can use whatever internal names it wants, but the `robot_submit_bid` tool should accept and return marketplace categories. He already notes this — just needs to be enforced.

### 4. No bid scoring on the fleet side

His engine accepts bids and lets the client pick a winner. Our engine scores bids with 4-factor weighting (price 40%, SLA 25%, confidence 20%, reputation 15%).

**Assessment:** This is correct. The fleet server is a pass-through — it collects bids and returns them. Scoring is the marketplace's job. The fleet server shouldn't impose its own scoring because the buyer (via the marketplace) might have different priorities.

### 5. `requires_approval` flag

His `BiddingTerms` includes `requires_approval: bool = True` — whether the fleet operator must approve before execution. This is a good safety feature for physical robots (operator wants to confirm before a robot moves).

**Assessment:** Our marketplace doesn't have this concept yet. When we call `robot_execute_task`, we assume execution is immediate. If the robot returns "waiting for approval," our engine would need to handle a new intermediate state.

**Recommendation:** For v1, this is fine as a robot-side concern. The robot's `execute()` method can block until approval is granted (or timeout). The marketplace just sees a slow execution, not a new state.

---

## What's Missing

### 1. No mention of deliverable QA
Our marketplace runs 4-level QA checks (basic → standards → PLS) on delivery data before payment release. His plan doesn't mention QA — the robot returns data and the marketplace uploads it. This is correct (QA is the marketplace's job), but he should know it exists so delivery_data includes the fields we check (CRS, accuracy, point density for Level 2+).

### 2. No mention of feedback integration
He mentions it in Stage 5c as "optional for v1" and shows the correct `auction_submit_feedback` call. Good — just needs to be wired once the marketplace MCP endpoint is reachable.

### 3. No mention of event tracking
Our marketplace emits events for every state transition (event log, M30). The fleet engine should emit similar events so the operator dashboard can show progress. Not blocking but worth noting.

---

## Impact on Our Marketplace if We Proceed

### What works immediately
- **Discovery:** Our demo page already queries the subgraph for `fleet_provider: yakrover`. Once he registers on Base (Stage 6), robots appear.
- **Wallet:** `getAgentWallet` already works. USDC payment flows through.
- **Bidding:** Our marketplace can call `robot_submit_bid` on each robot's MCP endpoint. His bid format matches our protocol spec.
- **Execution:** Our marketplace can call `robot_execute_task`. His delivery format matches our IPFS upload envelope.
- **Pricing:** Our marketplace can call `robot_get_pricing` to show pricing before auction.

### What needs coordination
- **Two Stripe flows:** Marketplace-mediated auctions should use our Stripe Checkout (with commission). Fleet-direct auctions use his. Need a flag or convention to distinguish.
- **Task categories:** Ensure `robot_submit_bid` uses marketplace categories, not internal fleet names.
- **BiddingTerms in discovery:** Our demo page needs to parse the IPFS agent card for bidding_terms and show them (we currently don't read IPFS).

### What doesn't affect us
- His internal fleet engine (`fleet_request_bids`, `fleet_accept_bid`, etc.) — these are for LLM clients on the fleet server, not for our marketplace. We call the robot-level tools directly.
- His `src/auction/` package — completely separate from our `auction/` package. No naming conflict since they're in different repos.

---

## Recommended Implementation Order (from our perspective)

1. **Stage 6 first** (multi-chain) — unblocks Base registration, which is our #1 blocker
2. **Stage 1d** (robot MCP tools) — the three tools we need to call from the marketplace
3. **Stage 3** (bidding terms on-chain) — so our discovery shows pricing before auction
4. **Stage 2a** (Tumbller bid/execute) — the physical robot we demo with
5. Everything else — fleet engine, Stripe handler, approval flow — can come later

---

## Questions for Anuraj

1. **Two engines:** Are you comfortable with your fleet engine being a lighter-weight local orchestrator (no scoring, no QA, no settlement) while the marketplace engine handles the full lifecycle?

2. **Stripe disambiguation:** When the marketplace creates a Stripe session (with 12% commission), should the robot-side skip its own payment flow? How should the fleet server know "this task came from the marketplace, payment is handled externally"?

3. **Stage 6 timeline:** Can multi-chain support land first? It's our highest-priority blocker for the Base registration demo.

4. **BiddingTerms in IPFS:** Will the agent card JSON include the full `bidding_terms` object, or just the flat metadata keys (`min_bid_price`, `accepted_currencies`, `task_categories`)? Our demo page reads the agent card via subgraph — we need to know the exact field names.
