"""RFP processing module — converts construction RFP text into structured task specs.

Vertical: construction (MDOT, AASHTO, federal highway RFP formats)

Two modes:
1. LLM-powered (default when ANTHROPIC_API_KEY is set): calls Claude with the
   rfp-to-robot-spec skill prompt + reference docs for semantic extraction.
2. Keyword-based (fallback): deterministic pattern matching for when no API key
   is available or for fast/cheap testing.

The LLM mode loads the skill references (michigan-standards, aashto-federal,
robot-sensor-mapping) as context and produces structured JSON task specs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Skill reference data paths
_SKILL_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "rfp-to-robot-spec"
_REFS_DIR = _SKILL_DIR / "references"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def _load_reference(name: str) -> str:
    """Load a skill reference file, returning empty string if not found."""
    path = _REFS_DIR / name
    if path.exists():
        return path.read_text()
    return ""


# Construction survey sensor mapping
SENSOR_MAPPING = {
    "aerial_lidar": {"category": "site_survey", "equipment": ["DJI Matrice 350 RTK + Zenmuse L2"]},
    "terrestrial_lidar": {"category": "site_survey", "equipment": ["Leica BLK ARC", "Leica RTC360"]},
    "photogrammetry": {"category": "aerial_survey", "equipment": ["DJI Matrice 350 RTK + Zenmuse P1"]},
    "gpr": {"category": "subsurface_scan", "equipment": ["GSSI StructureScan Mini XT"]},
    "rtk_gps": {"category": "control_survey", "equipment": ["Trimble R12i", "Leica GS18"]},
    "thermal_camera": {"category": "bridge_inspection", "equipment": ["Skydio X10 Thermal"]},
    "robotic_total_station": {"category": "control_survey", "equipment": ["Trimble SX12"]},
}

# Standard deliverable formats
DELIVERABLE_FORMATS = [
    "LandXML",
    "DXF",
    "CSV",
    "GeoTIFF",
    "LAS",
    "LAZ",
    "e57",
    "PDF",
    "Civil 3D TIN",
    "Pix4D Report",
]


def process_rfp(
    rfp_text: str,
    jurisdiction: str = "MI",
    site_info: dict | None = None,
    use_llm: bool = True,
) -> list[dict]:
    """Process an RFP text into structured task specs.

    When ANTHROPIC_API_KEY is set and use_llm=True, uses Claude for semantic
    extraction (more accurate, handles complex/unusual RFPs). Falls back to
    deterministic keyword matching when no API key or on failure.

    Args:
        rfp_text: The RFP document text.
        jurisdiction: State code (e.g., "MI", "OH", "AZ").
        site_info: Optional geographic and site details. When provided, these
            are embedded in every task spec so operators have full context.
            Expected keys:
                - project_name (str): Official project name
                - location (str): City/county/address description
                - coordinates (dict): {"lat": float, "lon": float} — project centroid
                - survey_area (dict): {"type": "corridor"|"polygon"|"point", "acres": float,
                    "length_miles": float, "width_ft": float} — site geometry
                - agency (str): Contracting agency (e.g., "MDOT", "City of Detroit")
                - project_id (str): Agency project/contract number
                - letting_date (str): Bid letting date (ISO format)
                - terrain (str): "flat"|"rolling"|"mountainous"|"urban"|"corridor"|"underground"
                - access_restrictions (list[str]): e.g., ["highway_traffic", "escort_required"]
                - airspace_class (str): FAA airspace (e.g., "G", "E", "D")
                - reference_standards (list[str]): e.g., ["MDOT Section 104.09", "NCHRP 748"]

    Returns a list of task spec dicts ready for auction_post_task.
    """
    tasks = []
    rfp_lower = rfp_text.lower()
    site_info = site_info or {}

    # Try LLM-powered extraction first (if API key available)
    if use_llm and ANTHROPIC_API_KEY:
        try:
            return _process_rfp_with_llm(rfp_text, jurisdiction, site_info)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"LLM RFP parsing failed, falling back to keywords: {e}")

    # Fallback: keyword-based extraction
    # Extract geographic context from RFP text when not provided
    if "location" not in site_info:
        site_info["location"] = _extract_location(rfp_text)
    if "terrain" not in site_info:
        site_info["terrain"] = _infer_terrain(rfp_lower)
    if "agency" not in site_info:
        site_info["agency"] = _extract_agency(rfp_text)
    if "project_name" not in site_info:
        site_info["project_name"] = _extract_project_name(rfp_text)

    # Detect task types from RFP text
    survey_types = []

    # Environmental / sensor monitoring (non-survey tasks)
    if any(kw in rfp_lower for kw in [
        "temperature", "humidity", "environmental monitor", "climate assess",
        "sensor reading", "env_sensing", "indoor climate", "server room",
        "air quality", "thermal comfort", "data logging",
    ]):
        survey_types.append("env_sensing")
    # Visual / camera inspection
    if any(kw in rfp_lower for kw in [
        "visual inspection", "camera inspect", "photo document", "crack detection",
        "condition assess", "defect", "visual_inspection",
    ]):
        survey_types.append("visual_inspection")
    # Construction survey types
    if any(kw in rfp_lower for kw in ["topographic", "topo survey", "surface survey", "corridor survey"]):
        survey_types.append("topographic")
    if any(kw in rfp_lower for kw in ["tunnel", "3d scan", "terrestrial lidar", "as-built"]):
        survey_types.append("tunnel_scan")
    if any(kw in rfp_lower for kw in ["subsurface", "gpr", "ground penetrating", "utility locate"]):
        survey_types.append("subsurface")
    if any(kw in rfp_lower for kw in ["progress monitor", "monthly survey", "cut/fill", "volume"]):
        survey_types.append("progress_monitoring")
    if any(kw in rfp_lower for kw in ["bridge inspect", "structural inspect", "thermal inspect"]):
        survey_types.append("bridge_inspection")
    if any(kw in rfp_lower for kw in ["photogramm", "orthomosaic", "aerial photo"]):
        survey_types.append("photogrammetry")
    if any(kw in rfp_lower for kw in ["control network", "control point", "benchmarks"]):
        survey_types.append("control_survey")

    if not survey_types:
        survey_types.append("topographic")  # Default for unrecognized RFPs

    # Generate a task spec for each detected survey type
    for i, survey_type in enumerate(survey_types):
        task = _build_task_spec(survey_type, rfp_text, jurisdiction, site_info, i, len(survey_types))
        tasks.append(task)

    return tasks


def _extract_location(rfp_text: str) -> str:
    """Extract location from RFP text."""
    import re

    rfp_lower = rfp_text.lower()
    # Look for state-route patterns like "I-94", "SR-89A", "US-131"
    route_match = re.search(r"\b(I-\d+|SR-\d+\w?|US-\d+|M-\d+)\b", rfp_text)
    route = route_match.group(0) if route_match else None

    # Look for city/county names
    for state in ["Michigan", "Ohio", "Arizona", "Texas", "California", "Indiana", "Wisconsin"]:
        if state.lower() in rfp_lower:
            return f"{route + ', ' if route else ''}{state}"
    return route or "Location not specified — provide in site_info"


def _infer_terrain(rfp_lower: str) -> str:
    """Infer terrain type from RFP text."""
    if any(kw in rfp_lower for kw in ["tunnel", "underground", "culvert"]):
        return "underground"
    if any(kw in rfp_lower for kw in ["highway", "corridor", "interstate", "freeway"]):
        return "corridor"
    if any(kw in rfp_lower for kw in ["urban", "city", "downtown"]):
        return "urban"
    if any(kw in rfp_lower for kw in ["mountain", "steep", "ridge"]):
        return "mountainous"
    if any(kw in rfp_lower for kw in ["bridge", "overpass", "viaduct"]):
        return "bridge_structure"
    if any(kw in rfp_lower for kw in ["indoor", "server room", "warehouse", "building", "facility"]):
        return "indoor"
    return "flat"


def _extract_agency(rfp_text: str) -> str:
    """Extract contracting agency from RFP text."""
    rfp_lower = rfp_text.lower()
    agencies = {
        "mdot": "Michigan Department of Transportation (MDOT)",
        "michigan department of transportation": "Michigan Department of Transportation (MDOT)",
        "odot": "Ohio Department of Transportation (ODOT)",
        "txdot": "Texas Department of Transportation (TxDOT)",
        "adot": "Arizona Department of Transportation (ADOT)",
        "usace": "US Army Corps of Engineers (USACE)",
        "faa": "Federal Aviation Administration (FAA)",
        "fhwa": "Federal Highway Administration (FHWA)",
    }
    for key, name in agencies.items():
        if key in rfp_lower:
            return name
    return "Agency not identified — provide in site_info"


def _extract_project_name(rfp_text: str) -> str:
    """Extract project name from RFP text (first substantive line)."""
    import re

    for line in rfp_text.strip().split("\n"):
        line = line.strip()
        if len(line) > 10 and not line.startswith("#"):
            # Clean up and truncate
            return re.sub(r"\s+", " ", line)[:120]
    return "Project name not extracted"


def _build_capability_requirements(t: dict, jurisdiction: str) -> dict:
    """Build capability_requirements from a task template."""
    hard: dict = {
        "sensors_required": t["sensors"],
    }
    if t.get("certifications"):
        hard["certifications_required"] = t["certifications"]
    if t.get("accuracy"):
        hard["accuracy_required"] = t["accuracy"]
    if t.get("indoor_capable"):
        hard["indoor_capable"] = True

    cap: dict = {"hard": hard}

    # Delivery schema (if template provides one)
    if "delivery_schema" in t:
        cap["delivery_schema"] = t["delivery_schema"]
        cap["qa_level"] = 1
        # For schema-driven tasks, payload mirrors the schema
        cap["payload"] = {"format": "json", "fields": list(t["delivery_schema"].get("required", []))}
    else:
        # Construction survey defaults
        cap["soft"] = {
            "preferred_deliverables": t["deliverables"],
            "preferred_coordinate_system": "State Plane" if jurisdiction == "MI" else "UTM",
            "preferred_datum": "NAD83(2011)",
        }
        cap["payload"] = {"format": "multi_file", "fields": t["deliverables"]}

    return cap


def _build_task_spec(
    survey_type: str,
    rfp_text: str,
    jurisdiction: str,
    site_info: dict,
    task_index: int,
    total_tasks: int,
) -> dict:
    """Build a single task spec from a detected survey type and site context."""
    import hashlib

    rfp_id = f"rfp_{hashlib.sha256(rfp_text[:200].encode()).hexdigest()[:12]}"

    templates = {
        "env_sensing": {
            "description": "Environmental monitoring — sensor readings at specified waypoints",
            "task_category": "env_sensing",
            "sensors": ["temperature", "humidity"],
            "deliverables": ["JSON"],
            "accuracy": {},
            "certifications": [],
            "budget_range": [50, 500],
            "sla_days": 1,
            "indoor_capable": True,
            "delivery_schema": {
                "description": "Waypoint readings with temperature and humidity",
                "required": ["readings", "summary", "duration_seconds"],
                "properties": {
                    "readings": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "required": ["waypoint", "temperature_c", "humidity_pct", "timestamp"],
                            "properties": {
                                "temperature_c": {"type": "number", "minimum": -40, "maximum": 85},
                                "humidity_pct": {"type": "number", "minimum": 0, "maximum": 100},
                                "waypoint": {"type": "integer", "minimum": 1},
                                "timestamp": {"type": "string"},
                            },
                        },
                    },
                    "summary": {"type": "string", "minLength": 1},
                    "duration_seconds": {"type": "number", "minimum": 0},
                },
            },
        },
        "visual_inspection": {
            "description": "Visual inspection — camera-based structural or condition assessment",
            "task_category": "visual_inspection",
            "sensors": ["camera", "visual"],
            "deliverables": ["PDF", "GeoTIFF"],
            "accuracy": {},
            "certifications": ["faa_part_107"],
            "budget_range": [500, 5000],
            "sla_days": 3,
        },
        "topographic": {
            "description": "Pre-construction topographic survey — aerial LiDAR corridor mapping with RTK-GPS control",
            "task_category": "site_survey",
            "sensors": ["aerial_lidar", "rtk_gps", "photogrammetry"],
            "deliverables": ["LandXML", "DXF", "LAS", "GeoTIFF"],
            "accuracy": {"horizontal_cm": 2.0, "vertical_cm": 5.0},
            "certifications": ["faa_part_107", "pls_license"],
            "budget_range": [15000, 85000],
            "sla_days": 14,
        },
        "tunnel_scan": {
            "description": "Tunnel 3D scanning and as-built survey — terrestrial LiDAR with confined space cert",
            "task_category": "as_built",
            "sensors": ["terrestrial_lidar"],
            "deliverables": ["e57", "LAS", "DXF"],
            "accuracy": {"horizontal_cm": 1.0, "vertical_cm": 1.0},
            "certifications": ["pls_license", "confined_space"],
            "budget_range": [50000, 120000],
            "sla_days": 21,
        },
        "subsurface": {
            "description": "Subsurface utility detection — GPR survey for underground infrastructure",
            "task_category": "subsurface_scan",
            "sensors": ["gpr"],
            "deliverables": ["DXF", "PDF", "CSV"],
            "accuracy": {"horizontal_cm": 15.0, "vertical_cm": 15.0},
            "certifications": ["faa_part_107"],
            "budget_range": [5000, 25000],
            "sla_days": 7,
        },
        "progress_monitoring": {
            "description": "Monthly construction progress monitoring — aerial survey for cut/fill volume tracking",
            "task_category": "progress_monitoring",
            "sensors": ["aerial_lidar", "photogrammetry"],
            "deliverables": ["GeoTIFF", "LAS", "PDF"],
            "accuracy": {"horizontal_cm": 5.0, "vertical_cm": 5.0},
            "certifications": ["faa_part_107"],
            "budget_range": [1500, 5000],
            "sla_days": 3,
        },
        "bridge_inspection": {
            "description": "Bridge structural inspection — visual and thermal drone survey per NBI requirements",
            "task_category": "bridge_inspection",
            "sensors": ["thermal_camera", "photogrammetry"],
            "deliverables": ["PDF", "GeoTIFF", "LAS"],
            "accuracy": {"horizontal_cm": 5.0, "vertical_cm": 5.0},
            "certifications": ["faa_part_107"],
            "budget_range": [8000, 35000],
            "sla_days": 10,
        },
        "photogrammetry": {
            "description": "Aerial photogrammetry survey — high-resolution orthomosaic and 3D model generation",
            "task_category": "aerial_survey",
            "sensors": ["photogrammetry", "rtk_gps"],
            "deliverables": ["GeoTIFF", "LAS", "DXF"],
            "accuracy": {"horizontal_cm": 3.0, "vertical_cm": 5.0},
            "certifications": ["faa_part_107"],
            "budget_range": [3000, 15000],
            "sla_days": 7,
        },
        "control_survey": {
            "description": "Survey control network establishment — RTK-GPS and total station ground control points",
            "task_category": "control_survey",
            "sensors": ["rtk_gps", "robotic_total_station"],
            "deliverables": ["CSV", "DXF", "PDF"],
            "accuracy": {"horizontal_cm": 1.0, "vertical_cm": 1.0},
            "certifications": ["pls_license"],
            "budget_range": [5000, 20000],
            "sla_days": 5,
        },
    }

    t = templates.get(survey_type, templates["topographic"])
    budget = (t["budget_range"][0] + t["budget_range"][1]) // 2  # type: ignore[index]

    return {
        "description": t["description"],
        "task_category": t["task_category"],
        "capability_requirements": _build_capability_requirements(t, jurisdiction),
        "budget_ceiling": budget,
        "sla_seconds": t["sla_days"] * 86400,  # type: ignore[operator]
        "task_decomposition": {
            "rfp_id": rfp_id,
            "task_index": task_index,
            "total_tasks": total_tasks,
            "dependencies": [],
            "bundling": "independent",
        },
        "project_metadata": {
            "jurisdiction": jurisdiction,
            "survey_type": survey_type,
            "source": "rfp_processor",
            "project_name": site_info.get("project_name", ""),
            "agency": site_info.get("agency", ""),
            "project_id": site_info.get("project_id", ""),
            "letting_date": site_info.get("letting_date", ""),
            "location": site_info.get("location", ""),
            "coordinates": site_info.get("coordinates", {}),
            "survey_area": site_info.get("survey_area", {}),
            "terrain": site_info.get("terrain", ""),
            "access_restrictions": site_info.get("access_restrictions", []),
            "airspace_class": site_info.get("airspace_class", "G"),
            "reference_standards": site_info.get("reference_standards", []),
        },
    }


# ---------------------------------------------------------------------------
# LLM-powered RFP parsing (uses Claude API)
# ---------------------------------------------------------------------------


    # _load_reference() is defined at module level (line 26) — no redefinition needed


def _process_rfp_with_llm(
    rfp_text: str,
    jurisdiction: str,
    site_info: dict,
) -> list[dict]:
    """Parse an RFP using Claude API with skill references for context.

    Loads the rfp-to-robot-spec skill's reference documents and sends them
    as context along with the RFP text. Claude extracts survey requirements
    and returns structured task specs.
    """
    import httpx

    # Load skill references
    michigan_ref = _load_reference("michigan-standards.md")
    federal_ref = _load_reference("aashto-federal-standards.md")
    sensor_ref = _load_reference("robot-sensor-mapping.md")

    # Build the system prompt from the skill definition
    system_prompt = f"""You are an expert construction survey specification extractor.
Given an RFP document, extract survey requirements and produce structured JSON task specs.

Each task spec must have these exact fields:
- description (str): Clear description of the survey task
- task_category (str): One of: site_survey, bridge_inspection, progress_monitoring, as_built, subsurface_scan, environmental_survey, control_survey, aerial_survey
- capability_requirements (dict): with "hard" (sensors_required, certifications_required, accuracy_required), "soft" (preferred_deliverables, preferred_coordinate_system, preferred_datum), and "payload" (format, fields)
- budget_ceiling (number): Estimated budget in USD based on scope and industry pricing
- sla_seconds (int): Deadline in seconds (days * 86400)
- task_decomposition (dict): rfp_id, task_index, total_tasks, dependencies (list), bundling ("independent")
- project_metadata (dict): jurisdiction, survey_type, source ("llm_extraction"), project_name, agency, location, coordinates, terrain

Reference: Robot & Sensor Mapping
{sensor_ref[:3000]}

Reference: Michigan Standards
{michigan_ref[:2000]}

Reference: Federal Standards
{federal_ref[:2000]}

Site info provided by the GC:
{json.dumps(site_info, indent=2)}

Jurisdiction: {jurisdiction}

IMPORTANT: Return ONLY a JSON array of task specs. No markdown, no explanation. Just the JSON array."""

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": f"Extract task specs from this RFP:\n\n{rfp_text[:8000]}"}],
        },
        timeout=30.0,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Claude API returned {response.status_code}: {response.text[:200]}")

    data = response.json()
    content = data.get("content", [{}])[0].get("text", "")

    # Parse JSON from response (handle markdown code blocks)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]  # Remove opening ```json
        if "```" in content:
            content = content[: content.rindex("```")]  # Remove closing ```

    specs = json.loads(content)
    if not isinstance(specs, list):
        specs = [specs]

    # Ensure each spec has required fields with defaults
    import hashlib

    rfp_id = f"rfp_{hashlib.sha256(rfp_text[:200].encode()).hexdigest()[:12]}"

    for i, spec in enumerate(specs):
        # Ensure task_decomposition
        if "task_decomposition" not in spec:
            spec["task_decomposition"] = {}
        td = spec["task_decomposition"]
        td.setdefault("rfp_id", rfp_id)
        td.setdefault("task_index", i)
        td.setdefault("total_tasks", len(specs))
        td.setdefault("dependencies", [])
        td.setdefault("bundling", "independent")

        # Ensure project_metadata
        if "project_metadata" not in spec:
            spec["project_metadata"] = {}
        pm = spec["project_metadata"]
        pm.setdefault("jurisdiction", jurisdiction)
        pm.setdefault("source", "llm_extraction")
        pm.update({k: v for k, v in site_info.items() if k not in pm})

        # Ensure budget_ceiling is a number
        if isinstance(spec.get("budget_ceiling"), str):
            spec["budget_ceiling"] = float(spec["budget_ceiling"].replace(",", "").replace("$", ""))

        # Ensure sla_seconds is an int
        if isinstance(spec.get("sla_seconds"), float):
            spec["sla_seconds"] = int(spec["sla_seconds"])

    return specs


def validate_task_specs(task_specs: list[dict]) -> dict:
    """Validate an array of task specs against the engine schema.

    Returns per-spec pass/fail with error details.
    """
    from auction.core import validate_task_spec

    results = []
    all_valid = True

    for i, spec in enumerate(task_specs):
        # Make a copy so validate_task_spec can mutate task_category
        spec_copy = dict(spec)
        errors = validate_task_spec(spec_copy)
        valid = len(errors) == 0
        if not valid:
            all_valid = False
        results.append(
            {
                "index": i,
                "valid": valid,
                "errors": errors,
                "task_category": spec_copy.get("task_category"),
                "description": spec.get("description", "")[:100],
            }
        )

    return {
        "total_specs": len(task_specs),
        "all_valid": all_valid,
        "valid_count": sum(1 for r in results if r["valid"]),
        "invalid_count": sum(1 for r in results if not r["valid"]),
        "results": results,
    }


def get_site_recon(rfp_text: str, task_specs: list[dict]) -> dict:
    """Generate a site reconnaissance report from RFP text and task specs.

    Uses project_metadata from task specs (populated by process_rfp with site_info)
    as authoritative source, falling back to RFP text parsing when fields are missing.

    Returns execution context: airspace classification, terrain, weather constraints,
    and access considerations. Each field is tagged with its source confidence.
    """
    rfp_lower = rfp_text.lower()

    # Pull site_info from task_specs project_metadata (populated by process_rfp)
    meta = task_specs[0].get("project_metadata", {}) if task_specs else {}

    # Location: prefer site_info, fall back to RFP text
    provided_location = meta.get("location", "")
    if provided_location:
        location = {"source": "SITE_INFO", "value": provided_location}
    else:
        location = {"source": "INFERRED", "value": "Unknown"}
        for state in ["michigan", "ohio", "arizona", "texas", "california"]:
            if state in rfp_lower:
                location = {"source": "RFP", "value": state.title()}
                break

    # Terrain: prefer site_info, fall back to RFP text
    provided_terrain = meta.get("terrain", "")
    if provided_terrain:
        terrain = provided_terrain
        terrain_source = "SITE_INFO"
    else:
        terrain = "flat"
        terrain_source = "INFERRED"
        if any(kw in rfp_lower for kw in ["mountain", "steep", "hillside", "ridge"]):
            terrain = "mountainous"
            terrain_source = "RFP"
        elif any(kw in rfp_lower for kw in ["urban", "city", "downtown", "building"]):
            terrain = "urban"
            terrain_source = "RFP"
        elif any(kw in rfp_lower for kw in ["highway", "corridor", "road", "interstate"]):
            terrain = "corridor"
            terrain_source = "RFP"
        elif any(kw in rfp_lower for kw in ["tunnel", "underground", "culvert"]):
            terrain = "underground"
            terrain_source = "RFP"

    # Airspace: prefer site_info, fall back to RFP text
    provided_airspace = meta.get("airspace_class", "")
    if provided_airspace and provided_airspace != "G":
        restrictions = ["LAANC authorization required"] if provided_airspace in ("B", "C", "D") else []
        airspace = {"class": provided_airspace, "source": "SITE_INFO", "restrictions": restrictions}
    else:
        airspace = {"class": "G", "source": "INFERRED", "restrictions": []}
        if any(kw in rfp_lower for kw in ["airport", "airfield", "runway"]):
            airspace = {"class": "B/C/D", "source": "RFP", "restrictions": ["LAANC authorization required"]}

    # Weather constraints
    sensors_needed = set()
    for spec in task_specs:
        cap = spec.get("capability_requirements", {})
        hard = cap.get("hard", {})
        sensors_needed.update(hard.get("sensors_required", []))

    weather = {
        "max_wind_kph": 40 if "aerial_lidar" in sensors_needed else 60,
        "precipitation": (
            "none_during_flight" if any(s in sensors_needed for s in ["aerial_lidar", "photogrammetry"]) else "light_ok"
        ),
        "visibility_km": 5.0,
        "source": "INFERRED",
    }

    return {
        "location": location,
        "terrain": {"type": terrain, "source": terrain_source},
        "coordinates": meta.get("coordinates", {}),
        "survey_area": meta.get("survey_area", {}),
        "airspace": airspace,
        "weather_constraints": weather,
        "access": {
            "requires_escort": "restricted" in rfp_lower
            or "military" in rfp_lower
            or "secure" in rfp_lower
            or "escort_required" in meta.get("access_restrictions", []),
            "traffic_control_needed": "highway" in rfp_lower
            or "interstate" in rfp_lower
            or "highway_traffic" in meta.get("access_restrictions", []),
            "confined_space": "tunnel" in rfp_lower or "culvert" in rfp_lower,
            "access_restrictions": meta.get("access_restrictions", []),
            "source": "RFP",
        },
        "sensors_identified": sorted(sensors_needed),
        "task_count": len(task_specs),
        "note": (
            "Site recon generated from RFP text analysis. "
            "Fields tagged INFERRED should be verified with public data sources (FAA, USGS, NOAA)."
        ),
    }
