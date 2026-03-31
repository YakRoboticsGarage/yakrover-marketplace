# Standards Reference for Task Spec Generation

Always load this file when generating task specs. Use these tables to populate standards-aligned fields.

## ASPRS Accuracy Classes (Edition 2, 2024)

Map RFP accuracy requirements to the nearest ASPRS class. Use for both `asprs_horizontal_class` and `asprs_vertical_class`.

| Class | RMSE (cm) | Typical Use |
|-------|-----------|-------------|
| 1cm | ≤1.0 | Dam deformation, precision engineering |
| 2.5cm | ≤2.5 | High-detail pavement, airport runways |
| 5cm | ≤5.0 | Design-grade highway surveys (MDOT default) |
| 10cm | ≤10.0 | Standard topographic mapping, FEMA floodplain |
| 15cm | ≤15.0 | Large-area mapping, environmental |
| 20cm | ≤20.0 | Reconnaissance surveys |
| 33.3cm | ≤33.3 | Large-area preliminary |
| 100cm | ≤100.0 | Regional planning |

**Converting from RFP language:**
- "±0.05 ft" = ±1.5cm → use `"5cm"` class (RMSE ≤5cm covers 95% confidence at ±3cm)
- "±0.10 ft" = ±3cm → use `"5cm"` class
- "±0.01 ft" = ±0.3cm → use `"1cm"` class
- "design grade" with no number → default `"5cm"`
- "preliminary" with no number → default `"15cm"`

## USGS Quality Levels (LiDAR Base Spec 2025 rev. A)

Use for `usgs_quality_level`. Also sets minimum point density for LAS deliverables.

| QL | NVA (cm) | VVA (cm) | Min Density (pts/m²) | Use Case |
|----|----------|----------|---------------------|----------|
| QL0 | ≤5.0 | ≤7.6 | ≥20 | High-detail corridor, airport, bridge |
| QL1 | ≤10.0 | ≤15.0 | ≥8 | Design-grade highway surveys |
| QL2 | ≤10.0 | ≤15.0 | ≥2 | Standard topographic (FEMA, USGS 3DEP) |
| QL3 | ≤20.0 | N/A | ≥0.5 | Large-area reconnaissance |

NVA = Non-Vegetated Vertical Accuracy (95% confidence)
VVA = Vegetated Vertical Accuracy (95th percentile)

**Default QL by project type (when RFP doesn't specify):**
- Highway design → QL1
- Highway preliminary → QL2
- Bridge/airport → QL0
- Environmental/recon → QL3
- Municipal/local → QL2

## EPSG Codes for Coordinate Systems

Use for `crs_epsg` and `vertical_datum_epsg`. Always prefer EPSG codes over string names.

### Horizontal CRS (State Plane NAD83)

| State/Zone | EPSG | String Name |
|------------|------|-------------|
| Michigan South | 2113 | NAD83 Michigan South |
| Michigan Central | 2112 | NAD83 Michigan Central |
| Michigan North | 2111 | NAD83 Michigan North |
| Ohio South | 3402 | NAD83 Ohio South |
| Ohio North | 3401 | NAD83 Ohio North |
| Indiana East | 2965 | NAD83 Indiana East |
| Indiana West | 2966 | NAD83 Indiana West |
| Illinois East | 3435 | NAD83 Illinois East |
| Illinois West | 3436 | NAD83 Illinois West |
| Texas North Central | 2276 | NAD83 TX North Central |
| Texas Central | 2277 | NAD83 TX Central |
| California Zone 5 | 2229 | NAD83 CA Zone 5 |
| Florida East | 2236 | NAD83 FL East |

### Vertical Datums

| Datum | EPSG | Use |
|-------|------|-----|
| NAVD88 | 5703 | Standard US vertical datum (default) |
| IGLD85 | 5714 | Great Lakes projects (MI, OH, WI, etc.) |
| NGVD29 | 5702 | Legacy — convert to NAVD88 unless explicitly required |

**Rule:** Default to `crs_epsg` based on project state + zone. Default `vertical_datum_epsg: 5703` (NAVD88) unless Great Lakes project → 5714 (IGLD85).

## Deliverable Formats and Versions

Use for the `deliverables` array. Always include `format` and `version` when a standard version exists.

| Format | Standard | Current Version | Notes |
|--------|----------|-----------------|-------|
| LAS | ASPRS LAS Specification | 1.4 | `point_record_format`: 6 (default), 7 (RGB), 8 (RGB+NIR) |
| LAZ | LAS compressed | 1.4 | Same spec as LAS, compressed |
| E57 | ASTM E2807 | 1.0 | Terrestrial scan data exchange |
| LandXML | LandXML.org | 1.2 | Civil engineering: surfaces, alignments, pipe networks |
| GeoTIFF | OGC GeoTIFF | 1.1 | Orthomosaics, DEMs, DSMs. Include `gsd_cm` for orthos |
| DXF | Autodesk | R2018+ | Contours, breaklines, planimetrics |
| GeoPackage | OGC | 1.3 | Vector features, preferred over SHP for new projects |
| CSV | — | — | Control points, coordinate lists |
| PDF | — | — | Reports, accuracy certificates |
| SHP | ESRI | — | Legacy vector. Prefer GeoPackage |
| GeoJSON | IETF RFC 7946 | — | Web-compatible vector data |
| IFC | ISO 16739 | 4.3 | BIM model deliverables |

**LAS deliverable template:**
```json
{
  "format": "LAS",
  "version": "1.4",
  "point_record_format": 6,
  "classification_standard": "asprs",
  "min_point_density_ppsm": 8
}
```

## MRTA Task Classification (iTax Taxonomy)

Use for `mrta_class`. Helps the scoring engine select appropriate allocation algorithms.

| Axis | Values | Meaning |
|------|--------|---------|
| `robot_type` | ST / MT | Single-Task (robot does one task) / Multi-Task |
| `task_type` | SR / MR | Single-Robot (one robot per task) / Multi-Robot |
| `allocation` | IA / TA | Instantaneous (assign now) / Time-extended (schedule over time) |
| `dependency` | ND / ID / XD / CD | No Dependency / In-schedule / Cross-schedule / Complex |

**Common construction survey patterns:**
- Standard single survey: `ST-SR-IA-ND` (most common)
- Compound survey from one RFP (topo + GPR): `ST-SR-IA-ND` per task (independent tasks)
- Baseline + quarterly monitoring: `ST-SR-TA-ID` (time-extended, in-schedule dependency)
- Multi-robot simultaneous scan: `ST-MR-IA-ND` (rare in construction)

## Regulatory Requirements

Use for the `regulatory` block.

| Field | When True | Standard |
|-------|-----------|----------|
| `faa_remote_id_required` | Always for drone ops | ASTM F3411-22a (FAA mandate Sep 2023) |
| `faa_part_107_required` | Always for commercial drone | 14 CFR Part 107 |
| `laanc_authorization` | Near airports or controlled airspace | ASTM F3548-21 (UTM) |
| `state_pls_required` | When deliverables need PLS stamp | State licensing boards |
| `osha_10_required` | Construction site access | OSHA 10-Hour Construction |
| `confined_space_required` | Tunnel, culvert, tank work | 29 CFR 1910.146 |
| `nbis_certified_required` | Bridge inspection team lead | FHWA-NHI-130055 |

**`laanc_authorization` values:**
- `"required"` — project is in controlled airspace; operator must obtain LAANC before flight
- `"not_required"` — Class G airspace, no authorization needed
- `"pre_approved"` — blanket authorization already in place for the site

**`airspace_class` values:** `"A"`, `"B"`, `"C"`, `"D"`, `"E"`, `"G"` (FAA airspace classification)
