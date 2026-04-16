"""Canonical sensor registry with alias normalization.

Provides a single source of truth for valid sensor names and maps
common aliases (from RFPs, natural language, equipment specs) to
canonical forms used by the auction engine.

Usage:
    from auction.sensor_registry import normalize_sensor, normalize_sensors

    normalize_sensor("LiDAR")           # -> "aerial_lidar"
    normalize_sensor("ground_penetrating_radar")  # -> "gpr"
    normalize_sensors(["LiDAR", "GPS"]) # -> ["aerial_lidar", "rtk_gps"]
"""

from __future__ import annotations

# Canonical sensor names — the only values that should appear in
# task specs and robot capability profiles.
CANONICAL_SENSORS = frozenset(
    [
        "aerial_lidar",
        "terrestrial_lidar",
        "photogrammetry",
        "thermal_camera",
        "gpr",
        "rtk_gps",
        "robotic_total_station",
        # Generic/legacy sensors (v0.x compat)
        "temperature",
        "humidity",
        "rgb_camera",
    ]
)

# Alias map: lowercase alias -> canonical sensor name.
# Multiple aliases can map to the same canonical sensor.
_ALIASES: dict[str, str] = {
    # aerial_lidar
    "lidar": "aerial_lidar",
    "aerial lidar": "aerial_lidar",
    "aerial-lidar": "aerial_lidar",
    "airborne_lidar": "aerial_lidar",
    "airborne lidar": "aerial_lidar",
    "uas_lidar": "aerial_lidar",
    "drone_lidar": "aerial_lidar",
    "drone lidar": "aerial_lidar",
    # terrestrial_lidar
    "terrestrial lidar": "terrestrial_lidar",
    "terrestrial-lidar": "terrestrial_lidar",
    "ground_lidar": "terrestrial_lidar",
    "ground lidar": "terrestrial_lidar",
    "tls": "terrestrial_lidar",
    "static_lidar": "terrestrial_lidar",
    # photogrammetry
    "photo": "photogrammetry",
    "photogrammetric": "photogrammetry",
    "aerial_photo": "photogrammetry",
    "aerial photo": "photogrammetry",
    "aerial-photo": "photogrammetry",
    "orthophoto": "photogrammetry",
    "orthomosaic": "photogrammetry",
    "rgb": "photogrammetry",
    # thermal_camera
    "thermal": "thermal_camera",
    "thermal camera": "thermal_camera",
    "thermal-camera": "thermal_camera",
    "infrared": "thermal_camera",
    "ir_camera": "thermal_camera",
    "flir": "thermal_camera",
    # gpr
    "ground_penetrating_radar": "gpr",
    "ground penetrating radar": "gpr",
    "ground-penetrating-radar": "gpr",
    "subsurface_radar": "gpr",
    # rtk_gps
    "gps": "rtk_gps",
    "rtk": "rtk_gps",
    "rtk gps": "rtk_gps",
    "rtk-gps": "rtk_gps",
    "gnss": "rtk_gps",
    "ppk": "rtk_gps",
    "ppk_gps": "rtk_gps",
    # robotic_total_station
    "total_station": "robotic_total_station",
    "total station": "robotic_total_station",
    "rts": "robotic_total_station",
    "robotic total station": "robotic_total_station",
    # legacy/generic
    "temp": "temperature",
    "humidity_sensor": "humidity",
    "camera": "rgb_camera",
}


def normalize_sensor(sensor: str) -> str:
    """Normalize a sensor name to its canonical form.

    If the sensor is already canonical, returns it unchanged.
    If it matches an alias (case-insensitive), returns the canonical form.
    If no match is found, returns the original lowercased value.
    """
    lower = sensor.strip().lower()
    if lower in CANONICAL_SENSORS:
        return lower
    # Check alias map
    canonical = _ALIASES.get(lower)
    if canonical:
        return canonical
    # Check with underscores replaced by spaces and vice versa
    alt = lower.replace("_", " ")
    canonical = _ALIASES.get(alt)
    if canonical:
        return canonical
    alt = lower.replace(" ", "_")
    if alt in CANONICAL_SENSORS:
        return alt
    # No match — return lowercased original
    return lower


def normalize_sensors(sensors: list[str]) -> list[str]:
    """Normalize a list of sensor names, preserving order and removing duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for s in sensors:
        normalized = normalize_sensor(s)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
