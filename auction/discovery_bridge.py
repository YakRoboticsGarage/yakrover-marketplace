"""Bridge between ERC-8004 on-chain discovery and the auction engine.

Discovers robots on-chain, wraps RobotPlugin instances as MockRobot-compatible
objects so the AuctionEngine can use them alongside mock robots.

This module is OPTIONAL — it requires the yakrover-8004-mcp ``src/`` to be
importable. When not available, the auction engine works with mock robots only.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from auction.core import Bid, DeliveryPayload, Task, sign_bid

if TYPE_CHECKING:
    from core.plugin import RobotPlugin

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PluginRobotAdapter
# ---------------------------------------------------------------------------

class PluginRobotAdapter:
    """Adapts a RobotPlugin (from yakrover-8004-mcp) to the MockRobot interface.

    The AuctionEngine expects objects with ``robot_id``, ``capability_metadata``,
    ``signing_key``, ``bid_engine(task) -> Bid | None``, and
    ``async execute(task) -> DeliveryPayload``.  This adapter wraps a
    ``RobotPlugin`` to satisfy that contract.
    """

    def __init__(
        self,
        plugin: RobotPlugin,
        signing_key: str = "default_hmac_key",
    ) -> None:
        self.plugin = plugin
        meta = plugin.metadata()

        self.robot_id: str = meta.name
        self.signing_key: str = signing_key

        # Defaults — enriched after a successful bid() call.
        self.capability_metadata: dict = {
            "sensors": [],
            "mobility_type": meta.robot_type,
            "indoor_capable": True,
            "location": meta.url_prefix,
        }
        self.reputation_metadata: dict = {
            "completion_rate": 0.5,
            "tasks_completed": 0,
        }

        # Internal: cache the bid dict for execute() to reuse metadata.
        self._last_bid_dict: dict | None = None

    # ------------------------------------------------------------------
    # bid_engine — called from a sync context by AuctionEngine
    # ------------------------------------------------------------------

    def bid_engine(self, task: Task) -> Bid | None:
        """Call the plugin's async ``bid()`` and convert to a ``Bid`` dataclass."""
        task_spec = _task_to_spec(task)

        try:
            bid_dict = _run_async(self.plugin.bid(task_spec))
        except Exception:
            log.debug("Plugin %s bid() raised; declining.", self.robot_id, exc_info=True)
            return None

        if bid_dict is None:
            return None

        self._last_bid_dict = bid_dict

        # Enrich adapter metadata from the bid response so that the engine
        # sees the same rich data as a native MockRobot.
        cap = bid_dict.get("capability_metadata", {})
        if cap:
            self.capability_metadata = cap
        rep = bid_dict.get("reputation_metadata", {})
        if rep:
            self.reputation_metadata = rep

        price = Decimal(str(bid_dict.get("price", "1.00")))
        sla = int(bid_dict.get("sla_commitment_seconds", task.sla_seconds))
        confidence = float(bid_dict.get("ai_confidence", 0.5))

        bid_hash = sign_bid(self.robot_id, task.request_id, price, self.signing_key)

        return Bid(
            request_id=task.request_id,
            robot_id=self.robot_id,
            price=price,
            sla_commitment_seconds=sla,
            ai_confidence=confidence,
            capability_metadata=self.capability_metadata,
            reputation_metadata=self.reputation_metadata,
            bid_hash=bid_hash,
        )

    # ------------------------------------------------------------------
    # execute — called from an async context by AuctionEngine
    # ------------------------------------------------------------------

    async def execute(self, task: Task) -> DeliveryPayload:
        """Execute via the plugin's MCP tools or simulator endpoint.

        Strategy:
        1. If the plugin has a ``client`` attribute (set by ``register_tools``),
           attempt to call the sensor endpoint directly.
        2. Otherwise, fall back to the fakerover simulator at localhost:8080.
        """
        data: dict = {}
        client = getattr(self.plugin, "client", None)

        if client is not None:
            try:
                sensor_data = await client.get("/sensor/ht")
                data = {
                    "temperature_celsius": sensor_data["temperature"],
                    "humidity_percent": sensor_data["humidity"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            except Exception:
                log.warning(
                    "Plugin client sensor read failed for %s; trying httpx fallback.",
                    self.robot_id,
                    exc_info=True,
                )
                client = None  # trigger fallback

        if not data:
            # Fallback: call the simulator directly via httpx.
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get("http://localhost:8080/sensor/ht")
                raw = resp.json()
            data = {
                "temperature_celsius": raw["temperature"],
                "humidity_percent": raw["humidity"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        now = datetime.now(timezone.utc)
        elapsed = (now - task.posted_at).total_seconds()
        sla_met = elapsed <= task.sla_seconds

        return DeliveryPayload(
            request_id=task.request_id,
            robot_id=self.robot_id,
            data=data,
            delivered_at=now,
            sla_met=sla_met,
        )


# ---------------------------------------------------------------------------
# discover_and_adapt — the public entry point
# ---------------------------------------------------------------------------

def discover_and_adapt(
    fleet_provider: str | None = None,
    signing_key: str = "default_hmac_key",
) -> list[PluginRobotAdapter]:
    """Discover robots on-chain and wrap them as auction-compatible adapters.

    Returns an empty list when the ``yakrover-8004-mcp`` package is not
    importable — the auction engine falls back to mock robots only.

    Args:
        fleet_provider: Optional filter passed to ``discover_robots()``.
        signing_key: Shared HMAC key used to sign bids from adapted robots.

    Returns:
        A list of :class:`PluginRobotAdapter` instances, one per discovered
        robot whose plugin class can be located and instantiated.
    """
    try:
        from core.discovery import discover_robots
    except ImportError:
        log.info("yakrover-8004-mcp not importable — skipping on-chain discovery.")
        return []

    try:
        raw = discover_robots(fleet_provider=fleet_provider)
    except Exception:
        log.warning("On-chain discovery failed.", exc_info=True)
        return []

    adapters: list[PluginRobotAdapter] = []
    for entry in raw:
        plugin = _instantiate_plugin(entry)
        if plugin is None:
            log.debug("No plugin found for discovered robot: %s", entry.get("name"))
            continue
        adapters.append(PluginRobotAdapter(plugin, signing_key=signing_key))

    log.info("Discovered %d on-chain robot(s), adapted %d.", len(raw), len(adapters))
    return adapters


def discover_and_adapt_from_plugins(
    plugins: list[RobotPlugin],
    signing_key: str = "default_hmac_key",
) -> list[PluginRobotAdapter]:
    """Wrap pre-instantiated RobotPlugin instances as auction adapters.

    Useful when you already have plugin objects (e.g. from a running MCP
    server) and want to add them to an AuctionEngine without on-chain
    discovery.
    """
    return [PluginRobotAdapter(p, signing_key=signing_key) for p in plugins]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _task_to_spec(task: Task) -> dict:
    """Convert an auction ``Task`` dataclass to the dict format RobotPlugin.bid() expects."""
    return {
        "request_id": task.request_id,
        "description": task.description,
        "task_category": task.task_category,
        "capability_requirements": task.capability_requirements,
        "budget_ceiling": str(task.budget_ceiling),
        "sla_seconds": task.sla_seconds,
    }


def _run_async(coro):
    """Run an async coroutine from a sync context.

    Uses the running loop if one exists (e.g. inside an async test or server),
    otherwise creates a new one.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside an async context — schedule in a new thread to avoid
        # blocking the event loop.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)

    return asyncio.run(coro)


_PLUGIN_REGISTRY: dict[str, type] = {}


def _instantiate_plugin(entry: dict) -> RobotPlugin | None:
    """Try to instantiate a RobotPlugin for a discovered robot entry.

    Looks up known plugin classes by fleet_provider and robot_type. Falls back
    to scanning ``robots.*`` subpackages.
    """
    # Lazy-populate the registry on first call.
    if not _PLUGIN_REGISTRY:
        _populate_plugin_registry()

    name = (entry.get("name") or "").lower()
    provider = (entry.get("fleet_provider") or "").lower()
    rtype = (entry.get("robot_type") or "").lower()

    # Try matching by name fragment, then provider+type.
    for key, cls in _PLUGIN_REGISTRY.items():
        if key in name or key in provider:
            try:
                return cls()
            except Exception:
                log.debug("Failed to instantiate plugin %s.", cls, exc_info=True)

    return None


def _populate_plugin_registry() -> None:
    """Scan for available RobotPlugin subclasses."""
    # Try importing known robots.  Each import is optional.
    _try_register("fakerover", "robots.fakerover", "FakeRoverPlugin")
    _try_register("tumbller", "robots.tumbller", "TumbllerPlugin")
    _try_register("tello", "robots.tello", "TelloPlugin")


def _try_register(key: str, module_path: str, class_name: str) -> None:
    """Attempt to import a plugin class and add it to the registry."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        _PLUGIN_REGISTRY[key] = cls
    except (ImportError, AttributeError):
        pass
