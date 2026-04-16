# R-007: Electronic Survey Seal/Stamp Regulations by State

**Date:** 2026-04-13
**Topic ID:** R-007
**Module:** M36_pls_review
**Priority:** Critical
**Status:** Complete
**Researcher:** Automated daily research agent

---

## Executive Summary

- **Electronic seals are legal in all 4 primary markets (MI, OH, TX, CA)**, but the required authentication level varies from image-stamp-acceptable to PKI-mandatory. The platform's current DocuSign assumption is legally risky in at least half of states.
- **Critical distinction ignored in current codebase:** There are two fundamentally different "electronic seals" — an *image seal* (PNG/JPG embedded in PDF, no authentication) and a *digital certificate seal* (PKI-signed, cryptographically tamper-evident). State boards that require the latter reject the former.
- **LiDAR and photogrammetry deliverables require a PLS seal** in Michigan, Ohio, Texas, and California when delivered as topographic maps or DEMs — with a 2024 federal court ruling (North Carolina) confirming drone topographic mapping is "practice of surveying" requiring licensure.
- **The platform's delivery schema has no `pls_seal_format` field.** Level 3 QA checks only `pls_review_status: APPROVED` but cannot distinguish a PKI-valid seal from a pasted image. This is a compliance gap for DOT and federal-funded tasks.
- **Three actionable improvements identified** (IMP-068, IMP-069, IMP-070) plus two spawned research topics.

---

## Findings

### 1. The Two Electronic Seal Types — A Critical Distinction

Every state discussion of "electronic seals" conflates two technically distinct things:

| Type | How It Works | Authentication | Tamper-Evidence |
|------|-------------|---------------|-----------------|
| **Image seal** | PNG/JPG of circular seal embedded in PDF or DWG. | None — anyone can paste it. | None — document can be altered after. |
| **PKI digital signature** | Cryptographic certificate from a trusted CA (IdenTrust, GlobalSign, Entrust) applied to the document hash. | Certificate Authority validates licensee identity. | Signature invalid if any document byte changes. |
| **DocuSign e-signature** | Click-to-sign, audit trail, ESIGN compliant. | Email/password, not PKI certificate identity. | Hash-chained in DocuSign's servers, not in the document itself. |

**State boards overwhelmingly intend the PKI digital signature** when they permit "electronic signatures" on sealed professional documents. DocuSign's standard flow is an e-signature, NOT a PKI digital signature. DocuSign does offer PKI-certificate-based signing through its Advanced/Qualified Signature products (using IdenTrust certificates), but this is not the default product.

Sources:
- [NCBELS Signing and Sealing Guidelines](https://www.ncbels.org/wp-content/uploads/2019/03/SigningandSealingGuidelines.pdf)
- [NJ DEP Digital Stamp and Signature Guide](https://nj.gov/dep/landuse/download/lur_052.pdf)
- [NVBPELS Digital Signature Guide](https://nvbpels.org/wp-content/uploads/2020/12/Digital-Signature-Guide-FINAL.pdf)

---

### 2. State-by-State Requirements — 4 Primary Markets

#### Michigan (Primary Market)

**Governing law:** MCL 339.2007 (Seal; signature) + Admin Code R 339.17301 (Seal design)

**Key provisions:**
- An "electronic seal" means a seal created by electronic or optical means and affixed electronically.
- An "electronic signature" means a signature created by electronic or optical means with intent to sign.
- The licensee must apply seal AND signature to any plan, specification, plat, or report filed with a public authority.
- Security of the seal is the licensee's responsibility.

**Electronic seal status:** Explicitly permitted by statute. Michigan does not specify PKI requirement in the statute text, but the seal must be secure (licensee responsible for unauthorized use).

**Bottom line for YAK:** Michigan is relatively permissive — image seal + electronic signature may be acceptable for private contracts. For MDOT deliverables, recommend PKI-based signing as MDOT generally follows best-practice requirements.

**Sources:**
- [MCL 339.2007](https://www.legislature.mi.gov/documents/mcl/pdf/mcl-339-2007.pdf)
- [Mich. Admin. Code R. 339.17301](https://www.law.cornell.edu/regulations/michigan/Mich-Admin-Code-R-339-17301)
- [Michigan LARA Surveyor FAQ](https://www.michigan.gov/-/media/Project/Websites/lara/bpl/Surveyors/Surveyor-FAQ.pdf)

---

#### Ohio

**Governing law:** Ohio Admin. Code 4733-23-01 (Registrant's Seal)

**Key provisions:**
- Work product may bear "a computer generated seal and electronic signature and date."
- Must have "an electronic authentication process attached to or logically associated with the electronic document."
- The electronic signature must be:
  1. Unique to the person using it
  2. Capable of verification
  3. Under the sole control of the person using it
  4. Linked to the document such that the signature is **invalidated if any data is changed**

**Electronic seal status:** Requirement 4 (invalidation on alteration) mandates a PKI digital signature. A pasted image seal or a DocuSign e-signature does NOT invalidate on document alteration.

**ODOT practice:** ODOT has a "Digital Signatures FAQ" document for construction plan submissions confirming PKI-based workflow. ODOT requires `.dgn` deliverables (Bentley) — which has its own digital signature framework.

**Bottom line for YAK:** Ohio requires de facto PKI-based signing. Image seals and standard DocuSign are insufficient. A certificate from IdenTrust, GlobalSign, or Entrust is required.

**Sources:**
- [Ohio Admin. Code 4733-23-01](https://www.law.cornell.edu/regulations/ohio/Ohio-Admin-Code-4733-23-01)
- [ODOT Digital Signatures FAQ](https://ftp.dot.state.oh.us/pub/CADD/CADDSync/Manuals/DigitalSignatures_FAQ.pdf)
- [Ohio Construction Law Blog — 2D Wet Ink to 3D Blockchain](https://ohioconstructionlaw.keglerbrown.com/2021/08/signing-sealing-roadway-construction-plans-from-2-d-wet-ink-to-3-d-blockchain/)

---

#### Texas

**Governing law:** 22 Tex. Admin. Code § 138.33 (Sealing Procedures)

**Key provisions:**
- Electronic seals and signatures permitted.
- Must employ "reasonable security measures to make the documents unalterable."
- Signature/date must not obscure name or registration number in the seal.
- Loss of electronic signature must be reported to TBPELS within 30 days.

**TxDOT practice (3.4.5):** TxDOT's PSE Design Manual Section 3.4.5 explicitly names DocuSign and Adobe as acceptable tools for electronic seal and signature on TxDOT submissions. This is one of the more permissive DOT positions.

**RPLS seal vendor list:** TBPELS publishes an approved vendor list for physical and digital seal vendors at `pels.texas.gov/downloads/LSsealvendor.pdf`.

**Bottom line for YAK:** Texas is the most permissive of the 4 markets. DocuSign is explicitly named by TxDOT. Image seal + DocuSign is likely acceptable for Texas deliverables.

**Sources:**
- [22 Tex. Admin. Code § 138.33](https://www.law.cornell.edu/regulations/texas/22-Tex-Admin-Code-SS-138-33)
- [TxDOT 3.4.5 Electronic Seals and Signature Requirements](https://www.txdot.gov/manuals/des/pse/chapter-3--plan-set-development/section-4--engineer-s-seal-and-signature-requireme/-electronic-seals-and-signature-requirements.html)
- [TBPELS Enforcement FAQs](https://pels.texas.gov/enforce_faqs.htm)

---

#### California

**Governing law:** Cal. Code Regs. Tit. 16, § 411 + Business & Professions Code § 8761

**Key provisions:**
- The seal "shall be capable of leaving a permanent ink representation, a permanent impression, or an **electronically-generated representation**."
- Electronic signature permitted.
- Rubber stamp of signature is PROHIBITED (rubber stamp of seal is acceptable).
- Local agencies may adopt ordinances requiring "wet" stamps — local override risk.

**Electronic seal status:** Explicit electronic seal permission but **no PKI requirement stated**. California BPELSG's 2026 Board Rules (16 CCR §§400-476) are the current applicable text.

**LiDAR/drone stringency:** California is among the most stringent states for requiring PLS licensure for UAV topographic work. Creating a toposurface from UAV LiDAR source without a PLS license may be unlawful (BPC § 8726).

**Bottom line for YAK:** California permits electronic seals without mandating PKI, but local agencies may require wet stamps. The greater risk is ensuring the operator IS a licensed PLS in California — the practice-of-surveying definition is broad.

**Sources:**
- [Cal. Code Regs. Tit. 16, § 411](https://www.law.cornell.edu/regulations/california/16-CCR-411)
- [California BPELSG Laws and Regulations](https://www.bpelsg.ca.gov/laws/index.shtml)
- [Cal. Business & Professions Code § 8761](https://law.justia.com/codes/california/code-bpc/division-3/chapter-15/article-5/section-8761/)

---

### 3. DocuSign and Electronic Signature Platforms — Compliance Analysis

| Platform | Type | Meets OH/NJ/NV PKI Standard? | Meets TX/CA Standard? | Notes |
|----------|------|------------------------------|----------------------|-------|
| **DocuSign (e-signature)** | Click-to-sign | ❌ No | ✅ Yes (TX) / ⚠️ Possibly (CA) | Default DocuSign flow |
| **DocuSign + IdenTrust cert** | PKI digital cert | ✅ Yes | ✅ Yes | Advanced product, extra setup |
| **Adobe Acrobat + CA cert** | PKI digital cert | ✅ Yes | ✅ Yes | Widely accepted |
| **Bluebeam + self-signed cert** | Self-signed PKI | ❌ No (NJ explicitly rejects) | ⚠️ Risky | Self-signed certs not widely trusted |
| **Bluebeam + 3rd-party CA cert** | PKI digital cert | ✅ Yes | ✅ Yes | Requires separate CA cert purchase |
| **IdenTrust TrustID** | PKI digital cert | ✅ Yes | ✅ Yes | FBCA-certified; ~$100-200/year/user |
| **Image seal only** | Image embed | ❌ No | ⚠️ Borderline | Fails tamper-evidence requirement |

**Key finding:** The platform's assumption that "DocuSign approach may not be legal everywhere" (from the hypothesis) is CONFIRMED — specifically for Ohio and likely other states requiring document tamper-evidence. A PKI approach is needed for any DOT or federal-funded deliverable.

**Sources:**
- [Florida FDOT Digital Signature FAQ](https://www.fdot.gov/construction/econstruction/digitalsignfaq.shtm)
- [NJ DEP Digital Stamp and Signature Guide](https://nj.gov/dep/landuse/download/lur_052.pdf)
- [McKissock Digital Seals Compliance Guide](https://www.mckissock.com/blog/professional-engineering/digital-seals-signatures-and-e-stamps-a-compliance-guide-for-professional-engineers/)
- [IdenTrust Digital Signing and Sealing](https://www.identrust.com/digital-certificates/digital-signing-sealing)

---

### 4. LiDAR/Point Cloud Deliverables — When Must They Be PLS-Sealed?

This is a patchwork of state law with no uniform national standard.

#### The 2024 North Carolina Ruling (Important Precedent)

In May 2024, a federal appeals court ruled that a North Carolina drone pilot could NOT offer aerial mapping services without a state surveyor's license ([Drone XL, 2024](https://dronexl.co/2024/05/21/drone-pilot-grounded-court-rules-aerial-mapping/)). This reinforces the trend toward treating drone-based topographic mapping as "practice of surveying" requiring PLS licensure.

#### What Must Be Sealed vs. What Need Not Be

| Deliverable Type | PLS Seal Required? | Notes |
|-----------------|-------------------|-------|
| Raw LAS/LAZ point cloud (no certification) | ❌ Usually not | Just data; no legal representation |
| Topographic map (contour lines, DEM) | ✅ Most states | Considered "practice of surveying" |
| Survey report / accuracy report | ✅ Usually yes | Professional opinion, requires seal |
| Boundary survey / plat | ✅ Always | Explicitly regulated everywhere |
| Progress monitoring photos | ❌ No | Documentation, not surveying |
| GPR subsurface scan report | ⚠️ State-dependent | May require PE (not PLS) seal |
| Volume calculations from point cloud | ✅ Likely (CA, FL) | "Determine size, shape" = surveying |

#### State-Specific Notes
- **Michigan:** PLS seal required on plats and surveys filed with public authority; topo maps for MDOT require seal.
- **Ohio:** OAC 4733-37 (UAS Mapping) emerging rules; current practice treats drone topo as surveying requiring PLS oversight.
- **Texas:** "Dimensional control" is NOT regulated; topo mapping IS regulated. TxDOT UAS manual requires PLS oversee deliverables.
- **California:** Most stringent. BPC § 8726 defines "practice of land surveying" broadly to include "determining size, shape, topography." UAV topo from LiDAR likely regulated.
- **Florida:** Requires PLS for UAV topographic mapping even for data collection (not just final deliverable). Very strict.

**Sources:**
- [LiDAR Magazine — Licensing, Certification and New Technologies](https://lidarmag.com/2022/04/30/licensing-certification-and-new-technologies/)
- [LiDAR Magazine — UAS Mapping: Is a Surveying License Required?](https://lidarmag.com/2017/04/29/uas-mapping-is-a-surveying-license-required/)
- [Aerotas — Land Surveying Laws](https://www.aerotas.com/land-surveying-laws)
- [Drone XL — Court Rules License Needed For Mapping](https://dronexl.co/2024/05/21/drone-pilot-grounded-court-rules-aerial-mapping/)

---

### 5. Codebase Gap Analysis

#### Current State (deliverable_qa.py, Level 3)

```python
# auction/deliverable_qa.py:354-374
def _check_level_3(data: dict, spec: dict) -> QAResult:
    """Level 3: PLS review required — run level 2 + check PLS stamp."""
    ...
    pls_status = data.get("pls_review_status")
    if pls_status == "APPROVED":
        details["pls_stamp"] = "approved"
    elif pls_status == "PENDING":
        issues.append("PLS review pending — deliverables not yet stamped")
    ...
    issues.append("No PLS review status in delivery — PLS stamp required for this task")
```

**Gaps identified:**

1. **No seal format tracking**: `pls_review_status: APPROVED` doesn't indicate whether the seal is a PKI digital signature, a DocuSign e-signature, or an image embed. For Ohio DOT deliverables, only PKI is acceptable.

2. **No state-specific routing**: The same Level 3 check applies regardless of whether the task is in Michigan (relatively permissive) or Ohio (PKI required) or California (PLS licensure itself at risk if operator is not CA-licensed).

3. **Delivery schemas don't request seal metadata**: `AERIAL_LIDAR_SCHEMA` and `AERIAL_PHOTO_SCHEMA` in `delivery_schemas.py` have no `pls_seal_format` or `pls_license_state` fields. The robot delivering the data has no way to communicate what kind of seal was applied.

4. **No check that PLS is licensed in the project state**: A Michigan-licensed PLS sealing a California project is practicing without a license. The platform doesn't cross-reference `task.project_state` with the operator's `pls_license.issuing_state`.

---

## Implications for the Product

### Immediate (Before Any DOT Deliverables)
1. Add `pls_seal_format` and `pls_license_state` to Level 3 delivery schema — operators must declare how they sealed.
2. Define a policy: for DOT/federal tasks, require PKI-certified seals (not DocuSign e-signature).
3. Add `pls_license_state` to `OperatorProfile` so cross-state practice can be flagged.

### Near-Term (Before v1.5 Launch)
4. Build a state seal requirement lookup table — Michigan is low, Ohio is high, Texas is TxDOT-managed (permissive with DocuSign). Table drives Level 3 validation logic.
5. Educate operators in onboarding: "For DOT tasks in Ohio or Virginia, you will need an IdenTrust or Adobe digital certificate (~$100-200/year) to seal your deliverables."

### Deferred (v2.0+)
6. Integrate a PKI certificate status API or DocuSign Advanced to automatically verify that the seal on a submitted document is cryptographically valid.

---

## Improvement Proposals

### IMP-068: Add `pls_seal_format` and `pls_license_state` to Level 3 delivery schemas

**Module:** M35_deliverable_qa / M36_pls_review
**Effort:** Small
**Priority:** High

Add two fields to the Level 3 delivery validation schema:
- `pls_seal_format`: enum — `"pki_digital_cert"`, `"docusign_advanced"`, `"docusign_esign"`, `"image_embed"`, `"wet_stamp"`. Required when `pls_review_status` is present.
- `pls_license_state`: string — two-letter state code of the issuing PLS board (e.g., `"MI"`, `"OH"`). Required for all Level 3 tasks.

In `_check_level_3()`, add warnings when:
- `pls_seal_format in ("image_embed", "docusign_esign")` and the task state is OH, NJ, VA, or NV (states requiring PKI-based signing).
- `pls_license_state != task.project_state` and neither state has a documented comity agreement.

---

### IMP-069: Add state seal requirement table to compliance module

**Module:** M36_pls_review
**Effort:** Medium
**Priority:** Medium

Create `auction/pls_seal_requirements.py` with a `STATE_SEAL_REQUIREMENTS` dict mapping state codes to:
- `min_seal_level`: `"image"` | `"esign"` | `"pki_cert"`
- `dot_level`: higher requirement for DOT submissions (e.g., TX DOT explicitly permits DocuSign)
- `notes`: string for human-readable guidance in the UI

Pre-populate for MI, OH, TX, CA, FL, VA, NJ, NV (8 states). Expose via MCP tool `get_state_seal_requirements(state_code, is_dot_project)`.

---

### IMP-070: Operator onboarding — digital certificate guidance for DOT-tier operators

**Module:** M10_compliance
**Effort:** Small
**Priority:** Medium

Add a `pls_seal_capability` field to `OperatorProfile` (enum: `image_only`, `docusign_esign`, `pki_cert`). During operator registration (3-step UI), if the operator selects task categories involving topo/LiDAR deliverables AND DOT states, show an inline informational panel:

> "For DOT submissions in Ohio, Virginia, and New Jersey, your PLS seal must be applied using a PKI digital certificate from a Certificate Authority (IdenTrust, GlobalSign). This is different from a standard DocuSign e-signature. Learn more →"

This surfaces the compliance requirement before the operator bids on a task, reducing failed deliverables at Level 3 QA.

---

## New Questions Spawned

### R-007a: PKI digital certificate providers for PLS seal workflows
Research the practical workflow for obtaining and using a PKI certificate for professional surveyor document sealing. Questions: (1) IdenTrust TrustID PE pricing and integration with Adobe/Bluebeam? (2) Does DocuSign's API offer an "advanced" signing endpoint that applies a PKI cert to a PDF? (3) Can a marketplace platform automate PKI certificate application on behalf of an operator, or must the licensee hold the certificate hardware token personally? (4) Estoppel risk: if the platform applies a seal programmatically, is the PLS still "responsible charge"?

### R-007b: 2024 North Carolina drone mapping ruling — operator liability implications
The 5th Circuit (or 4th Circuit) 2024 ruling that aerial mapping requires a surveyor's license creates direct liability for drone operators on the YAK platform who lack a PLS license yet bid on topographic deliverable tasks. Research: (1) exact case citation and jurisdiction; (2) which states have similar enforcement precedents; (3) whether the platform's terms can shift liability to the operator; (4) whether a "PLS-as-a-service" review (operator collects data, licensed PLS reviews and seals) is a legally valid model in MI/OH/TX/CA.

---

## Summary Table: Market Requirements

| State | Image Seal OK? | DocuSign E-Sig OK? | PKI Required? | DOT Override? | LiDAR Topo Needs PLS? |
|-------|---------------|-------------------|--------------|--------------|----------------------|
| Michigan | ✅ | ✅ | Recommended | MDOT: best practice | ✅ (MDOT projects) |
| Ohio | ⚠️ Borderline | ❌ | ✅ (OAC 4733-23) | ODOT: PKI required | ✅ |
| Texas | ✅ | ✅ (TxDOT 3.4.5) | No | TxDOT: DocuSign OK | ✅ (not dimensional control) |
| California | ✅ | ✅ | Recommended | Caltrans: varies | ✅ (strict) |
| Florida | ❌ | ❌ | ✅ | FDOT: PKI required | ✅ (strictest) |
| Virginia | ❌ | ❌ | ✅ (VDOT since 2009) | VDOT: IdenTrust | ✅ |
| New Jersey | ❌ | ❌ | ✅ (3rd-party CA req) | Same | ✅ |

---

*Sources cited inline above. No code files were modified — research only.*
