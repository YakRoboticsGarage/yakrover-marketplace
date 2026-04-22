"""IMP-052: End-to-end delivery schema verification across all 9 category simulators.

Each test generates simulated delivery data matching what the category server
would return, then validates it against the corresponding delivery schema.
"""

import random
import time

from auction.deliverable_qa import validate_delivery_schema
from auction.delivery_schemas import (
    AERIAL_LIDAR_SCHEMA,
    AERIAL_PHOTO_SCHEMA,
    AERIAL_THERMAL_SCHEMA,
    BRIDGE_INSPECTION_SCHEMA,
    CONFINED_SCHEMA,
    CORRIDOR_SCHEMA,
    ENV_SENSING_SCHEMA,
    GROUND_DELIVERY_SCHEMA,
    GROUND_GPR_SCHEMA,
    GROUND_LIDAR_SCHEMA,
    get_delivery_schema,
)

# ── Simulated data generators (mirrors category_server.py) ────────


def sim_gps(lat=42.5, lng=-83.5):
    return {
        "latitude": round(lat + random.uniform(-0.01, 0.01), 6),
        "longitude": round(lng + random.uniform(-0.01, 0.01), 6),
        "altitude_m": round(random.uniform(50, 120), 1),
        "fix": "RTK_FIXED",
        "satellites": random.randint(12, 24),
    }


def make_aerial_lidar_delivery():
    area = random.randint(20000, 80000)
    density = round(random.uniform(2.0, 12.0), 1)
    return {
        "point_cloud": {
            "format": "LAS 1.4",
            "version": "1.4",
            "point_count": int(area * density),
            "density_pts_m2": density,
            "area_m2": area,
            "classifications": [
                "ground",
                "low_vegetation",
                "medium_vegetation",
                "high_vegetation",
                "building",
                "noise",
            ],
            "bounding_box": {"min": sim_gps(), "max": sim_gps()},
        },
        "quality_metrics": {
            "horizontal_accuracy_cm": round(random.uniform(2.0, 3.5), 1),
            "vertical_accuracy_cm": round(random.uniform(3.0, 5.0), 1),
            "control_points_used": random.randint(6, 15),
            "overlap_pct": random.randint(60, 75),
        },
        "coordinate_system": {
            "epsg": 2253,
            "datum": "NAD83(2011)",
            "projection": "Michigan State Plane South",
        },
        "summary": f"Aerial LiDAR survey complete. {random.randint(3, 8)} flight lines captured.",
    }


def make_aerial_photo_delivery():
    return {
        "orthomosaic": {
            "format": "GeoTIFF",
            "gsd_cm": round(random.uniform(0.8, 3.5), 2),
            "width_px": random.randint(10000, 50000),
            "height_px": random.randint(8000, 40000),
            "bands": 4,
            "bounding_box": {"min": sim_gps(), "max": sim_gps()},
        },
        "photo_set": {
            "total_photos": random.randint(80, 400),
            "overlap_frontal_pct": random.randint(75, 85),
            "overlap_side_pct": random.randint(65, 75),
            "camera_model": "DJI Zenmuse P1 / FC6360",
        },
        "quality_metrics": {
            "horizontal_accuracy_cm": round(random.uniform(1, 4), 1),
            "vertical_accuracy_cm": round(random.uniform(2, 6), 1),
            "reprojection_error_px": round(random.uniform(0.3, 0.8), 2),
            "ground_control_points": random.randint(4, 10),
        },
        "summary": f"Photogrammetry complete. {random.randint(80, 400)} photos processed.",
    }


def make_ground_gpr_delivery():
    utilities = []
    for _ in range(random.randint(2, 8)):
        utilities.append(
            {
                "type": random.choice(["water", "sewer", "electric", "gas", "telecom"]),
                "depth_m": round(random.uniform(0.3, 2.5), 2),
                "confidence": round(random.uniform(0.6, 0.98), 2),
                "apwa_color": random.choice(["blue", "green", "red", "yellow", "orange"]),
                "position": sim_gps(),
            }
        )
    return {
        "scan_data": {
            "format": "DZT",
            "scan_lines": random.randint(10, 60),
            "total_length_m": round(random.uniform(50, 500), 1),
            "depth_m": round(random.uniform(1, 3), 1),
            "antenna_frequency_mhz": 1600,
        },
        "utility_detections": utilities,
        "survey_parameters": {
            "coordinate_system": "EPSG:2253 Michigan State Plane South",
            "accuracy_horizontal_cm": 15,
            "accuracy_depth_pct": 10,
            "asce_38_quality_level": "B",
        },
        "summary": f"GPR survey complete. {len(utilities)} utilities detected.",
    }


def make_aerial_thermal_delivery():
    anomalies = []
    for _ in range(random.randint(1, 5)):
        anomalies.append(
            {
                "severity": random.choice(["low", "medium", "high", "critical"]),
                "delta_t_c": round(random.uniform(2, 15), 1),
                "area_m2": round(random.uniform(0.5, 20), 1),
                "classification": random.choice(["moisture", "insulation_gap", "membrane_failure"]),
                "position": sim_gps(),
            }
        )
    return {
        "thermal_mosaic": {
            "format": "RJPEG",
            "resolution": "640x512",
            "temp_range_c": {
                "min": round(random.uniform(-5, 10), 1),
                "max": round(random.uniform(30, 65), 1),
            },
            "emissivity": 0.95,
            "images_captured": random.randint(50, 200),
        },
        "anomalies": anomalies,
        "survey_conditions": {
            "ambient_temp_c": round(random.uniform(5, 25), 1),
            "wind_speed_mph": round(random.uniform(2, 12), 1),
            "sky_condition": random.choice(["clear", "partly_cloudy", "overcast"]),
            "time_of_day": "pre-dawn",
        },
        "summary": f"Thermal survey complete. {len(anomalies)} anomalies detected.",
    }


def make_bridge_inspection_delivery():
    elements = []
    for elem in ["deck", "superstructure", "substructure", "bearings", "joints"]:
        elements.append(
            {
                "element": elem,
                "condition_state": random.randint(1, 4),
                "quantity_pct": round(random.uniform(60, 100), 1),
                "defects": random.sample(
                    ["spalling", "cracking", "corrosion", "delamination", "efflorescence"],
                    random.randint(0, 3),
                ),
            }
        )
    return {
        "inspection_set": {
            "total_images": random.randint(100, 400),
            "coverage_pct": round(random.uniform(85, 99), 1),
            "resolution_mp": 48,
            "gsd_mm": round(random.uniform(0.5, 2), 1),
        },
        "element_ratings": elements,
        "summary": f"Bridge inspection complete. {len(elements)} elements rated per NBI coding.",
    }


def make_ground_lidar_delivery():
    positions = [
        {
            "position_id": i + 1,
            "point_count": random.randint(500000, 2000000),
            "overlap_pct": round(random.uniform(30, 60), 1),
        }
        for i in range(random.randint(5, 15))
    ]
    return {
        "point_cloud": {
            "format": "E57",
            "point_count": sum(p["point_count"] for p in positions),
            "scan_positions": len(positions),
            "registration_error_mm": round(random.uniform(1, 5), 1),
        },
        "scan_positions": positions,
        "quality_metrics": {
            "registration_error_mm": round(random.uniform(1, 5), 1),
            "coverage_pct": round(random.uniform(90, 99), 1),
        },
        "summary": f"Ground LiDAR scan complete. {len(positions)} positions registered.",
    }


def make_confined_delivery():
    return {
        "point_cloud": {
            "format": "PLY",
            "point_count": random.randint(100000, 1000000),
            "positioning_method": "SLAM",
            "slam_confidence": round(random.uniform(0.75, 0.98), 2),
        },
        "inspection_photos": {
            "total_photos": random.randint(30, 150),
            "lighting": "onboard_led",
            "resolution_mp": 12,
        },
        "obstacle_map": {
            "obstacles_detected": random.randint(0, 8),
            "clearance_min_m": round(random.uniform(0.5, 3), 1),
        },
        "summary": "Confined space inspection complete. SLAM-based positioning.",
    }


def make_env_sensing_delivery():
    readings = [
        {
            "waypoint": i + 1,
            "temperature_c": round(random.uniform(18, 32), 1),
            "humidity_pct": round(random.uniform(30, 70), 1),
            "timestamp": str(time.time() + i * 60),
        }
        for i in range(3)
    ]
    return {
        "readings": readings,
        "summary": "Environmental readings captured at 3 waypoints.",
        "duration_seconds": round(random.uniform(10, 120), 1),
    }


def make_ground_delivery():
    start_ts = int(time.time() * 1000)
    commands = ["forward", "left", "forward", "right", "stop"]
    command_log = [
        {
            "command": cmd,
            "timestamp_ms": start_ts + i * 1000,
            "duration_ms": random.randint(200, 1500),
        }
        for i, cmd in enumerate(commands)
    ]
    return {
        "task_id": f"task_{random.randint(1000, 9999)}",
        "commands_executed": command_log,
        "duration_s": round(sum(c["duration_ms"] for c in command_log) / 1000.0, 2),
        "completion_status": "completed",
        "robot_id": "8453:42",
        "summary": f"Executed {len(commands)} motor commands.",
    }


# Corridor reuses aerial LiDAR structure with additions
def make_corridor_delivery():
    base = make_aerial_lidar_delivery()
    base["corridor_metrics"] = {
        "length_m": round(random.uniform(500, 5000), 1),
        "width_m": round(random.uniform(20, 60), 1),
        "cross_sections": random.randint(10, 100),
        "cross_section_interval_m": round(random.uniform(10, 50), 1),
    }
    return base


# ── Tests ────────────────────────────────────────────────────────


class TestAerialLidar:
    def test_schema_passes(self):
        data = make_aerial_lidar_delivery()
        issues = validate_delivery_schema(data, AERIAL_LIDAR_SCHEMA)
        assert issues == [], f"Aerial LiDAR schema failed: {issues}"

    def test_category_mapping(self):
        for cat in ["topo_survey", "aerial_survey", "volumetric", "site_survey", "control_survey", "mapping"]:
            schema = get_delivery_schema(cat)
            assert schema == AERIAL_LIDAR_SCHEMA, f"{cat} should map to AERIAL_LIDAR_SCHEMA"


class TestAerialPhoto:
    def test_schema_passes(self):
        data = make_aerial_photo_delivery()
        issues = validate_delivery_schema(data, AERIAL_PHOTO_SCHEMA)
        assert issues == [], f"Aerial photo schema failed: {issues}"

    def test_category_mapping(self):
        for cat in ["progress_monitoring", "visual_inspection", "environmental_survey"]:
            schema = get_delivery_schema(cat)
            assert schema == AERIAL_PHOTO_SCHEMA, f"{cat} should map to AERIAL_PHOTO_SCHEMA"


class TestGroundGPR:
    def test_schema_passes(self):
        data = make_ground_gpr_delivery()
        issues = validate_delivery_schema(data, GROUND_GPR_SCHEMA)
        assert issues == [], f"Ground GPR schema failed: {issues}"

    def test_category_mapping(self):
        for cat in ["subsurface_scan", "utility_detection"]:
            schema = get_delivery_schema(cat)
            assert schema == GROUND_GPR_SCHEMA, f"{cat} should map to GROUND_GPR_SCHEMA"


class TestAerialThermal:
    def test_schema_passes(self):
        data = make_aerial_thermal_delivery()
        issues = validate_delivery_schema(data, AERIAL_THERMAL_SCHEMA)
        assert issues == [], f"Aerial thermal schema failed: {issues}"

    def test_category_mapping(self):
        assert get_delivery_schema("thermal_inspection") == AERIAL_THERMAL_SCHEMA


class TestBridgeInspection:
    def test_schema_passes(self):
        data = make_bridge_inspection_delivery()
        issues = validate_delivery_schema(data, BRIDGE_INSPECTION_SCHEMA)
        assert issues == [], f"Bridge inspection schema failed: {issues}"

    def test_category_mapping(self):
        assert get_delivery_schema("bridge_inspection") == BRIDGE_INSPECTION_SCHEMA


class TestGroundLidar:
    def test_schema_passes(self):
        data = make_ground_lidar_delivery()
        issues = validate_delivery_schema(data, GROUND_LIDAR_SCHEMA)
        assert issues == [], f"Ground LiDAR schema failed: {issues}"

    def test_category_mapping(self):
        assert get_delivery_schema("as_built") == GROUND_LIDAR_SCHEMA


class TestConfined:
    def test_schema_passes(self):
        data = make_confined_delivery()
        issues = validate_delivery_schema(data, CONFINED_SCHEMA)
        assert issues == [], f"Confined space schema failed: {issues}"

    def test_category_mapping(self):
        assert get_delivery_schema("confined_space") == CONFINED_SCHEMA


class TestEnvSensing:
    def test_schema_passes(self):
        data = make_env_sensing_delivery()
        issues = validate_delivery_schema(data, ENV_SENSING_SCHEMA)
        assert issues == [], f"Env sensing schema failed: {issues}"

    def test_category_mapping(self):
        for cat in ["env_sensing", "sensor_reading"]:
            schema = get_delivery_schema(cat)
            assert schema == ENV_SENSING_SCHEMA, f"{cat} should map to ENV_SENSING_SCHEMA"


class TestCorridor:
    def test_schema_passes(self):
        data = make_corridor_delivery()
        issues = validate_delivery_schema(data, CORRIDOR_SCHEMA)
        assert issues == [], f"Corridor schema failed: {issues}"

    def test_category_mapping(self):
        assert get_delivery_schema("corridor_survey") == CORRIDOR_SCHEMA


class TestGroundDelivery:
    def test_schema_passes(self):
        data = make_ground_delivery()
        issues = validate_delivery_schema(data, GROUND_DELIVERY_SCHEMA)
        assert issues == [], f"Ground delivery schema failed: {issues}"

    def test_category_mapping(self):
        assert get_delivery_schema("delivery_ground") == GROUND_DELIVERY_SCHEMA

    def test_missing_required_field_fails(self):
        data = make_ground_delivery()
        del data["commands_executed"]
        issues = validate_delivery_schema(data, GROUND_DELIVERY_SCHEMA)
        assert any("commands_executed" in i for i in issues), (
            f"Expected missing-field issue for commands_executed, got: {issues}"
        )

    def test_empty_command_log_fails(self):
        data = make_ground_delivery()
        data["commands_executed"] = []
        issues = validate_delivery_schema(data, GROUND_DELIVERY_SCHEMA)
        assert any("minimum 1" in i for i in issues), (
            f"Expected minItems violation for empty commands_executed, got: {issues}"
        )


class TestAllCategoriesCovered:
    """Verify every task category in the mapping has a test."""

    def test_all_categories_mapped(self):
        from auction.delivery_schemas import DELIVERY_SCHEMAS

        assert len(DELIVERY_SCHEMAS) == 19
        for cat in DELIVERY_SCHEMAS:
            schema = get_delivery_schema(cat)
            assert schema is not None, f"No schema for {cat}"
