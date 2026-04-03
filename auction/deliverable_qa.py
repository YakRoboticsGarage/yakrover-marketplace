"""Deliverable quality assurance — flexible, buyer-configurable.

QA levels (set per-task in capability_requirements.qa_level):
  0: none      — accept on delivery, no checks (buyer trusts vendor)
  1: basic     — data exists, format valid, required fields present
  2: standards — point density, accuracy, CRS per ASPRS/USGS specs
  3: pls       — PLS review required before payment release

Level 0 is the default for simple tasks (env_sensing, demo).
Level 1 is the default for construction tasks.
Level 2 requires standards fields in the task spec (asprs_*, usgs_*).
Level 3 requires a PLS-stamped operator or PLS-as-a-service routing.

The buyer can override the default by setting qa_level explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# QA result
# ---------------------------------------------------------------------------


@dataclass
class QAResult:
    """Result of running QA checks on a delivery."""

    status: str  # "PASS", "WARN", "FAIL"
    level: int  # QA level that was applied (0-3)
    issues: list[str] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in ("PASS", "WARN")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "level": self.level,
            "level_name": QA_LEVEL_NAMES.get(self.level, "unknown"),
            "issues": self.issues,
            "checks_run": self.checks_run,
            "details": self.details,
            "passed": self.passed,
        }


QA_LEVEL_NAMES = {
    0: "none",
    1: "basic",
    2: "standards",
    3: "pls",
}

# Default QA level by task category
DEFAULT_QA_LEVELS = {
    "env_sensing": 1,
    "visual_inspection": 1,
    "mapping": 1,
    "delivery_ground": 1,
    "aerial_survey": 2,
    "site_survey": 2,
    "bridge_inspection": 2,
    "progress_monitoring": 1,
    "as_built": 2,
    "subsurface_scan": 1,
    "environmental_survey": 1,
    "control_survey": 2,
}


# ---------------------------------------------------------------------------
# QA engine
# ---------------------------------------------------------------------------


def get_qa_level(task_spec: dict) -> int:
    """Determine QA level for a task.

    Priority: explicit qa_level > task category default > 1.
    """
    # Explicit override
    cap_req = task_spec.get("capability_requirements", {})
    explicit = cap_req.get("qa_level")
    if explicit is not None:
        return max(0, min(3, int(explicit)))

    # Default by category
    category = task_spec.get("task_category", "")
    return DEFAULT_QA_LEVELS.get(category, 1)


def check_delivery(
    delivery_data: dict,
    task_spec: dict,
    *,
    qa_level: int | None = None,
) -> QAResult:
    """Run QA checks on delivery data at the appropriate level.

    Args:
        delivery_data: The robot's delivered data dict.
        task_spec: The original task specification.
        qa_level: Override QA level (if None, determined from task_spec).

    Returns:
        QAResult with status, issues, and details.
    """
    level = qa_level if qa_level is not None else get_qa_level(task_spec)

    if level == 0:
        return _check_level_0(delivery_data, task_spec)
    elif level == 1:
        return _check_level_1(delivery_data, task_spec)
    elif level == 2:
        return _check_level_2(delivery_data, task_spec)
    elif level == 3:
        return _check_level_3(delivery_data, task_spec)
    else:
        return QAResult(status="PASS", level=0, checks_run=["none"])


def _check_level_0(data: dict, spec: dict) -> QAResult:
    """Level 0: Accept on delivery. No checks."""
    return QAResult(
        status="PASS",
        level=0,
        checks_run=["none (buyer trusts vendor)"],
    )


def _check_level_1(data: dict, spec: dict) -> QAResult:
    """Level 1: Basic checks — data exists, format valid, fields present."""
    issues: list[str] = []
    checks: list[str] = []
    details: dict[str, Any] = {}

    # Check data is non-empty
    checks.append("data_exists")
    if not data:
        issues.append("Delivery data is empty")
        return QAResult(status="FAIL", level=1, issues=issues, checks_run=checks)

    details["field_count"] = len(data)

    # Check required fields from payload spec
    payload_spec = spec.get("capability_requirements", {}).get("payload", {})
    required_fields = payload_spec.get("fields", [])

    if required_fields:
        checks.append("required_fields")
        missing = [f for f in required_fields if f not in data]
        if missing:
            issues.append(f"Missing required fields: {missing}")
        details["required_fields"] = required_fields
        details["missing_fields"] = missing if required_fields else []

    # Check format
    payload_format = payload_spec.get("format", "json")
    checks.append("format_valid")
    if payload_format == "json" and not isinstance(data, dict):
        issues.append(f"Expected JSON dict, got {type(data).__name__}")

    # Plausibility checks for known sensor types
    checks.append("plausibility")
    _check_sensor_plausibility(data, issues, details)

    # Check for readings array (common delivery pattern)
    readings = data.get("readings")
    if readings is not None:
        checks.append("readings_present")
        if isinstance(readings, list):
            details["reading_count"] = len(readings)
            if len(readings) == 0:
                issues.append("Readings array is empty")
        else:
            issues.append(f"Readings should be a list, got {type(readings).__name__}")

    status = (
        "FAIL" if any("Missing required" in i or "empty" in i.lower() for i in issues) else "WARN" if issues else "PASS"
    )

    return QAResult(status=status, level=1, issues=issues, checks_run=checks, details=details)


def _check_level_2(data: dict, spec: dict) -> QAResult:
    """Level 2: Standards validation — ASPRS accuracy, USGS density, CRS."""
    # Run level 1 first
    result = _check_level_1(data, spec)
    if result.status == "FAIL":
        result.level = 2
        return result

    issues = list(result.issues)
    checks = list(result.checks_run)
    details = dict(result.details)

    hard = spec.get("capability_requirements", {}).get("hard", {})

    # Check CRS
    crs_epsg = hard.get("crs_epsg")
    if crs_epsg is not None:
        checks.append("crs_check")
        delivered_crs = data.get("coordinate_system") or data.get("crs_epsg") or data.get("crs")
        if delivered_crs:
            details["crs_delivered"] = str(delivered_crs)
        else:
            issues.append("No coordinate reference system in delivery (crs_epsg required)")

    # Check accuracy reporting
    asprs_class = hard.get("asprs_vertical_class") or hard.get("asprs_horizontal_class")
    if asprs_class is not None:
        checks.append("accuracy_reporting")
        accuracy = data.get("accuracy") or data.get("accuracy_report") or data.get("rmse")
        if accuracy:
            details["accuracy_reported"] = True
            details["accuracy_data"] = accuracy
        else:
            issues.append("Task requires ASPRS accuracy class but delivery has no accuracy reporting")

    # Check point density for LiDAR tasks
    usgs_ql = hard.get("usgs_quality_level")
    if usgs_ql is not None:
        checks.append("point_density")
        density = data.get("point_density_ppsm") or data.get("density")
        min_density = {"QL0": 20, "QL1": 8, "QL2": 2, "QL3": 0.5}.get(usgs_ql)
        if density is not None and min_density is not None:
            details["point_density_ppsm"] = density
            details["required_density_ppsm"] = min_density
            if density < min_density:
                issues.append(f"Point density {density} pts/m² below {usgs_ql} requirement ({min_density} pts/m²)")
        elif density is None and min_density is not None:
            issues.append(f"Task requires {usgs_ql} quality level but delivery has no point density data")

    # Check deliverables list
    deliverables_spec = spec.get("capability_requirements", {}).get("deliverables", [])
    if deliverables_spec:
        checks.append("deliverables_check")
        delivered_files = data.get("files") or data.get("deliverables") or data.get("file_manifest")
        if delivered_files and isinstance(delivered_files, list):
            details["files_delivered"] = len(delivered_files)
            details["files_required"] = len(deliverables_spec)
        elif not delivered_files:
            issues.append(f"Task specifies {len(deliverables_spec)} deliverable(s) but delivery has no file list")

    status = (
        "FAIL"
        if any("below" in i.lower() or "missing required" in i.lower() for i in issues)
        else "WARN"
        if issues
        else "PASS"
    )

    return QAResult(status=status, level=2, issues=issues, checks_run=checks, details=details)


def _check_level_3(data: dict, spec: dict) -> QAResult:
    """Level 3: PLS review required — run level 2 + check PLS stamp."""
    result = _check_level_2(data, spec)
    issues = list(result.issues)
    checks = list(result.checks_run)
    details = dict(result.details)

    checks.append("pls_stamp")
    pls_status = data.get("pls_review_status")
    if pls_status == "APPROVED":
        details["pls_stamp"] = "approved"
    elif pls_status == "PENDING":
        issues.append("PLS review pending — deliverables not yet stamped")
    elif pls_status == "REJECTED":
        issues.append("PLS review rejected — deliverables do not meet standards")
    else:
        issues.append("No PLS review status in delivery — PLS stamp required for this task")

    status = (
        "FAIL"
        if any("rejected" in i.lower() or "no pls" in i.lower() for i in issues)
        else "WARN"
        if issues
        else "PASS"
    )

    return QAResult(status=status, level=3, issues=issues, checks_run=checks, details=details)


# ---------------------------------------------------------------------------
# Sensor plausibility checks
# ---------------------------------------------------------------------------


def _check_sensor_plausibility(data: dict, issues: list[str], details: dict) -> None:
    """Check sensor readings are within plausible ranges."""

    # Temperature
    for key in ("temperature_celsius", "temperature_c"):
        temp = data.get(key)
        if temp is not None:
            if not (-40 <= temp <= 85):
                issues.append(f"{key} = {temp}°C outside plausible range [-40, 85]")
            details["temperature"] = temp

    # Humidity
    for key in ("humidity_percent", "humidity_pct"):
        hum = data.get(key)
        if hum is not None:
            if not (0 <= hum <= 100):
                issues.append(f"{key} = {hum}% outside plausible range [0, 100]")
            details["humidity"] = hum

    # Check readings array for sensor data
    readings = data.get("readings")
    if isinstance(readings, list):
        for i, r in enumerate(readings):
            if not isinstance(r, dict):
                continue
            for key in ("temperature_c", "temperature_celsius"):
                t = r.get(key)
                if t is not None and not (-40 <= t <= 85):
                    issues.append(f"readings[{i}].{key} = {t}°C outside plausible range")
            for key in ("humidity_pct", "humidity_percent"):
                h = r.get(key)
                if h is not None and not (0 <= h <= 100):
                    issues.append(f"readings[{i}].{key} = {h}% outside plausible range")
