# R-045: State Surveying Board Platform-Intermediary Liability — Does the Marketplace Face Enforcement Risk?

**Date:** 2026-04-15
**Topic ID:** R-045
**Module:** M36_pls_review
**Depends on:** R-007b (2024 NC Drone Mapping Court Ruling — completed 2026-04-14)
**Researcher:** Automated daily research agent

---

## Executive Summary

- **No documented case of a state surveying board pursuing a marketplace platform** (as opposed to the individual operator) has been found. All known enforcement actions — NC, OR, TX, PA — target the drone operator or company directly, not any platform that facilitated the transaction.

- **New York State law explicitly prohibits unlicensed entities from acting as intermediaries** between clients and licensed surveyors. NY's Office of the Professions holds: "An entity not authorized to provide professional engineering and/or land surveying services… cannot subcontract with a licensed professional engineer or land surveyor in order to provide professional services to a third party client." If YAK facilitates NY survey transactions without holding a NY surveyor's license, it may be in violation of this rule. However, this is a NY-specific statutory interpretation — no other state has published equivalent language.

- **The FlyGuys model (subcontractor to licensed firms, not direct-to-end-client)** is the established legally safe structure for drone data platforms operating at scale. YAK's current model — accepting RFPs from GCs/DOTs directly and dispatching operators — is structurally different and carries higher platform exposure in states that scrutinize the "offering to practice" element.

- **Section 230 CDA provides no shield** against professional licensing enforcement. It covers civil liability for user-generated content. State boards bringing administrative enforcement actions for unlicensed practice are not defamation or content-distribution claims.

- **Three risk-mitigation strategies** are available to YAK (from lowest to highest coverage): (1) Operator disclosure flow + terms-of-service disclaimer; (2) Require PLS attestation or "operated under PLS" declaration for topo-category tasks; (3) Platform obtains Certificate of Authorization (CoA) as a surveying firm in target states. The third option is how Zillow/Redfin resolved the analogous real estate intermediary licensing problem.

---

## Findings

### 1. Enforcement History: Has Any Board Targeted a Platform?

**Research finding: No documented cases found.**

All known surveying board enforcement actions against drone operators have targeted:
- The drone operator/LLC directly (e.g., *360 Virtual Drone Services LLC v. Ritter*, NC Board, 2018–2024)
- Survey companies misrepresenting the scope of unlicensed employees' work
- Engineers/surveyors who delegated to unlicensed staff without proper supervision

The NC Board issued cease-and-desist letters to **at least 6 drone companies** between 2018 and 2024. All were directed at the companies providing the drone service, not any platform through which they advertised or sold.

The Texas Board of Professional Engineers and Land Surveyors (TBPELS) 2025 disciplinary actions (e.g., *Create C.H. Solutions, Houston* — enforcement for practicing engineering without a license) similarly targeted the operator entity, not any marketplace.

**Implication:** State boards currently pursue enforcement under the theory of "offering or practicing without a license" which requires the *operator* to have done the offering. A marketplace platform that is not itself advertising survey services — but merely matching buyers to operators — presents a less obvious enforcement target under existing statutory language.

However, this is **not a safe harbor** — it is simply the current enforcement posture. As drone marketplaces grow, boards may expand enforcement to platforms that facilitate unlicensed practice at scale.

---

### 2. The New York Prohibition: A Material Outlier

New York State's Office of the Professions published formal guidance ([NY OPD FAQ](https://www.op.nysed.gov/professions/engineering/frequently-asked-practice-questions)) stating:

> "An entity not authorized to provide professional engineering and/or land surveying services, such as a general contractor, **cannot subcontract** with a licensed professional engineer or land surveyor in order to provide professional services to a third party client, because the service of the professional must be provided directly from the professional to the client without any unlicensed third party between the client and the professional."

**What this means for YAK in New York:**

If a GC in New York posts an RFP on YAK, YAK assigns a licensed NY PLS to the task, and the PLS delivers the survey — NY OPD guidance suggests that YAK (as an unlicensed intermediary) is inserting itself between the client and the professional in a way that may violate NY Education Law Article 145.

Section 6512.1 of NY Education Law makes it a **Class E felony** for unauthorized entities to practice or offer to practice professional engineering or land surveying.

**Counterargument:** YAK is an auction marketplace, not a surveying firm. It does not review deliverables, does not sign or seal anything, and does not exercise professional judgment. A strong argument can be made that YAK is providing a software/platform service rather than "offering to practice land surveying." But this distinction has not been tested in NY courts for the marketplace context specifically.

**Other state analogy (TX real estate):** Texas TREC makes it unlawful to pay referral fees to unlicensed real estate intermediaries — any entity collecting a fee for procuring a professional-services transaction must hold the relevant license. TBPELS follows analogous logic for engineering/surveying. Whether the YAK "platform fee" would be deemed a referral fee or a software service fee is an open legal question.

---

### 3. The FlyGuys Model: Subcontractor to Licensed Firms, Not Direct-to-Client

FlyGuys (the closest operational analogue to YAK's drone data marketplace) explicitly structures its business as follows:

> "Many licensed surveyors and engineering firms across the US are turning to FlyGuys to help with their drone services needs."  
> "Aerial drone services may collect imagery or elevation data, but that data does not hold legal weight unless it has been verified and certified by a licensed surveyor."

**FlyGuys' structural choice:** Their primary clients for topo/survey work are **licensed survey firms**, not end clients. The survey firm holds the contract with the GC or DOT; FlyGuys is the data-collection subcontractor. The licensed PLS firm is "in responsible charge" and seals the deliverables. FlyGuys is explicitly positioned as drone data collection infrastructure.

**YAK's structural difference:** YAK accepts RFPs directly from GCs and construction project owners. The buyer is the end client. The winning operator delivers directly to the buyer. A licensed PLS may or may not be involved — the platform does not currently require or track PLS involvement in the delivery chain.

This is the most material structural risk: **YAK is positioned as a surveying services procurement platform, not a data acquisition infrastructure provider for licensed firms.** In enforcement-prone states (NC, OR, TX, NY), this positioning invites board scrutiny.

---

### 4. Section 230 CDA Does Not Apply

Section 230 of the Communications Decency Act (47 U.S.C. § 230) provides:

> "No provider or user of an interactive computer service shall be treated as the publisher or speaker of any information provided by another information content provider."

This protects platforms from civil liability for **user-generated content** (defamation, product descriptions, reviews). It does not protect against:
- **Administrative enforcement actions** by state professional licensing boards
- **Criminal charges** under state unlicensed practice statutes
- **Federal criminal law** (already carved out by the statute itself)

Section 230 is irrelevant to professional licensing enforcement. The YAK platform cannot rely on Section 230 as a shield if a state board claims the platform is "offering to practice" surveying by accepting and facilitating survey RFPs.

---

### 5. How Analogous Platforms Solved the Problem: The Zillow/Redfin Model

The most instructive analogy is real estate. Zillow and Redfin, which facilitate real estate transactions (a licensed profession), resolved the licensing intermediary problem by:

- **Obtaining real estate brokerage licenses** in all states where they operate
- Employing licensed agents under those licenses
- Structuring the platform's contract with users as a brokerage engagement, not a referral service

Zillow holds brokerage licenses in multiple states. Redfin is licensed in all 50 states. This is not optional — it is how they operate legally.

**For YAK, the analogous path** would be to obtain a Certificate of Authorization (CoA) as a surveying firm (or, in states that allow it, as a professional services LLC with a licensed surveyor in responsible charge on staff). This would allow YAK to contract with end clients and subcontract to the winning operator. This is a significant operational step but is the most legally robust solution.

---

### 6. Risk Matrix by State

| State | Platform Risk Level | Basis | Notes |
|-------|-------------------|-------|-------|
| **New York** | **High** | Explicit OPD guidance: unlicensed intermediaries prohibited | Class E felony; most specific prohibition found |
| **North Carolina** | **High** | 4th Cir. binding; Board has actively targeted drone companies | SCOTUS petition pending — if cert granted, risk may decrease |
| **Oregon** | **High** | OSBEELS published explicit UAS guidance | Board has proactively published enforcement standards |
| **Virginia / Maryland / WV / SC** | **Medium-High** | 4th Circuit states; analogous statutes | No drone-specific enforcement documented, but legal authority exists |
| **Texas** | **Medium** | TBPELS; similar referral-fee enforcement posture | TxDOT UAS Manual permits drone surveys under PLS supervision |
| **Michigan** | **Medium** | MCL 339.2001; YAK's primary market | Primary market — LARA enforcement history is less aggressive |
| **California** | **Medium** | BPC § 8700; broad practice definition | Large market; CA DCA is enforcement-active generally |
| **Ohio** | **Medium** | ORC Ch. 4733; ODOT has high standards | High deliverable standards may make unlicensed work obvious |
| **Illinois** | **Lower** | 225 ILCS 330; potential carve-out for non-NSPS-accuracy products | Less enforcement pressure than coastal states |

---

### 7. No "Professional Licensing Safe Harbor" Exists

There is no statutory equivalent to the DMCA safe harbor or CDA Section 230 for professional licensing claims. Research found no federal or state law that explicitly insulates a marketplace from professional licensing enforcement on the basis that it is merely an online intermediary.

The closest analogues (healthcare "safe harbor" statutes in some states) apply only to specific alternative medicine practitioners, not to software platforms facilitating professional service transactions.

Healthcare platforms like Teladoc, Doctor on Demand, and Zocdoc have addressed this by employing licensed physicians directly, obtaining medical practice group licenses, or structuring as "technology platforms for independent physician practices" — but each has faced state medical board scrutiny at some point.

---

### 8. Viable Risk-Mitigation Strategies (Ordered by Coverage)

**Tier 1 — Minimal coverage (current state + disclosures):**
- Add clear platform terms: "YAK does not provide surveying services. YAK is a marketplace platform. Operators are responsible for ensuring their work complies with applicable PLS licensure requirements."
- Display operator PLS status in UI (currently missing for topo tasks)
- Disclaimer: "Topographic and topo-equivalent deliverables require a licensed Professional Land Surveyor. Ensure the winning operator holds a valid PLS license in the project state."

*Risk level remaining: Medium. Disclaimer does not prevent enforcement if the board views YAK as "offering to practice."*

**Tier 2 — Operational changes (medium coverage):**
- Add `pls_required: true/false` to task specs for topo-category tasks (IMP-068, proposed by R-007)
- Gate bidding on topo tasks so only operators with `pls_license` in the project state can bid OR operators who declare they "operate under a licensed PLS firm in responsible charge"
- Require operators accepting topo tasks to submit a "PLS in Responsible Charge" declaration naming the supervising PLS and their license number
- Structure contracts so the buyer contracts with the *operator/PLS firm*, and YAK is purely a platform fee on top — not the contracting party for the survey service

*Risk level remaining: Low-Medium. Demonstrates good faith compliance posture. The "PLS in Responsible Charge" declaration is the same model used by FlyGuys and Aerotas.*

**Tier 3 — Entity-level licensing (highest coverage):**
- Obtain a surveying firm Certificate of Authorization (CoA) in MI, OH, TX, NC, OR, NY — the states with active enforcement risk
- Employ or retain a licensed PLS in each state (part-time or advisory relationship)
- Structure YAK as the contracting surveying firm; winning operator is a licensed subcontractor under YAK's CoA; PLS reviews and seals all deliverables before delivery
- This is the Zillow/Redfin model applied to survey marketplaces

*Risk level remaining: Very Low. This is how legal entities in the space operate.*

---

## Codebase Gaps (Cross-Reference with R-007b)

| Gap | Location | Risk |
|-----|----------|------|
| `verify_operator()` requires `pls_license` for ALL tasks | `auction/compliance.py` | Over-restricts non-topo operators; does not contextually gate topo tasks |
| No `pls_required` flag on topo-category task specs | `auction/core.py` (TaskSpec) | Cannot implement Tier 2 bidding gate without this field |
| No "PLS in Responsible Charge" declaration field on bids | `auction/core.py` (Bid) | Cannot collect the responsible-charge attestation at bid time |
| Operator onboarding has no PLS role declaration | `auction/mcp_tools.py` | Operators cannot declare "I operate under PLS firm X" |
| No platform contract framing in task assignments | `auction/engine.py` | YAK is implicitly the procurement agent for the survey; contract structure not documented |
| No state-specific enforcement flag in geographic filtering | `auction/discovery_bridge.py` | High-risk states (NY, NC, OR) receive no special compliance gating |

---

## Improvement Proposals

### IMP-078: Add "PLS in Responsible Charge" declaration to bid submission for topo tasks

**Description:** When an operator submits a bid on a task where `pls_required: true`, require them to declare either (a) they hold a valid PLS in the project state (license number field), or (b) they operate under a licensed PLS firm in responsible charge (firm name + PLS name + license number). This data is stored with the bid and surfaced to the buyer. Prevents unlicensed operators from winning topo tasks without platform awareness.

**Module:** M7_bid_scorer + M10_compliance  
**Effort:** Medium  
**Priority:** High

### IMP-079: Add `pls_required` boolean to TaskSpec for topo-category tasks

**Description:** Add `pls_required: bool` field to the TaskSpec dataclass/schema. Set `True` for: `topo_survey`, `corridor_survey`, `site_survey`, `control_survey`, `as_built`, `aerial_survey`. Set `False` for: `progress_monitoring`, `gpr_scan`, `orthomosaic`, `inspection`, `thermal`, `volumetrics`. This enables the bidding gate (IMP-078) and surfaces compliance info in the buyer UI. Depends on IMP-068 (pls_seal_format from R-007).

**Module:** M5_auction_engine (core.py)  
**Effort:** Small  
**Priority:** High

### IMP-080: Update platform Terms of Service with professional licensing disclaimer and state-specific notices

**Description:** Add to the YAK marketplace Terms of Service: (1) "YAK is a technology platform, not a licensed surveying firm. YAK does not provide professional land surveying services." (2) "Operators are solely responsible for ensuring their work complies with applicable state professional licensing laws. For topographic survey deliverables, a licensed Professional Land Surveyor must be in responsible charge in the project state." (3) Per-state disclosure for NY, NC, OR (highest risk): "Topographic survey work in [STATE] requires a Licensed Professional Land Surveyor." This is Tier 1 mitigation — necessary as a baseline even if Tier 2/3 are implemented.

**Module:** Legal / system  
**Effort:** Small  
**Priority:** Critical

### IMP-081: Legal memo — obtain CoA/firm license in Michigan, Ohio, North Carolina as Tier 3 mitigation

**Description:** Commission a legal memo from a licensed surveying firm attorney (or a compliance service like Harbor Compliance) to evaluate: (1) What is required for YAK to obtain a Certificate of Authorization as a surveying firm in MI, OH, and NC? (2) What PLS relationship is required (employee vs. advisory)? (3) Does YAK's current "platform fee" model constitute engaging in unlicensed practice in these states? (4) Cost estimate. This is the Tier 3 path and would be required before YAK operationalizes at scale in any of these markets.

**Module:** Legal / system  
**Effort:** Large  
**Priority:** Medium (required before commercial launch in these states)

---

## New Questions Spawned

- **R-048:** Certificate of Authorization (CoA) requirements for surveying firms in MI, OH, NC, NY — what do you need, what does it cost, and can a technology company qualify?
- **R-049:** "PLS in Responsible Charge" model — how do Aerotas and FlyGuys structure their subcontractor agreements? Is there a standard contract template for data-collector subcontracts that explicitly establishes PLS responsible charge?

---

## Sources

- [NY OPD FAQ: Professional Engineering & Land Surveying](https://www.op.nysed.gov/professions/engineering/frequently-asked-practice-questions)
- [NY OPD Land Surveying FAQ](https://www.op.nysed.gov/professions/land-surveying/frequently-asked-practice-questions-land-surveying)
- [360 Virtual Drone Services LLC v. Ritter, 102 F.4th 263 (4th Cir. 2024) — Justia](https://law.justia.com/cases/federal/appellate-courts/ca4/23-1472/23-1472-2024-05-20.html)
- [360 Virtual Drone — Institute for Justice case page](https://ij.org/case/north-carolina-drones/)
- [SCOTUS Docket No. 24-279](https://www.supremecourt.gov/DocketPDF/24/24-279/325478/20240909130956229_Petition.pdf)
- [FlyGuys — Why Certified Surveyors Are Still Essential](https://flyguys.com/why-certified-surveyors-are-still-essential-in-the-age-of-drone-surveying/)
- [FlyGuys — Drone Mapping Services for Surveyors](https://flyguys.com/drone-services/drone-mapping-services/)
- [ENR — State Engineering Boards Target Drone Photographers](https://www.enr.com/articles/51837-state-engineering-boards-target-drone-photographers-for-unlicensed-survey-work)
- [Ward and Smith — Navigating the Skies](https://www.wardandsmith.com/articles/navigating-the-skies-why-drone-land-surveys-may-violate-licensing-statutes-not-first-amendment-rights)
- [J. Rupprecht Law — Drone Mapping and Unlicensed Land Surveying](https://jrupprechtlaw.com/drone-mapping-and-unlicensed-land-surveying-lawsuit/)
- [CLEARHQ — Does Drone Surveying Require a License?](https://www.clearhq.org/news/court-case-does-drone-surveying-require-a-license)
- [Zeitview Terms of Use](https://www.zeitview.com/termsofuse)
- [Section 230 — Electronic Frontier Foundation](https://www.eff.org/issues/cda230)
- [Texas TREC — Referral Fees to Unlicensed Individuals](https://www.texasrealestate.com/members/posts/referral-fees-to-unlicensed-individuals/)
- [Harbor Compliance — Engineering Firm License Requirements (50 State)](https://www.harborcompliance.com/engineering-firm-license-certificate-of-authorization)
- [Zillow Real Estate Licenses](https://www.zillow.com/info/real-estate-licenses/)
- [NSPE — 2026 Professional Liability Trends](https://www.nspe.org/career-growth/pe-magazine/issue-3-2025/looking-ahead-2026-professional-liability-trends)
