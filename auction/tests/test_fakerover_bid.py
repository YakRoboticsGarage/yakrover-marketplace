"""Tests for FakeRoverPlugin.bid() — updated for Anuraj's marketplace changes.

All tests mock the httpx client so they run without the simulator.
The plugin is imported from the sibling yakrover-8004-mcp repo with
stubbed dependencies (core.plugin, core.marketplace_tools, .client, .tools).
"""

import sys
import types
from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: stub the core modules that fakerover/__init__.py imports
# ---------------------------------------------------------------------------

# core.plugin — RobotMetadata, RobotPlugin, BiddingTerms
_CORE_PLUGIN = types.ModuleType("core.plugin")


class _RobotMetadata:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.name = kwargs.get("name", "")


class _RobotPlugin:
    async def bid(self, task_spec: dict) -> dict | None:
        return None

    def metadata(self):
        raise NotImplementedError

    def register_tools(self, mcp):
        raise NotImplementedError

    def tool_names(self) -> list[str]:
        raise NotImplementedError


@dataclass
class _BiddingTerms:
    min_price_cents: int = 50
    rate_per_minute_cents: int | None = 10
    currency: str = "usd"
    accepted_task_types: list[str] = field(default_factory=list)
    max_duration_secs: int = 180
    max_concurrent_tasks: int = 1
    requires_approval: bool = True


_CORE_PLUGIN.RobotMetadata = _RobotMetadata
_CORE_PLUGIN.RobotPlugin = _RobotPlugin
_CORE_PLUGIN.BiddingTerms = _BiddingTerms

sys.modules.setdefault("core", types.ModuleType("core"))
sys.modules["core.plugin"] = _CORE_PLUGIN

# core.marketplace_tools — MARKETPLACE_TOOL_NAMES
_CORE_MKT = types.ModuleType("core.marketplace_tools")
_CORE_MKT.MARKETPLACE_TOOL_NAMES = ["robot_submit_bid", "robot_execute_task", "robot_get_pricing"]
sys.modules["core.marketplace_tools"] = _CORE_MKT

# robots.fakerover.client and .tools stubs
_FAKEROVER_PKG = "robots.fakerover"
_FAKEROVER_CLIENT = types.ModuleType(f"{_FAKEROVER_PKG}.client")


class _StubFakeRoverClient:
    def __init__(self):
        self.base_url = "http://localhost:8080"

    async def get(self, path: str) -> dict:
        raise RuntimeError("stub — should be mocked")


_FAKEROVER_CLIENT.FakeRoverClient = _StubFakeRoverClient

_FAKEROVER_TOOLS = types.ModuleType(f"{_FAKEROVER_PKG}.tools")
_FAKEROVER_TOOLS.register = lambda mcp, client: None

sys.modules.setdefault("robots", types.ModuleType("robots"))
sys.modules.setdefault(_FAKEROVER_PKG, types.ModuleType(_FAKEROVER_PKG))
sys.modules[f"{_FAKEROVER_PKG}.client"] = _FAKEROVER_CLIENT
sys.modules[f"{_FAKEROVER_PKG}.tools"] = _FAKEROVER_TOOLS

# Import the real plugin
import importlib.util
import pathlib

_INIT_PATH = (
    pathlib.Path(__file__).resolve().parents[3] / "yakrover-8004-mcp" / "src" / "robots" / "fakerover" / "__init__.py"
)
if not _INIT_PATH.exists():
    _INIT_PATH = (
        pathlib.Path(__file__).resolve().parents[4]
        / "yakrover-8004-mcp"
        / "src"
        / "robots"
        / "fakerover"
        / "__init__.py"
    )

# This test imports the fakerover plugin directly from the sibling yakrover-8004-mcp
# repo. That's only available in a local dev setup with both repos checked out. CI
# only has this repo checked out, so skip the module cleanly rather than error.
if not _INIT_PATH.exists():
    pytest.skip(
        f"sibling repo not found at {_INIT_PATH} — these tests require a dev setup "
        "with both yakrover-marketplace and yakrover-8004-mcp cloned side by side",
        allow_module_level=True,
    )

spec = importlib.util.spec_from_file_location(_FAKEROVER_PKG, _INIT_PATH, submodule_search_locations=[])
_mod = importlib.util.module_from_spec(spec)
sys.modules[_FAKEROVER_PKG] = _mod
spec.loader.exec_module(_mod)

FakeRoverPlugin = _mod.FakeRoverPlugin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_spec_env_sensing() -> dict:
    """A valid env_sensing task with budget above minimum."""
    return {
        "task_category": "env_sensing",
        "budget_ceiling": 1.00,
        "sla_seconds": 3600,
        "capability_requirements": {
            "sensors_required": ["temperature", "humidity"],
        },
    }


def _task_spec_sensor_reading() -> dict:
    """A sensor_reading task (alternate accepted category)."""
    return {
        "task_category": "sensor_reading",
        "budget_ceiling": 1.00,
        "sla_seconds": 3600,
        "capability_requirements": {
            "sensors_required": ["temperature"],
        },
    }


def _task_spec_welding() -> dict:
    """A task requiring welding — fakerover should decline."""
    return {
        "task_category": "env_sensing",
        "budget_ceiling": 1.00,
        "sla_seconds": 3600,
        "capability_requirements": {
            "sensors_required": ["welding"],
        },
    }


def _task_spec_low_budget() -> dict:
    """A task with budget below minimum ($0.50)."""
    return {
        "task_category": "env_sensing",
        "budget_ceiling": 0.10,
        "sla_seconds": 3600,
        "capability_requirements": {
            "sensors_required": ["temperature"],
        },
    }


def _task_spec_wrong_category() -> dict:
    """A task with a category the fakerover doesn't handle."""
    return {
        "task_category": "site_survey",
        "budget_ceiling": 1.00,
        "sla_seconds": 3600,
        "capability_requirements": {},
    }


def _make_plugin_with_mock_client(mock_client) -> FakeRoverPlugin:
    plugin = FakeRoverPlugin()
    plugin.client = mock_client
    return plugin


def _mock_client_online() -> AsyncMock:
    client = AsyncMock()

    async def _get(path: str) -> dict:
        if path == "/info":
            return {"name": "Fake Rover", "firmware": "simulator-1.0.0", "uptime_seconds": 123}
        if path == "/sensor/ht":
            return {"temperature": 22.5, "humidity": 45.0}
        return {}

    client.get = AsyncMock(side_effect=_get)
    return client


# ---------------------------------------------------------------------------
# Tests — bid acceptance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bid_returns_dict_when_capable():
    """When simulator is online and task needs temp/humidity, bid() returns a dict."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    assert isinstance(result, dict)
    assert result["price"] == 0.5
    assert result["currency"] == "usd"
    assert result["sla_commitment_seconds"] == 30
    assert result["confidence"] == 0.95


@pytest.mark.asyncio
async def test_bid_sensor_reading_category():
    """sensor_reading is an accepted category alongside env_sensing."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_sensor_reading())
    assert result is not None
    assert result["price"] == 0.5


@pytest.mark.asyncio
async def test_bid_has_required_fields():
    """The bid dict must contain all required fields for the marketplace."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    required_keys = {"price", "currency", "sla_commitment_seconds", "confidence", "capabilities_offered"}
    assert required_keys.issubset(result.keys())


@pytest.mark.asyncio
async def test_bid_capabilities_offered():
    """capabilities_offered should list the sensors the robot has."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    assert "temperature" in result["capabilities_offered"]
    assert "humidity" in result["capabilities_offered"]


# ---------------------------------------------------------------------------
# Tests — bid rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bid_returns_none_when_incapable():
    """A task requiring 'welding' should be declined."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_welding())
    assert result is None


@pytest.mark.asyncio
async def test_bid_returns_none_when_simulator_offline():
    """If the httpx call raises, bid() returns None gracefully."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=Exception("Connection refused"))
    plugin = _make_plugin_with_mock_client(client)

    result = await plugin.bid(_task_spec_env_sensing())
    assert result is None


@pytest.mark.asyncio
async def test_bid_returns_none_for_wrong_category():
    """Tasks outside env_sensing/sensor_reading are declined."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_wrong_category())
    assert result is None


@pytest.mark.asyncio
async def test_bid_returns_none_for_low_budget():
    """Tasks below minimum budget ($0.50) are declined."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_low_budget())
    assert result is None
