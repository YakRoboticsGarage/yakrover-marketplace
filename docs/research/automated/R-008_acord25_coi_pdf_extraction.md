# R-008: ACORD 25 COI PDF Field Extraction Methods

**Date:** 2026-04-22  
**Topic ID:** R-008  
**Module:** M10_compliance  
**Priority:** critical (downgraded to high in roadmap — retained as critical due to production impact)  
**Researcher:** Daily research agent  

---

## Executive Summary

- The current `upload_document()` in `compliance.py` marks every COI as `VERIFIED` on upload with zero field extraction — coverage limits, expiration dates, named insured, and additional insured status are never validated.
- **COI ParseAPI** (`coiparseapi.com`) is the best near-term integration: purpose-built REST API, pdfplumber for digital PDFs + Claude Vision fallback for scanned ones, $0.10–$0.15/parse, 50 free parses, 3-second response time, returns structured JSON covering all ACORD 25 fields.
- **Sensible.so** is the best alternative for higher customization (SenseML extraction templates), per-document pricing, handles both ACORD 25 2010/05 and 2016/03 variants.
- Drone survey operators need CGL ≥ $1M/$2M (each occ/aggregate), Workers' Comp statutory, and DOT tasks often require $5M+ umbrella — none of these thresholds are currently enforced.
- Four improvement proposals follow: extraction API integration (IMP-105), coverage limit validation (IMP-106), expiration auto-detection (IMP-107), and additional insured / description-of-operations checks (IMP-108).

---

## 1. ACORD 25 Form Structure and Key Fields

ACORD 25 is the standard Certificate of Liability Insurance used across all US construction markets. Two versions are in active use: **2010/05** and **2016/03** (current). They are structurally identical.

### 1.1 Field Layout (all extraction-relevant fields)

**Producer block:**
- `producer_name`, `producer_address`, `producer_contact`, `producer_phone`, `producer_fax`, `producer_email`

**Insured block:**
- `named_insured` — legal entity name (critical: must match operator record)
- `insured_address`

**Commercial General Liability (CGL):**
- `cgl_occurrence` (checkbox: Occurrence vs Claims-Made)
- `cgl_policy_number`, `cgl_effective_date`, `cgl_expiration_date`
- `cgl_each_occurrence` — per-occurrence limit (target: ≥ $1,000,000)
- `cgl_damage_to_rented_premises`
- `cgl_med_exp`
- `cgl_personal_adv_injury`
- `cgl_general_aggregate` — total policy limit (target: ≥ $2,000,000)
- `cgl_products_completed_ops_aggregate`
- `cgl_per_project` (checkbox) — aggregate applies per project vs per policy

**Automobile Liability:**
- `auto_combined_single_limit`
- `auto_effective_date`, `auto_expiration_date`
- `auto_owned`, `auto_hired`, `auto_non_owned` (checkboxes)

**Workers' Compensation and Employers' Liability:**
- `wc_statutory` (checkbox)
- `wc_el_each_accident`, `wc_el_disease_per_policy`, `wc_el_disease_per_employee`
- `wc_effective_date`, `wc_expiration_date`

**Umbrella/Excess Liability:**
- `umbrella_each_occurrence`, `umbrella_aggregate`
- `umbrella_effective_date`, `umbrella_expiration_date`

**Certificate Holder:**
- `certificate_holder_name`, `certificate_holder_address`
- `additional_insured` (checkbox)
- `subrogation_waived` (checkbox)

**Description of Operations:**
- `description_of_operations` — free text (critical for drone/UAS scope verification)

**Key signals for drone operators:**
- Description should mention "drone", "UAS", "aerial", or "unmanned aircraft" — otherwise the policy may not cover UAS operations.
- Additional insured checkbox must be ticked if the marketplace (or the GC) requires AI status.

---

## 2. Extraction Methods

### 2.1 Tier 1 — Native PDF Form Fields (best case, zero cost)

Many ACORD 25 PDFs are generated from agency management software (Applied Epic, AMS360, Vertafore) as fillable forms with named PDF form fields. `pypdf` or `pdfplumber` can extract these directly:

```python
import pypdf

with open("acord25.pdf", "rb") as f:
    reader = pypdf.PdfReader(f)
    fields = reader.get_form_text_fields()
    # Returns dict of field_name → value
```

**Reliability:** Very high for digitally-generated PDFs. Field names vary by software vendor but follow ACORD naming conventions. No AI required. Zero marginal cost.

**Limitation:** Scanned/photographed PDFs have no form fields — fallback to Tier 2/3 required.

### 2.2 Tier 2 — Layout-Aware Text Extraction (digital PDFs, no form fields)

`pdfplumber` preserves spatial positioning of text, enabling anchor-based extraction:

```python
import pdfplumber, re

with pdfplumber.open("acord25.pdf") as pdf:
    page = pdf.pages[0]
    text = page.extract_text(layout=True)
    # Regex: find "EACH OCCURRENCE" then capture dollar amount on same line
    each_occ = re.search(r"EACH OCCURRENCE\s+\$\s*([\d,]+)", text)
```

**Reliability:** High for well-formatted digital PDFs. Brittle if insurer uses non-standard layout.

**Libraries:** `pdfplumber` (pip, MIT, maintained 2026). No C++ dependencies.

### 2.3 Tier 3 — Vision LLM (scanned/low-quality PDFs)

Pass a rendered PNG of the PDF page to Claude Sonnet / GPT-4o with a structured extraction prompt. Returns JSON with all coverage fields.

COI ParseAPI uses this exact approach: pdfplumber first, Claude Vision fallback.

**Reliability:** ~95%+ for clearly photographed COIs. Main risk: hallucinated coverage amounts. Always validate returned numbers are plausible (e.g., limits are multiples of $100K).

**Cost:** ~$0.01–$0.05/document for Claude Sonnet vision (token count ~2K prompt + 1K image).

---

## 3. Commercial API Services

### 3.1 COI ParseAPI — **Recommended Near-Term Integration**

- **URL:** https://coiparseapi.com/
- **What it does:** Purpose-built REST API. Submit a COI PDF (base64 or URL), get back structured JSON. Supports ACORD 25 and ACORD 28.
- **Architecture:** pdfplumber for clean digital PDFs; Claude Vision AI fallback for scanned/low-quality.
- **Fields returned:** Named insured, all coverage types, policy numbers, effective/expiration dates, limits (each occurrence, aggregate), additional insured flag, subrogation waived, description of operations.
- **Pricing:** 50 free parses (no credit card); $0.10–$0.15/parse at 10K+/month.
- **Speed:** ~3 seconds per document.
- **Construction fit:** Explicitly designed for subcontractor COI verification; references Procore integration.
- **Compliance scoring:** Returns a compliance score against configurable requirements.

**Integration sketch (worker/src/index.js or auction/compliance.py):**
```python
import httpx

async def extract_coi_fields(pdf_bytes: bytes, api_key: str) -> dict:
    resp = await httpx.AsyncClient().post(
        "https://api.coiparseapi.com/v1/parse",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("coi.pdf", pdf_bytes, "application/pdf")},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()  # structured coverage fields
```

### 3.2 Sensible.so — **Best for Custom Field Configuration**

- **URL:** https://www.sensible.so/blog/extracting-data-from-certificates-of-insurance
- **What it does:** Developer-first document extraction API with pre-built ACORD 25 template. Handles both 2010/05 and 2016/03 variants.
- **Key advantage:** SenseML lets you define custom extraction logic — useful if we need to handle state-specific ACORD variants or non-standard carrier layouts.
- **Pricing:** Per-document, transparent (see sensible.so/pricing — not scraped in this session; requires direct inquiry).
- **Fit:** Higher engineering setup overhead vs COI ParseAPI but more controllable.

### 3.3 Regure — **Best for Compliance Workflow**

- **URL:** https://www.getregure.com/documents/acord-25/
- **What it does:** ACORD 25 extraction + validation against contract requirements + expiration flagging + searchable database + automated renewal alerts.
- **Fit:** More of an operational platform than a raw API. Overkill for v1.x but relevant for v2.0+ when managing hundreds of operators.

### 3.4 Other Options (lower priority)

| Service | Notes |
|---------|-------|
| Base64.ai | 500+ doc types, general-purpose, not construction-specific |
| Docsumo | ACORD 25/26/125/126, enterprise pricing |
| ScanDocFlow | Acord 25 OCR API, 99% accuracy claim, 15s, 80% cost reduction |
| UiPath Document Understanding | Extracts 77 fields, enterprise RPA — too heavy for our stack |

---

## 4. Coverage Thresholds for Construction Drone Survey Operators

The FAA does not mandate drone insurance (except Minnesota). However, **clients and DOTs require it as a contract condition.** Typical requirements:

| Coverage Type | Standard Construction | DOT/Government Work |
|---|---|---|
| CGL Each Occurrence | $1,000,000 | $2,000,000–$5,000,000 |
| CGL General Aggregate | $2,000,000 | $4,000,000–$10,000,000 |
| Workers' Comp | Statutory (or documented exemption) | Statutory |
| Umbrella/Excess | $1,000,000 | $5,000,000+ |
| Auto Liability | $1,000,000 CSL | $1,000,000 CSL |

**Sole proprietor exemption:** Many drone operators have no employees and may be Workers' Comp exempt. This must be explicitly confirmed (not assumed) — the COI should state "Statutory" with the exemption noted, or a separate WC exemption certificate provided.

**Description of operations check:** If the COI's description of operations does not mention "drone", "UAS", "unmanned aircraft", or "aerial services", the GL policy may not cover drone operations — this is a material gap that should be flagged.

---

## 5. Current Codebase Gap Analysis

**File:** `auction/compliance.py`, `ComplianceChecker.upload_document()` (line ~57)

**Current behavior:**
```python
record = ComplianceRecord(
    ...
    status="VERIFIED",   # ← always VERIFIED on upload
    details={"content_length": len(content), "uploaded": True},  # ← no fields
)
```

**Gaps:**
1. No PDF field extraction — coverage limits, expiration dates, named insured never read.
2. `expires_at` must be provided manually by the caller — not auto-extracted from the PDF.
3. No validation of coverage limits against task type thresholds.
4. No additional insured check.
5. No description-of-operations check for UAS/drone scope.
6. A corrupted or blank PDF would pass as `VERIFIED`.
7. A $100K CGL policy would pass as `VERIFIED` as readily as a $5M one.

**Sample cert exists:** `data/sample_certs/insurance_coi_acord25.pdf` — can be used as test fixture.

---

## 6. Recommended Implementation Path

### Phase 1 (v1.5, small effort): PDF form field extraction (Tier 1)

Add `_extract_acord25_fields(pdf_bytes)` to `compliance.py` using `pypdf` form field extraction. Store extracted fields in `ComplianceRecord.details`. No external API needed. Handles ~70% of real-world COIs (digitally generated).

### Phase 2 (v1.5, medium effort): COI ParseAPI integration

Call COI ParseAPI for documents that don't have form fields (Tier 1 fallback). Gate behind `COI_PARSE_API_KEY` env var. Store full extracted JSON in `ComplianceRecord.details`. Add `coi_extraction_method: "form_fields" | "coi_parseapi" | "manual"` to the record.

### Phase 3 (v1.5, medium effort): Coverage limit validation

After extraction, validate extracted limits against task-type thresholds. Store `coverage_check: {passed: bool, gaps: [...]}` in `ComplianceRecord.details`. Surface gaps in `verify_operator()` output. Block task assignment if hard limits not met.

---

## 7. Improvement Proposals

### IMP-105: Integrate COI ParseAPI for automated ACORD 25 field extraction

- **Module:** M10_compliance
- **Effort:** medium
- **Description:** Replace the stub `upload_document()` with actual field extraction. When `doc_type == "insurance_coi"`, attempt Tier 1 (pypdf form fields) then fall back to COI ParseAPI if form fields are absent. Store full extraction results in `ComplianceRecord.details`. Requires `COI_PARSE_API_KEY` env var; without it, COIs are accepted but flagged as `manually_verified=False`.
- **Test:** Use `data/sample_certs/insurance_coi_acord25.pdf` as fixture.

### IMP-106: COI coverage limit validation against task-type thresholds

- **Module:** M10_compliance
- **Effort:** medium
- **Description:** After IMP-105 extraction, add a validation step comparing `cgl_each_occurrence` and `cgl_general_aggregate` to configurable per-task-type thresholds. Store result in `ComplianceRecord.details["coverage_check"]`. Expose as a field in `verify_operator()` output. For DOT tasks (task_type contains "dot" or "highway"), require $2M/$4M. Block `assign_bid()` if critical thresholds are not met.
- **Threshold table:** Configurable in `compliance.py` module constants (not hardcoded per task).

### IMP-107: COI expiration date auto-detection from extracted fields

- **Module:** M10_compliance
- **Effort:** small
- **Description:** After IMP-105 extraction, set `expires_at = min(cgl_expiration_date, wc_expiration_date, umbrella_expiration_date)` automatically — overriding any manually provided value. Add 30-day advance warning: `verify_operator()` returns `EXPIRING_SOON` status for COIs expiring within 30 days (currently only checks `EXPIRED`).
- **Impact:** Prevents the current gap where operators upload a COI with a 3-month-old expiration and the system accepts it because `expires_at` was not provided.

### IMP-108: Additional insured and description-of-operations validation

- **Module:** M10_compliance
- **Effort:** small
- **Description:** After IMP-105 extraction, store `additional_insured` (bool) and `description_of_operations` (str) from the COI. Add a UAS scope check: if description does not contain keywords {"drone", "uas", "unmanned", "aerial", "uav"}, add a warning to the `verify_operator()` output (`coi_scope_warning: "Policy may not cover UAS operations"`). Do not block — warn and require operator acknowledgment.

---

## 8. New Questions Spawned

None critical. The implementation path is clear. One monitoring item:

- **R-008a (optional):** COI ParseAPI uptime and reliability — the service is relatively new. If it shows reliability issues after 60 days of use, evaluate Sensible.so as a drop-in replacement (both return structured JSON).

---

## Sources

- [COI ParseAPI](https://coiparseapi.com/) — purpose-built COI extraction REST API
- [Sensible: Extracting data from certificates of insurance](https://www.sensible.so/blog/extracting-data-from-certificates-of-insurance) — ACORD 25 extraction template guide
- [Docsumo: Ultimate Guide to ACORD 25 Data Extraction](https://www.docsumo.com/blogs/data-extraction/from-acord-25-forms)
- [Regure: ACORD 25 AI Extraction & Automation](https://www.getregure.com/documents/acord-25/)
- [Unstract: AI Insurance Document Processing](https://unstract.com/ai-insurance-document-processing/acord-document-data-extraction/)
- [UiPath Document Understanding: ACORD 25 ML Package](https://docs.uipath.com/document-understanding/automation-cloud/latest/user-guide/acord25-ml-package) — extracts 77 fields
- [VertikalRMS: ACORD 25 and 27 Forms Explained (2026)](https://www.vertikalrms.com/article/acord-25-27-forms-complete-insurance-certificate-guide/)
- [ContractorNerd: ACORD 25 Certificates](https://www.contractornerd.com/blog/acord-25-certificates/)
- [BWI: Part 107 Drone Insurance Essential Coverage](https://bwifly.com/blog/part-107-drone-insurance-essential-coverage-for-faa-certified-uav-pilots/)
- [GetJones: COI Certificates Explained](https://getjones.com/blog/coi-certificates-explained-what-to-look-for-on-an-acord-form/)
- [pdfplumber GitHub](https://github.com/jsvine/pdfplumber)
- [NYC Buildings: Sample ACORD 25 COI](https://www.nyc.gov/assets/buildings/pdf/acord_cert_of_ins_sample.pdf)
