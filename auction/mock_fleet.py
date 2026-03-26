"""Mock robot fleet for the auction demo.

Three simulated robots that share a single fakerover simulator instance
at localhost:8080. See PRODUCT_SPEC_V01.md Section 6 for full specification.

v0.5 additions: TimeoutRobot, BadPayloadRobot, create_failure_fleet().
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from auction.core import Bid, DeliveryPayload, Task, sign_bid


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
            robot_sensors = set(s["type"] for s in raw_sensors if "type" in s)
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

        now = datetime.now(timezone.utc)
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
        now = datetime.now(timezone.utc)
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
