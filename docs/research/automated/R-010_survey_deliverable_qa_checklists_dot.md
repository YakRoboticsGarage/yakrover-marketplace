# R-010: Survey Deliverable QA Checklists from State DOTs

**Date:** 2026-04-23
**Topic ID:** R-010
**Module:** M35_deliverable_qa
**Priority:** High
**Researcher:** Automated daily research agent

---

## Executive Summary

- **USGS LBS 2025 rev. A and ASPRS Edition 2** define the federal/professional baseline that most state DOTs reference. Key automatable checks: Class 0 prohibition, 90%-cells density rule, swath Δz ≤ 8 cm, NVA RMSE thresholds, and minimum 30 checkpoints.
- **ODOT (Ohio)** mandates the highest point density of any researched DOT: **40 pts/m²**, five times the USGS QL1 minimum. Current codebase density thresholds (QL0=20, QL1=8…) do not encode this requirement.
- **TxDOT (Texas)** requires **25 pts/m²** standard (design-grade airborne) and two vertical RMSEV tiers (±0.15 ft / ±0.33 ft), with a UAS-specific specification document.
- **MDOT (Michigan)** uses NCHRP 748 Category 1A for most design survey (high accuracy, fine density), with validation points every ≤100 ft within 0.05 ft of the adjusted cloud — checkable against reported accuracy metadata.
- **Four automatable gaps** exist in `deliverable_qa.py` Level 2: (1) no Class 0 check, (2) density thresholds ignore state-DOT context, (3) RMSE thresholds not validated against ASPRS class, (4) checkpoint count not enforced. Four improvement proposals added.

---

## Findings

### 1. USGS Lidar Base Specification 2025 rev. A

**Source:** https://www.usgs.gov/ngp-standards-and-specifications/lidar-base-specification-online

The USGS LBS is the most widely-referenced federal standard and the baseline that state DOTs annotate. Key automatable acceptance criteria:

#### Point Density
- Grid cells at 2× nominal point spacing (ANPS) must have ≥1 point in **90% of cells**.
- Density is checked by generating a raster at 2×ANPS and counting cells with ≥1 first return.
- This is a spatial distribution check, **not** a simple average density — the current codebase's `point_density_ppsm` field captures average density but cannot validate the 90% distribution rule without raster analysis.

Quality level → ANPS → minimum equivalent density:
| Quality Level | ANPS (m) | Approx. pts/m² |
|---|---|---|
| QL0 | 0.05 | ~400 |
| QL1 | 0.35 | ~8.2 |
| QL2 | 0.7 | ~2.0 |
| QL3 | 2.0 | ~0.25 |

#### Classification Requirements
- **No Class 0 points permitted** in classified LAS deliverable, unless flagged as withheld.
- Classification must be **consistent across tiles, swaths, and lifts** — visible seams between tiles are grounds for rejection.
- Ground class (ASPRS class 2) must be present for any terrain/topo deliverable.

#### Swath Alignment Check
- Swath Δz ≤ 8 cm (green): acceptable.
- Swath Δz > 8 cm (yellow/red): unacceptable — triggers rework.
- This is a metadata value computed during processing; the delivery should include a max_swath_dz_cm field.

#### Void Areas
- A void = any area ≥ (4 × ANPS)² with no first returns.
- Void NODATA value: -999999, defined in GDAL_NODATA tag 42113.
- Voids over waterbodies are permitted and should be excluded from void check.

#### Data Void Threshold
- Entire project area must be covered; void percentage is not quantified by a fixed threshold — all non-permitted voids are grounds for rejection.

---

### 2. ASPRS Positional Accuracy Standards, Edition 2 (2024)

**Source:** https://aagsmo.org/wp-content/uploads/2023/03/ASPRS_PosAcc_Edition2_MainBody.pdf

Key changes from Edition 1 that affect Level 2 QA validation:

#### Checkpoint Count
- **Minimum 30 checkpoints** (raised from 20 in Edition 1).
- Maximum 120 checkpoints for large projects.
- Checkpoints must be in clear, open, undisturbed areas.

#### NVA vs VVA
- **NVA (Non-Vegetated Vertical Accuracy)**: Pass/fail. The binding metric.
- **VVA (Vegetated Vertical Accuracy)**: Report only. A project **cannot fail** for VVA alone.
- Current Level 2 code (`_check_level_2`) checks `accuracy` as a generic field without distinguishing NVA/VVA.

#### RMSE Reporting
- Survey errors are now **included** in RMSE (previously excluded).
- New term: **3D positional accuracy** (combines horizontal + vertical).
- RMSE terms renamed: RMSEz (vertical), RMSEH (horizontal, combines X+Y).

#### ASPRS Accuracy Class → RMSE Thresholds (NVA)
| Class | RMSEz (cm) | NVA 95% (cm) |
|---|---|---|
| A-I | 1.0 | 1.96 |
| A-II | 2.5 | 4.9 |
| B-I | 5.0 | 9.8 |
| B-II | 10.0 | 19.6 |
| C-I | 20.0 | 39.2 |

Current Level 2 code checks `asprs_vertical_class` from the task spec but only verifies that an accuracy report exists — it does **not** validate that RMSEz ≤ the class threshold. This is the most critical gap.

---

### 3. ODOT (Ohio DOT) — January 2024 Aerial LiDAR Spec

**Source:** https://www.odot.org/survey/surveyInternet/conventional-survey-specs/Aerial%20LIDAR%20Acquisition%20%26%20Mapping%20Specifications%20January%202024.pdf

- **Point density**: ≥ **40 pts/m²** minimum, higher in overlap areas.
- **Format**: LAS (version not explicitly specified but LAS 1.4 implied by ASPRS alignment).
- **Deliverable**: QC Report required before Stage 1 engineering plans.
- **Professional oversight**: All mapping certified by a licensed Professional Surveyor.
- **Deliverable format**: OpenRoads Designer **.dgn** terrain models required (confirmed from R-001).
- **Implication**: A task with `dot_state: OH` requires density_pts_m2 ≥ 40 at Level 2 QA, plus a .dgn deliverable — neither is currently enforced.

---

### 4. TxDOT (Texas DOT) — Design-Grade Airborne LiDAR

**Sources:**
- https://www.txdot.gov/content/dam/docs/division/row/survey/airborne-lidar-for-design.pdf
- https://www.txdot.gov/content/dam/docs/division/row/survey/uas-aerial-mapping-for-design.pdf

- **Point density**: **25 pts/m²** standard; **50 pts/m²** for increased-density specification.
- **Vertical RMSEV tiers**:
  - Tier 1: ±0.15 ft (≈4.6 cm) — high-accuracy design
  - Tier 2: ±0.33 ft (≈10.1 cm) — standard design
- **GEOID18** vertical datum required (March 2025 update per R-033 scope).
- **UAS-specific spec**: Separate document for UAS aerial mapping — different flight parameters.
- **Ground-truthing report**: Required as part of final deliverables.
- **Implication**: TxDOT projects need a `dot_state: TX` flag to apply 25 pts/m² threshold and check GEOID18 vertical datum.

---

### 5. MDOT (Michigan DOT) — Remote Sensing

**Source:** https://mdotwiki.state.mi.us/design/index.php/Chapter_9_-_Remote_Sensing

- **Accuracy category**: NCHRP Report 748 Category 1A for most design survey (high accuracy, fine density).
- **Validation points**: Every ≤100 ft on linear projects >0.5 mi; elevation within **0.05 ft** (≈1.5 cm) of adjusted cloud.
- **Local transformation**: Required for point cloud coordinate system unless waived in writing.
- **Dry pavement required**: LiDAR acquisition must be done when pavement is dry (affects data quality).
- **Copies**: Two copies to Lansing Survey Support + one to MDOT Region Surveyor.
- **Implication**: MDOT accuracy threshold is tighter than standard (0.05 ft / 1.5 cm vs ASPRS B-I 5 cm). The 0.05 ft threshold is deliverable-checkable if the operator reports max_validation_error_ft.

---

### 6. Caltrans (California DOT)

**Source:** https://dot.ca.gov/-/media/dot-media/programs/right-of-way/documents/ls-manual/15-surveys-a11y.pdf

- **Terrestrial Laser Scanning**: Chapter 15 of Caltrans LS Manual.
- Density: Sufficient for extraction of detail at specified scale — no fixed pts/m² threshold.
- QA: Scan points compared to validation points; DTM review in profile.
- Caltrans accepts ASPRS accuracy standards as the basis for accuracy validation.
- Deliverables: Multiple formats including DWG, DGN, LAS — project-specific.

---

### 7. FHWA / CFLHD LiDAR Services

**Source:** https://highways.dot.gov/sites/fhwa.dot.gov/files/docs/federal-lands/resources/survey-and-mapping/12741/cflhd-specifications-lidar-services-k.pdf

- CFLHD (Central Federal Lands Highway Division) has a separate LiDAR services specification used for federal-aid projects on federal lands.
- Aligns with USGS LBS quality levels.
- Relevant for any projects on federal land (national forests, parks, BLM).

---

### 8. Existing Automated QA Tools

From R-009, the tools are known. Relevant to this research:

- **laspy + Classification check**: `las.classification == 0` check is straightforward — any points with class 0 that are not withheld is a fail.
- **PDAL `filters.stats`**: Returns classification histogram — can detect Class 0 presence.
- **spatialised.net PDAL QA tutorial**: Demonstrates open-source LiDAR QA with PDAL, including density estimation per hexbin.
- **Flai AI**: Automatic LiDAR point cloud classification (useful for pre-check before submission but not a QA tool).

The key insight: the metadata fields needed for DOT QA checks (Class 0 presence, swath Δz, checkpoint count, NVA RMSE, void percentage) **must be computed by the operator's processing software (Pix4D, DJI Terra, DroneDeploy, etc.) and reported in the delivery payload** — the platform cannot compute them from the raw files without PDAL integration (which R-009a found requires Docker sidecar or conda).

---

## Implications for the Product

### Codebase Gaps

#### `deliverable_qa.py` Level 2 — Missing Checks

| DOT Standard | Required Check | Current Status |
|---|---|---|
| USGS LBS | Class 0 points = 0 | **Missing** |
| USGS LBS | Swath Δz ≤ 8 cm | **Missing** |
| ASPRS Ed.2 | RMSEz ≤ class threshold | **Missing** (reports existence only) |
| ASPRS Ed.2 | Checkpoint count ≥ 30 | **Missing** |
| ASPRS Ed.2 | NVA separate from VVA | **Missing** |
| ODOT | density ≥ 40 pts/m² | **Missing** (USGS QL used) |
| TxDOT | density ≥ 25 pts/m² | **Missing** |
| MDOT | max_validation_error ≤ 0.05 ft | **Missing** |

#### `delivery_schemas.py` AERIAL_LIDAR_SCHEMA — Missing Fields

| Field | Purpose | Current Status |
|---|---|---|
| `class_0_points` | USGS LBS compliance flag | **Missing** |
| `max_swath_dz_cm` | Swath alignment check | **Missing** |
| `nva_rmse_cm` | ASPRS NVA (pass/fail) | Rolled into `vertical_accuracy_cm` |
| `vva_rmse_cm` | ASPRS VVA (report only) | Missing |
| `checkpoint_count` | ASPRS Ed.2 ≥ 30 | `control_points_used` present but minimum=0 |
| `las_version` | LAS 1.4 compliance | **Missing** |

#### Task Spec — Missing Field

No `dot_state` field in `capability_requirements`. State-specific density thresholds (ODOT=40, TxDOT=25) cannot be applied without knowing the project state.

### Architectural Note

The Level 2 QA engine (`_check_level_2`) checks:
1. CRS (checks existence, not match to spec)
2. Accuracy (checks existence, not threshold)
3. Point density (checks against USGS QL thresholds, not DOT-specific)
4. Deliverables list (checks existence, not format)

All four checks need strengthening. The most impactful single change is **ASPRS RMSEz threshold validation** — this converts the check from "did the operator claim accuracy?" to "does the claimed accuracy meet the required class?"

---

## Improvement Proposals

### IMP-118: Add `dot_state` field to task spec and route DOT-specific density thresholds in Level 2 QA

**Module:** auction/deliverable_qa, auction/core  
**Effort:** Small  
**Evidence:** ODOT requires 40 pts/m², TxDOT requires 25 pts/m² — neither is enforced. The existing `point_density_ppsm` check uses USGS QL thresholds only.  
**Implementation:** Add optional `dot_state: str` to `capability_requirements`. In `_check_level_2`, if `dot_state` is set, look up state-specific density threshold before falling back to USGS QL. Initial table: `{OH: 40, TX: 25, MI: None (NCHRP 748 1A, no fixed pts/m²)}`.

### IMP-119: Add Class 0 check and checkpoint count check to `AERIAL_LIDAR_SCHEMA`

**Module:** auction/delivery_schemas, auction/deliverable_qa  
**Effort:** Small  
**Evidence:** USGS LBS 2025 prohibits Class 0 points in classified deliverables. ASPRS Ed.2 requires ≥30 checkpoints. Neither is checked.  
**Implementation:** Add `class_0_points: {type: integer, maximum: 0}` and `checkpoint_count: {type: integer, minimum: 30}` to `AERIAL_LIDAR_SCHEMA.properties.quality_metrics`. The Level 1 schema validator will then reject deliveries that fail these.

### IMP-120: Add ASPRS RMSEz threshold validation to Level 2 QA (NVA pass/fail)

**Module:** auction/deliverable_qa  
**Effort:** Small  
**Evidence:** ASPRS Ed.2 NVA thresholds: A-I=1.0 cm, A-II=2.5 cm, B-I=5.0 cm, B-II=10.0 cm, C-I=20.0 cm. Current code only checks that an accuracy report exists — it does not validate the RMSE against the spec.  
**Implementation:** In `_check_level_2`, when `asprs_vertical_class` is set, look up the RMSEz threshold table and compare against `data.get("nva_rmse_cm") or data.get("vertical_accuracy_cm")`. If reported RMSE > class threshold, FAIL. Also split `vertical_accuracy_cm` into `nva_rmse_cm` (NVA, binding) and `vva_rmse_cm` (VVA, report only) in schema.

### IMP-121: Add `max_swath_dz_cm` and swath alignment check to Level 2 QA

**Module:** auction/delivery_schemas, auction/deliverable_qa  
**Effort:** Small  
**Evidence:** USGS LBS: Δz > 8 cm in swath overlap areas = unacceptable. This is a standard output of LiDAR processing software (Pix4D, TerraSolid) and should be required in the delivery payload for aerial_survey and topo_survey tasks.  
**Implementation:** Add `max_swath_dz_cm: {type: number, maximum: 8.0}` to `AERIAL_LIDAR_SCHEMA.properties.quality_metrics`. Level 2 QA checks this field when present. Make it optional (WARN if missing, not FAIL) since mobile LiDAR doesn't have swath overlap in the same way.

---

## New Questions Spawned

1. **R-010a**: Is `.dgn` deliverable format enforcement feasible via the platform, or is it a buyer-side concern? ODOT requires .dgn — should the `deliverables` list in the task spec include format=dgn, and should Level 2 QA check this? (connects to R-029: ODOT operator capability)
2. **R-011** (already queued): Orthomosaic and DEM quality metrics — GSD, RMSE, completeness for GeoTIFF deliverables. This research confirms the AERIAL_PHOTO_SCHEMA gap (no GSD minimum, no checkpoint requirement).

---

## Sources

- [USGS Lidar Base Specification 2025 rev. A](https://www.usgs.gov/media/files/lidar-base-specification-2025-rev-a)
- [USGS LBS Deliverables](https://www.usgs.gov/ngp-standards-and-specifications/lidar-base-specification-deliverables)
- [USGS LBS Data Processing Requirements](https://www.usgs.gov/ngp-standards-and-specifications/lidar-base-specification-data-processing-and-handling-requirements)
- [ASPRS Positional Accuracy Standards Edition 2](https://aagsmo.org/wp-content/uploads/2023/03/ASPRS_PosAcc_Edition2_MainBody.pdf)
- [ODOT Aerial LiDAR Acquisition & Mapping Specifications January 2024](https://www.odot.org/survey/surveyInternet/conventional-survey-specs/Aerial%20LIDAR%20Acquisition%20%26%20Mapping%20Specifications%20January%202024.pdf)
- [TxDOT Airborne LiDAR Specifications for Design-Grade Mapping](https://www.txdot.gov/content/dam/docs/division/row/survey/airborne-lidar-for-design.pdf)
- [TxDOT UAS Aerial Mapping Specifications](https://www.txdot.gov/content/dam/docs/division/row/survey/uas-aerial-mapping-for-design.pdf)
- [MDOT Chapter 9 — Remote Sensing](https://mdotwiki.state.mi.us/design/index.php/Chapter_9_-_Remote_Sensing)
- [Caltrans Chapter 15 — Terrestrial Laser Scanning](https://dot.ca.gov/-/media/dot-media/programs/right-of-way/documents/ls-manual/15-surveys-a11y.pdf)
- [ODOT Survey and Mapping Specifications](https://www.transportation.ohio.gov/working/engineering/cadd-mapping/survey-mapping-specs)
- [Open LiDAR QA with PDAL — Spatialised](https://www.spatialised.net/lidar-qa-with-pdal-part-1/)
- [Mobile LiDAR Services: DOT Digital Delivery Guide 2025](https://iscano.com/real-world-applications-laser-scanning-lidar/mobile-lidar-services-dot-digital-delivery-guide/)
