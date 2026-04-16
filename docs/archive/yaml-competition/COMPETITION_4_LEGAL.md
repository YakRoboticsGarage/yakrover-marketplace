# Competition Round 4: Legal & Compliance Critique of PRODUCT_DSL.yaml

**Competitor:** 4 of 5 — Legal and Compliance Critic
**Date:** 2026-03-29
**Target:** `docs/research/PRODUCT_DSL.yaml` (schema 1.1)
**Methodology:** Compare every statute, regulation, and compliance obligation documented in the five research files against what the YAML actually models. Flag omissions, under-specifications, and liability exposure.

---

## 1. Payment Flow: Incomplete Chain

The research documents a precise legally-required chain: **bond/escrow funding -> milestone billing (AIA G702/G703) -> retainage withholding (5-10%) -> retainage release -> lien waiver exchange**. The YAML's `settlement.payment_split` models only a flat 25/75 acceptance/delivery split (PD-4). Missing from the YAML:

- **Retainage.** Research specifies 5-10% retainage held until substantial completion, with Michigan allowing reduction to 0% after 50% on public projects. The YAML has zero retainage modeling. At $72K, that is $7,200 the operator should expect held.
- **Lien waiver exchange.** Research documents automatic lien waiver exchange at closeout (Phase 4, step 13 of the recommended flow). The YAML state machine goes `verified -> settled` with no intermediate `lien_waiver_exchanged` state. Michigan's Construction Lien Act (MCL 570.1101 et seq.) makes this non-optional.
- **Progress billing format.** Research calls out AIA G702/G703 as the industry standard for progress billing. The YAML has no `billing_format` field on task specs or contracts.
- **Prompt payment timelines.** MCL 125.1561 mandates 10-day payment after owner pays, with 1.5%/month penalty. The YAML's `michigan_specifics` section lists the statute but the state machine has no timer enforcing it.

**Recommendation:** Add a `payment_flow` section to `legal:` with states: `escrow_funded -> milestone_billed -> milestone_approved -> payment_released -> retainage_held -> retainage_released -> lien_waiver_exchanged -> closed`. Attach prompt-payment timers per jurisdiction.

## 2. Insurance Model: Structurally Present but Operationally Thin

The YAML's `insurance_requirements` section captures CGL, E&O, and drone liability limits for private vs. DOT projects. Gaps:

- **Workers Compensation** is listed in research tables but absent from the YAML's `insurance_requirements` block. This is a statutory requirement in every state.
- **Umbrella/Excess liability** ($2M-$10M per research) is not modeled. DOT projects commonly require it.
- **Commercial Auto** ($1M-$2M per research) is missing. Operators drive trucks to sites.
- **COI verification fields** are described narratively (`legal:coi_verification`) but no schema exists for ACORD 25 parsed fields: policy number, NAIC number, additional insured status, waiver of subrogation, retroactive date, tail coverage.
- **E&O tail coverage risk.** Research warns E&O is claims-made, not occurrence. An operator who drops E&O after a project exposes the platform to downstream claims. No `tail_coverage_required` flag exists.
- **TxDOT Form 1560-CSS.** Research notes TxDOT rejects standard ACORD forms. No jurisdiction-specific COI variant is modeled.

**Recommendation:** Expand `insurance_requirements` to include all six coverage types from the research table. Add a `coi_schema` entity with parseable fields. Add `tail_coverage_minimum_years` to E&O requirements.

## 3. Money Transmission: Acknowledged but Under-Mitigated

The YAML has a single entry (`legal:money_transmitter`) noting the risk and stating v1.5 uses "prepaid credits covered by Stripe's licenses." This is dangerously thin:

- **State-by-state analysis is absent.** Money transmitter licensing is a per-state obligation (49 states + DC + territories). Relying on Stripe's license works only if the platform never touches funds outside Stripe's flow.
- **Escrow at v2.5 is a red flag.** The research recommends "Rolling Escrow" as the MVP payment model. The moment the platform holds funds in an escrow account it controls, it is almost certainly a money transmitter under most state laws. The YAML defers this to "legal review" but places escrow in the architecture (`component:escrow_contract`) without modeling the licensing prerequisite.
- **USDC settlement compounds the risk.** Crypto payments trigger additional federal (FinCEN) and state (BitLicense in NY) obligations. The YAML models `settlement:immediate_transparent` on Base with USDC but has no `money_services_business` compliance entity.

**Recommendation:** Add `legal:money_transmission` with fields: `stripe_coverage` (what Stripe's license covers), `escrow_licensing_required` (boolean per state), `crypto_msb_registration` (FinCEN requirement), `resolve_before` (must be before escrow launch, not after).

## 4. Data Ownership and Privacy: Present in Contract Template, Absent as First-Class Entity

Research devotes an entire section to data ownership (raw sensor data, processed deliverables, derived products, license-back rights, re-use rights). The YAML buries this inside `contract:consensusdocs_751.key_terms.data_ownership` as a single string: "Processed deliverables to client; raw data retained by operator." Missing:

- **Raw data retention rights for E&O defense.** Research explicitly states operators retain raw data for liability defense. This should be a platform policy, not just a contract term.
- **Derived product ownership.** Who owns the 3D model generated from a point cloud the client paid for? Not addressed.
- **Platform data rights.** The marketplace processes task specs, bids, deliverable metadata. Does the platform retain any rights for training, analytics, or benchmarking? Unaddressed.
- **Privacy for neighboring properties.** Research cites *United States v. Causby* and Nevada drone trespass law. Drone surveys near property boundaries can capture private data. No `privacy_buffer` or `neighboring_property_consent` field exists on task specs.
- **GDPR/state privacy.** If operator profiles contain personal information (PLS license number, home address), state privacy laws (CCPA, etc.) apply. No data handling classification exists in the YAML.

**Recommendation:** Promote `data_ownership` to a top-level section under `legal:` with explicit fields for raw, processed, derived, platform-retained, and privacy-buffer requirements.

## 5. Dispute Resolution: Flow Exists but Lacks Financial Teeth

The YAML's `award_confirmation` state machine models reject -> next bidder -> re-pool. The contract template specifies "Negotiation -> mediation -> arbitration." Gaps:

- **No dispute state in the task lifecycle.** The `task_lifecycle` state machine has no `disputed` state. What happens when a buyer rejects delivery and the operator contests? The machine goes `delivered -> in_progress` (request_redelivery), but there is no path to formal dispute resolution.
- **No escrow hold during dispute.** If funds are in escrow and a dispute arises, who holds them? The settlement interface has `refund` but no `freeze` or `hold_pending_dispute` method.
- **Small claims fast-track.** Research recommends a fast-track for disputes under $25K. The YAML does not model dollar-based dispute routing.
- **Statute of limitations.** Texas has a 10-year statute for survey error claims. The YAML does not model per-state limitation periods that affect E&O tail requirements.

**Recommendation:** Add a `disputed` state to `task_lifecycle` with transitions to `mediation`, `arbitration`, and `resolved`. Add `hold_pending_dispute` to the settlement interface.

## 6. Regulatory Risk: FAA and OSHA Modeled, State Licensing Under-Specified

- **FAA Part 107 and Part 108** are well-modeled in the YAML (`legal:faa_part_107`, `unknown:regulatory_autonomous_drone`).
- **OSHA** appears only in onboarding steps ("OSHA 10-hour construction") and one equipment detail. No `osha_compliance` entity exists. Research mentions OSHA compliance and site-specific safety plans as contract requirements. A robot injuring a worker on-site is a foreseeable event with no modeled response.
- **State PLS licensing reciprocity.** The YAML models Michigan's MCL 339.2001 but the marketplace targets AZ, NV, NM, and MI. Each state has different PLS requirements, experience minimums, and continuing education. No multi-state licensing model exists.
- **Remote ID.** FAA requires Remote ID on all drones over 0.55 lbs. Not mentioned in the YAML despite being a compliance prerequisite for every drone operation.
- **Debarment checking.** Research documents SAM.gov API integration for debarment verification. The YAML's `award_confirmation` lists `rejection_reasons` but `debarment` is not among them, and no `debarment_check` capability exists.

**Recommendation:** Add `legal:osha_compliance` (site safety plan requirement, incident reporting), `legal:remote_id` (FAA mandate), and `legal:debarment_check` (SAM.gov + state lists) as explicit entities. Expand PLS licensing to a multi-state model.

## 7. Demo: Legal Elements Present but Incomplete

The demo (index.html) correctly shows bond verification, PLS license badges, COI status (CGL + E&O + Aviation), and data ownership/dispute resolution terms in the signing card. Gaps:

- **No lien waiver step** in the demo flow. The closeout screen shows a result but no lien waiver exchange.
- **No retainage** displayed anywhere in the payment/result screens.
- **Data ownership term** says "Client owns all deliverables upon payment" -- this contradicts the research recommendation that raw data stays with the operator. The demo oversimplifies.
- **No Terms of Service or Privacy Policy link.** The footer has no legal links. A live marketplace must have these.
- **No limitation of liability disclosure.** Research recommends displaying the LOL cap (1x task fee) at award. The demo's signing card omits it.

---

## Summary: 14 Gaps, 5 Critical

| # | Gap | Severity | YAML Section Affected |
|---|-----|----------|-----------------------|
| 1 | No retainage modeling | CRITICAL | `settlement.payment_split` |
| 2 | No lien waiver state | CRITICAL | `state_machines.task_lifecycle` |
| 3 | No `disputed` state in task lifecycle | CRITICAL | `state_machines.task_lifecycle` |
| 4 | Money transmission licensing for escrow/crypto unmodeled | CRITICAL | `legal` |
| 5 | Workers Comp / Umbrella / Auto insurance missing | CRITICAL | `legal.insurance_requirements` |
| 6 | E&O tail coverage not enforced | HIGH | `legal.insurance_requirements` |
| 7 | Data ownership not a first-class entity | HIGH | `legal` |
| 8 | No prompt-payment timer in state machine | HIGH | `legal.michigan_specifics` |
| 9 | No multi-state PLS licensing model | MEDIUM | `legal` |
| 10 | No Remote ID compliance entity | MEDIUM | `legal.overhead` |
| 11 | No debarment check capability | MEDIUM | `architecture.capabilities` |
| 12 | No OSHA compliance entity | MEDIUM | `legal` |
| 13 | Platform data rights unaddressed | MEDIUM | `legal` |
| 14 | Demo contradicts research on raw data ownership | LOW | `demo/index.html` |

The YAML's legal section is structurally sound -- it has the right categories (moats, overhead, contracts, insurance, michigan_specifics). But it models legal compliance as a set of badges to display rather than as enforceable states, timers, and financial holds. The payment chain from bond to lien waiver needs to be a first-class state machine, not a narrative in research documents.
