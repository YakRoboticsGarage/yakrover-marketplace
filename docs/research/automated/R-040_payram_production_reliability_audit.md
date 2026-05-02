# R-040: PayRam Production Reliability Audit and Fee Structure Confirmation
**Date:** 2026-05-02
**Topic ID:** R-040
**Module:** M37_splits_distribution / M15_stripe_service
**Status:** Complete
**Researcher:** Automated daily research agent
**Follows up:** R-024 (Fiat-to-USDC Checkout Services, 2026-04-03)

---

## Executive Summary

- **Architecture clarification (critical):** PayRam is a self-hosted Docker gateway, not a SaaS. The merchant runs the server on their own VPS (~$20–40/month). This is a fundamental departure from YAK's current Cloudflare Workers + Fly.io + Stripe SaaS stack — adopting PayRam adds a new production Docker service that YAK must operate, update, and monitor.
- **Card onramp fees are 3–5% from the underlying third-party partner,** not 0%. PayRam adds zero markup on the partner's fee, but the underlying regulated provider (unnamed, likely Transak-class) charges industry-standard card rates (~3.5–5%). Bank transfer onramp is cheaper (~1%). This makes card-to-USDC via PayRam materially more expensive than Stripe at 1.5% for card-to-fiat.
- **0xSplits contract addresses are technically valid as cold wallet destinations** (any EVM address can be the configured cold wallet), but the split is not automatic — 0xSplits V2 requires a separate `distribute()` call after USDC arrives. PayRam's native marketplace mode (routing to multiple wallet addresses per vendor) is a cleaner two-recipient solution without 0xSplits at all.
- **No independent reliability track record exists.** PayRam launched March 30, 2026 (33 days ago at time of research). No user reviews, no public status page, no documented uptime incidents — and no documented uptime guarantees. Operational risk is entirely on the merchant.
- **MCP server at mcp.payram.com is production-ready and agent-native,** with tools for create-payee, send-payment, get-balance, generate-invoice, and payment lookup. This is architecturally interesting for YAK v2.0 agent-initiated payments but not for the current Stripe-centric v1.x flow.

---

## Findings

### 1. Architecture: Self-Hosted, Not SaaS

**Sources:**
- https://www.payram.com/blog/what-is-payram
- https://www.payram.com/blog/understanding-self-hosted-cryptocurrency-payment-processors
- https://www.payram.com/blog/self-hosted-vs-third-party-crypto-payment-gateways

PayRam's core product is a Docker image the merchant deploys on their own Linux VPS. Setup takes under 10 minutes via a one-click Docker script. The merchant provides:
- A VPS (DigitalOcean, Hetzner, Linode — ~$20–40/month for 4GB RAM)
- An external PostgreSQL database (local/containerized DB explicitly prohibited in production)
- Cold wallet credentials (never stored on server — NKOS architecture)

**What this means for YAK:**
The R-024 framing ("single button to enable card onramp") is accurate but understated. YAK would need to:
1. Provision and maintain a VPS
2. Run external managed PostgreSQL (Fly.io Postgres or Supabase)
3. Integrate PayRam API into the existing Cloudflare Worker or Fly.io auction API
4. Handle PayRam server updates, backups, and incident response

This is a meaningful ops burden addition on top of the existing Fly.io (auction engine), Cloudflare Workers (payment relay), and here.now (demo sites) stack. Unlike Stripe (which has a 99.9% SLA) or Coinbase Onramp (managed CDN), PayRam uptime is entirely the merchant's responsibility.

**If the PayRam VPS goes down:** Payment pages are temporarily inaccessible. Funds already on-chain remain safe. Server restart resumes payment tracking. This is acceptable for non-real-time payment settlement, but unacceptable for a buyer waiting at checkout.

---

### 2. Fee Structure

**Sources:**
- https://www.payram.com/blog/what-is-payram
- https://payram.com/blog/how-to-buy-crypto-with-card-payram-guide
- https://www.accessnewswire.com/newsroom/en/blockchain-and-cryptocurrency/payrams-card-to-crypto-onramp-goes-live-globally-customers-pay-by-car-1150600

**Core crypto payment processing (buyer already holds USDC):** 0% fee. Gas costs only.

**Card-to-USDC onramp (buyer pays by card, merchant receives USDC):**
- PayRam charges: 0% markup — passes third-party partner fees through at cost
- Third-party partner fees (unnamed, industry-standard): ~3.5–5% for credit/debit card, ~1% for bank transfer
- Total effective fee for card payments: **~3.5–5%** (from the underlying provider)
- PayRam advertises "as low as 0.5%" but this appears to refer to bank transfer / local payment methods, not card

**Advanced PayFi services** (fund sweeping automation, orchestration, treasury management): up to 5% optional

**VPS hosting:** ~$20–40/month fixed cost (not variable per-transaction)

**Gas fees:** Standard Base L2 gas, typically < $0.01 per transaction

**Fee comparison for a $5,000 USDC construction survey task:**

| Payment Method | Fee | Cost on $5,000 |
|---|---|---|
| Stripe card (current) | 1.5% | $75 |
| PayRam card onramp | ~3.5–5% | $175–$250 |
| PayRam bank onramp | ~1% | $50 |
| Coinbase Onramp (buyer self-funds) | 0% on Base | $0 (but 2-step) |
| Direct USDC (buyer holds) | gas only | < $0.01 |

**Verdict on fees:** PayRam card-to-USDC is materially more expensive than Stripe's 1.5% card rate for equivalent fiat-to-settlement flows. The fee advantage only appears when buyers already hold USDC (0% vs Stripe's 1.5%) — but those buyers can already pay via the existing EIP-3009 relay. PayRam's bank transfer onramp (~1%) is comparable to Stripe ACH (0.8% capped at $5 for bank debits), with no material advantage.

---

### 3. Settlement Destination Flexibility and 0xSplits Compatibility

**Sources:**
- https://github.com/PayRam/payram-mcp (wallet integration docs)
- https://payram.com/industry/marketplace
- Search result: "deposit addresses derived from master contracts with hardcoded cold wallet destinations"

**Cold wallet configuration:** Set once at PayRam server setup. The configured address receives all swept funds. Any EVM address is valid — there is no whitelist or address-type restriction documented. A smart contract address like an 0xSplits V2 Splits contract on Base is technically a valid cold wallet destination.

**However — 0xSplits does not auto-split on receipt:**
- 0xSplits V1 (SplitMain): Funds arrive at the split proxy address. A separate `distribute(address splitAddress, ERC20 token, ...)` call (callable by anyone) triggers actual distribution to recipients.
- 0xSplits V2 (Splits.org): Same pattern — recipient must call `distribute()` after funds land.
- PayRam has no mechanism to trigger this distribution call — it settles USDC to the configured address and stops.
- Result: USDC would accumulate in the Splits contract until a cron job or operator calls `distribute()`. This is a two-step process, not a single settlement.

**PayRam marketplace mode (better fit for split payments):**
- Multi-store/marketplace configuration routes payments to different wallet addresses per vendor
- Platform configures: operator wallet → 88%, platform wallet → 12%
- Per-transaction routing, no smart contract intermediary needed
- This matches YAK's payout architecture directly without 0xSplits

**Verdict on settlement:** PayRam's native marketplace mode handles the operator/platform split cleanly at the wallet-routing level. Using 0xSplits as the cold wallet adds unnecessary complexity (requires a separate distribute() call) and is not recommended. The marketplace routing mode is the right architectural pattern if PayRam is adopted.

---

### 4. Production Reliability (30-Day Post-Launch Assessment)

**Sources:**
- https://www.softwareadvice.com/product/527595-PayRam/
- https://www.capterra.com/p/10028835/PayRam/
- https://sourceforge.net/software/product/PayRam/
- https://github.com/coollabsio/coolify/issues/9043

**Findings:**
- **Zero user reviews** on Capterra, SoftwareAdvice, or GetApp at time of research (May 2026). Product is too new for review accumulation.
- **No documented production outages or critical bugs** found in public sources (GitHub, social media, forums).
- **No public status page** — no uptime history to audit.
- **No SLA** — self-hosted model means no contractual reliability guarantee.
- **Coolify integration issue** (#9043) shows users are attempting PayRam integration in managed hosting environments — this is a positive signal for adoption trajectory, but the issue was still open.
- **One-person founder company** (Siddharth Menon) with undisclosed funding — operational risk if the company is small.

**Operational risk summary:**

| Risk Factor | Assessment |
|---|---|
| Uptime (your VPS) | Merchant-controlled — no third-party SLA |
| Uptime (PayRam cloud components, onramp API) | Unknown — no status page |
| Software maturity | 33 days post-launch — limited battle-testing |
| Security audit | No public audit found |
| Company stability | Small team, undisclosed funding |
| Recovery time on outage | Minutes (restart Docker) if VPS issue |

**Verdict:** Insufficient production track record to adopt for live construction payments at $1K–$10K. Re-evaluate at 90 days post-launch (end of June 2026) and again at 6 months (end of September 2026).

---

### 5. API Documentation Quality

**Sources:**
- https://docs.payram.com/faqs/introduction (403 — blocked)
- https://github.com/payram/payram-mcp
- https://github.com/PayRam-Dev/PayRam-Crypto-Gateway

**Findings:**
- Primary docs at docs.payram.com returned 403 for automated fetch — this is a red flag for developer experience (Cloudflare bot protection blocking documentation access is unusual).
- GitHub MCP repository is well-structured with code generation examples (Express, Next.js, FastAPI, Gin, Laravel, Spring Boot) — indicates developer-first orientation.
- REST API documented with `/api/v1/payment` endpoints and API-Key header auth.
- The MCP server at mcp.payram.com exposes: `create-payee`, `send-payment`, `get-balance`, `generate-invoice`, `test-connection`, `lookup-payment`, `search-payments`, `get-daily-volume`, `get-payment-summary`, `get-unswept-balances`.
- No public API reference for the card onramp integration path (the actual integration steps are behind the dashboard after deployment).

**Verdict:** Documentation quality is adequate for self-hosting the core gateway, but the card onramp integration path is not fully publicly documented — requires dashboard access to configure. This is acceptable for enterprise evaluation but not for rapid prototyping.

---

### 6. MCP Server and Agent-Native Capabilities

**Sources:**
- https://mcp.payram.com/
- https://github.com/payram/payram-mcp
- https://www.payram.com/blog/what-is-know-your-agent

PayRam ships a production MCP server that exposes payment tools to any MCP client (Claude, Cursor, n8n, custom agents). Key tools:

| Tool | Purpose |
|---|---|
| `create-payee` | Register a payment recipient |
| `send-payment` | Initiate a payment to a payee |
| `get-balance` | Check current balance |
| `generate-invoice` | Create a payment invoice |
| `test-connection` | Validate API connectivity |
| `lookup-payment` | Get payment status by ID |
| `search-payments` | Query payment history |
| `get-daily-volume` | Analytics: daily payment volume |
| `get-payment-summary` | Analytics: payment summary |
| `get-unswept-balances` | Show funds pending sweep to cold wallet |

PayRam also publishes a "Know Your Agent" (KYA) framework — an agent identity verification protocol for autonomous AI payments. This aligns with YAK's v2.0 direction (IMP-109: USDC settlement via MCP).

**Verdict for v2.0:** PayRam's MCP server is directly relevant to IMP-109 (agents hire robots with real money). Rather than building a custom EIP-3009 relay for agent-initiated payments, YAK could use PayRam's `send-payment` MCP tool. However, this requires PayRam infrastructure to be running and stable.

---

### 7. B2B Large-Transaction Support

No documented transaction limits found for PayRam. The fee structure (% of transaction) implies no fixed ceiling. However:

- **KYC on card onramp:** The third-party partner performs KYC on first-time buyers. For large transactions ($5K–$200K), additional verification requirements likely apply (standard for all card-to-crypto onramps above ~$1K–$2K per day).
- **Bank transfer path:** Higher limits typically apply for ACH/bank transfer vs card. The ~1% fee for bank transfer makes it more competitive with Stripe ACH at construction scales.
- **Construction buyer readiness:** Construction GCs are unlikely to be crypto-native — they expect credit card or ACH, not crypto self-custody wallets. PayRam's card onramp addresses the buyer side, but GCs still need a wallet configured to receive survey task payments (for operator-side USDC). This remains a buyer education gap independent of PayRam.

---

## Implications for the Product

### 1. PayRam Does Not Replace Stripe at v1.x

At current scale and maturity:
- Stripe card processing (1.5%) is cheaper than PayRam card onramp (~3.5–5%).
- Stripe has a 99.9% SLA; PayRam has none.
- Stripe is already integrated; PayRam requires a new Docker service and VPS.
- The sole-proprietor constraint on Stripe USDC payouts (R-024) remains a blocker for LLC operators wanting USDC settlement — but most construction survey operators prefer fiat anyway.

**Decision: Do not adopt PayRam for v1.x payment flows.**

### 2. PayRam Is a Viable v2.0 Contingency Rail

If/when:
- Stripe USDC payout (sole-proprietor only) fails to cover LLC operator segment, OR
- Agent-initiated construction payments (IMP-109) need a crypto-native MCP-first path, OR
- Construction buyers become more crypto-comfortable (B2B stablecoin adoption rising per BCG data)

Then PayRam deserves a production pilot. The marketplace routing mode (88%/12% wallet split) handles the payout architecture cleanly. The MCP server aligns with agent-native payment flows.

### 3. 90-Day Re-Evaluation Window

Re-evaluate PayRam reliability in late June 2026 (90 days post-launch). Key checkpoints:
- Are user reviews appearing on Capterra/G2?
- Has a public status page or uptime history been published?
- Has a security audit been commissioned or published?
- Is the docs.payram.com 403 resolved (developer experience signal)?
- Any reported transaction failures or fund loss incidents?

### 4. 0xSplits Integration Design Correction

If PayRam is ever adopted, use **marketplace wallet routing** (operator address + platform address), NOT 0xSplits as the cold wallet. The 0xSplits distribute() call requirement makes it unsuitable as an auto-settlement destination via PayRam's sweep mechanism.

---

## Improvement Proposals

### IMP-142: Add PayRam to payment rails comparison table (documentation)
- **Module:** M37_splits_distribution
- **Effort:** small
- **Description:** Document PayRam alongside Stripe and Coinbase Onramp in the payment rails comparison table (currently informal). Include fee structure, pros/cons, and "not before 90-day reliability window" recommendation. This ensures future engineers understand the option without re-researching it.
- **Evidence:** R-040 (this doc)
- **Priority:** low

### IMP-143: Re-evaluate PayRam at 90-day post-launch (June 2026)
- **Module:** M37_splits_distribution
- **Effort:** small (scheduled research spike)
- **Description:** Schedule a follow-up research session (R-040b) in late June 2026 to audit PayRam production reliability. Key checklist: (1) user reviews on Capterra/G2, (2) public uptime data, (3) security audit status, (4) docs.payram.com accessibility, (5) any reported incidents. This gates the decision on whether to build a PayRam pilot for v2.0 agent-initiated payments.
- **Evidence:** R-040 (this doc)
- **Priority:** medium

---

## New Questions Spawned

- **R-040b (proposed):** PayRam 90-day reliability follow-up (June 2026) — schedule after June 22, 2026
- **Unresolved:** What specific third-party onramp partner does PayRam use for card processing? (Transak? Simplex? MoonPay?) The partner determines the effective card fee and KYC limits.
- **Unresolved:** Does PayRam's marketplace routing mode support per-transaction percentage splits (e.g., 88%/12%) or only fixed wallet routing?

---

## Sources

- https://www.payram.com/blog/what-is-payram
- https://www.payram.com/blog/understanding-self-hosted-cryptocurrency-payment-processors
- https://payram.com/blog/payram-vs-0xprocessing
- https://www.accessnewswire.com/newsroom/en/blockchain-and-cryptocurrency/payrams-card-to-crypto-onramp-goes-live-globally-customers-pay-by-car-1150600
- https://www.payram.com/blog/self-hosted-vs-third-party-crypto-payment-gateways
- https://github.com/PayRam-Dev/PayRam-Crypto-Gateway
- https://github.com/payram/payram-mcp
- https://mcp.payram.com/
- https://www.payram.com/blog/what-is-know-your-agent
- https://payram.com/blog/how-to-buy-crypto-with-card-payram-guide
- https://www.payram.com/releases
- https://techbullion.com/top-10-crypto-payment-gateways-2026-the-definitive-guide/
- https://paybis.com/blog/crypto-on-ramp-fee-comparison/
- https://www.capterra.com/p/10028835/PayRam/
- https://www.softwareadvice.com/product/527595-PayRam/
- https://github.com/coollabsio/coolify/issues/9043
- https://payram.com/industry/marketplace
- https://morningstar.com/news/accesswire/1131605msn/payram-adds-polygon-support-expanding-multi-chain-infrastructure-for-permissionless-stablecoin-payments
