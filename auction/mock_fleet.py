"""Mock robot fleet for the auction demo.

Three simulated robots that share a single fakerover simulator instance
at localhost:8080. See PRODUCT_SPEC_V01.md Section 6 for full specification.

v0.5 additions: TimeoutRobot, BadPayloadRobot, create_failure_fleet().
"""

from __future__ import annotations

import asyncio
import json as _json_mod
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from auction.core import Bid, DeliveryPayload, Task, sign_bid


def _load_sample(data: dict, path: Path, key: str) -> None:
    """Load a sample deliverable file into the data dict. Skips if file missing."""
    if not path.exists():
        return
    text = path.read_text()
    if path.suffix == ".json":
        try:
            data[key] = _json_mod.loads(text)
        except _json_mod.JSONDecodeError:
            data[key] = text[:500]
    elif path.suffix == ".csv":
        # Include first 5 rows as preview
        lines = text.strip().split("\n")
        data[key] = {"header": lines[0], "rows": len(lines) - 1, "preview": lines[:6]}
    else:
        data[key] = {"file": str(path), "size_bytes": path.stat().st_size}


# ---------------------------------------------------------------------------
# MockRobot base class
# ---------------------------------------------------------------------------


class MockRobot:
    """Base class for simulated demo robots.

    Each subclass provides fixed capability/reputation metadata and bid
    parameters. The bid_engine checks sensor requirements; execute()
    dispatches to the fakerover simulator.
    """

    robot_id: str
    capability_metadata: dict
    reputation_metadata: dict
    signing_key: str

    # Subclasses set these for deterministic bids
    _price: Decimal
    _sla_seconds: int
    _ai_confidence: float

    def bid_engine(self, task: Task) -> Bid | None:
        """Generate a signed bid if this robot has the required sensors.

        Returns None if the robot lacks any sensor listed in
        task.capability_requirements.hard.sensors_required.

        Handles both WoT TD sensor format (list of dicts with "type" key)
        and flat format (list of strings).
        """
        hard = task.capability_requirements.get("hard", {})
        required_sensors = set(hard.get("sensors_required", []))

        # Support WoT TD sensor format (list of dicts) and flat string lists
        raw_sensors = self.capability_metadata.get("sensors", [])
        if raw_sensors and isinstance(raw_sensors[0], dict):
            robot_sensors = {s["type"] for s in raw_sensors if "type" in s}
        else:
            robot_sensors = set(raw_sensors)

        if not required_sensors.issubset(robot_sensors):
            return None

        bid_hash = sign_bid(
            self.robot_id,
            task.request_id,
            self._price,
            self.signing_key,
        )

        return Bid(
            request_id=task.request_id,
            robot_id=self.robot_id,
            price=self._price,
            sla_commitment_seconds=self._sla_seconds,
            ai_confidence=self._ai_confidence,
            capability_metadata=self.capability_metadata,
            reputation_metadata=self.reputation_metadata,
            bid_hash=bid_hash,
        )

    async def execute(self, task: Task) -> DeliveryPayload:
        """Execute the task by calling the fakerover simulator.

        All mock robots dispatch to the same simulator at localhost:8080.
        In v0.5, each robot would call its own MCP endpoint.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/sensor/ht")
            data = response.json()

        now = datetime.now(UTC)
        elapsed_seconds = (now - task.posted_at).total_seconds()
        sla_met = elapsed_seconds <= task.sla_seconds

        return DeliveryPayload(
            request_id=task.request_id,
            robot_id=self.robot_id,
            data={
                "temperature_celsius": data["temperature"],
                "humidity_percent": data["humidity"],
                "timestamp": now.isoformat(),
            },
            delivered_at=now,
            sla_met=sla_met,
        )


# ---------------------------------------------------------------------------
# Robot A: fakerover-bay3
# ---------------------------------------------------------------------------


def _generate_env_sensing_data(robot_id: str, task: Task) -> DeliveryPayload:
    """Generate schema-compliant env_sensing delivery data locally.

    Produces readings matching the delivery_schema from rfp_processor:
    readings[], summary, duration_seconds.
    Falls back to simple temp/humidity dict for non-env_sensing tasks.
    """
    import random

    now = datetime.now(UTC)
    elapsed = (now - task.posted_at).total_seconds()
    sla_met = elapsed <= task.sla_seconds

    has_delivery_schema = bool(task.capability_requirements.get("delivery_schema"))
    if task.task_category == "env_sensing" and has_delivery_schema:
        num_waypoints = 3
        readings = []
        for wp in range(1, num_waypoints + 1):
            readings.append({
                "waypoint": wp,
                "temperature_c": round(21.0 + random.uniform(-2.0, 3.0), 1),
                "humidity_pct": round(45.0 + random.uniform(-5.0, 10.0), 1),
                "timestamp": now.isoformat(),
            })
        data: dict[str, Any] = {
            "readings": readings,
            "summary": f"Environmental scan complete. {num_waypoints} waypoints measured. "
                       f"Avg temp: {sum(r['temperature_c'] for r in readings)/len(readings):.1f}°C, "
                       f"Avg humidity: {sum(r['humidity_pct'] for r in readings)/len(readings):.1f}%",
            "duration_seconds": round(elapsed, 1),
        }
    else:
        data = {
            "temperature_celsius": round(22.0 + random.uniform(-1.0, 2.0), 1),
            "humidity_percent": round(48.0 + random.uniform(-3.0, 5.0), 1),
            "timestamp": now.isoformat(),
        }

    return DeliveryPayload(
        request_id=task.request_id,
        robot_id=robot_id,
        data=data,
        delivered_at=now,
        sla_met=sla_met,
    )


class FakeRoverBay3(MockRobot):
    """Warehouse rover in Bay 3 — closest to typical task locations."""

    def __init__(self) -> None:
        self.robot_id = "fakerover-bay3"
        self.capability_metadata = {
            "sensors": [
                {"type": "temperature", "model": "AHT20", "accuracy_celsius": 0.3},
                {"type": "humidity", "model": "AHT20", "accuracy_rh_pct": 2.0},
            ],
            "mobility_type": "ground_wheeled",
            "indoor_capable": True,
            "location": "warehouse_bay_3",
            "battery_percent": 87,
        }
        self.reputation_metadata = {
            "completion_rate": 0.994,
            "tasks_completed": 47,
            "on_time_rate": 0.98,
        }
        self.signing_key = "bay3_secret_key_v01"
        self._price = Decimal("0.35")
        self._sla_seconds = 180
        self._ai_confidence = 0.98

    async def execute(self, task: Task) -> DeliveryPayload:
        """Generate mock sensor data locally — no external simulator needed."""
        return _generate_env_sensing_data(self.robot_id, task)


# ---------------------------------------------------------------------------
# Robot B: fakerover-bay7
# ---------------------------------------------------------------------------


class FakeRoverBay7(MockRobot):
    """Warehouse rover in Bay 7 — farther away, lower battery."""

    def __init__(self) -> None:
        self.robot_id = "fakerover-bay7"
        self.capability_metadata = {
            "sensors": [
                {"type": "temperature", "model": "AHT20", "accuracy_celsius": 0.3},
                {"type": "humidity", "model": "AHT20", "accuracy_rh_pct": 2.0},
            ],
            "mobility_type": "ground_wheeled",
            "indoor_capable": True,
            "location": "warehouse_bay_7",
            "battery_percent": 65,
        }
        self.reputation_metadata = {
            "completion_rate": 0.955,
            "tasks_completed": 31,
            "on_time_rate": 0.94,
        }
        self.signing_key = "bay7_secret_key_v01"
        self._price = Decimal("0.55")
        self._sla_seconds = 300
        self._ai_confidence = 0.91

    async def execute(self, task: Task) -> DeliveryPayload:
        """Generate mock sensor data locally — no external simulator needed."""
        return _generate_env_sensing_data(self.robot_id, task)


# ---------------------------------------------------------------------------
# Robot C: mock-drone-01
# ---------------------------------------------------------------------------


class MockDrone01(MockRobot):
    """Aerial drone — has RGB camera only, no temperature/humidity sensors.

    Always self-excludes from env_sensing tasks. Would bid on
    visual_inspection or aerial_survey tasks (not exercised in v0.1).
    """

    def __init__(self) -> None:
        self.robot_id = "mock-drone-01"
        self.capability_metadata = {
            "sensors": ["rgb_camera"],
            "mobility_type": "aerial",
            "indoor_capable": False,
            "location": "facility_airspace",
            "battery_percent": 92,
        }
        self.reputation_metadata = {
            "completion_rate": 0.942,
            "tasks_completed": 19,
        }
        self.signing_key = "drone01_secret_key_v01"
        self._price = Decimal("0.45")
        self._sla_seconds = 120
        self._ai_confidence = 0.95


# ---------------------------------------------------------------------------
# Robot D: timeout-robot (v0.5)
# ---------------------------------------------------------------------------


class TimeoutRobot(MockRobot):
    """Robot whose execute() never returns. Triggers timeout/abandonment."""

    def __init__(self) -> None:
        self.robot_id = "timeout-robot"
        self.capability_metadata = {
            "sensors": ["temperature", "humidity"],
            "mobility_type": "ground_wheeled",
            "indoor_capable": True,
            "location": "warehouse_bay_5",
            "battery_percent": 70,
        }
        self.reputation_metadata = {
            "completion_rate": 0.50,
            "tasks_completed": 6,
        }
        self.signing_key = "timeout_robot_key_v01"
        self._price = Decimal("0.30")
        self._sla_seconds = 5
        self._ai_confidence = 0.95

    async def execute(self, task: Task) -> DeliveryPayload:
        """Never completes — triggers timeout/abandonment in the orchestrator."""
        await asyncio.sleep(999999)
        # Unreachable, but satisfies the return type
        raise RuntimeError("TimeoutRobot should never reach this line")


# ---------------------------------------------------------------------------
# Robot E: badpayload-robot (v0.5)
# ---------------------------------------------------------------------------


class BadPayloadRobot(MockRobot):
    """Robot that delivers invalid data. Triggers rejection."""

    def __init__(self) -> None:
        self.robot_id = "badpayload-robot"
        self.capability_metadata = {
            "sensors": ["temperature", "humidity"],
            "mobility_type": "ground_wheeled",
            "indoor_capable": True,
            "location": "warehouse_bay_6",
            "battery_percent": 80,
        }
        self.reputation_metadata = {
            "completion_rate": 0.60,
            "tasks_completed": 10,
        }
        self.signing_key = "badpayload_robot_key_v01"
        self._price = Decimal("0.35")
        self._sla_seconds = 60
        self._ai_confidence = 0.90

    async def execute(self, task: Task) -> DeliveryPayload:
        """Return a payload with invalid data — fails verification."""
        now = datetime.now(UTC)
        elapsed_seconds = (now - task.posted_at).total_seconds()
        sla_met = elapsed_seconds <= task.sla_seconds

        return DeliveryPayload(
            request_id=task.request_id,
            robot_id=self.robot_id,
            data={"temperature_celsius": None, "humidity_percent": -1},
            delivered_at=now,
            sla_met=sla_met,
        )


# ---------------------------------------------------------------------------
# Fleet factory functions
# ---------------------------------------------------------------------------


def create_demo_fleet() -> list[MockRobot]:
    """Create the standard three-robot fleet for the v0.1 demo."""
    return [FakeRoverBay3(), FakeRoverBay7(), MockDrone01()]


def create_scenario3_fleet() -> list[MockRobot]:
    """Create a two-robot fleet for the 'cheapest doesn't win' demo.

    Robot X is cheap but unreliable (slow SLA, low confidence/reputation).
    Robot Y is expensive but reliable (fast SLA, high confidence/reputation).
    Robot Y should win despite costing more.
    """
    robot_x = MockRobot()
    robot_x.robot_id = "robot-x"
    robot_x.capability_metadata = {
        "sensors": ["temperature", "humidity"],
        "mobility_type": "ground_wheeled",
        "indoor_capable": True,
        "location": "warehouse_bay_1",
        "battery_percent": 80,
    }
    robot_x.reputation_metadata = {
        "completion_rate": 0.80,
        "tasks_completed": 12,
    }
    robot_x.signing_key = "robotx_secret_key_v01"
    robot_x._price = Decimal("0.40")
    robot_x._sla_seconds = 600
    robot_x._ai_confidence = 0.70

    robot_y = MockRobot()
    robot_y.robot_id = "robot-y"
    robot_y.capability_metadata = {
        "sensors": ["temperature", "humidity"],
        "mobility_type": "ground_wheeled",
        "indoor_capable": True,
        "location": "warehouse_bay_2",
        "battery_percent": 95,
    }
    robot_y.reputation_metadata = {
        "completion_rate": 0.99,
        "tasks_completed": 85,
    }
    robot_y.signing_key = "roboty_secret_key_v01"
    robot_y._price = Decimal("0.60")
    robot_y._sla_seconds = 120
    robot_y._ai_confidence = 0.97

    return [robot_x, robot_y]


def create_failure_fleet() -> list[MockRobot]:
    """Create a fleet with failure-mode robots for v0.5 testing.

    Contains a robot that times out, one that delivers bad data,
    and a normal rover for comparison.
    """
    return [TimeoutRobot(), BadPayloadRobot(), FakeRoverBay3()]


# ---------------------------------------------------------------------------
# Construction survey fleet (v1.5)
# ---------------------------------------------------------------------------


class ConstructionMockRobot(MockRobot):
    """Base for construction survey robots. Delivers mock survey data.

    Unlike warehouse robots with fixed prices, construction robots bid
    as a percentage of the task budget_ceiling. This simulates realistic
    competitive bidding where operators price relative to the job scope.
    """

    name: str = ""
    operator_company: str = ""
    coverage_area: dict = {}
    certifications: list = []
    _bid_pct: float = 0.85  # Bid at 85% of budget by default

    def bid_engine(self, task: Task) -> Bid | None:
        """Bid proportionally to the task budget, not at a fixed price.

        Construction tasks range from $1,500 to $120,000. A fixed price
        doesn't work across that range. Instead each robot bids at its
        _bid_pct of the task's budget_ceiling.
        """
        hard = task.capability_requirements.get("hard", {})
        required_sensors = set(hard.get("sensors_required", []))

        # Support both WoT TD format and flat string lists
        raw_sensors = self.capability_metadata.get("sensors", [])
        if raw_sensors and isinstance(raw_sensors[0], dict):
            robot_sensors = {s["type"] for s in raw_sensors if "type" in s}
        else:
            robot_sensors = set(raw_sensors)

        if not required_sensors.issubset(robot_sensors):
            return None

        # Price as percentage of budget
        price = (task.budget_ceiling * Decimal(str(self._bid_pct))).quantize(Decimal("1"))

        bid_hash = sign_bid(
            self.robot_id,
            task.request_id,
            price,
            self.signing_key,
        )

        return Bid(
            request_id=task.request_id,
            robot_id=self.robot_id,
            price=price,
            sla_commitment_seconds=self._sla_seconds,
            ai_confidence=self._ai_confidence,
            capability_metadata=self.capability_metadata,
            reputation_metadata=self.reputation_metadata,
            bid_hash=bid_hash,
        )

    async def execute(self, task: Task) -> DeliveryPayload:
        """Return survey deliverables with real sample file references.

        Includes expected payload fields for verification, rich metadata,
        and references to actual sample files in auction/data/sample_deliverables/.
        """
        now = datetime.now(UTC)
        elapsed_seconds = (now - task.posted_at).total_seconds()
        sla_met = elapsed_seconds <= task.sla_seconds

        # Include all expected payload fields so confirm_delivery passes verification
        payload_spec = task.capability_requirements.get("payload", {})
        expected_fields = payload_spec.get("fields", [])

        data: dict[str, Any] = {}
        for field_name in expected_fields:
            data[field_name] = f"{field_name.lower().replace(' ', '_')}_output.{field_name.lower()}"

        # Load real sample deliverable data based on task category
        _samples_dir = Path(__file__).parent / "data" / "sample_deliverables"
        category = task.task_category

        if category in ("site_survey", "aerial_survey", "progress_monitoring"):
            # Topo/aerial survey — include accuracy report and cross-sections
            _load_sample(data, _samples_dir / "accuracy_report.json", "accuracy_report")
            _load_sample(data, _samples_dir / "cross_sections.csv", "cross_sections_sample")
            _load_sample(data, _samples_dir / "survey_control.csv", "control_points_sample")
            data["deliverable_files"] = [
                {"name": "surface.xml", "format": "LandXML 1.2", "sample": str(_samples_dir / "landxml_surface.xml")},
                {"name": "cross_sections.csv", "format": "CSV", "rows": 25},
                {"name": "point_cloud.las", "format": "LAS 1.4", "points": 12_450_000},
                {"name": "orthomosaic.tif", "format": "GeoTIFF", "gsd_cm": 2.0},
            ]
        elif category == "as_built":
            # Tunnel scan — include tunnel report
            _load_sample(data, _samples_dir / "tunnel_scan_report.json", "tunnel_report")
            data["deliverable_files"] = [
                {"name": "tunnel_pointcloud.e57", "format": "e57", "points": 89_200_000},
                {"name": "tunnel_pointcloud.las", "format": "LAS 1.4", "points": 89_200_000},
                {"name": "tunnel_cross_sections.dxf", "format": "DXF R2018", "sections": 240},
            ]
        elif category == "subsurface_scan":
            # GPR survey — include utility report
            _load_sample(data, _samples_dir / "gpr_utility_report.json", "gpr_report")
            data["deliverable_files"] = [
                {"name": "utility_map.dxf", "format": "DXF R2018"},
                {"name": "gpr_report.pdf", "format": "PDF"},
                {"name": "utility_coordinates.csv", "format": "CSV"},
            ]
        elif category == "bridge_inspection":
            _load_sample(data, _samples_dir / "accuracy_report.json", "accuracy_report")
            data["deliverable_files"] = [
                {"name": "bridge_model.las", "format": "LAS 1.4", "points": 45_000_000},
                {"name": "thermal_overlay.tif", "format": "GeoTIFF"},
                {"name": "inspection_report.pdf", "format": "PDF"},
            ]
        else:
            # Control survey or other
            _load_sample(data, _samples_dir / "survey_control.csv", "control_points_sample")
            data["deliverable_files"] = [
                {"name": "control_points.csv", "format": "CSV"},
                {"name": "control_network.dxf", "format": "DXF R2018"},
            ]

        # Common metadata
        data.update(
            {
                "coordinate_system": "MI South State Plane (EPSG:2113)",
                "datum": "NAD83(2011) / NAVD88",
                "processing_software": getattr(self, "_processing_software", "Pix4Dmatic 1.62"),
                "operator": self.operator_company,
                "timestamp": now.isoformat(),
                "pls_review_status": "PENDING",
            }
        )

        return DeliveryPayload(
            request_id=task.request_id,
            robot_id=self.robot_id,
            data=data,
            delivered_at=now,
            sla_met=sla_met,
        )


class GreatLakesAerial(ConstructionMockRobot):
    """Great Lakes Aerial Surveys — DJI M350 RTK + Zenmuse L2.

    Michigan-based, specializes in DOT corridor surveys.
    PLS: Jennifer Chen, MI #42871.
    """

    def __init__(self) -> None:
        self.robot_id = "great-lakes-aerial"
        self.name = "Great Lakes Aerial Surveys"
        self.operator_company = "Great Lakes Aerial Surveys LLC"
        self.capability_metadata = {
            "sensors": ["aerial_lidar", "rtk_gps", "photogrammetry"],
            "mobility_type": "aerial",
            "indoor_capable": False,
            "equipment": [
                {"type": "aerial_lidar", "model": "DJI Matrice 350 RTK + Zenmuse L2", "accuracy_cm": 2.0},
                {"type": "rtk_gps", "model": "Trimble R12i", "accuracy_cm": 0.8},
                {"type": "photogrammetry", "model": "Zenmuse P1 (42MP)", "gsd_cm": 1.5},
            ],
            "coverage_area": {
                "states": ["MI", "OH", "IN"],
                "max_range_miles": 200,
                "base": "Detroit, MI",
            },
            "certifications": ["faa_part_107", "pls_license"],
            "pls_info": {"name": "Jennifer Chen", "license": "MI #42871", "expires": "2027-11-30"},
            "insurance": {
                "cgl": "$2,000,000/$4,000,000",
                "eo": "$2,000,000/$4,000,000",
                "aviation": "$5,000,000",
                "carrier": "Hartford",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.994,
            "tasks_completed": 287,
            "on_time_rate": 0.98,
            "average_accuracy_cm": 1.9,
            "mdot_projects": 42,
        }
        self.signing_key = "great_lakes_aerial_key_v01"
        self._price = Decimal("72000")
        self._bid_pct = 0.82
        self._sla_seconds = 12 * 86400
        self._ai_confidence = 0.97


class WolverineSurveyTech(ConstructionMockRobot):
    """Wolverine Survey Technologies — Spot + Leica BLK ARC.

    Ground scanning specialist. Tunnels, bridges, confined spaces.
    PLS: David Okonkwo, MI #38902.
    """

    def __init__(self) -> None:
        self.robot_id = "wolverine-survey-tech"
        self.name = "Wolverine Survey Technologies"
        self.operator_company = "Wolverine Survey Technologies Inc."
        self.capability_metadata = {
            "sensors": ["terrestrial_lidar", "rtk_gps"],
            "mobility_type": "ground_legged",
            "indoor_capable": True,
            "equipment": [
                {"type": "terrestrial_lidar", "model": "Boston Dynamics Spot + Leica BLK ARC", "accuracy_cm": 0.5},
                {"type": "rtk_gps", "model": "Leica GS18", "accuracy_cm": 0.8},
            ],
            "coverage_area": {
                "states": ["MI", "OH"],
                "max_range_miles": 150,
                "base": "Ann Arbor, MI",
            },
            "certifications": ["pls_license", "confined_space"],
            "pls_info": {"name": "David Okonkwo", "license": "MI #38902", "expires": "2026-08-15"},
            "insurance": {
                "cgl": "$2,000,000/$4,000,000",
                "eo": "$2,000,000/$4,000,000",
                "aviation": "N/A",
                "carrier": "Berkley",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.989,
            "tasks_completed": 156,
            "on_time_rate": 0.96,
            "average_accuracy_cm": 0.4,
            "tunnel_projects": 23,
        }
        self.signing_key = "wolverine_survey_key_v01"
        self._price = Decimal("95000")
        self._bid_pct = 0.90
        self._sla_seconds = 18 * 86400
        self._ai_confidence = 0.96


class PetoskeyDroneWorks(ConstructionMockRobot):
    """Petoskey Drone Works — DJI M350 RTK + Zenmuse P1.

    Photogrammetry specialist. Northern Michigan coverage.
    PLS: Sarah Lightfoot, MI #45201.
    """

    def __init__(self) -> None:
        self.robot_id = "petoskey-drone-works"
        self.name = "Petoskey Drone Works"
        self.operator_company = "Petoskey Drone Works LLC"
        self.capability_metadata = {
            "sensors": ["photogrammetry", "rtk_gps", "aerial_lidar"],
            "mobility_type": "aerial",
            "indoor_capable": False,
            "equipment": [
                {"type": "photogrammetry", "model": "DJI Matrice 350 RTK + Zenmuse P1", "gsd_cm": 1.2},
                {"type": "aerial_lidar", "model": "DJI Zenmuse L2", "accuracy_cm": 2.0},
                {"type": "rtk_gps", "model": "Trimble R12i", "accuracy_cm": 0.8},
            ],
            "coverage_area": {
                "states": ["MI"],
                "max_range_miles": 250,
                "base": "Petoskey, MI",
            },
            "certifications": ["faa_part_107", "pls_license"],
            "pls_info": {"name": "Sarah Lightfoot", "license": "MI #45201", "expires": "2028-03-20"},
            "insurance": {
                "cgl": "$1,000,000/$2,000,000",
                "eo": "$1,000,000/$2,000,000",
                "aviation": "$5,000,000",
                "carrier": "Travelers",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.978,
            "tasks_completed": 89,
            "on_time_rate": 0.95,
            "average_accuracy_cm": 2.1,
        }
        self.signing_key = "petoskey_drone_key_v01"
        self._price = Decimal("55000")
        self._bid_pct = 0.75
        self._sla_seconds = 10 * 86400
        self._ai_confidence = 0.94


class MidwestGPR(ConstructionMockRobot):
    """Midwest GPR Services — GSSI StructureScan Mini XT.

    Subsurface utility detection specialist. Tri-state coverage.
    """

    def __init__(self) -> None:
        self.robot_id = "midwest-gpr"
        self.name = "Midwest GPR Services"
        self.operator_company = "Midwest GPR Services LLC"
        self.capability_metadata = {
            "sensors": ["gpr", "rtk_gps"],
            "mobility_type": "ground_wheeled",
            "indoor_capable": True,
            "equipment": [
                {"type": "gpr", "model": "GSSI StructureScan Mini XT", "depth_m": 3.0},
                {"type": "rtk_gps", "model": "Leica GS18", "accuracy_cm": 0.8},
            ],
            "coverage_area": {
                "states": ["MI", "OH", "IN", "IL"],
                "max_range_miles": 300,
                "base": "Kalamazoo, MI",
            },
            "certifications": ["faa_part_107"],
            "insurance": {
                "cgl": "$1,000,000/$2,000,000",
                "eo": "$1,000,000/$2,000,000",
                "aviation": "N/A",
                "carrier": "CNA",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.985,
            "tasks_completed": 203,
            "on_time_rate": 0.97,
            "utility_locates_completed": 1847,
        }
        self.signing_key = "midwest_gpr_key_v01"
        self._price = Decimal("12000")
        self._bid_pct = 0.78
        self._sla_seconds = 5 * 86400
        self._ai_confidence = 0.96


class TridentInspection(ConstructionMockRobot):
    """Trident Autonomous Inspection — Skydio X10 Thermal.

    Bridge and structural inspection. Visual + thermal.
    """

    def __init__(self) -> None:
        self.robot_id = "trident-inspection"
        self.name = "Trident Autonomous Inspection"
        self.operator_company = "Trident Autonomous LLC"
        self.capability_metadata = {
            "sensors": ["thermal_camera", "photogrammetry", "rtk_gps"],
            "mobility_type": "aerial",
            "indoor_capable": False,
            "equipment": [
                {"type": "thermal_camera", "model": "Skydio X10 Thermal", "resolution": "640x512"},
                {"type": "photogrammetry", "model": "Skydio X10 Visual", "gsd_cm": 0.8},
                {"type": "rtk_gps", "model": "Integrated Skydio RTK", "accuracy_cm": 2.0},
            ],
            "coverage_area": {
                "states": ["MI", "OH", "WI", "IN"],
                "max_range_miles": 250,
                "base": "Grand Rapids, MI",
            },
            "certifications": ["faa_part_107"],
            "insurance": {
                "cgl": "$2,000,000/$4,000,000",
                "eo": "$1,000,000/$2,000,000",
                "aviation": "$5,000,000",
                "carrier": "Zurich",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.991,
            "tasks_completed": 134,
            "on_time_rate": 0.97,
            "bridge_inspections": 67,
        }
        self.signing_key = "trident_inspection_key_v01"
        self._price = Decimal("18000")
        self._bid_pct = 0.80
        self._sla_seconds = 7 * 86400
        self._ai_confidence = 0.95


class ClearLineSurvey(ConstructionMockRobot):
    """ClearLine Survey Co. — Autel EVO II Pro RTK.

    Budget-tier aerial survey. Good for progress monitoring.
    """

    def __init__(self) -> None:
        self.robot_id = "clearline-survey"
        self.name = "ClearLine Survey Co."
        self.operator_company = "ClearLine Survey Co."
        self.capability_metadata = {
            "sensors": ["photogrammetry", "rtk_gps"],
            "mobility_type": "aerial",
            "indoor_capable": False,
            "equipment": [
                {"type": "photogrammetry", "model": "Autel EVO II Pro RTK", "gsd_cm": 2.5},
                {"type": "rtk_gps", "model": "Autel integrated RTK", "accuracy_cm": 1.5},
            ],
            "coverage_area": {
                "states": ["MI"],
                "max_range_miles": 100,
                "base": "Lansing, MI",
            },
            "certifications": ["faa_part_107"],
            "insurance": {
                "cgl": "$1,000,000/$2,000,000",
                "eo": "$500,000/$1,000,000",
                "aviation": "$2,000,000",
                "carrier": "Liberty Mutual",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.965,
            "tasks_completed": 52,
            "on_time_rate": 0.94,
        }
        self.signing_key = "clearline_survey_key_v01"
        self._price = Decimal("3500")
        self._bid_pct = 0.70
        self._sla_seconds = 3 * 86400
        self._ai_confidence = 0.91


class MeridianGeospatial(ConstructionMockRobot):
    """Meridian Geospatial — DJI M350 RTK + P1 + RTK base station.

    Full-service survey operator. Control networks + aerial.
    PLS: Robert Vasquez, MI #41033.
    """

    def __init__(self) -> None:
        self.robot_id = "meridian-geospatial"
        self.name = "Meridian Geospatial"
        self.operator_company = "Meridian Geospatial Services Inc."
        self.capability_metadata = {
            "sensors": ["photogrammetry", "aerial_lidar", "rtk_gps", "robotic_total_station"],
            "mobility_type": "aerial",
            "indoor_capable": False,
            "equipment": [
                {"type": "photogrammetry", "model": "DJI Matrice 350 RTK + Zenmuse P1", "gsd_cm": 1.2},
                {"type": "aerial_lidar", "model": "DJI Zenmuse L2", "accuracy_cm": 2.0},
                {"type": "rtk_gps", "model": "Trimble R12i", "accuracy_cm": 0.8},
                {"type": "robotic_total_station", "model": "Trimble SX12", "accuracy_arcsec": 1.0},
            ],
            "coverage_area": {
                "states": ["MI", "OH", "IN", "WI", "IL"],
                "max_range_miles": 400,
                "base": "Traverse City, MI",
            },
            "certifications": ["faa_part_107", "pls_license"],
            "pls_info": {"name": "Robert Vasquez", "license": "MI #41033", "expires": "2027-06-01"},
            "insurance": {
                "cgl": "$2,000,000/$4,000,000",
                "eo": "$2,000,000/$4,000,000",
                "aviation": "$5,000,000",
                "carrier": "Federal Insurance Company",
            },
            "battery_percent": 100,
        }
        self.reputation_metadata = {
            "completion_rate": 0.997,
            "tasks_completed": 412,
            "on_time_rate": 0.99,
            "average_accuracy_cm": 1.6,
            "control_networks_established": 89,
        }
        self.signing_key = "meridian_geospatial_key_v01"
        self._price = Decimal("68000")
        self._bid_pct = 0.88
        self._sla_seconds = 14 * 86400
        self._ai_confidence = 0.98


def create_construction_fleet() -> list[MockRobot]:
    """Create a 7-operator construction survey fleet for Michigan.

    Includes aerial LiDAR, ground scanning, GPR, thermal inspection,
    photogrammetry, and full-service operators. All with real equipment
    specs, Michigan coverage, and realistic pricing.
    """
    return [
        GreatLakesAerial(),
        WolverineSurveyTech(),
        PetoskeyDroneWorks(),
        MidwestGPR(),
        TridentInspection(),
        ClearLineSurvey(),
        MeridianGeospatial(),
    ]


def create_full_fleet() -> list[MockRobot]:
    """Create combined fleet: original sensor robots + construction operators.

    Used when both sensor-reading and construction survey tasks need to work.
    """
    return create_demo_fleet() + create_construction_fleet()


class RuntimeRegisteredRobot(ConstructionMockRobot):
    """Robot created at runtime from operator registration form.

    Accepts all fields in __init__ (unlike the hardcoded fleet subclasses).
    Inherits bid_engine() (budget-percentage bidding with sensor filtering)
    and execute() (mock survey deliverables) from ConstructionMockRobot.
    """

    def __init__(
        self,
        robot_id: str,
        name: str,
        sensors: list[str],
        capability_metadata: dict,
        reputation_metadata: dict,
        signing_key: str,
        bid_pct: float = 0.80,
        sla_seconds: int = 3600,
        ai_confidence: float = 0.85,
    ):
        self.robot_id = robot_id
        self.name = name
        self.operator_company = name
        self.capability_metadata = capability_metadata
        self.reputation_metadata = reputation_metadata
        self.signing_key = signing_key
        self._bid_pct = bid_pct
        self._sla_seconds = sla_seconds
        self._ai_confidence = ai_confidence
        self._price = Decimal("1")  # unused by ConstructionMockRobot.bid_engine() but required on base
