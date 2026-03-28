---
name: rfp-to-robot-spec
description: Process construction RFP documents into structured robot task specifications for the YAK ROBOTICS marketplace. Use whenever the user uploads, pastes, or references a construction RFP, bid document, survey scope, project specification, or describes a survey need in plain language. Also trigger when the user says "parse this RFP", "extract specs", "what robots do we need", or mentions MDOT, DOT, highway survey, bridge inspection, topographic survey, GPR scan, LiDAR, or construction survey requirements — even if they don't explicitly ask for a "task spec."
---

# RFP → Robot Task Spec

Transform construction RFP documents into machine-readable task specifications that the robot marketplace auction engine can process directly.

## Workflow

### 1. Canonicalize input

Accept any of: pasted RFP text, file path (PDF/text), URL, or plain-language description. Normalize to text. If the input is vague ("I need a survey for a highway project"), ask the user for: location, acreage, accuracy needs, and deadline. If those are in the document, extract them — don't ask again.

### 2. Extract survey requirements

Scan for these categories. Mark each as FOUND or NOT FOUND:

- Survey type (topo, as-built, control, bridge, hydraulic, photogrammetric, environmental)
- Accuracy (horizontal, vertical, point density — in feet or metric)
- Area/scope (acres, linear feet, structure count)
- Deliverable formats (LandXML, DXF, GeoTIFF, LAS, CSV, e57, PDF)
- Coordinate system and datum
- Certifications (FAA Part 107, licensed surveyor, OSHA, PE, dive)
- Referenced standards (MDOT sections, AASHTO, NCHRP, USGS QL, FEMA)
- Timeline (letting date, completion deadline, seasonal constraints)
- Special conditions (traffic control, night work, environmental restrictions, utility conflicts)

### 3. Load applicable standards

Load the right reference for the project's jurisdiction:
- **Michigan projects** (MDOT, county, municipal): read `references/michigan-standards.md`
- **Federal projects** (USACE, FAA, FHWA) or **any state without its own reference**: read `references/aashto-federal-standards.md`
- **Projects with both** (federally-funded state highway): load both files

If no accuracy is specified in the RFP, use the defaults table in `references/aashto-federal-standards.md` (bottom section) based on project type.

### 4. Map to robots and sensors

Read `references/robot-sensor-mapping.md`. For each survey requirement, identify the robot platform, sensor, and estimated cost. If the RFP requires multiple survey types, each becomes a separate task spec (different robots may bid on each).

### 5. Generate task spec JSON

Output one JSON block per task. Each must pass validation:

```bash
python scripts/validate_task_spec.py < spec.json
```

The spec structure:

```json
{
  "description": "Clear one-line summary of this specific task",
  "task_category": "site_survey | bridge_inspection | progress_monitoring | as_built | subsurface_scan | environmental_survey | control_survey",
  "capability_requirements": {
    "hard": {
      "sensors_required": ["aerial_lidar", "rtk_gps"],
      "accuracy_required": {"vertical_ft": 0.05, "horizontal_ft": 0.05},
      "certifications_required": ["faa_part_107", "licensed_surveyor"],
      "area_acres": 12,
      "terrain": "highway_corridor",
      "standards_compliance": ["MDOT_104.09", "NCHRP_748_Cat1A"]
    },
    "soft": {
      "preferred_deliverables": ["LAS", "LandXML", "DXF", "GeoTIFF"],
      "preferred_coordinate_system": "NAD83 Michigan South Zone",
      "preferred_datum": "NAVD88"
    },
    "payload": {
      "type": "survey_data",
      "fields": ["point_cloud", "topo_surface", "ortho_mosaic"],
      "format": "multi_file"
    }
  },
  "budget_ceiling": "5000.00",
  "sla_seconds": 259200,
  "payment_method": "auto",
  "project_metadata": {
    "project_name": "...",
    "agency": "MDOT",
    "location": "...",
    "letting_date": "...",
    "reference_standards": ["MDOT Sec 104.09"]
  }
}
```

### 6. Present results

Output in this order:
1. **Summary** — one paragraph on the project and survey needs
2. **Extracted Requirements** — bulleted list of everything found
3. **Task Specs** — JSON blocks (one per robot type)
4. **Cost Estimate** — per-task and total, with market range
5. **Robot Recommendations** — which platforms fulfill each task

Flag any requirements that no current marketplace robot can fulfill.

## References

- `references/michigan-standards.md` — MDOT accuracy tables, LiDAR specs, survey types, coordinate systems. Load for Michigan projects.
- `references/aashto-federal-standards.md` — AASHTO, USGS QL levels, FHWA bridge, FAA airport, USACE dam standards, OSHA requirements, state plane zones, and default accuracy tables. Load for federal projects or when state-specific standards are unavailable.
- `references/robot-sensor-mapping.md` — survey need → robot platform → sensor → price range. Load for step 4.

## Validation

After generating specs, run the validation script to catch schema errors before presenting to the user:

```bash
python scripts/validate_task_spec.py spec.json
```

This checks: required fields, valid categories, known sensors, valid certifications, budget minimum, deliverable formats. Exit 0 = valid.

## Example inputs

See `examples/` directory for 6 diverse RFP types:
- `mdot-highway-rfp.txt` — MDOT US-131 resurfacing, Michigan, 6.6 miles
- `bridge-inspection-rfp.txt` — Wayne County 47-bridge NBIS program, Michigan
- `txdot-highway-rfp.txt` — TxDOT IH-45 corridor, Houston, 16 miles, $750K-1.2M
- `usace-dam-inspection.txt` — USACE dam safety, Iowa, deformation monitoring + underwater
- `faa-airport-rfp.txt` — FAA aeronautical survey, Grand Rapids GRR, restricted airspace
- `commercial-site-survey.txt` — Private GC pre-bid, Romulus MI, 45-acre Kroger expansion
- `municipal-progress-monitoring.txt` — City of Ann Arbor, 14-month recurring progress docs
