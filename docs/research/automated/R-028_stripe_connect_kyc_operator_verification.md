# R-028: Stripe Identity and Connect KYC as Operator Verification

**Date:** 2026-04-16
**Topic ID:** R-028
**Module:** M10_compliance, M15_stripe_service
**Status:** complete
**Priority:** high
**Estimated sessions:** 1
**Depends on:** R-027 (complete)

---

## Executive Summary

- **Hypothesis confirmed with caveats.** Stripe Connect Express KYC (when `payouts_enabled = true` and `requirements.currently_due = []`) is sufficient baseline trust for operators bidding on tasks below $10K. Stripe verifies government ID, SSN/EIN, DOB, address, beneficial owners, and screens all accounts against OFAC + UN sanctions + PEP lists — ongoing, not one-time.
- **Critical codebase gap:** `activate()` in `operator_registry.py` checks only that `stripe_account_id` is non-None. It does NOT call `get_account()` to verify `payouts_enabled = true`. An operator with a created-but-unverified Stripe account can be activated and win tasks — but will fail payout at settlement.
- **The verification trust signal is `payouts_enabled = true`.** `stripe_service.py` already has `get_account()` which returns this field. Fix is 3–5 lines in `activate()`.
- **Stripe Identity (separate product, $1.50/check) is the right escalation path** for operators whose automatic Connect verification fails, or for first-win escalation checks at $25K+. It is not needed for the baseline gate.
- **Stripe Managed Risk is the right supplemental layer** — included at no additional cost for revenue-share Connect models. It handles ongoing OFAC monitoring, chargeback-rate interventions, and payout pauses automatically.
- **Stripe does NOT verify Secretary of State registration** — entity-level KYB (Middesk, IMP-066) remains necessary for tasks above $25K. R-027's tiered verification design is confirmed correct.

---

## Findings

### 1. What Does Stripe Connect Express Actually Verify?

When an operator completes the Stripe Express onboarding flow (`account_links` create + redirect), Stripe collects and verifies:

| Data Point | Collection Method | Stripe Verification |
|---|---|---|
| Legal name (individual) | Form input | Cross-referenced against ID document |
| Date of birth | Form input | Cross-referenced against ID document |
| Address | Form input | Address verification service |
| SSN last 4 | Form input | IRS match for tax purposes |
| SSN full (required >$600 threshold) | Form input | IRS TIN match |
| Government-issued ID (scan) | Document upload (when auto-verify fails) | OCR + liveness check |
| Business name (LLC) | Form input | Basic EIN lookup |
| EIN | Form input | IRS match |
| Beneficial owners (25%+ stake) | Additional form step | Identity checked per owner |
| Bank account / debit card | Routing + account number | Micro-deposit verification or Plaid instant |

**OFAC and sanctions screening:** Stripe screens ALL connected accounts against OFAC Specially Designated Nationals list, UN sanctions, and PEP (Politically Exposed Persons) databases. This is ongoing — if an account is later flagged, Stripe pauses payouts and emails the platform. The platform does NOT need to run separate OFAC checks for operators with verified Connect accounts.

**What Stripe does NOT verify:**
- Secretary of State registration / good-standing status
- FAA Part 107 certification
- Professional licenses (PLS, PE)
- Insurance status
- Business "good standing" in any state
- UCC filings, liens, or judgments

**Key limitation from Stripe documentation:** "Platforms should not rely on Stripe's verification to meet any independent legal KYC or verification requirements." This means Stripe handles the *payments-industry* KYC obligation (FinCEN, BSA compliance), but platforms retain responsibility for their own marketplace trust decisions.

Sources:
- [Stripe: KYC Requirements for Connected Accounts](https://support.stripe.com/questions/know-your-customer-(kyc)-requirements-for-connected-accounts)
- [Stripe: Identity Verification for Connected Accounts](https://docs.stripe.com/connect/identity-verification)
- [Stripe: Understanding Sanctions](https://support.stripe.com/questions/understanding-sanctions)
- [Stripe: Required Verification Information](https://docs.stripe.com/connect/required-verification-information)

---

### 2. The Verification Trust Signal: `payouts_enabled`

The canonical way to check whether Stripe has completed KYC for a connected account:

```python
account = stripe.Account.retrieve(account_id)
verified = (
    account["payouts_enabled"] is True
    and account["charges_enabled"] is True
    and len(account["requirements"]["currently_due"]) == 0
)
```

**`payouts_enabled = true`** means:
- Identity verification complete
- Bank account linked and verified
- No outstanding `currently_due` requirements
- No OFAC/sanctions hold active

**`requirements.currently_due`** lists fields still needed. If non-empty, payouts are blocked or will be blocked by `current_deadline`. An account can be created (and even have an `account_id`) without being verified.

**`requirements.disabled_reason`** explains why payouts are disabled, if they are. Values include `requirements.past_due`, `listed` (sanctions), `platform_paused`, `under_review`.

The `stripe_service.py` `get_account()` method already calls `stripe.Account.retrieve()` and returns the full account dict, including these fields. The platform already has the tool to check verification status — it just isn't being called at activation.

Sources:
- [Stripe: Handle Verification Updates](https://docs.stripe.com/connect/handle-verification-updates)
- [Stripe: Handle Verification with the API](https://docs.stripe.com/connect/handling-api-verification)
- [Stripe: Risk and Liability Management](https://docs.stripe.com/connect/risk-management)

---

### 3. Stripe Identity (Separate Product) — When to Use It

**Stripe Identity** is a standalone verification product distinct from Connect's built-in KYC. It runs a selfie + ID document capture flow via a hosted verification session.

**Pricing:** $1.50/completed verification after the first 50 free.

**Verification types available:**
- `document` — ID scan, OCR extraction, fraud/liveness detection
- `selfie` — Selfie match against document photo
- `id_number` — SSN lookup (US only)
- `address` — Address verification
- `phone` — Phone number check

**When does Connect Express auto-verification fail?**
- Common triggers: address doesn't match ID, thin credit file, unusual name patterns, high-risk geography
- Failure rate: not published, but small businesses and new immigrants are common failure cases

**When YAK should use Stripe Identity:**
1. **Escalation trigger:** When `activate()` detects `payouts_enabled = false` but `stripe_account_id` is set — offer the operator a Stripe Identity verification session as a manual escalation path
2. **High-value first-win:** At first task win ≥$25K (alongside Middesk KYB from IMP-066)
3. **Platform option:** Could be offered as a "Verified Operator" badge to operators who complete Stripe Identity — signals extra trust to buyers

**What Stripe Identity does NOT cover:** It does not verify the business entity, only the individual. For LLCs, you'd verify the individual representative, not the LLC itself.

Sources:
- [Stripe Identity](https://stripe.com/identity)
- [Stripe Identity: Verification Checks](https://docs.stripe.com/identity/verification-checks)
- [Stripe: Billing for Stripe Identity](https://support.stripe.com/questions/billing-for-stripe-identity)

---

### 4. Stripe Managed Risk — Platform's Passive Safety Net

For Express accounts, platforms bear responsibility for losses from connected account fraud. **Stripe Managed Risk** transfers this obligation to Stripe.

**What Managed Risk does:**
- Stripe monitors risk signals (elevated losses, chargeback spikes, refund rates) on connected accounts
- Applies automated interventions (payout holds, payment rate limits) without platform action required
- Stripe assumes liability for unrecoverable negative balances on flagged accounts

**Cost:** Included at no additional charge for revenue-share Connect models (standard for most Express integrations).

**For YAK:** This is the right passive safety layer. Construction survey tasks don't typically generate chargebacks (no consumer goods), but OFAC monitoring and anomalous payout detection are relevant as volume grows.

**How to enable:** Contact Stripe — it's not self-serve for all accounts. Some platforms get it by default under newer Connect agreements.

Sources:
- [Stripe Managed Risk](https://docs.stripe.com/connect/risk-management/managed-risk)
- [New Features for SaaS Platforms: Risk and Compliance](https://stripe.com/blog/new-features-to-help-saas-platforms-manage-risk-and-stay-compliant)

---

### 5. Accounts v2 API (December 2025) — Relevant for Future Architecture

Stripe's new Accounts v2 API (released December 2025) introduces a single identity object shared across Stripe:
- One `Account` object represents both the connected account and the customer relationship
- KYC data shared: if an operator was previously verified as a buyer (customer), no re-verification needed
- Responsibility for KYC collection: can now be explicitly set to `Stripe` (default for Express) vs `platform` (Custom)

**YAK relevance:** This is a future migration consideration, not an immediate action. The current Connect Express integration works with v1 API. Accounts v2 offers cleaner onboarding if YAK ever supports operators who are also buyers (e.g., a firm surveys for others while also contracting surveys out).

Sources:
- [Stripe: Connect and Accounts v2 API](https://docs.stripe.com/connect/accounts-v2)
- [Stripe: Accounts v2 Changelog](https://docs.stripe.com/changelog/clover/2025-12-15/accounts-v2)

---

### 6. Codebase State Assessment

**`auction/stripe_service.py`:**
- `create_connect_account()` creates an Express account with `transfers` capability — correct
- `get_account()` calls `stripe.Account.retrieve()` — **already returns `payouts_enabled`, `charges_enabled`, and `requirements` hash**
- No method to check verification status cleanly; callers must parse the raw dict

**`auction/operator_registry.py`:**
- `OperatorProfile.stripe_account_id` field exists (IMP-064 implemented — good)
- `activate()` checks `stripe_account_id` is not None — **does NOT call `get_account()` to check `payouts_enabled`**
- Gap: operator can be activated with a created-but-unverified Stripe account (e.g., operator started onboarding but didn't finish ID verification)

**`auction/compliance.py`:**
- No reference to Stripe at all — compliance and payment are fully decoupled
- This is architecturally correct: `ComplianceChecker` handles document-based compliance, `OperatorRegistry.activate()` handles payment-path readiness
- But the `activate()` gate needs the Stripe `payouts_enabled` check to close the loop

**Webhook handling:**
- The platform should receive `account.updated` events when a connected account's verification status changes (e.g., Stripe flags them for sanctions post-activation)
- `worker/src/index.js` handles Stripe webhooks but likely doesn't process `account.updated` for Connect accounts
- This is a gap: if Stripe OFAC-flags an operator after activation, there's no mechanism to auto-suspend them in the marketplace

---

### 7. Tiered Verification Design (Confirmed from R-027)

The three-tier design from R-027 is confirmed correct and maps to Stripe's verification products:

| Tier | Task Value | Verification | Stripe Product | Cost |
|---|---|---|---|---|
| 1 — Baseline | <$10K | `payouts_enabled = true` on Connect Express account | Connect Express (built-in) | $0 marginal |
| 2 — Enhanced | $10K–$25K | Tier 1 + insurance COI review + FAA Part 107 check | Connect Express + manual doc review | $0 |
| 3 — Full KYB | $25K+ | Tier 2 + Middesk entity check + SAM.gov exclusion | Connect Express + Middesk + SAM.gov | ~$1–5/check Middesk |

Stripe Identity ($1.50/check) slots in as an escalation path when Connect auto-verification fails (rare) or as an optional "Verified Operator" badge.

---

## Implications for the Product

1. **The most impactful single fix is adding `payouts_enabled` check to `activate()`.** This closes a production-blocking gap. Implementation is ~5 lines calling the existing `get_account()` method. This is IMP-085 below.

2. **Add a `check_stripe_account_status()` helper to `stripe_service.py`.** The raw account dict from `get_account()` requires callers to parse `payouts_enabled`, `charges_enabled`, and `requirements.currently_due`. A clean helper returning a status struct makes the check reusable across `activate()`, pre-bid validation, and settlement. This is IMP-086.

3. **Handle `account.updated` webhooks for Connect accounts.** When Stripe OFAC-flags an operator post-activation, the platform must auto-suspend them. This requires a webhook handler in `worker/src/index.js` that updates `OperatorProfile.status` to `suspended`. This is IMP-087.

4. **Stripe Identity is the right escalation, not the baseline.** Do not require all operators to pass Stripe Identity — it creates friction for the majority (Connect auto-verification succeeds). Use it only when auto-verification fails or at the $25K+ threshold.

5. **OFAC screening is handled by Stripe — no separate integration needed.** The Connect KYC includes OFAC/UN sanctions screening. Do not add a separate OFAC check to `compliance.py` for operators who have completed Stripe onboarding.

---

## Improvement Proposals

### IMP-085: Check `payouts_enabled` in `activate()` before allowing operator activation

**Module:** M15_stripe_service / M10_compliance  
**Effort:** small  
**Priority:** high  
**Description:** In `OperatorRegistry.activate()`, after checking `stripe_account_id` is set, call `StripeService.get_account(stripe_account_id)` and verify `payouts_enabled is True`. If `payouts_enabled is False`, return an issue with the `disabled_reason` from the account's `requirements` hash. In stub mode (no Stripe key), skip this check and log a warning. This closes the gap where an operator with a partially-completed Stripe onboarding is activated into the marketplace but cannot receive payouts at settlement.

```python
# In activate() — after the stripe_account_id check:
if self._stripe_service:
    acct = self._stripe_service.get_account(profile.stripe_account_id)
    if not acct.get("stub") and not acct.get("payouts_enabled"):
        reason = acct.get("requirements", {}).get("disabled_reason", "incomplete verification")
        issues.append(f"Stripe account not payout-ready: {reason}. Complete Stripe onboarding.")
```

### IMP-086: Add `check_stripe_account_status()` helper to `stripe_service.py`

**Module:** M15_stripe_service  
**Effort:** small  
**Priority:** medium  
**Description:** Add a `check_stripe_account_status(account_id)` method to `StripeService` that returns a clean struct:
```python
{
    "payouts_enabled": bool,
    "charges_enabled": bool,
    "currently_due": list[str],   # [] = fully verified
    "disabled_reason": str | None,
    "status": "verified" | "pending" | "blocked" | "error"
}
```
This method is called by `activate()` (IMP-085), by pre-bid validation in `engine.py`, and by the `account.updated` webhook handler (IMP-087). Stub mode returns `{"status": "verified", "payouts_enabled": True, ...}` to allow test operations.

### IMP-087: Handle `account.updated` webhook to auto-suspend OFAC-flagged operators

**Module:** M15_stripe_service / worker  
**Effort:** medium  
**Priority:** medium  
**Description:** Add a webhook handler in `worker/src/index.js` for the `account.updated` event on connected accounts. When `payouts_enabled` changes to `false` on an account linked to an active operator, emit a `platform_operator_suspended` event and (via auction API) set the operator's status to `suspended`. Log the suspension reason from `requirements.disabled_reason`. This ensures that Stripe OFAC flags, post-activation KYC failures, or platform-initiated holds are reflected in marketplace eligibility automatically. Requires the Stripe webhook secret to be configured for Connect account events (separate from payment webhook secret).

---

## New Questions Spawned

### R-050: Stripe Connect account webhooks — implementation guide for `account.updated` events

**Hypothesis:** The platform needs to receive `account.updated` webhook events from Stripe for all connected accounts (Express) to detect post-activation status changes (OFAC flags, KYC failures, payout holds). Research: (1) How does `worker/src/index.js` need to be modified to receive Connect account events? (2) Is a separate webhook endpoint (and separate secret) required for Connect events vs payment events? (3) What is the event signature validation pattern for account-level webhooks? (4) How does the platform subscribe to events for all connected accounts vs a single account?

---

## Summary

R-027 established the tiered verification design; R-028 zooms in on the specific Stripe implementation. The key finding: the codebase has the right field (`stripe_account_id` on `OperatorProfile`) and the right Stripe method (`get_account()`), but doesn't call one from the other. Three targeted improvements (IMP-085, 086, 087) close the gap from "account exists" to "account is verified and payout-ready."

The broader hypothesis is confirmed: Stripe Connect Express KYC — specifically the `payouts_enabled = true` signal — is a trustworthy baseline gate for construction survey tasks below $10K. It covers identity, OFAC/sanctions screening, and tax identity. It does not cover business entity registration (Middesk, IMP-066) or professional licenses (compliance.py documents). The tiered design (R-027) remains the right architecture.
