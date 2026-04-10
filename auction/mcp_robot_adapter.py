"""Adapter that calls a remote robot's MCP endpoint for bidding and execution.

Implements the MockRobot interface (robot_id, capability_metadata, bid_engine,
execute) so the AuctionEngine can use real on-chain robots discovered via
subgraph alongside mock robots.

The robot's MCP server exposes:
- robot_submit_bid: evaluate a task and return a bid
- robot_execute_task: execute an accepted task and return delivery data

Communication uses MCP Streamable HTTP (JSON-RPC over HTTP with session).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from auction.core import Bid, DeliveryPayload, Task, sign_bid

log = logging.getLogger(__name__)


class MCPRobotAdapter:
    """Calls a remote robot's MCP endpoint for bidding and execution.

    Satisfies the interface expected by AuctionEngine:
    - robot_id (str)
    - capability_metadata (dict)
    - reputation_metadata (dict)
    - signing_key (str)
    - bid_engine(task) -> Bid | None
    - async execute(task) -> DeliveryPayload
    """

    def __init__(
        self,
        robot_id: str,
        mcp_endpoint: str,
        wallet: str | None = None,
        chain_id: int | None = None,
        description: str = "",
        signing_key: str = "default_hmac_key",
        bearer_token: str | None = None,
        mcp_tools: list[str] | None = None,
    ) -> None:
        self.robot_id = robot_id
        self.name = robot_id
        self.mcp_endpoint = mcp_endpoint
        self.wallet = wallet
        self.chain_id = chain_id
        self.signing_key = signing_key
        self.bearer_token = bearer_token
        self._known_tools: list[str] = list(mcp_tools) if mcp_tools else []

        self.capability_metadata: dict = {
            "sensors": [
                {"type": "temperature", "model": "AHT20", "accuracy_celsius": 0.3},
                {"type": "humidity", "model": "AHT20", "accuracy_rh_pct": 2.0},
            ],
            "mobility_type": "differential_drive",
            "indoor_capable": True,
            "location": description or mcp_endpoint,
        }
        self.reputation_metadata: dict = {
            "completion_rate": 0.9,
            "tasks_completed": 0,
            "on_time_rate": 0.9,
        }

        self._session_id: str | None = None
        self.is_simulator: bool = "fakerover" in robot_id.lower() or "faker" in robot_id.lower()

    def _resolve_tools(self, tool_list: list[str]) -> tuple[str | None, str | None]:
        """Match available tools to move and sensor actions by name patterns.

        Returns (move_tool, sensor_tool) or None for either if not found.
        Searches for common patterns in tool names.
        """
        move_tool = None
        sensor_tool = None

        move_patterns = ["_move", "move_", "fly_waypoint", "navigate", "drive"]
        sensor_patterns = ["temperature", "humidity", "sensor", "reading", "measure", "capture"]

        for tool_name in tool_list:
            lower = tool_name.lower()
            if not move_tool:
                for pat in move_patterns:
                    if pat in lower:
                        move_tool = tool_name
                        break
            if not sensor_tool:
                for pat in sensor_patterns:
                    if pat in lower:
                        sensor_tool = tool_name
                        break

        return move_tool, sensor_tool

    def is_reachable(self, timeout: float = 5.0) -> bool:
        """Quick probe: can we initialize an MCP session with this robot?"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            if self.bearer_token:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
            resp = httpx.post(
                self.mcp_endpoint,
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "probe", "version": "1.0"},
                    },
                    "id": 0,
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self._session_id = sid
                return True
        except Exception:
            pass
        return False

    def _mcp_headers(self) -> dict:
        """Headers for MCP Streamable HTTP."""
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        if self.bearer_token:
            h["Authorization"] = f"Bearer {self.bearer_token}"
        return h

    async def _mcp_call(self, method: str, params: dict, call_id: int = 1) -> dict | None:
        """Make an MCP JSON-RPC call and return the result."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": call_id,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Initialize session if needed
            if not self._session_id:
                init_resp = await client.post(
                    self.mcp_endpoint,
                    headers=self._mcp_headers(),
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "marketplace", "version": "1.0"},
                        },
                        "id": 0,
                    },
                )
                # Extract session ID from response header
                sid = init_resp.headers.get("mcp-session-id")
                if sid:
                    self._session_id = sid

            resp = await client.post(
                self.mcp_endpoint,
                headers=self._mcp_headers(),
                json=payload,
            )

        # Parse SSE response — look for data: lines
        for line in resp.text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                import json
                msg = json.loads(line[6:])
                if "result" in msg:
                    return msg["result"]
                if "error" in msg:
                    log.warning("MCP error from %s: %s", self.robot_id, msg["error"])
                    return None

        return None

    # ------------------------------------------------------------------
    # bid_engine — called from sync context by AuctionEngine
    # ------------------------------------------------------------------

    def bid_engine(self, task: Task) -> Bid | None:
        """Call robot_submit_bid via MCP and convert to a Bid."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(asyncio.run, self._bid_async(task)).result(timeout=30)
        else:
            result = asyncio.run(self._bid_async(task))

        return result

    async def _bid_async(self, task: Task) -> Bid | None:
        """Async implementation of bid request."""
        result = await self._mcp_call("tools/call", {
            "name": "robot_submit_bid",
            "arguments": {
                "task_description": task.description,
                "task_category": task.task_category,
                "budget_ceiling": float(task.budget_ceiling),
                "sla_seconds": task.sla_seconds,
                "capability_requirements": task.capability_requirements,
            },
        })

        if not result:
            return None

        # Parse structured content or text content
        content = result
        if "structuredContent" in result:
            content = result["structuredContent"]
        elif "content" in result and isinstance(result["content"], list):
            import json
            for block in result["content"]:
                if block.get("type") == "text":
                    try:
                        content = json.loads(block["text"])
                    except (json.JSONDecodeError, KeyError):
                        pass

        if result.get("isError"):
            log.debug("Robot %s declined bid: %s", self.robot_id, content)
            return None

        if not content.get("willing_to_bid"):
            return None

        price = Decimal(str(content.get("price", "1.00")))
        sla = int(content.get("sla_commitment_seconds", task.sla_seconds))
        confidence = float(content.get("confidence", 0.5))

        # Enrich capability metadata from bid response
        caps = content.get("capabilities_offered", [])
        if caps:
            self.capability_metadata["sensors"] = [
                {"type": s} if isinstance(s, str) else s for s in caps
            ]

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
    # execute — called from async context by AuctionEngine
    # ------------------------------------------------------------------

    async def execute(self, task: Task) -> DeliveryPayload:
        """Execute by moving the robot to waypoints and reading sensors at each.

        For each waypoint: move forward → read temperature + humidity.
        Uses the robot's individual MCP tools (tumbller_move,
        tumbller_get_temperature_humidity) for real sensor data.
        Falls back to robot_execute_task if individual tools fail.
        """
        import asyncio

        # Pre-warm: ensure MCP session is alive and discover available tools
        if not self._session_id:
            log.info("Warming up MCP session for %s...", self.robot_id)
            await self._mcp_call("tools/list", {})

        # Discover tools from robot's MCP server if not already known
        if not self._known_tools:
            try:
                tools_result = await self._mcp_call("tools/list", {})
                if tools_result and isinstance(tools_result, dict):
                    tool_entries = tools_result.get("tools", [])
                    self._known_tools = [t["name"] for t in tool_entries if isinstance(t, dict) and "name" in t]
                    log.info("Discovered %d tools from %s: %s",
                             len(self._known_tools), self.robot_id, self._known_tools[:5])
            except Exception as e:
                log.warning("Tool discovery failed for %s: %s", self.robot_id, e)

        # Resolve move and sensor tools dynamically
        move_tool, sensor_tool = self._resolve_tools(self._known_tools)

        # DEPRECATED FALLBACK — commented out to test dynamic resolution.
        # If this causes execution failures, the robot's MCP server needs to
        # expose tools with discoverable names (containing "move", "temperature", etc.)
        # TODO: Remove entirely once dynamic resolution is verified in production.
        # if not move_tool:
        #     if "tumbller" in self.robot_id.lower():
        #         move_tool = "tumbller_move"
        #     else:
        #         move_tool = "fakerover_move"
        #     log.info("Using fallback move tool: %s", move_tool)
        # if not sensor_tool:
        #     if "tumbller" in self.robot_id.lower():
        #         sensor_tool = "tumbller_get_temperature_humidity"
        #     else:
        #         sensor_tool = "fakerover_get_temperature_humidity"
        #     log.info("Using fallback sensor tool: %s", sensor_tool)
        if not move_tool:
            log.warning("No move tool found for %s — execution will skip movement", self.robot_id)
        if not sensor_tool:
            log.warning("No sensor tool found for %s — execution will use robot_execute_task fallback", self.robot_id)

        log.info("Executing %s with tools: move=%s, sensor=%s", self.robot_id, move_tool, sensor_tool)

        start = datetime.now(UTC)
        num_waypoints = 3
        readings = []

        # Waypoint-by-waypoint execution using resolved tools
        for wp in range(1, num_waypoints + 1):
            if move_tool:
                move_result = await self._mcp_call("tools/call", {
                    "name": move_tool,
                    "arguments": {"direction": "forward"},
                })
                move_ok = move_result and not move_result.get("isError")
                if move_ok:
                    log.info("Waypoint %d: moved forward via %s", wp, move_tool)
                else:
                    log.warning("Waypoint %d: move failed (%s), reading at current position", wp, move_tool)

            # Brief pause for robot to settle
            await asyncio.sleep(1.0)
            if not sensor_tool:
                break  # no sensor tool — skip to robot_execute_task fallback
            sensor_result = await self._mcp_call("tools/call", {
                "name": sensor_tool,
                "arguments": {},
            })

            if sensor_result and not sensor_result.get("isError"):
                sensor_data = sensor_result.get("structuredContent") or {}
                if not sensor_data and sensor_result.get("content"):
                    import json
                    for block in sensor_result["content"]:
                        if block.get("type") == "text":
                            try:
                                sensor_data = json.loads(block["text"])
                            except (json.JSONDecodeError, KeyError):
                                pass

                readings.append({
                    "waypoint": wp,
                    "temperature_c": round(float(sensor_data.get("temperature", 0)), 1),
                    "humidity_pct": round(float(sensor_data.get("humidity", 0)), 1),
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                log.info("Waypoint %d: %.1f°C, %.1f%%",
                         wp, readings[-1]["temperature_c"], readings[-1]["humidity_pct"])
            else:
                log.warning("Waypoint %d: sensor read failed", wp)

        now = datetime.now(UTC)
        elapsed = (now - start).total_seconds()
        sla_met = (now - task.posted_at).total_seconds() <= task.sla_seconds

        # If no readings at all, fall back to robot_execute_task
        if not readings:
            log.warning("No waypoint readings — falling back to robot_execute_task")
            fallback = await self._mcp_call("tools/call", {
                "name": "robot_execute_task",
                "arguments": {
                    "task_id": task.request_id,
                    "task_description": task.description,
                    "parameters": task.capability_requirements,
                },
            })
            content = {}
            if fallback:
                content = fallback.get("structuredContent") or {}
                if not content and fallback.get("content"):
                    import json
                    for block in fallback["content"]:
                        if block.get("type") == "text":
                            try:
                                content = json.loads(block["text"])
                            except (json.JSONDecodeError, KeyError):
                                pass
            dd = content.get("delivery_data", {})
            # Parse single reading into waypoint format
            for r in dd.get("readings", []):
                readings.append({
                    "waypoint": len(readings) + 1,
                    "temperature_c": round(float(r.get("value", 0)), 1) if r.get("type") == "temperature" else 0,
                    "humidity_pct": round(float(r.get("value", 0)), 1) if r.get("type") == "humidity" else 0,
                    "timestamp": now.isoformat(),
                })

        temps = [r["temperature_c"] for r in readings if r.get("temperature_c")]
        humids = [r["humidity_pct"] for r in readings if r.get("humidity_pct")]
        summary = (
            f"{len(readings)} waypoints measured by {self.robot_id}. "
            f"Temp: {min(temps, default=0):.1f}-{max(temps, default=0):.1f}°C, "
            f"Humidity: {min(humids, default=0):.1f}-{max(humids, default=0):.1f}%"
        )

        data = {
            "readings": readings,
            "summary": summary,
            "duration_seconds": round(elapsed, 1),
        }

        return DeliveryPayload(
            request_id=task.request_id,
            robot_id=self.robot_id,
            data=data,
            delivered_at=now,
            sla_met=sla_met,
        )
