# Plan: Live Payment Settlement Demo (v3 — Real Auction, Real Robots, Real Delivery)

**Date:** 2026-04-02
**Status:** Draft for review
**Supersedes:** v2 (same file without _v3)
**Goal:** A real auction with robots registered on Base, verifiable data delivery via IPFS, and real payment settlement where buyer can verify before releasing funds.

---

## The Full Flow

```
1. DISCOVER    Robot registered on Base (ERC-8004) with payment address in agent card
2. AUCTION     Buyer posts task → robot bids → buyer awards winner
3. EXECUTE     Robot performs survey task
4. DELIVER     Robot uploads deliverables to IPFS → submits delivery tx on-chain
                 {commitment_hash, ipfs_cid, data_hash}
5. VERIFY      Buyer downloads from IPFS, checks content matches spec
6. PAY         Buyer releases payment → Stripe (fiat) or USDC via Splits (crypto)
7. PROVE       On-chain record: task → delivery → payment. All verifiable.
```

---

## What Makes This a "Real" Demo

| Element | Fake (current mcp-demo) | Real (this plan) |
|---------|------------------------|-------------------|
| Robot | Mock fleet in Python | ERC-8004 registered on Base |
| Auction | Simulated scoring | Real engine with real bids |
| Delivery | In-memory dict | IPFS upload + on-chain delivery record |
| Verification | `pls_review_status: "PENDING"` | Buyer downloads from IPFS, checks data |
| Payment | Logged to stdout | Stripe Checkout or USDC transfer |
| Proof | None | On-chain: delivery tx + payment tx |

---

## Component 1: ERC-8004 Agent Card — Payment Fields

**Spec for 8004 team.** Add these fields to the agent card:

### On-chain metadata additions
```python
agent.setMetadata({
    # ... existing fields ...
    "payment_address": "0x...",              # Wallet address for USDC on Base
    "stripe_connect_id": "acct_...",         # Stripe Connect Express account (optional)
    "accepted_payments": "stripe,usdc",      # Comma-separated methods
    "min_task_price": "50",                  # Minimum in cents (USD)
})
```

### IPFS service metadata additions
```json
{
  "services": [
    {
      "name": "MCP",
      "endpoint": "https://...",
      "mcpTools": [...],
      "fleetEndpoint": "https://...",
      "payment": {
        "accepted_methods": ["stripe", "usdc"],
        "stripe_connect_id": "acct_...",
        "usdc_wallet": "0x...",
        "usdc_chain": "base",
        "splits_address": "0x...",
        "min_task_price_cents": 50,
        "currency": "usd"
      }
    }
  ]
}
```

### Enable x402 flag
```python
agent.setX402Support(True)  # Currently False
```

### Registration flow change
When an operator registers their robot:
1. Operator completes Stripe Connect Express onboarding → gets `acct_...`
2. Operator provides (or we generate) a Base wallet address for USDC
3. Both IDs stored in agent card on-chain + IPFS
4. Marketplace discovers robots and reads payment info from agent card

---

## Component 2: Verifiable Delivery via IPFS

### The problem
Currently `DeliveryPayload.data` is an in-memory dict. The buyer has no way to verify the data exists independently. For payment release to be trustworthy, delivery must be:
- **Immutable** — content can't change after submission
- **Addressable** — buyer can fetch it independently
- **Verifiable** — content hash matches what was promised

### The solution: IPFS + on-chain record

**Step 1: Robot uploads deliverables to IPFS**
```
Robot completes survey
  → Packages deliverables (LAS, GeoTIFF, DXF, report PDF)
  → Uploads to IPFS (via Pinata, web3.storage, or direct)
  → Gets back CID (content-addressable hash): e.g. bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi
```

**Step 2: Robot submits delivery record**
Could be on-chain (tx on Base) or via MCP tool. For the demo, an MCP tool is simpler:
```
auction_submit_delivery(
    request_id: "req_...",
    ipfs_cid: "bafybei...",
    data_hash: "sha256:abc123...",    # Hash of the actual file(s)
    file_manifest: [
        {"name": "point_cloud.las", "size_bytes": 4200000, "format": "LAS 1.4"},
        {"name": "ortho.tiff", "size_bytes": 12000000, "format": "GeoTIFF"},
        {"name": "report.pdf", "size_bytes": 350000, "format": "PDF"}
    ]
)
```

**Step 3: Buyer verifies**
```
Buyer receives delivery notification
  → Downloads from IPFS gateway: https://ipfs.io/ipfs/{cid}
  → Checks: files present, formats correct, data plausible
  → Clicks "Accept delivery + release payment"
  OR
  → Clicks "Reject — data doesn't match spec"
```

### For the demo
The "robot" uploads a pre-packaged sample dataset to IPFS (real LAS snippet, real GeoTIFF, real PDF report). The CID is real and verifiable. The buyer can actually click the IPFS link and see real survey data.

---

## Component 3: Demo Page (yakrobot.bid/mcp-demo-2)

### Updated flow

```
┌─────────────────────────────────────────────────────────┐
│  1. DISCOVER                                             │
│  "Found 3 robots on Base with survey capabilities"       │
│  [Robot cards with real ERC-8004 data]                   │
├─────────────────────────────────────────────────────────┤
│  2. AUCTION                                              │
│  Claude processes RFP → posts task → collects bids       │
│  [Step feed — same as current demo]                      │
├─────────────────────────────────────────────────────────┤
│  3. DELIVERY                                             │
│  "Apex Aerial delivered survey data"                     │
│  IPFS: bafybei...  [View on IPFS →]                     │
│  Files: point_cloud.las (4.2MB), ortho.tiff (12MB)      │
│  Data hash: sha256:abc123...                             │
│                                                          │
│  [Download & Verify]  [View on Basescan →]               │
├─────────────────────────────────────────────────────────┤
│  4. PAYMENT                                              │
│  "Release payment to Apex Aerial Surveys"                │
│                                                          │
│  Task total:           $0.50                             │
│  Operator payout:      $0.44 (88%)                       │
│  Platform commission:  $0.06 (12%)                       │
│                                                          │
│  [Pay $0.50 with Card]    [Pay $0.01 USDC]              │
├─────────────────────────────────────────────────────────┤
│  5. CONFIRMATION                                         │
│  ✓ Payment complete                                      │
│  Operator received: $0.44                                │
│  Platform received: $0.06                                │
│  [View Stripe receipt →]  [View on Basescan →]          │
│                                                          │
│  On-chain proof:                                         │
│  • Robot identity: ERC-8004 #989 on Base                │
│  • Delivery: IPFS bafybei... (verified)                  │
│  • Payment: Stripe tr_... or Base tx 0x...              │
└─────────────────────────────────────────────────────────┘
```

---

## Component 4: Payment Settlement

### Stripe rail (Phase 1 — built in mcp-demo-2)
- Buyer clicks "Pay $0.50 with Card"
- Stripe Checkout with `application_fee_amount` (12%) + `transfer_data.destination` (operator's `acct_...` from agent card)
- Webhook confirms → receipt shown

### USDC rail (Phase 2)
- Buyer clicks "Pay $0.01 USDC"
- Wallet connect (Coinbase Wallet / MetaMask)
- USDC transfer to Splits.org contract on Base (88/12 auto-split)
- Basescan tx link shown

### Future: fiat-in/USDC-out (R-024 research)
- Buyer pays with card via Coinbase Onramp or Stripe crypto payouts
- USDC arrives at Splits contract
- Operator receives USDC, platform receives USDC
- One buyer UX, one settlement rail

---

## Implementation Phases

### Phase 1: Stripe settlement (BUILT — needs activation)
Already in mcp-demo-2. Needs:
- [ ] Production Stripe account + keys in worker
- [ ] One operator completes Connect onboarding
- [ ] Webhook registered in Stripe dashboard
- [ ] Worker redeployed with secrets

### Phase 2: ERC-8004 payment fields (1-2 days, 8004 team)
- [ ] Add `payment` fields to RobotMetadata dataclass
- [ ] Add payment metadata to on-chain registration
- [ ] Add payment service descriptor to IPFS agent card
- [ ] Register at least 1 robot on Base with payment info
- [ ] Update discovery.py to return payment fields

### Phase 3: IPFS delivery (2-3 days)
- [ ] Pre-package sample survey dataset (LAS snippet, GeoTIFF, PDF report)
- [ ] Upload to IPFS via Pinata (one-time, get CID)
- [ ] New MCP tool: `auction_submit_delivery_ipfs(request_id, ipfs_cid, data_hash, manifest)`
- [ ] Update `confirm_delivery` to verify IPFS CID is accessible
- [ ] Demo page: show IPFS link, file manifest, data hash in delivery step

### Phase 4: Wire discovery → auction → delivery → payment (2-3 days)
- [ ] Demo page discovers real robots from Base (via MCP server calling discovery.py)
- [ ] Auction uses real robot data (capabilities, pricing from agent card)
- [ ] Delivery shows real IPFS CID (pre-staged data)
- [ ] Payment reads `stripe_connect_id` or `usdc_wallet` from agent card
- [ ] Confirmation shows on-chain proof links

### Phase 5: USDC payment via Splits (2-3 days)
- [ ] Create Splits.org contract on Base (88/12)
- [ ] Wallet connect in demo page
- [ ] USDC transfer to Split address
- [ ] Basescan proof link

### Total: ~10-12 days

---

## What the 8004 Team Needs to Do

**Priority: HIGH — blocks the demo**

1. **Add payment fields to agent card schema** (see Component 1 above)
2. **Register at least 1 robot on Base mainnet** with:
   - Survey capabilities (aerial_lidar, rtk_gps, photogrammetry)
   - Stripe Connect account ID (operator completes onboarding)
   - USDC wallet address on Base
3. **Update discovery tool** to return payment fields
4. **Enable x402 support flag** on the registered robot

**Deliverable:** A robot discoverable on Base with `discover_robot_agents()` that returns a payment section in the agent card.

---

## Sample Delivery Dataset (Pre-Staged)

For the demo, we pre-upload a real (but small) survey dataset to IPFS:

```
demo-survey-delivery/
├── point_cloud_sample.las      # 500KB — real LAS 1.4 point cloud (small area)
├── orthomosaic_sample.tiff     # 2MB — real GeoTIFF orthomosaic
├── topo_surface.xml            # 100KB — LandXML surface
├── survey_report.pdf           # 200KB — generated report with accuracy stats
└── manifest.json               # File list, sizes, formats, CRS, accuracy
```

This gets uploaded once to IPFS. The CID never changes. Every demo run references the same CID but the auction/payment is different each time.

---

## End-to-End Proof Chain

After a successful demo run, an observer can independently verify:

| What | Where to verify | Link format |
|------|----------------|-------------|
| Robot exists | Base block explorer | `basescan.org/token/{erc8004_address}?a={token_id}` |
| Robot capabilities | IPFS | `ipfs.io/ipfs/{agent_card_cid}` |
| Delivery data exists | IPFS | `ipfs.io/ipfs/{delivery_cid}` |
| Delivery data is authentic | SHA-256 hash | Recompute hash, compare to on-chain record |
| Payment occurred (Stripe) | Stripe receipt | `receipt.stripe.com/...` |
| Payment occurred (USDC) | Base block explorer | `basescan.org/tx/{tx_hash}` |
| Revenue split (USDC) | Splits.org | `app.splits.org/accounts/{split_address}` |

**This is the "real money through a real robot auction" proof that investors can verify independently.**

---

## Decisions (Carried from v2, Updated)

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | Stripe mode | Production |
| 2 | Crypto chain | Base for demo, Ethereum mainnet for production |
| 3 | Revenue split | Stripe `application_fee_amount` for fiat, Splits.org for crypto |
| 4 | Robot identity | Register on Base with payment fields in agent card |
| 5 | Delivery verification | IPFS upload + CID in delivery record. Buyer verifies before payment. |
| 6 | x402 | Reserved for agent-to-robot control (Tumbller use case), not marketplace settlement |
| 7 | Fiat-to-USDC bridge | Research topic R-024. Not built for demo — keep rails separate. |
