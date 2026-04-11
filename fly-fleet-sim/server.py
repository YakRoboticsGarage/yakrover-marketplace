"""
Multi-category robot fleet simulator.

Single FastMCP server with mounted sub-servers per robot category.
Tools are namespaced (e.g., ground_gpr_robot_submit_bid).

The MCPRobotAdapter resolves tool names dynamically via tools/list,
so namespaced marketplace tools work correctly.

Categories: aerial_lidar, aerial_photo, aerial_thermal, fixedwing,
            ground_lidar, ground_gpr, confined, skydio, fakerover
"""

import random
import time
import os

from fastmcp import FastMCP


# ── Simulated data generators ──────────────────────────────────────

def sim_gps(base_lat=42.5, base_lng=-83.5):
    return {"latitude": round(base_lat + random.uniform(-0.01, 0.01), 6),
            "longitude": round(base_lng + random.uniform(-0.01, 0.01), 6),
            "altitude_m": round(random.uniform(50, 120), 1), "fix": "RTK_FIXED",
            "satellites": random.randint(12, 24)}

def sim_battery():
    return {"level_pct": random.randint(40, 100), "voltage_v": round(random.uniform(21.5, 25.2), 1),
            "estimated_flight_min": random.randint(8, 45)}

def sim_lidar():
    return {"points_captured": random.randint(800_000, 4_200_000), "density_pts_m2": round(random.uniform(5, 25), 1),
            "accuracy_cm": round(random.uniform(1.5, 4.0), 1), "format": "LAS 1.4", "timestamp": time.time()}

def sim_photo():
    return {"resolution_mp": random.choice([20, 45, 48, 61]), "gsd_cm": round(random.uniform(0.8, 3.5), 2),
            "photos_captured": random.randint(1, 200), "format": "JPEG+RAW", "timestamp": time.time()}

def sim_thermal():
    return {"min_temp_c": round(random.uniform(-5, 15), 1), "max_temp_c": round(random.uniform(25, 85), 1),
            "avg_temp_c": round(random.uniform(18, 35), 1), "resolution": "640x512", "timestamp": time.time()}

def sim_gpr():
    return {"scan_length_m": round(random.uniform(5, 100), 1), "depth_m": round(random.uniform(0.3, 3.0), 1),
            "frequency_mhz": random.choice([400, 900, 1600]), "utilities_detected": random.randint(0, 8),
            "format": "DZT", "timestamp": time.time()}

def sim_wind():
    return {"speed_mph": round(random.uniform(2, 18), 1), "direction_deg": random.randint(0, 359),
            "gusts_mph": round(random.uniform(5, 25), 1)}


# ── Category config ───────────────────────────────────────────────

CATEGORY_CONFIG = {
    "aerial_lidar":    {"sensors": {"aerial_lidar", "rtk_gps"}, "task_cats": {"env_sensing", "topo_survey", "volumetric"}, "bid_range": (0.70, 0.90)},
    "aerial_photo":    {"sensors": {"photogrammetry", "rtk_gps"}, "task_cats": {"visual_inspection", "progress_monitoring", "env_sensing"}, "bid_range": (0.65, 0.88)},
    "aerial_thermal":  {"sensors": {"thermal_camera", "photogrammetry"}, "task_cats": {"visual_inspection", "thermal_inspection", "env_sensing"}, "bid_range": (0.72, 0.90)},
    "fixedwing":       {"sensors": {"aerial_lidar", "photogrammetry", "rtk_gps"}, "task_cats": {"topo_survey", "corridor_survey", "env_sensing"}, "bid_range": (0.75, 0.92)},
    "ground_lidar":    {"sensors": {"terrestrial_lidar", "photogrammetry"}, "task_cats": {"env_sensing", "as_built", "tunnel_survey"}, "bid_range": (0.78, 0.92)},
    "ground_gpr":      {"sensors": {"gpr", "rtk_gps"}, "task_cats": {"subsurface_scan", "utility_detection", "env_sensing"}, "bid_range": (0.72, 0.88)},
    "confined":        {"sensors": {"terrestrial_lidar", "photogrammetry"}, "task_cats": {"confined_space", "tunnel_survey", "env_sensing"}, "bid_range": (0.80, 0.95)},
    "skydio":          {"sensors": {"photogrammetry", "thermal_camera"}, "task_cats": {"visual_inspection", "bridge_inspection", "env_sensing"}, "bid_range": (0.68, 0.85)},
    "fakerover":       {"sensors": {"temperature", "humidity"}, "task_cats": {"env_sensing", "sensor_reading"}, "bid_range": (0.60, 0.85)},
}


# ── Category MCP builder ─────────────────────────────────────────

def build_category(name, cfg):
    """Build a FastMCP server for a robot category with marketplace + operational tools."""
    mcp = FastMCP(f"{name} Simulator")
    my_sensors = cfg["sensors"]
    my_cats = cfg["task_cats"]
    bid_lo, bid_hi = cfg["bid_range"]

    # ── Marketplace tools (standard 8004 protocol) ────────────────

    @mcp.tool
    async def robot_submit_bid(
        task_description: str, task_category: str, budget_ceiling: float,
        sla_seconds: int, capability_requirements: dict,
    ) -> dict:
        """Evaluate a task and return a bid, or decline."""
        if task_category not in my_cats:
            return {"willing_to_bid": False, "reason": f"Category '{task_category}' not supported"}
        reqs = capability_requirements or {}
        hard = reqs.get("hard", reqs)
        required = set(hard.get("sensors_required", []))
        if required and not required.issubset(my_sensors):
            return {"willing_to_bid": False, "reason": f"Missing sensors: {sorted(required - my_sensors)}"}
        if budget_ceiling < 0.50:
            return {"willing_to_bid": False, "reason": "Budget too low"}
        bid_pct = bid_lo + random.random() * (bid_hi - bid_lo)
        return {
            "willing_to_bid": True, "price": round(budget_ceiling * bid_pct, 2),
            "currency": "usd", "sla_commitment_seconds": sla_seconds,
            "confidence": round(0.70 + random.random() * 0.25, 2),
            "capabilities_offered": sorted(my_sensors),
        }

    @mcp.tool
    async def robot_execute_task(
        task_id: str, task_description: str, parameters: dict, payment_source: str = "fleet",
    ) -> dict:
        """Execute a task and return simulated delivery data."""
        readings = []
        for i in range(3):
            r = {"waypoint": i + 1, "position": sim_gps(), "timestamp": time.time() + i * 60}
            if "gpr" in my_sensors: r["gpr"] = sim_gpr()
            if "aerial_lidar" in my_sensors or "terrestrial_lidar" in my_sensors: r["lidar"] = sim_lidar()
            if "photogrammetry" in my_sensors: r["photo"] = sim_photo()
            if "thermal_camera" in my_sensors: r["thermal"] = sim_thermal()
            if "temperature" in my_sensors: r["temperature_c"] = round(random.uniform(18, 32), 1)
            readings.append(r)
        return {"task_id": task_id, "status": "completed", "readings": readings}

    @mcp.tool
    async def robot_get_pricing() -> dict:
        """Return pricing and availability."""
        return {"min_task_price_usd": 0.50, "rate_per_minute_usd": round(0.05 + random.random() * 0.15, 2),
                "accepted_currencies": ["usd", "usdc"], "task_categories": sorted(my_cats), "availability": "online"}

    # ── Operational tools (category-specific) ─────────────────────

    if name in ("aerial_lidar", "aerial_photo", "aerial_thermal", "fixedwing", "skydio"):
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

    if name == "aerial_lidar":
        @mcp.tool
        async def capture_lidar_scan(duration_seconds: int = 30) -> dict:
            """Capture LiDAR scan."""
            return sim_lidar()
        @mcp.tool
        async def get_wind_speed() -> dict:
            """Get wind speed."""
            return sim_wind()
    elif name == "aerial_photo":
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture photo."""
            return sim_photo()
        @mcp.tool
        async def set_camera_params(iso: int = 100, shutter_speed: str = "1/1000") -> dict:
            """Set camera params."""
            return {"status": "params_set", "iso": iso}
    elif name == "aerial_thermal":
        @mcp.tool
        async def capture_thermal() -> dict:
            """Capture thermal image."""
            return sim_thermal()
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture photo."""
            return sim_photo()
    elif name == "fixedwing":
        @mcp.tool
        async def launch_vtol() -> dict:
            """VTOL launch."""
            return {"status": "airborne", "altitude_m": 120}
        @mcp.tool
        async def fly_corridor(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict:
            """Fly corridor."""
            return {"status": "corridor_complete", "distance_km": round(random.uniform(1, 20), 1)}
        @mcp.tool
        async def land_vtol() -> dict:
            """VTOL land."""
            return {"status": "landed", "position": sim_gps()}
    elif name == "skydio":
        @mcp.tool
        async def fly_orbit(center_lat: float, center_lng: float, radius_m: float = 20) -> dict:
            """Orbit point."""
            return {"status": "orbit_complete", "photos_captured": random.randint(12, 36)}
        @mcp.tool
        async def capture_photo() -> dict:
            """Capture photo."""
            return sim_photo()
        @mcp.tool
        async def autonomous_inspect(structure_type: str = "bridge") -> dict:
            """Autonomous inspection."""
            return {"status": "complete", "images_captured": random.randint(50, 200)}
    elif name in ("ground_lidar", "ground_gpr"):
        @mcp.tool
        async def walk_to(latitude: float, longitude: float) -> dict:
            """Walk to position."""
            return {"status": "arrived", "position": sim_gps(latitude, longitude)}
        @mcp.tool
        async def get_position() -> dict:
            """Get position."""
            return sim_gps()
        @mcp.tool
        async def check_battery() -> dict:
            """Check battery."""
            return sim_battery()
        @mcp.tool
        async def dock() -> dict:
            """Return to dock."""
            return {"status": "docking"}
        if name == "ground_lidar":
            @mcp.tool
            async def scan_360_lidar() -> dict:
                """360 LiDAR scan."""
                return sim_lidar()
        else:
            @mcp.tool
            async def deploy_gpr() -> dict:
                """Deploy GPR."""
                return {"status": "gpr_deployed", "frequency_mhz": 1600}
            @mcp.tool
            async def scan_gpr_line(length_m: float = 10) -> dict:
                """Scan GPR line."""
                return sim_gpr()
            @mcp.tool
            async def mark_utility(depth_m: float, utility_type: str = "unknown") -> dict:
                """Mark utility."""
                return {"status": "marked", "depth_m": depth_m, "type": utility_type}
    elif name == "confined":
        @mcp.tool
        async def fly_indoor(direction: str = "forward", distance_m: float = 5) -> dict:
            """Fly indoors."""
            return {"status": "moved", "direction": direction}
        @mcp.tool
        async def capture_lidar_scan() -> dict:
            """Indoor LiDAR scan."""
            s = sim_lidar(); s["environment"] = "indoor"; return s
        @mcp.tool
        async def capture_photo() -> dict:
            """Photo with lighting."""
            return sim_photo()
        @mcp.tool
        async def detect_obstacle() -> dict:
            """Detect obstacles."""
            return {d + "_m": round(random.uniform(0.3, 10), 1) for d in ["front", "rear", "left", "right"]}
        @mcp.tool
        async def check_battery() -> dict:
            """Check battery."""
            return sim_battery()
        @mcp.tool
        async def return_to_pilot() -> dict:
            """Return to entry."""
            return {"status": "returning"}
    elif name == "fakerover":
        @mcp.tool
        async def move(direction: str = "forward") -> dict:
            """Move rover."""
            return {"status": "moved", "direction": direction}
        @mcp.tool
        async def is_online() -> dict:
            """Check online."""
            return {"online": True}
        @mcp.tool
        async def get_temperature_humidity() -> dict:
            """Read sensors."""
            return {"temperature_c": round(random.uniform(18, 32), 1), "humidity_pct": round(random.uniform(30, 70), 1)}

    return mcp


# ── Build + mount ─────────────────────────────────────────────────

mcp = FastMCP("yakrover Fleet Simulator")

for cat_name, cat_cfg in CATEGORY_CONFIG.items():
    cat_mcp = build_category(cat_name, cat_cfg)
    mcp.mount(cat_mcp, namespace=cat_name)

@mcp.tool
async def health() -> dict:
    """Fleet simulator health."""
    return {"status": "ok", "categories": len(CATEGORY_CONFIG)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
