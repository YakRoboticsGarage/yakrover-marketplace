"""Tests for FakeRoverPlugin.bid() — Track D of v1.0 build plan.

All tests mock the httpx client so they run without the simulator.
"""

import sys
import types
from decimal import Decimal, InvalidOperation
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: make the fakerover plugin importable outside the yakrover-8004-mcp
# tree by stubbing the `core.plugin` module that it imports at the top level.
# ---------------------------------------------------------------------------
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


_CORE_PLUGIN.RobotMetadata = _RobotMetadata
_CORE_PLUGIN.RobotPlugin = _RobotPlugin
sys.modules.setdefault("core", types.ModuleType("core"))
sys.modules["core.plugin"] = _CORE_PLUGIN

# Now we can import the real plugin code.
# We need to also stub the sibling imports (.client, .tools) so the module loads.
_FAKEROVER_PKG = "robots.fakerover"
_FAKEROVER_CLIENT = types.ModuleType(f"{_FAKEROVER_PKG}.client")


class _StubFakeRoverClient:
    """Minimal stub so the module can be imported; tests replace via mocking."""

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

# Perform the real import — this loads the actual __init__.py code via the
# stubbed dependencies.
import importlib.util, pathlib

_INIT_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "yakrover-8004-mcp"
    / "src"
    / "robots"
    / "fakerover"
    / "__init__.py"
)

# If the path doesn't resolve (CI, different layout), try the sibling repo.
if not _INIT_PATH.exists():
    _INIT_PATH = (
        pathlib.Path(__file__).resolve().parents[4]
        / "yakrover-8004-mcp"
        / "src"
        / "robots"
        / "fakerover"
        / "__init__.py"
    )

spec = importlib.util.spec_from_file_location(
    f"{_FAKEROVER_PKG}", _INIT_PATH, submodule_search_locations=[]
)
_mod = importlib.util.module_from_spec(spec)
sys.modules[_FAKEROVER_PKG] = _mod
spec.loader.exec_module(_mod)

FakeRoverPlugin = _mod.FakeRoverPlugin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_spec_env_sensing() -> dict:
    """A task spec that requires temperature and humidity sensors."""
    return {
        "capability_requirements": {
            "hard": {
                "sensors_required": ["temperature", "humidity"],
            }
        }
    }


def _task_spec_welding() -> dict:
    """A task spec that requires a welding capability the fakerover lacks."""
    return {
        "capability_requirements": {
            "hard": {
                "sensors_required": ["welding"],
            }
        }
    }


def _make_plugin_with_mock_client(mock_client) -> FakeRoverPlugin:
    """Create a FakeRoverPlugin and inject a mock client."""
    plugin = FakeRoverPlugin()
    plugin.client = mock_client
    return plugin


def _mock_client_online() -> AsyncMock:
    """Return a mock FakeRoverClient whose .get() returns healthy responses."""
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
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bid_returns_dict_when_capable():
    """When the simulator is online and the task needs temp/humidity, bid() returns a dict."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    assert isinstance(result, dict)
    assert result["robot_id"] == "Fake Rover"
    assert result["price"] == "0.50"
    assert result["sla_commitment_seconds"] == 180


@pytest.mark.asyncio
async def test_bid_returns_none_when_incapable():
    """A task requiring 'welding' should be declined (None)."""
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
async def test_bid_has_required_fields():
    """The bid dict must contain all required top-level keys."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    required_keys = {
        "robot_id",
        "price",
        "sla_commitment_seconds",
        "ai_confidence",
        "capability_metadata",
        "reputation_metadata",
    }
    assert required_keys.issubset(result.keys())


@pytest.mark.asyncio
async def test_bid_price_is_decimal_string():
    """The price field must be a string parseable as a Decimal."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    assert isinstance(result["price"], str)
    try:
        parsed = Decimal(result["price"])
    except InvalidOperation:
        pytest.fail(f"price '{result['price']}' is not a valid Decimal string")
    assert parsed > 0


@pytest.mark.asyncio
async def test_bid_capability_metadata_sensors():
    """capability_metadata.sensors must be a list of dicts each with a 'type' key."""
    plugin = _make_plugin_with_mock_client(_mock_client_online())
    result = await plugin.bid(_task_spec_env_sensing())

    sensors = result["capability_metadata"]["sensors"]
    assert isinstance(sensors, list)
    assert len(sensors) >= 1
    for sensor in sensors:
        assert isinstance(sensor, dict)
        assert "type" in sensor
