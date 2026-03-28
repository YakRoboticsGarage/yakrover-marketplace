# Payment Bond Verification for the Robot Marketplace

**Date:** 2026-03-28
**Context:** The demo uses a real MDOT I-94 project ($2B+ program). At this scale, payment is guaranteed by surety bonds, not credit cards.

---

## What Is a Payment Bond

A payment bond is a three-party legal instrument:
- **Principal** (the GC) — who owes money to subcontractors
- **Obligee** (the project owner, e.g., MDOT) — who requires the bond
- **Surety** (insurance company) — who guarantees payment if the GC defaults

The surety underwrites the GC's financial capacity before issuing the bond. If the GC fails to pay a subcontractor, the surety pays the sub directly and then recovers from the GC.

## When Bonds Are Required

| Project Type | Threshold | Statute |
|---|---|---|
| Federal (USACE, FAA, etc.) | >$150,000 | Miller Act (40 U.S.C. 3131-3134) |
| Michigan public (MDOT, county, city) | >$50,000 | MCL 129.201-129.212 |
| Private (commercial, industrial) | Not required | Contractual only |

**For our I-94 demo ($170K robot tasks on an MDOT project): the bond already exists.** The GC is legally required to have it. The marketplace just needs to verify it.

## What the Bond Document Contains

A standard AIA A312 Payment Bond document includes:
- **Bond number** — unique identifier from the surety
- **Surety company name** — e.g., Travelers Casualty and Surety Company of America
- **Principal** — the GC's legal name, address
- **Obligee** — MDOT or the project owner
- **Project description** — name, location, contract number
- **Penal sum** — the bond amount (usually = contract price)
- **Effective date**
- **Surety seal and signature**
- **Power of Attorney** — authorizing the surety agent to execute the bond

## How the Marketplace Verifies a Bond

### For public projects (bond exists):
1. GC uploads bond certificate (PDF)
2. Marketplace extracts: bond number, surety name, principal, penal sum, project
3. **Verification options:**
   - Cross-reference against the surety's online bond verification portal (most major sureties have these)
   - Check the surety's standing on Treasury Dept Circular 570 (list of approved sureties for federal bonds)
   - Verify the bond amount covers the task values being posted
4. Mark tasks as **"Payment Bonded"** — operators can see verified payment security

### For private projects (no bond):
1. GC connects bank account (Plaid for ACH verification)
2. Marketplace verifies sufficient balance or credit facility
3. GC funds first milestone into marketplace escrow
4. Mark tasks as **"Escrow Funded"** — operators see payment deposited

## What the Demo Should Show

Since the I-94 project is MDOT (public, >$50K), the payment screen should show:

**Option A: Upload Bond (public projects)**
- "Your MDOT project requires a payment bond under Michigan law (MCL 129.201)"
- Upload button for bond certificate PDF
- After "upload": show extracted bond details (bond #, surety, amount)
- Verification badge: "Payment Bonded — verified by [Surety Name]"

**Option B: Fund Escrow (private projects)**
- "Connect bank account to fund milestone escrow"
- ACH connection via Plaid
- Deposit first milestone amount
- Badge: "Escrow Funded — $72,000 deposited"

For the demo, Option A is correct since this is an MDOT project. The demo should mock the bond upload and show the verification.

## Surety Verification Portals (Real)

| Surety | Portal |
|---|---|
| Travelers | travelers.com/surety-bonds |
| Liberty Mutual | libertymutualsurety.com |
| CNA | cnasurety.com |
| Zurich | zurichna.com/surety |
| The Hartford | thehartford.com/business-insurance/surety-bonds |

These portals allow third parties to verify bond validity by bond number.

## Flow: Task Spec → Valid Auction (Public Project)

```
1. Agent decomposes RFQ → 3 task specs
2. GC reviews tasks, confirms scope
3. GC uploads payment bond certificate (already exists for MDOT project)
4. Marketplace verifies bond: number, surety, coverage amount, project match
5. Tasks marked "PAYMENT BONDED" — visible to all operators
6. Auctions open — operators bid knowing payment is surety-guaranteed
7. Award — winning operator receives PO referencing the bond
8. Work → Milestone billing → Marketplace facilitates payment
9. If GC doesn't pay: operator claims against the bond
```

This is NOT a new payment mechanism — it's the marketplace verifying an existing construction industry standard and making it visible to robot operators, reducing trust friction.
