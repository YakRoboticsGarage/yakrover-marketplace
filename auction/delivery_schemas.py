"""Category-specific delivery schemas for QA validation.

Vertical: construction (ASPRS, USGS, ASCE 38, ASTM, NBI standards)

Each schema defines the expected structure of delivery data from a robot
in that category. The schema is included in the task spec so the robot
can self-validate before submitting, and the QA engine validates on receipt.

Schema format follows the same JSON Schema subset used by deliverable_qa.py:
  required: list of required top-level keys
  properties: dict of field definitions with type, minimum, maximum, minItems, etc.
"""

# ── Aerial LiDAR (M350+L2, Freefly Astro, IF1200) ────────────────
# Deliverables: LAS 1.4 point cloud, DEM, contours
# Standards: ASPRS Positional Accuracy, USGS LBS v2.1

AERIAL_LIDAR_SCHEMA = {
    "description": "Aerial LiDAR survey deliverable — point cloud metadata and quality metrics",
    "required": ["point_cloud", "quality_metrics", "coordinate_system", "summary"],
    "properties": {
        "point_cloud": {
            "type": "object",
            "required": ["format", "version", "point_count", "density_pts_m2", "area_m2", "classifications"],
            "properties": {
                "format": {"type": "string"},  # "LAS 1.4"
                "version": {"type": "string"},
                "point_count": {"type": "integer", "minimum": 1000},
                "density_pts_m2": {"type": "number", "minimum": 1.0},
                "area_m2": {"type": "number", "minimum": 10},
                "classifications": {"type": "array", "minItems": 1},  # ["ground", "vegetation", "building"]
                "bounding_box": {"type": "object"},
            },
        },
        "quality_metrics": {
            "type": "object",
            "required": ["horizontal_accuracy_cm", "vertical_accuracy_cm"],
            "properties": {
                "horizontal_accuracy_cm": {"type": "number", "minimum": 0},
                "vertical_accuracy_cm": {"type": "number", "minimum": 0},
                "control_points_used": {"type": "integer", "minimum": 0},
                "overlap_pct": {"type": "number", "minimum": 0, "maximum": 100},
            },
        },
        "coordinate_system": {
            "type": "object",
            "required": ["epsg", "datum"],
            "properties": {
                "epsg": {"type": "integer"},
                "datum": {"type": "string"},
                "projection": {"type": "string"},
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── Aerial Photogrammetry (M350+P1, Mavic 3E, Autel EVO) ─────────
# Deliverables: orthomosaic GeoTIFF, 3D point cloud, DSM
# Standards: ASPRS accuracy, GSD requirements

AERIAL_PHOTO_SCHEMA = {
    "description": "Aerial photogrammetry deliverable — orthomosaic and 3D model metadata",
    "required": ["orthomosaic", "photo_set", "quality_metrics", "summary"],
    "properties": {
        "orthomosaic": {
            "type": "object",
            "required": ["format", "gsd_cm", "width_px", "height_px"],
            "properties": {
                "format": {"type": "string"},  # "GeoTIFF"
                "gsd_cm": {"type": "number", "minimum": 0.1},
                "width_px": {"type": "integer", "minimum": 100},
                "height_px": {"type": "integer", "minimum": 100},
                "bands": {"type": "integer"},
                "bounding_box": {"type": "object"},
            },
        },
        "photo_set": {
            "type": "object",
            "required": ["total_photos", "overlap_frontal_pct", "overlap_side_pct"],
            "properties": {
                "total_photos": {"type": "integer", "minimum": 1},
                "overlap_frontal_pct": {"type": "number", "minimum": 50},
                "overlap_side_pct": {"type": "number", "minimum": 50},
                "camera_model": {"type": "string"},
            },
        },
        "quality_metrics": {
            "type": "object",
            "required": ["horizontal_accuracy_cm", "vertical_accuracy_cm"],
            "properties": {
                "horizontal_accuracy_cm": {"type": "number", "minimum": 0},
                "vertical_accuracy_cm": {"type": "number", "minimum": 0},
                "reprojection_error_px": {"type": "number", "minimum": 0},
                "ground_control_points": {"type": "integer", "minimum": 0},
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── Ground GPR (Spot + GSSI StructureScan) ────────────────────────
# Deliverables: DZT scan files, utility map (DXF), anomaly report
# Standards: ASCE 38 (utility quality levels), APWA color codes

GROUND_GPR_SCHEMA = {
    "description": "GPR subsurface scan deliverable — utility detection and scan metadata",
    "required": ["scan_data", "utility_detections", "survey_parameters", "summary"],
    "properties": {
        "scan_data": {
            "type": "object",
            "required": ["format", "scan_lines", "total_length_m", "depth_m"],
            "properties": {
                "format": {"type": "string"},  # "DZT"
                "scan_lines": {"type": "integer", "minimum": 1},
                "total_length_m": {"type": "number", "minimum": 0.1},
                "depth_m": {"type": "number", "minimum": 0.1},
                "antenna_frequency_mhz": {"type": "integer"},
            },
        },
        "utility_detections": {
            "type": "array",
            "minItems": 0,
            "items": {
                "type": "object",
                "required": ["type", "depth_m", "confidence"],
                "properties": {
                    "type": {"type": "string"},  # "water", "sewer", "electric", "gas", "telecom", "unknown"
                    "depth_m": {"type": "number", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "apwa_color": {"type": "string"},  # APWA Uniform Color Code
                    "position": {"type": "object"},
                },
            },
        },
        "survey_parameters": {
            "type": "object",
            "required": ["coordinate_system", "accuracy_horizontal_cm"],
            "properties": {
                "coordinate_system": {"type": "string"},
                "accuracy_horizontal_cm": {"type": "number", "minimum": 0},
                "accuracy_depth_pct": {"type": "number", "minimum": 0},
                "asce_38_quality_level": {"type": "string"},  # "A", "B", "C", "D"
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── Aerial Thermal (M350+H30T) ────────────────────────────────────
# Deliverables: radiometric thermal mosaic, anomaly map, visual reference
# Standards: ASTM C1153 (roof moisture), RESNET (building envelope)

AERIAL_THERMAL_SCHEMA = {
    "description": "Thermal inspection deliverable — anomaly detection and thermal metrics",
    "required": ["thermal_mosaic", "anomalies", "survey_conditions", "summary"],
    "properties": {
        "thermal_mosaic": {
            "type": "object",
            "required": ["format", "resolution", "temp_range_c"],
            "properties": {
                "format": {"type": "string"},  # "RJPEG" or "TIFF"
                "resolution": {"type": "string"},  # "640x512"
                "temp_range_c": {"type": "object"},
                "emissivity": {"type": "number", "minimum": 0, "maximum": 1},
                "images_captured": {"type": "integer", "minimum": 1},
            },
        },
        "anomalies": {
            "type": "array",
            "minItems": 0,
            "items": {
                "type": "object",
                "required": ["severity", "delta_t_c", "position"],
                "properties": {
                    "severity": {"type": "string"},  # "low", "medium", "high", "critical"
                    "delta_t_c": {"type": "number"},
                    "area_m2": {"type": "number", "minimum": 0},
                    "classification": {"type": "string"},  # "moisture", "insulation_gap", "membrane_failure"
                    "position": {"type": "object"},
                },
            },
        },
        "survey_conditions": {
            "type": "object",
            "required": ["ambient_temp_c", "wind_speed_mph"],
            "properties": {
                "ambient_temp_c": {"type": "number"},
                "wind_speed_mph": {"type": "number", "minimum": 0},
                "sky_condition": {"type": "string"},
                "time_of_day": {"type": "string"},
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── Bridge / Skydio Inspection ────────────────────────────────────
# Deliverables: annotated inspection photos, element condition ratings
# Standards: NBI (National Bridge Inventory), AASHTO element-level

BRIDGE_INSPECTION_SCHEMA = {
    "description": "Bridge/structure inspection deliverable — element ratings and photo documentation",
    "required": ["inspection_set", "element_ratings", "summary"],
    "properties": {
        "inspection_set": {
            "type": "object",
            "required": ["total_images", "coverage_pct"],
            "properties": {
                "total_images": {"type": "integer", "minimum": 1},
                "coverage_pct": {"type": "number", "minimum": 0, "maximum": 100},
                "resolution_mp": {"type": "number", "minimum": 1},
                "gsd_mm": {"type": "number", "minimum": 0},
            },
        },
        "element_ratings": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["element", "condition_state", "quantity_pct"],
                "properties": {
                    "element": {"type": "string"},  # "deck", "superstructure", "substructure", "bearing"
                    "condition_state": {"type": "integer", "minimum": 1, "maximum": 4},  # NBI 1-4
                    "quantity_pct": {"type": "number", "minimum": 0, "maximum": 100},
                    "defects": {"type": "array"},
                },
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── Fixed-Wing Corridor (WingtraOne) ──────────────────────────────
# Same as aerial LiDAR but with corridor-specific metadata
CORRIDOR_SCHEMA = AERIAL_LIDAR_SCHEMA.copy()
CORRIDOR_SCHEMA["description"] = "Fixed-wing corridor survey deliverable — extended LiDAR coverage"


# ── Ground LiDAR / Terrestrial (Spot + BLK ARC) ──────────────────
# Deliverables: registered point cloud, cross-sections, as-built comparison
GROUND_LIDAR_SCHEMA = {
    "description": "Ground LiDAR as-built deliverable — interior/tunnel scan metadata",
    "required": ["point_cloud", "scan_positions", "quality_metrics", "summary"],
    "properties": {
        "point_cloud": {
            "type": "object",
            "required": ["format", "point_count", "scan_positions"],
            "properties": {
                "format": {"type": "string"},
                "point_count": {"type": "integer", "minimum": 1000},
                "scan_positions": {"type": "integer", "minimum": 1},
                "registration_error_mm": {"type": "number", "minimum": 0},
            },
        },
        "scan_positions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["position_id", "point_count"],
                "properties": {
                    "position_id": {"type": "integer"},
                    "point_count": {"type": "integer"},
                    "overlap_pct": {"type": "number"},
                },
            },
        },
        "quality_metrics": {
            "type": "object",
            "required": ["registration_error_mm"],
            "properties": {
                "registration_error_mm": {"type": "number", "minimum": 0},
                "coverage_pct": {"type": "number", "minimum": 0, "maximum": 100},
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── Confined Space (ELIOS 3) ──────────────────────────────────────
# Deliverables: indoor point cloud, inspection photos, obstacle map
CONFINED_SCHEMA = {
    "description": "Confined space inspection deliverable — GPS-denied indoor scan",
    "required": ["point_cloud", "inspection_photos", "obstacle_map", "summary"],
    "properties": {
        "point_cloud": {
            "type": "object",
            "required": ["format", "point_count", "positioning_method"],
            "properties": {
                "format": {"type": "string"},
                "point_count": {"type": "integer", "minimum": 100},
                "positioning_method": {"type": "string"},  # "SLAM"
                "slam_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "inspection_photos": {
            "type": "object",
            "required": ["total_photos"],
            "properties": {
                "total_photos": {"type": "integer", "minimum": 1},
                "lighting": {"type": "string"},  # "onboard_led"
                "resolution_mp": {"type": "number"},
            },
        },
        "obstacle_map": {
            "type": "object",
            "required": ["obstacles_detected"],
            "properties": {
                "obstacles_detected": {"type": "integer", "minimum": 0},
                "clearance_min_m": {"type": "number", "minimum": 0},
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


# ── FakeRover / Env Sensing (temperature + humidity) ──────────────
ENV_SENSING_SCHEMA = {
    "description": "Environmental sensor readings — temperature and humidity at waypoints",
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
}


# ── Category → Schema mapping ────────────────────────────────────

DELIVERY_SCHEMAS = {
    # Task categories → delivery schema
    "topo_survey": AERIAL_LIDAR_SCHEMA,
    "aerial_survey": AERIAL_LIDAR_SCHEMA,
    "volumetric": AERIAL_LIDAR_SCHEMA,
    "corridor_survey": CORRIDOR_SCHEMA,
    "progress_monitoring": AERIAL_PHOTO_SCHEMA,
    "visual_inspection": AERIAL_PHOTO_SCHEMA,
    "subsurface_scan": GROUND_GPR_SCHEMA,
    "utility_detection": GROUND_GPR_SCHEMA,
    "thermal_inspection": AERIAL_THERMAL_SCHEMA,
    "bridge_inspection": BRIDGE_INSPECTION_SCHEMA,
    "as_built": GROUND_LIDAR_SCHEMA,
    "confined_space": CONFINED_SCHEMA,
    "env_sensing": ENV_SENSING_SCHEMA,
    "sensor_reading": ENV_SENSING_SCHEMA,
    "site_survey": AERIAL_LIDAR_SCHEMA,
    "environmental_survey": AERIAL_PHOTO_SCHEMA,
    "control_survey": AERIAL_LIDAR_SCHEMA,
    "mapping": AERIAL_LIDAR_SCHEMA,
}


def get_delivery_schema(task_category: str) -> dict:
    """Get the delivery schema for a task category. Falls back to env_sensing."""
    return DELIVERY_SCHEMAS.get(task_category, ENV_SENSING_SCHEMA)
