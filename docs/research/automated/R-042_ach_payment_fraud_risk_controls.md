# R-042: ACH Payment Fraud Patterns and Risk Controls for Marketplace Platforms

**Date:** 2026-04-21
**Topic ID:** R-042
**Module:** M15_stripe_service
**Status:** Complete
**Priority:** High
**Researcher:** Automated daily research agent

---

## Executive Summary

- **Platform bears all R10 loss.** Stripe ACH disputes are final and non-contestable. If a buyer files an unauthorized return (R10) within 60 days of settlement, Stripe reverses funds from the platform balance immediately — even if the operator has already been paid. The current code (`handleTransferToOperator`) transfers 100% of task value to the operator immediately on `pi.status === "succeeded"`, creating a direct exposure window.
- **Nacha Phase 2 compliance is due June 22, 2026 — 62 days away.** YAK is an Originator under Nacha rules (Stripe is TPSP). Compliance requires documented, risk-based fraud monitoring processes covering both unauthorized returns and payments induced by false pretenses. No documentation currently exists.
- **Instant verification (already used) is the strongest fraud lever.** YAK already uses `verification_method: instant` in the ACH intent, meaning Stripe Financial Connections verifies account ownership before the debit. This eliminates most R02/R03/R04 (closed/wrong account) returns. The remaining risk is R10 and R29 (authorized by account owner but disputed later, or corporate unauthorized).
- **R10 window is 60 calendar days; R29 is 2 business days.** For B2B construction payments (CCD/CTX SEC code), R29 applies — shorter return window. R10 applies if the account holder is an individual, not a business.
- **No per-buyer velocity controls or first-payment amount cap exist in the codebase.** A buyer who obtains unauthorized access to bank account credentials can initiate a $10K+ ACH task payment, the operator gets paid immediately, and then the R10 dispute reverses funds from the platform.

---

## Findings

### 1. ACH Return Code Taxonomy and Thresholds

Nacha maintains three return rate thresholds for Originators (rolling 60-day window):

| Category | Return Codes | Threshold |
|----------|-------------|-----------|
| Unauthorized returns | R05, R07, R10, R11, R29, R51 | **< 0.5%** |
| Administrative returns | R02, R03, R04 | < 3.0% |
| All returns | All codes | < 15.0% |

The 0.5% unauthorized threshold is the most dangerous for YAK: a single $10K R10 return from a $1M/month ACH volume (100 tasks) puts YAK at 1.0% — double the threshold. At 10 tasks/month, a single R10 is 10%.

**Most relevant return codes for construction B2B payments:**

| Code | Reason | Return Window | Applies To |
|------|--------|--------------|-----------|
| R10 | Customer advises unauthorized | 60 calendar days | Consumer accounts |
| R29 | Corporate customer advises unauthorized | 2 business days | Corporate/business accounts |
| R02 | Account closed | 2 business days | Both |
| R03 | No account/unable to locate | 2 business days | Both |
| R20 | Non-transaction account (savings/money market) | 2 business days | Both |

**Key implication:** Most construction GC buyers use business accounts, so R29 (2-day window) is more likely than R10 (60-day window). This is actually favorable — the return window closes quickly before funds are deployed to operators.

Sources: [Nacha R-042: R10 full definition](https://www.nacha.org/rules/differentiating-unauthorized-return-reasons), [Checkbook complete guide](https://checkbook.io/blog/the-complete-ach-return-codes-guide-master-payment-processing-in-2025/), [Ramp ACH return codes](https://ramp.com/blog/ach-return-codes)

---

### 2. Who Bears the Loss on Stripe ACH Disputes

**Critical finding: The platform bears 100% of loss for ACH disputes via Stripe.**

From Stripe's documentation on Connect marketplace disputes:
> "Stripe always debits refunds, disputed amounts, and associated fees from the platform balance."

Furthermore:
> "All ACH disputes are final. There is no way to challenge or recover funds through Stripe."

This creates a specific exposure in the current YAK implementation:

1. Buyer initiates $5,000 ACH payment
2. PaymentIntent status transitions: `requires_payment_method` → `processing` (2-4 days) → `succeeded`
3. `handleTransferToOperator` fires immediately on `succeeded`, sends $5,000 to operator Connect account
4. Buyer files R10 dispute within 60 days (R29: 2 business days for corporate)
5. Stripe debits $5,000 + return fee from **platform Stripe balance**
6. Operator has already been paid; platform is at a loss

The current code comment acknowledges the timing (`// ACH debit settled`) but does not implement a hold period to absorb the return window risk.

Sources: [Stripe Connect disputes](https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes), [Service Fusion ACH overview](https://servicefusion.zendesk.com/hc/en-us/articles/34748435383053-Overview-of-ACH-Disputes-and-Chargebacks-with-Stripe)

---

### 3. Current Implementation Analysis

**`worker/src/index.js` — handleCreateAchIntent (line 1251)**

Strengths:
- Uses `verification_method: instant` — Stripe Financial Connections verifies account ownership in real-time. This is the single most impactful fraud control.
- Uses `financial_connections.permissions: balances` — can verify sufficient funds before debiting (though not currently checked in the response handler).
- Tracks ACH lifecycle events via webhooks (`processing`, `succeeded`, `failed`) to KV store.

Gaps:
- No per-buyer ACH velocity control (unlimited payments from a single buyer)
- No first-payment amount cap for new buyers
- No balance sufficiency check before transfer
- Transfer fires immediately on `succeeded` with no hold for R29/R10 return windows
- No Nacha-required fraud monitoring documentation

**`worker/src/index.js` — handleTransferToOperator (line 1333)**

Gaps:
- Transfers 100% of payment amount to operator immediately on `succeeded`
- No delivery-verified hold (operator could be paid before work is confirmed)
- No R29 2-business-day hold for corporate payer accounts
- `source_transaction` fallback to general platform balance (line 1410) is a safety net but increases settlement risk if platform balance is low

---

### 4. Nacha 2026 Compliance Requirements (Due June 22, 2026)

**Phase 2 effective June 22, 2026 applies to ALL Originators regardless of volume.**

As of that date, YAK must have:
1. **Documented risk-based processes** reasonably intended to identify ACH entries initiated due to fraud, including "false pretenses" (BEC, vendor impersonation, account takeover).
2. **Annual review** of those processes.
3. Procedures specifically for detecting both unauthorized transactions AND authorized-but-deceived transactions.

YAK qualifies as an Originator because it initiates ACH debits from buyer accounts. Stripe is a Third-Party Service Provider (TPSP) and does not absorb Originator compliance obligations.

**What "risk-based processes" means at YAK's scale:**
- Written documentation of fraud monitoring approach (can be a 1-2 page policy)
- Monitoring of return codes (already done via KV webhooks)
- Controls for new-payee risk (first-time buyer ACH limits)
- Escalation procedure when return thresholds are approached

The rules do not prescribe specific technical controls — they require documented intent and annual review. This is achievable with a policy doc and minor code changes.

Sources: [Nacha Phase 2 requirements](https://www.nacha.org/rules/risk-management-topics-fraud-monitoring-phase-2), [Nacha 2026 originator tips](https://www.nacha.org/news/tips-originators-comply-2026-risk-management-rules), [Larsco 2026 summary](https://larsco.com/blog/nacha-2026-ach-fraud-rules-what-originators-must-know), [JP Morgan 2026 guide](https://www.jpmorgan.com/insights/treasury/payables-disbursements/prepare-for-the-2026-nacha-rule-changes)

---

### 5. Fraud Patterns at $1K–$10K Construction Scale

**Primary fraud vectors for construction survey marketplace ACH:**

| Vector | Description | YAK Exposure |
|--------|-------------|-------------|
| Account takeover (ATO) | Attacker gains access to buyer's banking credentials via phishing, pays large task | High — $1K-$10K per transaction is worth targeting |
| Business Email Compromise (BEC) | Attacker impersonates GC finance dept, initiates task/payment | Medium — needs marketplace access, not just bank creds |
| Unauthorized ACH by terminated employee | Former GC employee uses corporate ACH access | Low-medium — R29 applies (2-day window) |
| Friendly fraud | Buyer pays, takes delivery, then files R10 claiming unauthorized | Low — B2B construction clients have incentive to maintain relationships |
| Insufficient funds (R01) | Buyer's account lacks funds at settlement time | Medium — construction GCs may have cash flow cycles; mitigated by balance check |

**Key industry statistic:** "67% of all fraud is linked to 7% of payments made to newly added payees" (Oscilar, 2026). For YAK, a first-time buyer placing a large ACH task is the highest-risk transaction.

Sources: [Unit21 ACH Fraud Detection 2026](https://www.unit21.ai/blog/ach-fraud-detection-in-2026-how-the-schemes-work-and-how-to-stop-them), [Oscilar ACH fraud detection 2026](https://oscilar.com/blog/ach-fraud-detection-in-2026)

---

### 6. Stripe Financial Connections: Already the Right Approach

YAK's current use of `verification_method: instant` with Financial Connections is optimal for fraud reduction. Stripe's own data indicates instant verification significantly reduces R03/R04/R20 returns by confirming:
- Account exists and is active
- Account ownership matches the payment initiator
- Balance data available (but not currently used in decision logic)

The remaining risk is R10/R29 (account owner disputes after successful debit) — these cannot be prevented by instant verification because the account is legitimately accessible; the dispute comes later.

**Balance check opportunity:** The `financial_connections.permissions: balances` is already requested in `handleCreateAchIntent`. Stripe can return `balance.available` at the time of the Financial Connections flow. This data could be used to block ACH payments where the available balance is below the task amount — preventing R01 (insufficient funds) returns. No code change is needed in the Payment Intent; the balance is available in the Payment Method response after Financial Connections completes.

---

## Implications for the Product

### Immediate (< 30 days)
1. **Operator transfer hold period** for B2B ACH is the highest-priority gap. The platform is exposed to the full task value if a buyer disputes after the operator is paid. Options: (a) hold transfer until 3 business days post-`succeeded`, (b) hold until delivery is confirmed, or (c) hold a percentage in reserve (e.g., 10%) for 30 days. Given YAK's commit-on-hire model, holding until delivery confirmation is most aligned with the product design.

2. **First-payment ACH cap.** A first-time buyer should be limited to $2,500 on their first ACH task. Subsequent payments build trust score.

### Compliance (< 60 days — June 22, 2026)
3. **Nacha Phase 2 documentation.** YAK needs a written fraud monitoring policy before June 22, 2026. This is a compliance obligation, not optional. A 2-page policy document covering: monitoring approach, return code tracking, new-buyer controls, and annual review process satisfies the requirement.

### Medium-term
4. **ACH return rate dashboard.** KV tracking of ACH lifecycle events is already in place. A simple aggregate query (returns/total attempts, grouped by return code) would surface Nacha threshold violations before they become enforcement issues.

5. **Balance sufficiency check.** Use the Financial Connections balance data (already requested) to block tasks where available balance < task amount. Reduces R01 returns.

---

## Improvement Proposals

### IMP-099: Hold operator ACH transfer until delivery confirmation (not immediately on `succeeded`)
- **Module:** M15_stripe_service / worker
- **Evidence:** `worker/src/index.js:1373` — `handleTransferToOperator` fires on `pi.status === "succeeded"` with no hold
- **Risk:** Platform loses full task value if buyer files R10/R29 dispute after operator is paid
- **Fix:** In the ACH settlement flow, hold the transfer until the delivery record is confirmed in KV (auction delivery accepted). For tasks without delivery confirmation, impose a 3-business-day hold after `succeeded`.
- **Effort:** medium
- **Priority:** high

### IMP-100: First-payment ACH cap — $2,500 maximum for first-time buyers
- **Module:** M15_stripe_service / worker
- **Evidence:** `worker/src/index.js:1253` — `handleCreateAchIntent` has no buyer-history check
- **Risk:** First-time buyers are highest-fraud-risk (67% of fraud linked to new payees)
- **Fix:** Check KV for prior `ach:pi_*` success entries for this buyer (by session/email). If none, cap `amount_cents` at 250000 ($2,500). Return an error with instructions to use Card for higher amounts.
- **Effort:** small
- **Priority:** medium

### IMP-101: Nacha Phase 2 compliance policy document
- **Module:** docs/
- **Evidence:** Nacha Phase 2 effective June 22, 2026; YAK is an Originator
- **Risk:** Non-compliance with Nacha fraud monitoring rules — potential network suspension
- **Fix:** Write `docs/legal/ACH_FRAUD_MONITORING_POLICY.md` covering: scope, risk-based monitoring approach (return code tracking via KV), new-buyer controls (IMP-100), false pretenses controls (Financial Connections instant verification), escalation procedures, annual review date. This is a documentation task, not a code change.
- **Effort:** small
- **Priority:** critical (deadline June 22, 2026)

### IMP-102: Use Financial Connections balance data to block ACH payments below task amount
- **Module:** M15_stripe_service / worker
- **Evidence:** `worker/src/index.js:1283` — `balances` permission is already requested; returned in Financial Connections response but not checked
- **Risk:** R01 returns (insufficient funds) for large task payments
- **Fix:** In the frontend ACH payment flow, after Financial Connections completes, check if `financial_connections_account.balance.available.usd >= amount_cents`. If not, surface an error: "Insufficient account balance for this task amount. Please use Card or reduce task scope."
- **Effort:** small
- **Priority:** low

---

## New Questions Spawned

- **R-051 (check if exists):** Nacha's WEB vs. CCD/CTX SEC code distinction — YAK may be using `us_bank_account` which defaults to WEB (internet-originated) code. B2B construction payments should use CCD (corporate credit/debit). This distinction affects return code applicability and fee liability. Verify what SEC code Stripe's `us_bank_account` payment method assigns, and whether YAK needs to specify CCD for business accounts.

---

## Sources

- [Checkbook ACH Return Codes Guide 2025](https://checkbook.io/blog/the-complete-ach-return-codes-guide-master-payment-processing-in-2025/)
- [Nacha Differentiating Unauthorized Return Reasons](https://www.nacha.org/rules/differentiating-unauthorized-return-reasons)
- [Nacha 2026 Fraud Monitoring Phase 2](https://www.nacha.org/rules/risk-management-topics-fraud-monitoring-phase-2)
- [Nacha Tips for Originators 2026](https://www.nacha.org/news/tips-originators-comply-2026-risk-management-rules)
- [Larsco Nacha 2026 ACH Fraud Rules](https://larsco.com/blog/nacha-2026-ach-fraud-rules-what-originators-must-know)
- [JP Morgan 2026 Nacha Guide](https://www.jpmorgan.com/insights/treasury/payables-disbursements/prepare-for-the-2026-nacha-rule-changes)
- [Stripe ACH Direct Debit Documentation](https://docs.stripe.com/payments/ach-direct-debit)
- [Stripe ACH Fraud 101](https://stripe.com/resources/more/ach-fraud-101-how-these-scams-work-and-how-to-prevent-them)
- [Stripe ACH Risk Mitigation Guide](https://stripe.com/resources/more/ach-risk-mitigation-101-a-guide-for-businesses)
- [Stripe Connect Marketplace Disputes](https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes)
- [Stripe Financial Connections Documentation](https://docs.stripe.com/financial-connections)
- [Unit21 ACH Fraud Detection 2026](https://www.unit21.ai/blog/ach-fraud-detection-in-2026-how-the-schemes-work-and-how-to-stop-them)
- [Oscilar ACH Fraud Detection 2026](https://oscilar.com/blog/ach-fraud-detection-in-2026)
- [Ramp ACH Return Codes](https://ramp.com/blog/ach-return-codes)
- [Dwolla ACH Return Process](https://www.dwolla.com/updates/understanding-ach-return-process)
- [Sardine New Nacha Requirements](https://www.sardine.ai/blog/new-nacha-rules)
