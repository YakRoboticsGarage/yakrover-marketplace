# AASHTO & Federal Survey Standards Reference

Load this file when processing non-Michigan RFPs or when federal standards are referenced. Also load alongside michigan-standards.md when both state and federal standards apply (common for federally-funded state projects).

## AASHTO Survey Accuracy Standards

### Horizontal Control (AASHTO Survey Guide 2019)
| Order | Relative Accuracy | Typical Use |
|---|---|---|
| First Order | 1:100,000 | Geodetic networks, large-area mapping |
| Second Order Class I | 1:50,000 | State highway surveys, urban mapping |
| Second Order Class II | 1:20,000 | Local highway surveys, most construction |
| Third Order Class I | 1:10,000 | Construction layout, minor projects |
| Third Order Class II | 1:5,000 | Preliminary surveys, reconnaissance |

### Vertical Control (FGDC Standards)
| Order | Allowable Closure | Typical Use |
|---|---|---|
| First Order Class I | 0.5mm√K | National network, major structures |
| First Order Class II | 0.7mm√K | Regional networks |
| Second Order Class I | 1.0mm√K | State highway projects (default) |
| Second Order Class II | 1.3mm√K | Local projects, municipal work |
| Third Order | 2.0mm√K | Construction staking, preliminary |

(K = distance in km of the leveling loop)

## USGS Quality Levels (for Aerial LiDAR)

| Quality Level | NVA (cm) | VVA (cm) | Point Density (pts/m²) | Typical Use |
|---|---|---|---|---|
| QL0 | ≤5.0 | ≤7.6 | ≥20 | High-detail corridor mapping |
| QL1 | ≤10.0 | ≤15.0 | ≥8 | Design-grade highway surveys |
| QL2 | ≤10.0 | ≤15.0 | ≥2 | Standard topographic mapping (FEMA, USGS) |
| QL3 | ≤20.0 | N/A | ≥0.5 | Large-area reconnaissance |

NVA = Non-Vegetated Vertical Accuracy (95% confidence)
VVA = Vegetated Vertical Accuracy (95th percentile)

## FHWA Bridge Inspection Standards

### NBIS Requirements (23 CFR 650)
- Routine inspection: every 24 months (max)
- Underwater inspection: every 60 months
- Fracture-critical inspection: every 24 months
- NBI condition codes: 0-9 scale for deck, superstructure, substructure
- FHWA-NHI-130055 certification required for team leader

### AASHTO Manual for Bridge Element Inspection
- Element-level condition states: CS1 (good) through CS4 (severe)
- Quantity-based reporting: each element measured in units
- Defect coding with severity and extent

## FAA Survey Standards (for Airport Projects)

### AC 150/5300-18B — General Guidance and Specifications for Aeronautical Surveys
- Runway surveys: ±0.05 ft horizontal, ±0.01 ft vertical on pavement
- Obstruction surveys: ±1.0 ft horizontal, ±0.5 ft vertical
- NAVD88 vertical datum required
- Coordinate system: NAD83 State Plane

### AC 150/5320-5D — Airport Drainage Design
- Drainage survey accuracy: ±0.1 ft vertical for invert elevations
- Storm sewer survey: all pipe inverts, diameters, materials

## USACE Standards (for Waterway/Dam Projects)

### EM 1110-1-1005 — Topographic Surveying
- Horizontal: Second Order Class I minimum
- Vertical: Second Order Class I minimum
- All surveys tied to NSRS (National Spatial Reference System)

### EM 1110-2-1003 — Hydrographic Surveying
- Single-beam: ±0.5 ft vertical at 95%
- Multi-beam: ±1.0 ft vertical at 95%
- Horizontal positioning: ±2.0 m (RTK differential)

### Dam Safety (ER 1110-2-1156)
- Deformation monitoring: ±0.01 ft precision
- Settlement monitoring: ±0.005 ft precision
- Survey frequency: monthly during high-pool, quarterly otherwise

## OSHA Requirements for Construction Site Access

- OSHA 10-Hour Construction: minimum for site access
- OSHA 30-Hour Construction: required for supervisory roles
- Fall protection (29 CFR 1926 Subpart M): applies to drone launch/retrieval on elevated structures
- Confined space (29 CFR 1910.146): required for culvert, tunnel, tank entry

## Common Coordinate Systems by State

| Region | State Plane Zone | FIPS Code |
|---|---|---|
| Michigan South | NAD83 Michigan South | 2113 |
| Michigan Central | NAD83 Michigan Central | 2112 |
| Michigan North | NAD83 Michigan North | 2111 |
| Ohio South | NAD83 Ohio South | 3402 |
| Ohio North | NAD83 Ohio North | 3401 |
| Indiana East/West | NAD83 Indiana East/West | 1301/1302 |
| Illinois East/West | NAD83 Illinois East/West | 1201/1202 |
| Texas (5 zones) | NAD83 TX North/Central/South | 4201-4205 |
| California (6 zones) | NAD83 CA I-VI | 0401-0406 |
| Florida (3 zones) | NAD83 FL North/East/West | 0901-0903 |

## Default Accuracy When Not Specified

When an RFP does not specify accuracy requirements, apply these defaults based on project type:

| Project Type | Horizontal | Vertical | LiDAR QL |
|---|---|---|---|
| Highway design survey | ±0.05 ft | ±0.05 ft | QL1 |
| Highway preliminary | ±0.10 ft | ±0.10 ft | QL2 |
| Bridge inspection | N/A (visual) | N/A | N/A |
| Bridge survey (new) | ±0.05 ft | ±0.02 ft | QL0 |
| Airport pavement | ±0.05 ft | ±0.01 ft | QL0 |
| Municipal/local road | ±0.10 ft | ±0.10 ft | QL2 |
| Environmental/recon | ±1.0 ft | ±0.5 ft | QL3 |
| Dam deformation | ±0.01 ft | ±0.005 ft | N/A (terrestrial) |
