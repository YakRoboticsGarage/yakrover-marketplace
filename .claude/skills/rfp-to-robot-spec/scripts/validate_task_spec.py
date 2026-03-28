#!/usr/bin/env python3
"""Validate a robot task spec JSON against the auction engine schema.

Usage: python validate_task_spec.py < spec.json
       python validate_task_spec.py spec.json

Exits 0 if valid, 1 if invalid (with error messages on stderr).
"""
import json
import sys
from decimal import Decimal, InvalidOperation

VALID_CATEGORIES = {
    "site_survey", "bridge_inspection", "progress_monitoring",
    "as_built", "subsurface_scan", "environmental_survey", "control_survey"
}

VALID_SENSORS = {
    "aerial_lidar", "rtk_gps", "photogrammetry", "gpr", "thermal",
    "visual", "terrestrial_lidar", "sonar", "air_quality", "water_quality",
    "crack_detection", "profiler", "magnetometer"
}

VALID_CERTS = {
    "faa_part_107", "licensed_surveyor", "osha_10", "osha_30",
    "mot_certified", "pe_required", "fhwa_nhi_130055",
    "confined_space", "dive_certified", "bvlos_waiver"
}

VALID_DELIVERABLES = {
    "LandXML", "DXF", "DWG", "GeoTIFF", "LAS", "LAZ", "e57",
    "CSV", "PDF", "JPG", "PNG", "TIFF", "shapefile", "KML"
}

VALID_TERRAINS = {
    "highway_corridor", "commercial", "residential", "bridge",
    "dam", "pipeline", "airport", "rail", "industrial", "municipal",
    "waterway", "mine", "solar_farm"
}


def validate(spec: dict) -> list[str]:
    errors = []

    # Required top-level fields
    for field in ["description", "task_category", "capability_requirements", "budget_ceiling"]:
        if field not in spec:
            errors.append(f"Missing required field: {field}")

    # task_category
    cat = spec.get("task_category", "")
    if cat and cat not in VALID_CATEGORIES:
        errors.append(f"Invalid task_category '{cat}'. Valid: {sorted(VALID_CATEGORIES)}")

    # budget_ceiling
    try:
        budget = Decimal(str(spec.get("budget_ceiling", "0")))
        if budget < Decimal("0.50"):
            errors.append(f"budget_ceiling must be >= $0.50, got ${budget}")
    except (InvalidOperation, ValueError):
        errors.append(f"budget_ceiling must be a number, got {spec.get('budget_ceiling')!r}")

    # task_decomposition
    decomp = spec.get("task_decomposition")
    if decomp is not None:
        if not isinstance(decomp, dict):
            errors.append("task_decomposition must be a dict")
        else:
            if "rfp_id" not in decomp:
                errors.append("task_decomposition missing 'rfp_id'")
            idx = decomp.get("task_index")
            total = decomp.get("total_tasks")
            if idx is not None and total is not None:
                if not isinstance(idx, int) or not isinstance(total, int):
                    errors.append("task_index and total_tasks must be integers")
                elif idx < 1 or idx > total:
                    errors.append(f"task_index {idx} out of range (1-{total})")
            bundling = decomp.get("bundling", "independent")
            if bundling not in ("independent", "preferred_bundle", "required_bundle"):
                errors.append(f"Invalid bundling '{bundling}'. Valid: independent, preferred_bundle, required_bundle")
            deps = decomp.get("dependencies", [])
            if not isinstance(deps, list):
                errors.append("dependencies must be a list of task indices")
            elif deps and total:
                for d in deps:
                    if not isinstance(d, int) or d < 1 or d > total or d == idx:
                        errors.append(f"Invalid dependency {d} (must be 1-{total}, not self)")

    # capability_requirements structure
    cap = spec.get("capability_requirements", {})
    if not isinstance(cap, dict):
        errors.append("capability_requirements must be a dict")
    else:
        hard = cap.get("hard", {})
        if isinstance(hard, dict):
            sensors = hard.get("sensors_required", [])
            for s in sensors:
                if s not in VALID_SENSORS:
                    errors.append(f"Unknown sensor '{s}'. Valid: {sorted(VALID_SENSORS)}")

            certs = hard.get("certifications_required", [])
            for c in certs:
                if c not in VALID_CERTS:
                    errors.append(f"Unknown certification '{c}'. Valid: {sorted(VALID_CERTS)}")

            terrain = hard.get("terrain", "")
            if terrain and terrain not in VALID_TERRAINS:
                errors.append(f"Unknown terrain '{terrain}'. Valid: {sorted(VALID_TERRAINS)}")

        soft = cap.get("soft", {})
        if isinstance(soft, dict):
            deliverables = soft.get("preferred_deliverables", [])
            for d in deliverables:
                if d not in VALID_DELIVERABLES:
                    errors.append(f"Unknown deliverable format '{d}'. Valid: {sorted(VALID_DELIVERABLES)}")

    # sla_seconds
    sla = spec.get("sla_seconds")
    if sla is not None and (not isinstance(sla, int) or sla < 0):
        errors.append(f"sla_seconds must be a positive integer, got {sla!r}")

    return errors


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # Handle single spec or array of specs
    specs = data if isinstance(data, list) else [data]

    all_valid = True
    for i, spec in enumerate(specs):
        errors = validate(spec)
        if errors:
            all_valid = False
            label = f"Task {i+1}" if len(specs) > 1 else "Task spec"
            for e in errors:
                print(f"ERROR [{label}]: {e}", file=sys.stderr)
        else:
            label = f"Task {i+1}" if len(specs) > 1 else "Task spec"
            print(f"OK [{label}]: {spec.get('description', 'unnamed')[:60]}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
