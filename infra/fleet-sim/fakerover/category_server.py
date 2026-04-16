"""
Standalone robot category MCP server.

Run with: CATEGORY=ground_gpr python category_server.py

Each instance is a single FastMCP server with:
- robot_submit_bid, robot_execute_task, robot_get_pricing (8004 protocol)
- Category-specific operational tools
- All tools un-namespaced (plain names)

One Fly.io app per category. Robot IPFS cards point directly to the
category's endpoint (e.g., yakrover-ground-gpr.fly.dev/mcp).
"""

import random
import time
import os
import sys

from fastmcp import FastMCP


# ── Simulated data generators ──────────────────────────────────────

def sim_gps(lat=42.5, lng=-83.5):
    return {"latitude": round(lat + random.uniform(-0.01, 0.01), 6),
            "longitude": round(lng + random.uniform(-0.01, 0.01), 6),
            "altitude_m": round(random.uniform(50, 120), 1), "fix": "RTK_FIXED",
            "satellites": random.randint(12, 24)}

def sim_battery():
    return {"level_pct": random.randint(40, 100), "voltage_v": round(random.uniform(21.5, 25.2), 1),
            "estimated_flight_min": random.randint(8, 45)}

def sim_lidar():
    return {"points_captured": random.randint(800_000, 4_200_000),
            "density_pts_m2": round(random.uniform(5, 25), 1),
            "accuracy_cm": round(random.uniform(1.5, 4.0), 1),
            "format": "LAS 1.4", "timestamp": time.time()}

def sim_photo():
    return {"resolution_mp": random.choice([20, 45, 48, 61]),
            "gsd_cm": round(random.uniform(0.8, 3.5), 2),
            "photos_captured": random.randint(1, 200),
            "format": "JPEG+RAW", "timestamp": time.time()}

def sim_thermal():
    return {"min_temp_c": round(random.uniform(-5, 15), 1),
            "max_temp_c": round(random.uniform(25, 85), 1),
            "avg_temp_c": round(random.uniform(18, 35), 1),
            "resolution": "640x512", "timestamp": time.time()}

def sim_gpr():
    return {"scan_length_m": round(random.uniform(5, 100), 1),
            "depth_m": round(random.uniform(0.3, 3.0), 1),
            "frequency_mhz": random.choice([400, 900, 1600]),
            "utilities_detected": random.randint(0, 8),
            "format": "DZT", "timestamp": time.time()}

def sim_wind():
    return {"speed_mph": round(random.uniform(2, 18), 1),
            "direction_deg": random.randint(0, 359),
            "gusts_mph": round(random.uniform(5, 25), 1)}


# ── Category configs ──────────────────────────────────────────────

CATEGORIES = {
    "aerial_lidar": {
        "label": "Aerial LiDAR",
        "sensors": {"aerial_lidar", "rtk_gps"},
        "task_cats": {"env_sensing", "topo_survey", "volumetric"},
        "bid_range": (0.70, 0.90),
    },
    "aerial_photo": {
        "label": "Aerial Photogrammetry",
        "sensors": {"photogrammetry", "rtk_gps"},
        "task_cats": {"visual_inspection", "progress_monitoring", "env_sensing"},
        "bid_range": (0.65, 0.88),
    },
    "aerial_thermal": {
        "label": "Aerial Thermal",
        "sensors": {"thermal_camera", "photogrammetry"},
        "task_cats": {"visual_inspection", "thermal_inspection", "env_sensing"},
        "bid_range": (0.72, 0.90),
    },
    "ground_gpr": {
        "label": "Ground GPR",
        "sensors": {"gpr", "rtk_gps"},
        "task_cats": {"subsurface_scan", "utility_detection", "env_sensing"},
        "bid_range": (0.72, 0.88),
    },
    "skydio": {
        "label": "Skydio X10",
        "sensors": {"photogrammetry", "thermal_camera"},
        "task_cats": {"visual_inspection", "bridge_inspection", "env_sensing"},
        "bid_range": (0.68, 0.85),
    },
    "fixedwing": {
        "label": "Fixed-Wing VTOL",
        "sensors": {"aerial_lidar", "photogrammetry", "rtk_gps"},
        "task_cats": {"topo_survey", "corridor_survey", "env_sensing"},
        "bid_range": (0.75, 0.92),
    },
    "ground_lidar": {
        "label": "Ground LiDAR",
        "sensors": {"terrestrial_lidar", "photogrammetry"},
        "task_cats": {"env_sensing", "as_built", "confined_space"},
        "bid_range": (0.78, 0.92),
    },
    "confined": {
        "label": "Confined Space",
        "sensors": {"terrestrial_lidar", "photogrammetry"},
        "task_cats": {"confined_space", "env_sensing"},
        "bid_range": (0.80, 0.95),
    },
    "fakerover": {
        "label": "FakeRover",
        "sensors": {"temperature", "humidity"},
        "task_cats": {"env_sensing"},
        "bid_range": (0.60, 0.85),
    },
}


def build_server(category: str) -> FastMCP:
    cfg = CATEGORIES[category]
    mcp = FastMCP(cfg["label"] + " Simulator")
    my_sensors = cfg["sensors"]
    my_cats = cfg["task_cats"]
    bid_lo, bid_hi = cfg["bid_range"]

    # ── 8004 Marketplace tools ────────────────────────────────────

    @mcp.tool
    async def robot_submit_bid(
        task_description: str, task_category: str, budget_ceiling: float,
        sla_seconds: int, capability_requirements: dict,
    ) -> dict:
        """Evaluate a task and return a bid, or decline."""
        if task_category not in my_cats:
            return {"willing_to_bid": False,
                    "reason": f"Category '{task_category}' not accepted. Supported: {sorted(my_cats)}"}
        reqs = capability_requirements or {}
        hard = reqs.get("hard", reqs)
        required = set(hard.get("sensors_required", []))
        if required and not required.issubset(my_sensors):
            return {"willing_to_bid": False,
                    "reason": f"Missing sensors: {sorted(required - my_sensors)}"}
        if budget_ceiling < 0.50:
            return {"willing_to_bid": False, "reason": "Budget below minimum"}
        bid_pct = bid_lo + random.random() * (bid_hi - bid_lo)
        return {
            "willing_to_bid": True,
            "price": round(budget_ceiling * bid_pct, 2),
            "currency": "usd",
            "sla_commitment_seconds": sla_seconds,
            "confidence": round(0.70 + random.random() * 0.25, 2),
            "capabilities_offered": sorted(my_sensors),
        }

    @mcp.tool
    async def robot_execute_task(
        task_id: str, task_description: str, parameters: dict,
        payment_source: str = "fleet",
    ) -> dict:
        """Execute a task and return category-specific delivery data."""

        if category == "aerial_lidar" or category == "fixedwing":
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "point_cloud": {"format": "LAS 1.4", "version": "1.4", "point_count": random.randint(800000, 4200000),
                    "density_pts_m2": round(random.uniform(5, 25), 1), "area_m2": random.randint(5000, 50000),
                    "classifications": ["ground", "vegetation", "building", "noise"],
                    "bounding_box": {"min": sim_gps(), "max": sim_gps()}},
                "quality_metrics": {"horizontal_accuracy_cm": round(random.uniform(1.5, 5), 1),
                    "vertical_accuracy_cm": round(random.uniform(2, 8), 1),
                    "control_points_used": random.randint(4, 12), "overlap_pct": random.randint(60, 85)},
                "coordinate_system": {"epsg": 2253, "datum": "NAD83(2011)", "projection": "Michigan State Plane South"},
                "summary": f"Aerial LiDAR survey complete. {random.randint(3, 8)} flight lines captured."}}

        elif category == "aerial_photo":
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "orthomosaic": {"format": "GeoTIFF", "gsd_cm": round(random.uniform(0.8, 3.5), 2),
                    "width_px": random.randint(10000, 50000), "height_px": random.randint(8000, 40000),
                    "bands": 4, "bounding_box": {"min": sim_gps(), "max": sim_gps()}},
                "photo_set": {"total_photos": random.randint(80, 400),
                    "overlap_frontal_pct": random.randint(75, 85), "overlap_side_pct": random.randint(65, 75),
                    "camera_model": "DJI Zenmuse P1 / FC6360"},
                "quality_metrics": {"horizontal_accuracy_cm": round(random.uniform(1, 4), 1),
                    "vertical_accuracy_cm": round(random.uniform(2, 6), 1),
                    "reprojection_error_px": round(random.uniform(0.3, 0.8), 2),
                    "ground_control_points": random.randint(4, 10)},
                "summary": f"Photogrammetry complete. {random.randint(80, 400)} photos processed into orthomosaic."}}

        elif category == "ground_gpr":
            utilities = []
            for i in range(random.randint(2, 8)):
                utilities.append({"type": random.choice(["water", "sewer", "electric", "gas", "telecom", "unknown"]),
                    "depth_m": round(random.uniform(0.3, 2.5), 2),
                    "confidence": round(random.uniform(0.6, 0.98), 2),
                    "apwa_color": random.choice(["blue", "green", "red", "yellow", "orange", "purple"]),
                    "position": sim_gps()})
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "scan_data": {"format": "DZT", "scan_lines": random.randint(10, 60),
                    "total_length_m": round(random.uniform(50, 500), 1), "depth_m": round(random.uniform(1, 3), 1),
                    "antenna_frequency_mhz": 1600},
                "utility_detections": utilities,
                "survey_parameters": {"coordinate_system": "EPSG:2253 Michigan State Plane South",
                    "accuracy_horizontal_cm": 15, "accuracy_depth_pct": 10, "asce_38_quality_level": "B"},
                "summary": f"GPR survey complete. {len(utilities)} utilities detected across {random.randint(10,60)} scan lines."}}

        elif category == "aerial_thermal":
            anomalies = []
            for i in range(random.randint(0, 5)):
                anomalies.append({"severity": random.choice(["low", "medium", "high", "critical"]),
                    "delta_t_c": round(random.uniform(2, 15), 1),
                    "area_m2": round(random.uniform(0.5, 20), 1),
                    "classification": random.choice(["moisture", "insulation_gap", "membrane_failure", "hvac_leak"]),
                    "position": sim_gps()})
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "thermal_mosaic": {"format": "RJPEG", "resolution": "640x512",
                    "temp_range_c": {"min": round(random.uniform(-5, 10), 1), "max": round(random.uniform(30, 65), 1)},
                    "emissivity": 0.95, "images_captured": random.randint(50, 200)},
                "anomalies": anomalies,
                "survey_conditions": {"ambient_temp_c": round(random.uniform(5, 25), 1),
                    "wind_speed_mph": round(random.uniform(2, 12), 1),
                    "sky_condition": random.choice(["clear", "partly_cloudy", "overcast"]),
                    "time_of_day": "pre-dawn"},
                "summary": f"Thermal survey complete. {len(anomalies)} anomalies detected."}}

        elif category == "skydio":
            elements = []
            for elem in ["deck", "superstructure", "substructure", "bearings", "joints"]:
                elements.append({"element": elem, "condition_state": random.randint(1, 4),
                    "quantity_pct": round(random.uniform(60, 100), 1),
                    "defects": random.sample(["spalling", "cracking", "corrosion", "delamination", "efflorescence", "staining"], random.randint(0, 3))})
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "inspection_set": {"total_images": random.randint(100, 400),
                    "coverage_pct": round(random.uniform(85, 99), 1),
                    "resolution_mp": 48, "gsd_mm": round(random.uniform(0.5, 2), 1)},
                "element_ratings": elements,
                "summary": f"Bridge inspection complete. {len(elements)} elements rated per NBI coding."}}

        elif category == "ground_lidar":
            positions = [{"position_id": i+1, "point_count": random.randint(500000, 2000000),
                "overlap_pct": round(random.uniform(30, 60), 1)} for i in range(random.randint(5, 15))]
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "point_cloud": {"format": "E57", "point_count": sum(p["point_count"] for p in positions),
                    "scan_positions": len(positions), "registration_error_mm": round(random.uniform(1, 5), 1)},
                "scan_positions": positions,
                "quality_metrics": {"registration_error_mm": round(random.uniform(1, 5), 1),
                    "coverage_pct": round(random.uniform(90, 99), 1)},
                "summary": f"Ground LiDAR scan complete. {len(positions)} positions registered."}}

        elif category == "confined":
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "point_cloud": {"format": "PLY", "point_count": random.randint(100000, 1000000),
                    "positioning_method": "SLAM", "slam_confidence": round(random.uniform(0.75, 0.98), 2)},
                "inspection_photos": {"total_photos": random.randint(30, 150),
                    "lighting": "onboard_led", "resolution_mp": 12},
                "obstacle_map": {"obstacles_detected": random.randint(0, 8),
                    "clearance_min_m": round(random.uniform(0.5, 3), 1)},
                "summary": f"Confined space inspection complete. SLAM-based positioning."}}

        else:
            # fakerover / env_sensing fallback
            readings = [{"waypoint": i+1, "temperature_c": round(random.uniform(18, 32), 1),
                "humidity_pct": round(random.uniform(30, 70), 1),
                "timestamp": str(time.time() + i * 60)} for i in range(3)]
            return {"task_id": task_id, "status": "completed", "delivery_data": {
                "readings": readings, "summary": "Environmental readings captured at 3 waypoints.",
                "duration_seconds": round(random.uniform(10, 120), 1)}}

    @mcp.tool
    async def robot_get_pricing() -> dict:
        """Return pricing and availability."""
        return {
            "min_task_price_usd": 0.50,
            "rate_per_minute_usd": round(0.05 + random.random() * 0.15, 2),
            "accepted_currencies": ["usd", "usdc"],
            "max_concurrent_tasks": 1,
            "task_categories": sorted(my_cats),
            "availability": "online",
        }

    # ── Category-specific operational tools ────────────────────────

    if category in ("aerial_lidar", "aerial_photo", "aerial_thermal", "skydio", "fixedwing"):
        @mcp.tool
        async def fly_waypoint(latitude: float, longitude: float, altitude_m: float = 60) -> dict:
            """Fly to a GPS waypoint."""
            return {"status": "arrived", "position": sim_gps(latitude, longitude)}
        @mcp.tool
        async def get_gps_position() -> dict:
            """Get GPS position."""
            return sim_gps()
        @mcp.tool
        async def check_battery() -> dict:
            """Check battery."""
            return sim_battery()
        @mcp.tool
        async def return_to_home() -> dict:
            """Return to launch."""
            return {"status": "landing", "eta_seconds": random.randint(30, 120)}

    if category == "aerial_lidar":
        @mcp.tool
        async def capture_lidar_scan(duration_seconds: int = 30) -> dict:
            """Capture LiDAR point cloud."""
            return sim_lidar()
        @mcp.tool
        async def set_flight_altitude(altitude_m: float) -> dict:
            """Set altitude."""
            return {"status": "altitude_set", "altitude_m": altitude_m}
        @mcp.tool
        async def get_wind_speed() -> dict:
            """Get wind speed."""
            return sim_wind()

    elif category == "aerial_photo":
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture geotagged photo."""
            return sim_photo()
        @mcp.tool
        async def capture_video(duration_seconds: int = 10) -> dict:
            """Record video."""
            return {"status": "recorded", "duration_s": duration_seconds, "resolution": "4K"}
        @mcp.tool
        async def set_camera_params(iso: int = 100, shutter_speed: str = "1/1000", aperture: float = 2.8) -> dict:
            """Set camera params."""
            return {"status": "params_set", "iso": iso, "shutter_speed": shutter_speed}

    elif category == "aerial_thermal":
        @mcp.tool
        async def capture_thermal() -> dict:
            """Capture thermal image."""
            return sim_thermal()
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture visual photo."""
            return sim_photo()
        @mcp.tool
        async def get_surface_temp(latitude: float, longitude: float) -> dict:
            """Get surface temperature at a point."""
            return {"temperature_c": round(random.uniform(15, 65), 1),
                    "position": sim_gps(latitude, longitude)}

    elif category == "ground_gpr":
        @mcp.tool
        async def walk_to(latitude: float, longitude: float) -> dict:
            """Walk to position."""
            return {"status": "arrived", "position": sim_gps(latitude, longitude)}
        @mcp.tool
        async def deploy_gpr() -> dict:
            """Deploy GPR antenna."""
            return {"status": "gpr_deployed", "frequency_mhz": 1600, "calibration": "complete"}
        @mcp.tool
        async def scan_gpr_line(length_m: float = 10, direction_deg: int = 0) -> dict:
            """Scan a GPR line."""
            return sim_gpr()
        @mcp.tool
        async def get_position() -> dict:
            """Get position."""
            return sim_gps()
        @mcp.tool
        async def check_battery() -> dict:
            """Check battery."""
            b = sim_battery()
            b["estimated_runtime_min"] = random.randint(30, 90)
            return b
        @mcp.tool
        async def dock() -> dict:
            """Return to dock."""
            return {"status": "docking", "eta_seconds": random.randint(60, 300)}
        @mcp.tool
        async def mark_utility(depth_m: float, utility_type: str = "unknown") -> dict:
            """Mark detected utility."""
            return {"status": "marked", "depth_m": depth_m, "type": utility_type,
                    "position": sim_gps()}

    elif category == "skydio":
        @mcp.tool
        async def fly_orbit(center_lat: float, center_lng: float, radius_m: float = 20, altitude_m: float = 30) -> dict:
            """Orbit a point of interest."""
            return {"status": "orbit_complete", "photos_captured": random.randint(12, 36)}
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture photo."""
            return sim_photo()
        @mcp.tool
        async def capture_thermal() -> dict:
            """Capture thermal image."""
            return sim_thermal()
        @mcp.tool
        async def autonomous_inspect(structure_type: str = "bridge") -> dict:
            """Autonomous inspection scan."""
            return {"status": "inspection_complete", "structure": structure_type,
                    "images_captured": random.randint(50, 200), "anomalies": random.randint(0, 5)}

    elif category == "fixedwing":
        @mcp.tool
        async def launch_vtol() -> dict:
            """VTOL launch sequence."""
            return {"status": "airborne", "altitude_m": 120, "mode": "cruise"}
        @mcp.tool
        async def fly_corridor(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict:
            """Fly corridor survey between two points."""
            return {"status": "corridor_complete", "distance_km": round(random.uniform(1, 20), 1), "photos": random.randint(50, 500)}
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture geotagged photo during flight."""
            return sim_photo()
        @mcp.tool
        async def land_vtol() -> dict:
            """VTOL landing."""
            return {"status": "landed", "position": sim_gps()}
        @mcp.tool
        async def set_flight_plan(waypoints: list) -> dict:
            """Upload flight plan."""
            return {"status": "plan_loaded", "waypoints": len(waypoints) if waypoints else 0}

    elif category in ("ground_lidar", "confined"):
        @mcp.tool
        async def walk_to(latitude: float, longitude: float) -> dict:
            """Walk/fly to position."""
            return {"status": "arrived", "position": sim_gps(latitude, longitude)}
        @mcp.tool
        async def scan_360_lidar() -> dict:
            """360-degree LiDAR scan."""
            return sim_lidar()
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture photo."""
            return sim_photo()
        @mcp.tool
        async def get_position() -> dict:
            """Get position."""
            return sim_gps()
        @mcp.tool
        async def check_battery() -> dict:
            """Check battery."""
            return sim_battery()
        if category == "ground_lidar":
            @mcp.tool
            async def dock() -> dict:
                """Return to dock."""
                return {"status": "docking", "eta_seconds": random.randint(60, 300)}
            @mcp.tool
            async def navigate_stairs(direction: str = "up") -> dict:
                """Navigate stairs."""
                return {"status": "stairs_complete", "direction": direction}
        else:
            @mcp.tool
            async def detect_obstacle() -> dict:
                """Detect obstacles."""
                return {d + "_m": round(random.uniform(0.3, 10), 1) for d in ["front", "rear", "left", "right"]}
            @mcp.tool
            async def return_to_pilot() -> dict:
                """Return to entry point."""
                return {"status": "returning", "eta_seconds": random.randint(30, 180)}

    elif category == "fakerover":
        @mcp.tool
        async def move(direction: str = "forward") -> dict:
            """Move rover."""
            return {"status": "moved", "direction": direction, "distance_m": round(random.uniform(0.5, 2.0), 1)}
        @mcp.tool
        async def is_online() -> dict:
            """Check online status."""
            return {"online": True}
        @mcp.tool
        async def get_temperature_humidity() -> dict:
            """Read temperature and humidity."""
            return {"temperature_c": round(random.uniform(18, 32), 1), "humidity_pct": round(random.uniform(30, 70), 1)}

    return mcp


if __name__ == "__main__":
    category = os.environ.get("CATEGORY", "").strip()
    if not category or category not in CATEGORIES:
        print(f"Set CATEGORY env var. Valid: {sorted(CATEGORIES)}")
        sys.exit(1)
    port = int(os.environ.get("PORT", 8000))
    server = build_server(category)
    server.run(transport="http", host="0.0.0.0", port=port)
