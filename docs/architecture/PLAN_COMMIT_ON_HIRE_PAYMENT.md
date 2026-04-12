# Plan: Commit-on-Hire, Execute-on-Delivery Payment

**Date:** 2026-04-05
**Status:** Research + security review before implementation
**Goal:** Buyer signs payment commitment when awarding a task. Money only moves after data delivery + QA validation.

---

## The Flow

```
1. AUCTION     Buyer posts task, robots bid, buyer selects winner
2. COMMIT      Buyer signs ERC-2612 permit (authorizes payment, no money moves)
                 → Platform stores signed permit securely
                 → Robot sees: "payment committed, safe to start work"
3. EXECUTE     Robot performs task
4. DELIVER     Robot returns data, platform uploads to IPFS
5. QA          Deliverable QA runs (Level 0-3, buyer-configurable)
6. ACCEPT      Buyer confirms delivery
7. EXECUTE $   Platform submits permit + transferFrom (money moves NOW)
                 → 88% to robot wallet
                 → 12% to platform wallet
```

**The permit is a signed IOU — cryptographic proof the buyer will pay, but no funds locked.**

---

## Security Analysis

### Threat Model

This system handles real money (demo: $0.01-$0.50, production: $1K-$200K). The signed permit is effectively a bearer check — anyone who has the signature can submit it and spend the buyer's USDC.

#### Threat 1: Permit signature theft
**Risk:** If an attacker obtains the stored permit (v, r, s), they can submit it themselves and redirect the transferFrom to a different address.
**Mitigation:** The permit only authorizes a specific `spender` (our relay wallet). Only our relay wallet can call `transferFrom`. An attacker with the permit signature but without our relay wallet's private key cannot spend the USDC. The USDC contract enforces this — `transferFrom` requires `msg.sender == approved spender`.
**Residual risk:** If the relay wallet private key AND the permit signature are both compromised, the attacker can drain the permitted amount. This is the same risk profile as any custodial system.

#### Threat 2: Buyer front-runs by spending USDC before execution
**Risk:** Buyer signs permit, robot starts working, buyer transfers their USDC elsewhere. When we try to execute the permit, `transferFrom` fails (insufficient balance).
**Mitigation:**
- Check buyer's USDC balance before starting execution (`balanceOf` call)
- If balance drops below committed amount, pause execution and notify
- For large tasks ($1K+): consider requiring the buyer to approve a higher amount or use actual escrow
- The permit is still valid — if the buyer re-funds their wallet, we can execute
**Residual risk:** Buyer can grief the robot by committing then withdrawing. Reputation system and platform banning are the deterrents.

#### Threat 3: Permit replay
**Risk:** Attacker replays a previously used permit signature.
**Mitigation:** USDC uses a nonce per address. Each permit increments the nonce. A used permit signature is permanently invalid. This is handled by the USDC contract, not our code.
**Residual risk:** None — replay is impossible by protocol design.

#### Threat 4: Permit expiration
**Risk:** Robot takes longer than the permit deadline. When we try to execute, permit is expired.
**Mitigation:**
- Set generous deadlines (24 hours for small tasks, 7 days for large tasks)
- Monitor time remaining and alert before expiry
- If expired: buyer must re-sign a new permit (re-commit)
- Don't start execution if permit deadline is too close to SLA
**Residual risk:** Operational — buyer needs to re-sign. Not a security risk.

#### Threat 5: Relay wallet compromise
**Risk:** Attacker gets the relay wallet private key. Can submit any stored permit and redirect funds.
**Mitigation:**
- Relay wallet private key stored as Cloudflare Worker secret (encrypted at rest)
- Relay wallet only holds ETH for gas — no USDC
- Relay wallet address is hardcoded in the permit (spender) — attacker can only spend what buyers have explicitly permitted to this specific address
- For production: migrate to KMS-backed signing (AWS KMS, GCP Cloud HSM)
**Residual risk:** Medium for demo (env var). Low for production (KMS).

#### Threat 6: Platform submits permit prematurely (before QA)
**Risk:** Bug or malicious actor causes the platform to execute the permit before delivery/QA.
**Mitigation:**
- Server-side state check: only execute permit when task state == VERIFIED (post-QA)
- Separate the permit execution from the QA flow — different code paths
- Audit log: every permit execution is logged with task state, QA result, timestamp
**Residual risk:** Low — code bug. Mitigated by tests and state machine enforcement.

#### Threat 7: Large payment amounts
**Risk:** $200K permit stored in KV for days while robot works.
**Mitigation:**
- For amounts > $1,000: require on-chain escrow (Phase 3 feature) instead of permit
- Permit-based flow is appropriate for amounts up to ~$1,000
- Above that threshold: use RobotTaskEscrow.sol (funds locked in contract, not dependent on buyer's wallet balance)
- Document the threshold in the task posting UI

---

## Storage Design

### Where to store the permit signature

The signed permit (v, r, s, deadline, amount, nonce) must be stored between commit (step 2) and execution (step 7). Options:

| Storage | Pros | Cons |
|---------|------|------|
| Cloudflare KV | Durable, encrypted at rest, TTL support | Eventual consistency (rare issue) |
| SQLite (auction store) | Transactional, co-located with task state | Only available when MCP server runs |
| Worker memory | Fast | Lost on redeploy/restart |

**Recommendation:** Cloudflare KV with TTL matching permit deadline. Key: `permit:{request_id}`. The Worker that creates the checkout also executes the permit — same process, same KV namespace.

### Permit record schema

```json
{
  "request_id": "req_abc123",
  "chain_id": 8453,
  "owner": "0xb84165c9bf12a33b4afe513acfc165bf44a27eaa",
  "spender": "0x4b5974229f96ac5987d6e31065d73d6fd8e130d9",
  "amount": "10000",
  "operator_wallet": "0x99a55d71682807fde9c81e0984aBdd2C7AcCE136",
  "platform_wallet": "0xe33356d0d16c107eac7da1fc7263350cbdb548e5",
  "deadline": 1743955200,
  "nonce": "0",
  "v": 28,
  "r": "0x...",
  "s": "0x...",
  "committed_at": "2026-04-05T10:00:00Z",
  "status": "committed",
  "executed_at": null,
  "tx_hashes": null
}
```

Status values: `committed` → `executing` → `executed` | `expired` | `failed`

---

## Implementation

### Demo page changes (mcp-demo-2)

**Step 2 (after bid acceptance):** Show payment commitment card:
```
Task awarded to Apex Aerial Surveys — $0.01

[Commit Payment — Sign Permit]

You will sign a gasless authorization. No money moves until
you accept the delivery. You can cancel before execution starts.
```

Buyer clicks → signs EIP-712 permit → signature sent to Worker → stored in KV.

**Step 6 (after QA passes):** Show release button:
```
QA passed (Level 1: basic). Delivery verified.

[Release Payment — $0.01 to operator]

Your signed commitment from Step 2 will now be executed.
88% ($0.0088) to operator, 12% ($0.0012) to platform.
```

Buyer clicks → Worker retrieves stored permit from KV → submits on-chain.

### Worker endpoints

**POST /api/commit-payment**
- Receives: permit signature (v, r, s), chain_id, amount, deadline, operator_wallet
- Validates: amount matches task, deadline is far enough, buyer balance sufficient
- Stores: permit record in KV with TTL = deadline
- Returns: commitment_id, status

**POST /api/execute-payment**
- Receives: request_id (looks up stored permit from KV)
- Validates: task state is VERIFIED, permit not expired, buyer balance still sufficient
- Executes: permit() + transferFrom() on-chain
- Updates: KV record with tx hashes and execution timestamp
- Returns: tx hashes, explorer links

**GET /api/payment-commitment?request_id=...**
- Returns: commitment status, time remaining, amount

### Balance monitoring

Before executing the permit, the Worker should check the buyer's current USDC balance:

```javascript
const balance = await usdc.balanceOf(owner);
if (balance < totalAmount) {
  return { error: "Buyer's USDC balance insufficient. Was: committed, now: $X available." };
}
```

This catches the front-running scenario (Threat 2).

---

## Amount Thresholds

| Amount | Payment Method | Rationale |
|--------|---------------|-----------|
| < $1 | Gasless permit (commit + execute) | Gas cost ~$0.005, trivial amounts |
| $1 - $1,000 | Gasless permit (commit + execute) | Permit risk is acceptable, buyer can re-fund |
| $1,000 - $10,000 | Permit + balance monitoring | Check balance before execution, alert if drops |
| > $10,000 | On-chain escrow (future) | Too much value to rely on buyer's wallet balance |

For the demo ($0.01-$0.50), the permit flow is appropriate. For production construction surveys ($45K), we should eventually use `RobotTaskEscrow.sol` — but that's a Phase 3 item.

---

## Demo UX Flow

```
Step 1: Discover robots
Step 2: Run auction → winner selected
Step 3: COMMIT PAYMENT — buyer signs permit (gasless, no money moves)
        → "Payment committed. $0.01 authorized for Apex Aerial."
        → "Funds remain in your wallet until delivery is accepted."
Step 4: Robot executes task
Step 5: Delivery arrives → IPFS CID shown
Step 6: QA runs → results shown (Level 1: basic — passed)
Step 7: RELEASE PAYMENT — buyer clicks to execute
        → Worker checks balance, submits permit + transferFrom
        → "Payment complete. $0.0088 to operator, $0.0012 to platform."
        → Tx hashes + explorer links shown
Step 8: Feedback
```

Payment commitment (Step 3) and payment execution (Step 7) are visually distinct moments. The buyer sees their funds are committed but not spent. The robot sees the commitment and starts working.
