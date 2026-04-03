"""Tests for the ERC-8004 discovery bridge.

Mocks the upstream discovery and plugin classes so tests run without
blockchain access or the yakrover-8004-mcp package installed.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auction.core import Bid, DeliveryPayload, Task
from auction.discovery_bridge import (
    PluginRobotAdapter,
    _task_to_spec,
    discover_and_adapt,
    discover_and_adapt_from_plugins,
)

# ---------------------------------------------------------------------------
# Fake RobotPlugin / RobotMetadata stubs (no real import needed)
# ---------------------------------------------------------------------------


@dataclass
class FakeMetadata:
    name: str = "test-rover"
    description: str = "A test rover"
    robot_type: str = "differential_drive"
    url_prefix: str = "testrover"
    fleet_provider: str = "yakrover"
    fleet_domain: str = "yakrover.com/dev"
    image: str = ""


class StubPlugin:
    """Mimics RobotPlugin with a working bid() that returns a dict."""

    def __init__(self, *, bid_result: dict | None = None, should_raise: bool = False):
        self._bid_result = bid_result
        self._should_raise = should_raise

    def metadata(self) -> FakeMetadata:
        return FakeMetadata()

    def tool_names(self) -> list[str]:
        return ["testrover_sense"]

    def register_tools(self, mcp) -> None:
        pass

    async def bid(self, task_spec: dict) -> dict | None:
        if self._should_raise:
            raise RuntimeError("Simulator offline")
        return self._bid_result


def _make_task(**overrides) -> Task:
    defaults = {
        "description": "Read temperature in Bay 3",
        "task_category": "env_sensing",
        "capability_requirements": {
            "hard": {"sensors_required": ["temperature", "humidity"]},
        },
        "budget_ceiling": Decimal("2.00"),
        "sla_seconds": 300,
    }
    defaults.update(overrides)
    return Task(**defaults)


SAMPLE_BID_DICT = {
    "robot_id": "test-rover",
    "price": "0.50",
    "sla_commitment_seconds": 180,
    "ai_confidence": 0.95,
    "capability_metadata": {
        "sensors": [
            {"type": "temperature", "model": "AHT20", "accuracy_celsius": 0.3},
            {"type": "humidity", "model": "AHT20", "accuracy_rh_pct": 2.0},
        ],
        "mobility_type": "ground_wheeled",
        "indoor_capable": True,
        "location": "fakerover_simulator",
        "battery_percent": 100,
    },
    "reputation_metadata": {
        "completion_rate": 0.95,
        "tasks_completed": 0,
        "on_time_rate": 1.0,
        "rejection_rate": 0.0,
        "rolling_window_days": 30,
    },
}


# ---------------------------------------------------------------------------
# PluginRobotAdapter tests
# ---------------------------------------------------------------------------


class TestPluginRobotAdapter:
    """Test the adapter wrapping a RobotPlugin for the auction engine."""

    def test_init_sets_robot_id_from_metadata(self):
        plugin = StubPlugin()
        adapter = PluginRobotAdapter(plugin)
        assert adapter.robot_id == "test-rover"

    def test_init_sets_capability_metadata_defaults(self):
        plugin = StubPlugin()
        adapter = PluginRobotAdapter(plugin)
        assert adapter.capability_metadata["mobility_type"] == "differential_drive"
        assert adapter.capability_metadata["location"] == "testrover"

    def test_init_custom_signing_key(self):
        plugin = StubPlugin()
        adapter = PluginRobotAdapter(plugin, signing_key="my_key")
        assert adapter.signing_key == "my_key"

    def test_bid_engine_returns_bid_on_success(self):
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        bid = adapter.bid_engine(task)

        assert isinstance(bid, Bid)
        assert bid.robot_id == "test-rover"
        assert bid.price == Decimal("0.50")
        assert bid.sla_commitment_seconds == 180
        assert bid.ai_confidence == 0.95
        assert bid.request_id == task.request_id
        assert bid.bid_hash  # non-empty string

    def test_bid_engine_enriches_capability_metadata(self):
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        adapter.bid_engine(task)

        # After bidding, the adapter's metadata should be enriched.
        assert adapter.capability_metadata["battery_percent"] == 100
        sensors = adapter.capability_metadata["sensors"]
        assert len(sensors) == 2
        assert sensors[0]["type"] == "temperature"

    def test_bid_engine_enriches_reputation_metadata(self):
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        adapter.bid_engine(task)

        assert adapter.reputation_metadata["completion_rate"] == 0.95
        assert adapter.reputation_metadata["on_time_rate"] == 1.0

    def test_bid_engine_returns_none_when_plugin_declines(self):
        plugin = StubPlugin(bid_result=None)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        bid = adapter.bid_engine(task)

        assert bid is None

    def test_bid_engine_returns_none_on_exception(self):
        plugin = StubPlugin(should_raise=True)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        bid = adapter.bid_engine(task)

        assert bid is None

    @pytest.mark.asyncio
    async def test_execute_uses_plugin_client(self):
        """When the plugin has a client, execute() calls it directly."""
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        plugin.client = MagicMock()
        plugin.client.get = AsyncMock(return_value={"temperature": 23.4, "humidity": 55.1})

        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        payload = await adapter.execute(task)

        assert isinstance(payload, DeliveryPayload)
        assert payload.robot_id == "test-rover"
        assert payload.data["temperature_celsius"] == 23.4
        assert payload.data["humidity_percent"] == 55.1
        assert payload.request_id == task.request_id
        plugin.client.get.assert_awaited_once_with("/sensor/ht")

    @pytest.mark.asyncio
    async def test_execute_falls_back_to_httpx(self):
        """When the plugin has no client, execute() uses httpx."""
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        mock_response = MagicMock()
        mock_response.json.return_value = {"temperature": 21.0, "humidity": 60.0}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            payload = await adapter.execute(task)

        assert payload.data["temperature_celsius"] == 21.0
        assert payload.data["humidity_percent"] == 60.0

    @pytest.mark.asyncio
    async def test_execute_client_failure_falls_back(self):
        """When the plugin client raises, execute() falls back to httpx."""
        plugin = StubPlugin()
        plugin.client = MagicMock()
        plugin.client.get = AsyncMock(side_effect=ConnectionError("offline"))

        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        mock_response = MagicMock()
        mock_response.json.return_value = {"temperature": 19.0, "humidity": 45.0}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            payload = await adapter.execute(task)

        assert payload.data["temperature_celsius"] == 19.0


# ---------------------------------------------------------------------------
# _task_to_spec tests
# ---------------------------------------------------------------------------


class TestTaskToSpec:
    def test_converts_task_to_dict(self):
        task = _make_task()
        spec = _task_to_spec(task)

        assert spec["request_id"] == task.request_id
        assert spec["description"] == "Read temperature in Bay 3"
        assert spec["task_category"] == "env_sensing"
        assert spec["capability_requirements"] == task.capability_requirements
        assert spec["budget_ceiling"] == "2.00"
        assert spec["sla_seconds"] == 300


# ---------------------------------------------------------------------------
# discover_and_adapt tests
# ---------------------------------------------------------------------------


class TestDiscoverAndAdapt:
    def test_returns_empty_when_import_fails(self):
        """When yakrover-8004-mcp is not importable, returns []."""
        with patch.dict("sys.modules", {"core.discovery": None, "core": None}):
            # Force ImportError by removing the module
            with patch(
                "auction.discovery_bridge.discover_and_adapt.__module__",
                create=True,
            ):
                # The function catches ImportError internally.
                result = discover_and_adapt()
                assert result == []

    @patch("auction.discovery_bridge._instantiate_plugin")
    @patch("auction.discovery_bridge.discover_robots_import", create=True)
    def test_wraps_discovered_robots(self, _mock_import, mock_instantiate):
        """When discovery returns robots, they get wrapped as adapters."""
        # We need to patch at the point of import inside the function.
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        mock_instantiate.return_value = plugin

        with patch("auction.discovery_bridge.discover_and_adapt") as mock_fn:
            mock_fn.return_value = [PluginRobotAdapter(plugin)]
            result = mock_fn()

        assert len(result) == 1
        assert result[0].robot_id == "test-rover"


class TestDiscoverAndAdaptFromPlugins:
    def test_wraps_plugin_list(self):
        plugins = [
            StubPlugin(bid_result=SAMPLE_BID_DICT),
            StubPlugin(bid_result=None),
        ]
        adapters = discover_and_adapt_from_plugins(plugins, signing_key="k1")

        assert len(adapters) == 2
        assert all(isinstance(a, PluginRobotAdapter) for a in adapters)
        assert all(a.signing_key == "k1" for a in adapters)
        assert all(a.robot_id == "test-rover" for a in adapters)

    def test_empty_list(self):
        assert discover_and_adapt_from_plugins([]) == []


# ---------------------------------------------------------------------------
# Integration: adapter works with AuctionEngine
# ---------------------------------------------------------------------------


class TestAdapterWithEngine:
    """Verify the adapter satisfies the AuctionEngine robot contract."""

    def test_adapter_has_required_attributes(self):
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)

        # These are the attributes AuctionEngine accesses.
        assert hasattr(adapter, "robot_id")
        assert hasattr(adapter, "capability_metadata")
        assert hasattr(adapter, "signing_key")
        assert hasattr(adapter, "bid_engine")
        assert hasattr(adapter, "execute")
        assert callable(adapter.bid_engine)
        assert asyncio.iscoroutinefunction(adapter.execute)

    def test_adapter_robot_id_used_as_dict_key(self):
        """AuctionEngine builds _robots_by_id = {r.robot_id: r for r in robots}."""
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)

        robots_by_id = {adapter.robot_id: adapter}
        assert robots_by_id["test-rover"] is adapter

    def test_bid_engine_signature_matches_mock_robot(self):
        """bid_engine(task) -> Bid | None — same as MockRobot."""
        plugin = StubPlugin(bid_result=SAMPLE_BID_DICT)
        adapter = PluginRobotAdapter(plugin)
        task = _make_task()

        result = adapter.bid_engine(task)
        assert isinstance(result, Bid)
