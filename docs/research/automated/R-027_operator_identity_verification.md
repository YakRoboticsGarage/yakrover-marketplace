# R-027: Robot Operator Identity Verification — Individuals and Businesses

**Date:** 2026-04-12
**Topic ID:** R-027
**Module:** M10_compliance
**Status:** complete
**Priority:** critical
**Estimated sessions:** 2 (completed in 1 — topic fully resolved)

---

## Executive Summary

- **Stripe Connect Express KYC is sufficient as a baseline gate** for operators at task values below ~$10K. Stripe already collects and verifies government ID, SSN/EIN, DOB, and address during onboarding — this satisfies minimum "know your seller" requirements for non-federal work at demo scale.
- **Entity-level KYB (via Middesk) is the right upgrade** for operators first winning tasks above $10K. One-time cost of ~$1–5/check via Middesk's Secretary of State + IRS + OFAC data sources covers 100% of US businesses. This unblocks R-006b and R-028.
- **GCs care about three things, in order: insurance COI, license/certification, and references.** Business registration and KYB services are secondary trust signals — existing compliance.py fields (faa_part_107, insurance_coi, pls_license) already map directly to GC requirements.
- **The current `verify_operator()` "compliant" flag is incorrectly strict** — it fails operators for MISSING `pls_license`, `sam_registration`, `dot_prequalification`, and `dbe_certification` even when those docs are NOT_REQUIRED for the task type.
- **INFORM Consumers Act does not apply** to construction survey services — it covers only tangible consumer products, not services.
- **SAM.gov exclusion check (already implemented) is the right debarment gate** for MDOT and federal-funded projects, but we should also check active entity registration for federal work.

---

## Findings

### 1. What Does a GC Actually Need to Trust an Operator?

Research from subcontractor prequalification guides (Procore, Highwire, Leif Assurance, DPR Construction) reveals a consistent pattern: GCs scale their verification requirements with contract value.

**Standard prequalification checklist (GC perspective):**

| Verification Layer | Required For | Notes |
|---|---|---|
| Insurance COI (CGL, workers comp, auto, umbrella) | All work | Minimum limits vary by GC. Survey work typically $1M CGL. Aviation endorsement for drones. |
| Trade/professional license | Licensed trades, PLS-stamped deliverables | FAA Part 107 is the drone analog. PLS required if signing surveys. |
| Business registration / entity existence | Contracts >$25K | Secretary of State confirmation that the entity exists and is in good standing |
| Bonding capacity | Public contracts, lump-sum >$100K | Surety bond required for many public contracts |
| References / past work | All work, weight varies | Not verifiable programmatically |
| SAM.gov exclusion check | Federal-funded projects only | Required for MDOT federal-aid projects |
| E-Verify / workers' comp verification | Federal contracts | Less relevant for solo drone operators |

**For construction survey at $1K–$10K (our wedge):** Insurance COI + FAA Part 107 is the baseline. PLS supervision agreement matters for deliverables that will be used in official drawings.

**For full project lifecycle at $25K–$72K:** Add business registration check + bonding capacity inquiry + SAM.gov exclusion.

Sources:
- [Procore: Subcontractor Prequalification](https://www.procore.com/library/subcontractor-prequalification)
- [Highwire: 2025 Guide to Subcontractor Prequalification](https://www.highwire.com/blog/the-complete-guide-to-subcontractor-prequalification)
- [Leif Assurance: Insurance, Surety Bonds, Safety](https://www.insurancebuiltforcontractors.com/subcontractor-prequalification-insurance-surety-bonds-safety-and-more/)
- [DPR Construction: Subcontractor Prequalification](https://www.dpr.com/subcontractor-prequalification)

### 2. KYB Services for Marketplace Operator Verification

Three services evaluated for our use case:

#### Middesk

- **What it checks:** Secretary of State records (all 50 states, direct integration), IRS EIN verification, OFAC + sanctions screening, PEP screening, adverse media, business address verification.
- **Coverage:** 100% of US businesses; 92% of records updated within 10 days.
- **Data sources:** Official SoS filings, IRS, OFAC — authoritative, not third-party data.
- **API:** Minimal input required (business name + address). Returns registration status, filing history, officers, addresses.
- **Pricing:** Not publicly listed. Estimated $500/month floor; per-check pricing decreases with volume. Enterprise negotiated.
- **Best fit for YAK:** Entity-level verification triggered once per operator when they first win a task above a threshold. Low volume = low cost. US-only (our market is 100% US).
- **Limitation:** Does not include individual KYC — need Stripe Identity or separate service for sole proprietors where company = person.

Sources:
- [Middesk KYB API](https://www.middesk.com/kyb-business-verification-api)
- [Middesk: Secretary of State API Sources](https://www.middesk.com/blog/secretary-of-state-api)
- [Middesk: OFAC API](https://www.middesk.com/ofac-api)
- [Vendr: Middesk Pricing 2026](https://www.vendr.com/marketplace/middesk)

#### Persona

- **What it checks:** KYB (company verification, UBO identification, document collection) + KYC in unified workflow. Contextual matching improves match rate by up to 55% over direct string match.
- **Key differentiator:** No-code workflow builder; combined KYC+KYB in one platform; `Persona Connect` for collaborative identity (multiple platforms sharing verifications).
- **AML screening:** Via third-party integration, not native.
- **Pricing:** Startup plan available; exact pricing quote-required. Comparable to Stripe Identity (market standard rate).
- **Best fit for YAK:** If we need both individual identity + business verification in one platform, Persona is cleaner. Overkill for current volume.

Sources:
- [Persona: KYB Solutions](https://withpersona.com/solutions/know-your-business)
- [Persona KYB platform update](https://www.biometricupdate.com/202503/persona-updates-kyc-kyb-platform)
- [Persona at Money20/20: Connect launch](https://ffnews.com/newsarticle/fintech/persona-launches-connect-at-money20-20-usa-to-build-the-rails-for-collaborative-identity/)

#### Stripe Connect Express (existing)

- **What it checks:** KYC for the individual representative: government ID, DOB, address, SSN (US) or EIN for businesses. Optionally: gov ID document + selfie match via Stripe Identity add-on.
- **Coverage:** Handles regulatory KYC; Stripe handles the compliance burden for financial services.
- **Key limitation:** Stripe Connect Express KYC is identity verification, not entity verification. Stripe confirms "this is a real person" but does not verify the business entity is properly registered with a state SoS.
- **What it does NOT cover:** Secretary of State registration status, OFAC screening beyond basic sanctions, professional licenses (FAA Part 107, PLS), insurance.
- **Cost:** Included in Connect platform fee (no marginal cost per operator for the baseline KYC).
- **Best fit for YAK:** Use as the mandatory first gate — every operator must complete Stripe onboarding before bidding. This covers KYC and enables payments. Not a substitute for entity-level KYB.

Sources:
- [Stripe: Identity Verification for Connected Accounts](https://docs.stripe.com/connect/identity-verification)
- [Stripe Connect: KYC Requirements](https://support.stripe.com/questions/know-your-customer-(kyc)-requirements-for-connected-accounts)
- [Greenmoov: Stripe Connect for Marketplace Payments (2026)](https://greenmoov.app/articles/en/stripe-connect-for-marketplace-payments-explained-account-types-onboarding-and-pricing-2026-guide)

### 3. How Other Construction Marketplaces Verify Contractors

**Procore Marketplace:** Partners must pass a marketplace approval checklist, but this is an ISV/integration partner process — not operator-facing contractor verification. Procore itself facilitates document collection and license tracking but does not independently verify credentials.

**BuildOps (2026):** Focused on dispatching and CRM for contractors — no independent third-party verification layer. Document collection is operator self-service.

**Zeitview / DroneBase:** These drone survey platforms handle operator vetting through portfolio review + pilot profile approval. No published KYB/KYC requirements. Trust is built through platform reputation scores, not third-party verification.

**Key observation:** At the $1K–$10K survey task scale, the construction tech industry standard is **document self-attestation + insurance COI verification + license lookup**. Full third-party KYB is rare below $50K contract value. The platform's trust layer (reputation score, delivery history) substitutes for expensive upfront KYB.

### 4. SAM.gov: Entity API vs Exclusions API

The current `compliance.py` implements the SAM.gov Exclusions API (debarment check) — this is correct for federal-funded projects. There is a separate **Entity Management API** that returns active registration status, DUNS/UEI, NAICS codes, and business type.

**Entity API relevance for YAK:**
- MDOT federal-aid highway survey projects require SAM.gov active registration
- The Entity API is free (public access: 10 req/day; registered: 1,000/day)
- For federally-funded tasks, we should check both: (1) not excluded AND (2) actively registered
- For private/state-funded projects, SAM.gov registration is not required

Sources:
- [SAM.gov Entity Management API](https://open.gsa.gov/api/entity-api/)
- [GovConAPI: SAM.gov API Guide 2026](https://govconapi.com/sam-gov-api-guide)

### 5. Operator Entity Type: Sole Proprietor vs LLC

This is relevant because **Stripe USDC payouts are limited to sole proprietors and individuals**, not LLCs (per R-024 findings).

**What the data shows:**
- No industry survey provides exact LLC vs sole proprietor percentages for drone survey operators.
- 35% of all drone operators do mapping/surveying as primary use case.
- 55% of drone companies had <10 employees in 2024 (dropping to 48.2% in 2025 as the sector matures).
- FAA Part 107 is structure-neutral — no business entity required.
- Industry guidance strongly recommends LLCs for drone survey operators performing construction work (liability protection for $1M+ projects). At $45K+ task values, operating without LLC protection is unusual.

**Implication for Stripe USDC payouts:** The majority of serious construction survey operators at $10K+ task values are likely LLCs, not sole proprietors. Stripe USDC payouts (R-024) may have limited uptake for this segment. The fiat payout path (ACH/card) is the primary settlement route.

Sources:
- [Drone Pilot Ground School: Do I Need an LLC?](https://www.dronepilotgroundschool.com/kb/do-i-need-an-llc-to-start-my-drone-business/)
- [Heliguy: Global State of Drones 2025](https://www.heliguy.com/blogs/posts/global-state-of-drones-2025-industry-whitepaper/)
- [FAA: Part 107 Commercial Operators](https://www.faa.gov/uas/commercial_operators)

### 6. INFORM Consumers Act Applicability

The INFORM Consumers Act (effective June 27, 2023) requires online marketplaces to verify high-volume sellers. **It does NOT apply to YAK** because:
- The Act covers "tangible personal property distributed in commerce for personal, family, or household purposes."
- Construction survey services are neither tangible goods nor consumer products.
- "High-volume third-party seller" threshold (200+ transactions AND $5K+ revenue in 12 months) is also not met at our task volume.

Sources:
- [FTC: INFORM Act Business Guidance](https://www.ftc.gov/business-guidance/resources/INFORMAct)
- [Middesk: What Is the INFORM Consumers Act](https://www.middesk.com/blog/what-is-inform-consumers-act)

### 7. Current Codebase State

**`auction/compliance.py`:**
- `ComplianceChecker` stores 6 doc types: `faa_part_107`, `insurance_coi`, `pls_license`, `sam_registration`, `dot_prequalification`, `dbe_certification`.
- Upload marks docs as VERIFIED immediately — no async external API verification.
- `verify_operator()` returns `compliant: True` only if ALL 6 doc types are VERIFIED. This fails operators who haven't uploaded `pls_license` even when the task doesn't require it.
- `check_sam_exclusion()` correctly calls SAM.gov Exclusions API v4 when `SAM_GOV_API_KEY` is set.

**`auction/operator_registry.py`:**
- `activate()` gate checks: equipment ≥1, `faa_part_107` in certifications, insurance COI set. **This is the right minimal gate.**
- No entity verification (KYB) anywhere in the codebase. No Stripe Connect status check at activation.
- `OperatorProfile` does not store Stripe Connect account ID — there's no way to confirm an operator has completed Stripe onboarding.

**Key gap:** There is no link between `OperatorProfile` and the operator's Stripe Connect Express account. An operator can be activated for bidding and win a task without ever completing Stripe onboarding, which would cause payout failure at settlement.

---

## Implications for the Product

1. **Stripe Connect onboarding must be mandatory before activation** — Not just before first payout. Store `stripe_account_id` on `OperatorProfile` and add it to the `activate()` gate. This closes the gap where an operator wins a task but can't receive payment.

2. **The `compliant` flag in `verify_operator()` needs task-type context** — A drone survey task without PLS deliverables should treat `pls_license`, `sam_registration`, `dot_prequalification`, `dbe_certification` as `NOT_REQUIRED`. Only `faa_part_107` and `insurance_coi` are always required.

3. **Tiered verification by task value is the correct design:**
   - **Tier 1 — Demo/small tasks (<$5K):** Stripe Connect Express onboarding (KYC only). Baseline trust. Zero marginal cost.
   - **Tier 2 — Mid-range tasks ($5K–$25K):** Tier 1 + insurance COI verified + FAA Part 107 active status (LAANC cert lookup or manual document review).
   - **Tier 3 — Large tasks ($25K+):** Tier 2 + Middesk entity check (SoS registration, EIN match, OFAC) + SAM.gov exclusion check. Triggered once per operator at first Tier 3 win.

4. **Add SAM.gov Entity registration check** for federal-funded projects (MDOT federal-aid tasks). The Entity API is already free — a 5-line addition to `compliance.py` alongside the existing exclusions check.

5. **Drone survey operator entity type is likely mostly LLC** at construction scale — do not invest in optimizing Stripe USDC payout path specifically for operator payouts (R-041 hypothesis partially confirmed).

---

## Improvement Proposals

### IMP-064: Add `stripe_account_id` to `OperatorProfile` and enforce it at activation

**Module:** M10_compliance  
**Effort:** small  
**Priority:** high  
**Description:** Add `stripe_account_id: str | None` field to `OperatorProfile`. In `activate()`, check that `stripe_account_id` is set and non-None before allowing activation. This closes the gap where an operator can win tasks but has no payout path. The 3-step registration UI (v1.4) should write the Connect account ID back to the registry on completion.

### IMP-065: Tiered compliance gate — `NOT_REQUIRED` for task-type-irrelevant docs

**Module:** M10_compliance  
**Effort:** small  
**Priority:** medium  
**Description:** The `verify_operator()` `compliant` flag returns `False` if any of 6 doc types is MISSING. For drone-only tasks (no PLS deliverables, no SAM registration, no DOT prequalification), these docs should be auto-set to `NOT_REQUIRED`. Add a `task_type` parameter to `verify_operator()` that populates `NOT_REQUIRED` status for docs that aren't applicable to the task type. Always required: `faa_part_107`, `insurance_coi`. Conditionally required: `pls_license` (PLS-stamped deliverables), `sam_registration` (federal-funded), `dot_prequalification` (DOT contracts), `dbe_certification` (DBE set-asides).

### IMP-066: Middesk entity-level KYB trigger at first Tier-3 task win

**Module:** M10_compliance  
**Effort:** medium  
**Priority:** medium  
**Description:** When an operator first wins a task with value ≥$25K, trigger a Middesk KYB check via their API (name + address → SoS + IRS + OFAC result). Store the result on `OperatorProfile` as `kyb_status: {vendor, result, checked_at}`. If KYB returns FAIL (entity not found, SoS inactive, OFAC hit), hold payout and flag for manual review. IMP-065 (tiered gate) should be implemented first. Middesk API key added to env vars.

### IMP-067: SAM.gov Entity registration check for federal-funded tasks

**Module:** M10_compliance  
**Effort:** small  
**Priority:** low  
**Description:** Add `check_sam_entity_registration(entity_name)` to `compliance.py` alongside the existing `check_sam_exclusion()`. Uses the SAM.gov Entity Management API v4 (same API key). For tasks tagged as `federal_funded: True` (MDOT federal-aid projects), check both active registration and exclusion. This is currently a gap — we check debarment but not active registration status.

---

## New Questions Spawned

1. **R-028** (already in roadmap): Stripe Identity and Connect KYC as operator verification — can be unblocked now.
2. **Consider adding to roadmap:** DroneBase / Zeitview operator onboarding deep-dive — how do current drone-specific platforms vet pilots in practice? What signals do they use for reputation scoring?
3. **Consider adding to roadmap:** Insurance COI automated parsing (ACORD 25) — R-008 in roadmap — reinforced as high priority since insurance is the #1 GC trust signal and we currently accept it as self-reported text.

---

## Sources

- [Procore: Subcontractor Prequalification](https://www.procore.com/library/subcontractor-prequalification)
- [Highwire: 2025 Guide to Subcontractor Prequalification](https://www.highwire.com/blog/the-complete-guide-to-subcontractor-prequalification)
- [Leif Assurance: Subcontractor Prequalification](https://www.insurancebuiltforcontractors.com/subcontractor-prequalification-insurance-surety-bonds-safety-and-more/)
- [DPR Construction: Subcontractor Prequalification](https://www.dpr.com/subcontractor-prequalification)
- [Middesk KYB API](https://www.middesk.com/kyb-business-verification-api)
- [Middesk: Secretary of State API](https://www.middesk.com/blog/secretary-of-state-api)
- [Middesk: OFAC API](https://www.middesk.com/ofac-api)
- [Vendr: Middesk Pricing 2026](https://www.vendr.com/marketplace/middesk)
- [iDenfy: Best KYB Software Providers 2026](https://idenfy.com/blog/best-kyb-software/)
- [Compliancely: Top KYB Software Providers 2026](https://compliancely.com/blog/best-kyb-software-providers/)
- [Persona: KYB Solutions](https://withpersona.com/solutions/know-your-business)
- [Persona KYB platform update](https://www.biometricupdate.com/202503/persona-updates-kyc-kyb-platform)
- [Stripe: Identity Verification for Connected Accounts](https://docs.stripe.com/connect/identity-verification)
- [Stripe Connect: KYC Requirements](https://support.stripe.com/questions/know-your-customer-(kyc)-requirements-for-connected-accounts)
- [Greenmoov: Stripe Connect for Marketplace Payments (2026)](https://greenmoov.app/articles/en/stripe-connect-for-marketplace-payments-explained-account-types-onboarding-and-pricing-2026-guide)
- [SAM.gov Entity Management API](https://open.gsa.gov/api/entity-api/)
- [GovConAPI: SAM.gov API Guide 2026](https://govconapi.com/sam-gov-api-guide)
- [FTC: INFORM Act Business Guidance](https://www.ftc.gov/business-guidance/resources/INFORMAct)
- [Middesk: What Is the INFORM Consumers Act](https://www.middesk.com/blog/what-is-inform-consumers-act)
- [Drone Pilot Ground School: Do I Need an LLC?](https://www.dronepilotgroundschool.com/kb/do-i-need-an-llc-to-start-my-drone-business/)
- [Heliguy: Global State of Drones 2025](https://www.heliguy.com/blogs/posts/global-state-of-drones-2025-industry-whitepaper/)
- [FAA: Part 107 Commercial Operators](https://www.faa.gov/uas/commercial_operators)
- [gcheck: Gig Worker Identity Verification](https://gcheck.com/blog/gig-worker-identity-verification/)
- [Intellicheck: Verifying Gig and Contract Workers](https://www.intellicheck.com/resource-library/verifying-gig-and-contract-workers-heres-what-you-need-to-know-intellicheckverifying)
