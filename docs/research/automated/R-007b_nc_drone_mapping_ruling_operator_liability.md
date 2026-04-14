# R-007b: 2024 North Carolina Drone Mapping Court Ruling — Operator Liability Implications

**Date:** 2026-04-14  
**Topic ID:** R-007b  
**Module:** M36_pls_review  
**Depends on:** R-007 (Electronic survey seal regulations)  
**Researcher:** Automated daily research agent  

---

## Executive Summary

- **Case confirmed:** *360 Virtual Drone Services LLC v. Ritter*, 102 F.4th 263 (4th Cir. 2024, May 20) — a federal appeals court ruled that offering drone aerial-mapping services (orthomosaics, photogrammetric models, geo-referenced data) constitutes the "practice of surveying" in North Carolina and requires a PLS license. A SCOTUS petition (No. 24-279) is pending; supplemental briefing was filed December 2025 — no cert grant yet.

- **4th Circuit scope:** Directly binding in VA, WV, MD, NC, SC. Highly persuasive in other circuits given analogous state surveying statutes. At least 6 other drone companies received NC Board cease-and-desist letters; one has implications for states with similar "practice of surveying" statutory language.

- **"Data collector subcontractor" model is legally valid:** A licensed PLS can hire an unlicensed drone operator as a data collector, provided the PLS is "in responsible charge" of methodology, accuracy, and processing. Platforms like Aerotas and FlyGuys operate on exactly this model. This is the **viable operational path** for the YAK platform in the near term.

- **Codebase has three material gaps:** (1) `verify_operator()` in `compliance.py` requires `pls_license` for ALL task types even when not legally required; (2) no `pls_required` flag on task specs for topo-category tasks; (3) operator onboarding has no PLS-role declaration (licensed surveyor vs. data collector subcontractor).

- **Immediate platform risk:** Operators bidding on `topo_survey`, `corridor_survey`, `site_survey`, `control_survey`, `as_built`, and `aerial_survey` tasks without a PLS license — or without operating under a licensed PLS firm — are engaged in unlicensed practice of surveying in NC and likely other states. The platform currently has no gate or disclosure.

---

## Findings

### 1. Case Details: *360 Virtual Drone Services LLC v. Ritter*

**Citation:** 102 F.4th 263 (4th Cir. 2024)  
**Case No.:** 23-1472  
**Date decided:** May 20, 2024  
**Court:** United States Court of Appeals for the Fourth Circuit (Richmond, VA)  
**Parties:** Michael Jones / 360 Virtual Drone Services LLC (drone operator) vs. Andrew Ritter et al. (NC Board of Examiners for Engineers and Surveyors)

**What happened:** Michael Jones, FAA Part 107 certified, began offering aerial mapping services (orthomosaic composites, 3D models with geo-referenced measurable data) for construction companies and property owners. In December 2018, the NC Board initiated an investigation; in June 2019, issued a cease-and-desist. Jones sued in 2021 on First Amendment grounds. Both the district court and the 4th Circuit ruled for the Board.

**Holding:** The North Carolina Engineering and Land Surveying Act constitutes "a generally applicable licensing regime that restricts the practice of surveying to those licensed" and primarily regulates **conduct** rather than speech. The court applied intermediate scrutiny (not strict scrutiny), and the Act survived that test. Key: offering maps with measurable location data = practicing surveying, regardless of whether the tool is a drone rather than a total station.

**What the decision explicitly covers:**
- Orthomosaic aerial imagery for construction companies ✓ requires PLS
- Bird's-eye property images with geo-referenced data ✓ requires PLS
- Pure aerial photography without measurable location data ✗ does NOT require PLS (not addressed by this case but implicit in the statute)

**SCOTUS status:** Cert petition filed September 2024 (No. 24-279). Supplemental brief filed December 2025. The question presented: whether the 4th Circuit applied the correct First Amendment standard for occupational licensing laws. The Institute for Justice is counsel. **No cert grant as of April 2026.** If cert is granted, the case could limit state boards' ability to require PLS licensure for drone mapping — a favorable outcome for the industry. But the status quo (PLS required in NC-analogous states) governs until then.

**Sources:**  
- [Justia full opinion](https://law.justia.com/cases/federal/appellate-courts/ca4/23-1472/23-1472-2024-05-20.html)  
- [SCOTUS docket No. 24-279](https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/html/public/24-279.html)  
- [Institute for Justice case page](https://ij.org/case/north-carolina-drones/)  
- [SCOTUSblog](https://www.scotusblog.com/cases/case-files/360-virtual-drone-services-llc-v-ritter/)

---

### 2. Geographic Scope of Risk

#### States with documented enforcement or explicit UAS guidance:

| State | Agency | Status | Notes |
|-------|--------|--------|-------|
| **North Carolina** | NC Board of Examiners for Engineers and Surveyors | **Active enforcement** | 6+ cease & desist letters to drone companies (2018–2024); won in court; 4th Cir. affirmed |
| **Oregon** | OSBEELS (Oregon State Board of Examiners for Engineering and Land Surveying) | **Explicit UAS guidance published** | Published brochure: photogrammetric mapping, topographic mapping, volume computation, 3D mapping all require PLS license; cites civil and criminal penalties for unlicensed practice |
| **Virginia** | DPOR | **4th Circuit state** | Directly bound by *360 Virtual Drone*; surveying statutes analogous to NC |
| **Maryland** | DLLR | **4th Circuit state** | Same as Virginia |
| **West Virginia** | — | **4th Circuit state** | Same |

#### States with strong statutory frameworks and likely exposure (enforcement not confirmed at drone-specific level):

| State | Key Statute | Risk Level | Notes |
|-------|-------------|-----------|-------|
| **Michigan** | MCL 339.2001 et seq. (Occupational Code, Professional Surveyors) | Medium | "Practice of surveying" broadly defined; LARA administers; primary YAK market |
| **Ohio** | ORC Chapter 4733 | Medium-High | ODOT QL2 minimum + .dgn deliverables; OH Board has historically enforced |
| **Texas** | TBPELS; TX Occ. Code Ch. 1071 | Medium | TxDOT UAS Manual explicitly permits drone surveys *when performed by or under supervision of licensed surveyor*; TBPELS has broad "geomatics" definition |
| **California** | BPC § 8700 et seq. | Medium | Broad practice-of-surveying definition including "location, relocation, establishment...of any point" |
| **Illinois** | 225 ILCS 330 | Lower | One source notes IL may permit non-licensed delivery if product does not meet NSPS accuracy standards — a narrow carve-out |

#### Key principle across states:
The critical trigger is whether the drone output **conveys measurable location information** (contours, coordinates, property lines, volumes). Pure aerial photography without measurable data is not surveying in any state. This line exactly aligns with the YAK task categories below.

---

### 3. "PLS-as-a-Service" / Data Collector Subcontractor Model

This is the industry-accepted solution adopted by successful drone survey platforms:

**How it works:**
1. Licensed PLS firm contracts with the buyer (GC, DOT, owner)
2. PLS firm subcontracts the data acquisition (flight, point cloud capture) to a drone operator
3. Drone operator delivers raw data (LAS/LAZ, imagery, GCPs) to the PLS firm
4. PLS firm processes, QAs, certifies, and seals the final deliverable
5. PLS assumes "responsible charge" — supervises methodology, accuracy standards, processing workflow

**Legal basis:** The supervised data collector is NOT practicing surveying (they are collecting instrument data under direction). The licensed PLS who certifies the work IS practicing surveying. This mirrors how survey crews have worked for 100+ years — unlicensed rodmen/instrument operators supervised by a licensed surveyor.

**Supervision standard:** The PLS does NOT need to be physically present, but must:
- Define the methodology and accuracy requirements
- Verify GCP placement and accuracy
- Review and approve the data processing pipeline
- Apply their seal and signature to the final deliverable

**Platforms using this model:**
- **Aerotas:** "Aerotas only works with licensed surveyors or engineers. We are not a licensed land surveyor." — drone operator provides data acquisition; PLS firm processes and stamps.
- **FlyGuys:** Nationwide drone services for "surveyors and mappers" — positioning itself as a data acquisition subcontractor to PLS firms, not as a surveying entity.

**YAK implication:** The platform should support two distinct operator roles:
1. **Operator-as-PLS:** Operator holds a PLS license in the project state. They are the surveyor of record. They deliver sealed, stamped survey products.
2. **Operator-as-Data-Collector:** Operator is a licensed Part 107 drone pilot operating as a subcontractor under a named, licensed PLS firm. They deliver raw data (LAS, imagery, GCPs) to the PLS firm. The PLS firm is responsible for the sealed deliverable. The buyer (GC) must have a pre-existing or concurrent engagement with the PLS firm.

**Sources:**
- [Aerotas land surveying laws](https://www.aerotas.com/land-surveying-laws)
- [FlyGuys drone services for surveyors](https://flyguys.com/drone-services/drone-mapping-services/)
- [LIDAR Magazine: UAS Mapping - is a surveying license required?](https://lidarmag.com/2017/04/29/uas-mapping-is-a-surveying-license-required/)
- [QK Inc UAS & Land Surveying](https://www.qkinc.com/uncategorized/uav-uas-drones-and-land-surveying-do-i-really-need-a-land-surveyors-license-for-that/)
- [Ward and Smith legal analysis](https://www.wardandsmith.com/articles/navigating-the-skies-why-drone-land-surveys-may-violate-licensing-statutes-not-first-amendment-rights)

---

### 4. Task Categories That Trigger PLS Exposure

Based on the deliverable types and task descriptions, the following YAK task categories produce surveying deliverables that require PLS licensure in NC-analogous states:

| Task Category | Deliverables (typical) | PLS Required? | Risk Level |
|---------------|------------------------|---------------|-----------|
| `topo_survey` | LAS/LAZ, GeoTIFF, LandXML, DXF | **Yes** | High |
| `corridor_survey` | LAS/LAZ, GeoTIFF, cross-sections | **Yes** | High |
| `site_survey` | LAS/LAZ, GeoTIFF, DXF, LandXML | **Yes** | High |
| `control_survey` | CSV (GCPs), LandXML | **Yes** | High |
| `as_built` | LAS/LAZ, LandXML, IFC, DXF | **Yes** | High |
| `aerial_survey` | LAS/LAZ, GeoTIFF, orthomosaic | **Yes** | High |
| `progress_monitoring` | GeoTIFF, volumetrics | **Depends** | Medium (if volumes = sealed) |
| `volumetric` | CSV, GeoTIFF | **Depends** | Medium |
| `bridge_inspection` | PDF, GeoTIFF, thermal | **No** (inspection, not surveying) | Low |
| `subsurface_scan` | GeoPackage, SHP, GeoJSON | **No** | Low |
| `thermal_inspection` | PDF, GeoTIFF | **No** | Low |
| `environmental_survey` | PDF, GeoJSON | **No** | Low |
| `utility_detection` | GeoPackage, SHP | **No** | Low |

---

### 5. Current Codebase Gaps

#### Gap 1: `verify_operator()` in `compliance.py` (line 124)
```python
"compliant": verified_count == len(checklist),  # requires ALL 6 docs
```
This requires `pls_license` for ALL task types to achieve `compliant=True`. Non-topo operators (thermal, GPR, progress monitoring) will always appear non-compliant unless they hold a PLS license. This creates false negatives. Per R-027, `verify_operator()` needs task-type context.

#### Gap 2: No `pls_required` flag on task specs
`VALID_TASK_CATEGORIES` in `core.py` (lines 120–143) has no metadata indicating which categories legally require a PLS license. The auction engine has no pre-bid gate checking PLS status for survey tasks. An operator without a PLS license can bid on and win a `topo_survey` task today with no warning.

#### Gap 3: Operator registration has no PLS-role declaration
The 3-step operator registration UI (v1.4 milestone) collects profile, equipment, and payment info but does not ask: "Are you a licensed PLS, or do you operate as a data collector under PLS supervision?" This is the most operationally critical question for platform liability.

#### Gap 4: No platform T&C clause for unlicensed practice
`auction_generate_agreement()` at `mcp_tools.py:1751` references "PLS supervision" in the generated agreement, but this is in the subcontract — not in platform T&Cs that bind the operator at registration time.

---

## Implications for the Product

### Near-term (v1.5 / operator onboarding redesign)

1. **Add `pls_required` to task spec schema.** Survey task categories should carry a `pls_required: true` field. The rfp_processor should set this based on deliverable types and project state.

2. **Gate bid submission on PLS role declaration.** For `pls_required=true` tasks, require the operator to declare before bidding:
   - "I am a licensed PLS in [state]" → trigger pls_license doc upload/check
   - "I am a data collection subcontractor operating under PLS firm [name] [license#]" → require supervising PLS info
   
3. **Fix `verify_operator()` to be task-type-aware.** This was already noted in R-027 (IMP-065). The `compliant` flag should NOT penalize thermal/GPR operators for lacking a PLS license.

4. **Add platform T&C clause.** Operator registration should include an explicit acknowledgment: "For tasks requiring a PLS license in the project state, I certify I hold the required license or am operating as a data collector under a licensed PLS firm in responsible charge."

5. **Add `data_collector_subcontractor` operator role.** Let the platform position itself as a data acquisition marketplace, not a surveying practice. The platform facilitates the buyer-PLS relationship; operators collect data under PLS supervision.

### Medium-term (v1.6+)

6. **PLS verification at award time.** Before executing a `pls_required` task, the platform should check the operator's PLS status against LARA (Michigan), TBPELS (Texas), or other state APIs. See IMP-001/R-006 deferred items — the case for state-specific PLS checks is stronger now.

7. **Monitor SCOTUS cert grant.** If SCOTUS grants cert in *360 Virtual Drone v. Ritter* and narrows the First Amendment scope, the result could reduce state boards' enforcement authority. This could be favorable for the market. Monitor quarterly.

---

## Improvement Proposals

### IMP-072: Add `pls_required` flag to task spec and RFP processor

Add `pls_required: bool` and `pls_supervision_model: Literal["operator_is_pls", "operator_subcontracts_pls", "not_required"]` to the task spec schema. Set `pls_required=true` automatically for task categories `topo_survey`, `corridor_survey`, `site_survey`, `control_survey`, `as_built`, `aerial_survey`. The rfp_processor should populate this field based on task category and project state. The bid submission flow should surface this to the operator.

**Module:** M36_pls_review / M1_rfp_processor  
**Effort:** Small  
**Priority:** High  

### IMP-073: Pre-bid PLS role declaration gate for survey task categories

Before an operator submits a bid on a task where `pls_required=true`, require them to declare their PLS role: (a) licensed PLS in the project state (triggers pls_license doc check), or (b) data-collection subcontractor operating under a named PLS firm (requires PLS firm name and license number). Operators who cannot make either declaration should be blocked from bidding on that task category.

**Module:** M10_compliance / M5_auction_engine  
**Effort:** Medium  
**Priority:** High  

### IMP-074: Platform T&C operator certification clause for licensing compliance

Add an explicit acknowledgment clause to operator registration: "For tasks requiring a Professional Land Surveyor (PLS) license in the project state, I certify I hold the required license or am operating as a data-collection subcontractor under a licensed PLS firm in responsible charge. I acknowledge that the platform is not responsible for my compliance with state occupational licensing laws and that violations may result in civil or criminal penalties." This shifts liability to the operator and protects the platform as an intermediary facilitating a data-acquisition subcontract.

**Module:** M10_compliance  
**Effort:** Small  
**Priority:** High  

### IMP-075: Operator profile — "Survey Role" field and `data_collector_subcontractor` role

In the operator registration UI (Step 1 — Profile), add a "Survey Role" field for operators who select survey-related task categories: (a) Licensed PLS, (b) Data Collection Subcontractor (under PLS supervision), or (c) Not bidding on licensed-survey tasks. If "Data Collection Subcontractor": collect the supervising PLS firm name, state, and license number. Store on `OperatorProfile`. Used by bid gating (IMP-073) and agreement generation to correctly populate the "PLS supervision" clause.

**Module:** M10_compliance  
**Effort:** Small  
**Priority:** Medium  

---

## New Research Questions Spawned

### R-045: State surveying board platform-intermediary liability

**Hypothesis:** The NC Board targeted the drone operator directly. But if YAK is facilitating transactions where unlicensed operators deliver sealed survey products, could the platform itself face enforcement action as an "aider and abettor" of unlicensed practice? Research: (1) Has any state board pursued a marketplace/platform rather than (or in addition to) the individual operator? (2) Does the INFORM Act or state analogs create disclosure obligations? (3) What legal shield does "facilitating data acquisition subcontracts" provide vs. "providing surveying services"?

### R-046: ASPRS Certified Photogrammetrist (CP) as an operator credential alternative

**Hypothesis:** ASPRS offers a Certified Photogrammetrist credential that requires demonstrated UAS mapping competency and exam. Some clients and states accept CP as evidence of professional competency for non-boundary survey deliverables (progress monitoring, volumetrics, orthomosaics). Research: (1) Is ASPRS CP accepted by any state DOT as a qualification for drone survey subcontracting? (2) Does CP reduce E&O insurance premiums for operators? (3) Should YAK support "ASPRS CP" as a compliance document type?

---

## Summary Table

| Question | Answer |
|----------|--------|
| Exact case citation | *360 Virtual Drone Services LLC v. Ritter*, 102 F.4th 263 (4th Cir. 2024) |
| Which circuit? | 4th (VA, WV, MD, NC, SC) |
| SCOTUS status? | Petition pending (No. 24-279); no cert grant as of Apr 2026 |
| Other states with explicit enforcement | Oregon (OSBEELS guidance), plus likely OH, TX, CA, MI via statute |
| Does current T&Cs shift liability? | No — no current platform T&C clause covers this |
| Is "data collector under PLS" model valid? | Yes — industry-standard, used by Aerotas, FlyGuys |
| Does onboarding need PLS disclosure? | Yes — for topo/LiDAR/site survey categories |
| Codebase gaps | `pls_required` flag missing; `verify_operator()` task-type unaware; no PLS role declaration |
| New proposals | IMP-072, IMP-073, IMP-074, IMP-075 |
| New topics | R-045, R-046 |
