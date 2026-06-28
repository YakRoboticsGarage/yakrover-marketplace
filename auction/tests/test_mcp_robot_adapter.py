"""Tests for MCPRobotAdapter.execute() fallback to robot_execute_task.

Covers two bugs found in the teleop / ground-delivery path:

A. The adapter must supply a motor-command sequence (parameters["commands"]) to
   teleop robots — the task pipeline doesn't carry one, so a default is injected
   for delivery_ground tasks. Without it the robot rejects the task.

B. When the robot returns no usable delivery_data (an error / success=false), the
   adapter must raise RobotExecutionError instead of fabricating a zero-value
   sensor payload that later fails QA with an opaque "missing required field".
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from auction.core import Task
from auction.mcp_robot_adapter import (
    DEFAULT_TELEOP_COMMANDS,
    MCPRobotAdapter,
    RobotExecutionError,
)


def _ground_task(**overrides) -> Task:
    defaults = {
        "description": "Issue a short motor-command sequence to the Tumbller",
        "task_category": "delivery_ground",
        "capability_requirements": {"hard": {"mobility_type": "ground_wheeled"}},
        "budget_ceiling": Decimal("0.60"),
        "sla_seconds": 60,
    }
    defaults.update(overrides)
    return Task(**defaults)


def _adapter() -> MCPRobotAdapter:
    # Move tool present, no sensor tool → execute() goes straight to the
    # robot_execute_task fallback (the teleop path).
    return MCPRobotAdapter(
        robot_id="npc-robot",
        mcp_endpoint="https://example.invalid/mcp",
        mcp_tools=["berlin_tumbller_move", "robot_execute_task"],
    )


def _mock_mcp_call(exec_response: dict, recorder: list):
    """Build a fake _mcp_call that records calls and returns canned results."""

    async def _call(method, params, call_id=1):
        recorder.append((method, params))
        if method == "tools/call" and params.get("name", "").endswith("robot_execute_task"):
            return exec_response
        # tools/list warmup, move calls, etc. — benign empty result.
        return {}

    return _call


@pytest.mark.asyncio
async def test_teleop_injects_default_commands_and_passes_through_delivery():
    """Fix A: default commands are sent; the robot's ground delivery is returned as-is."""
    delivery_data = {
        "task_id": "req_test",
        "commands_executed": [{"command": "forward", "timestamp_ms": 1, "duration_ms": 2}],
        "duration_s": 1.0,
        "completion_status": "completed",
        "summary": "Executed 1/1 motor commands in 1.0s (completed).",
    }
    exec_response = {
        "structuredContent": {"success": True, "error": None, "delivery_data": delivery_data}
    }
    calls: list = []
    adapter = _adapter()
    adapter._mcp_call = _mock_mcp_call(exec_response, calls)  # type: ignore[method-assign]

    payload = await adapter.execute(_ground_task())

    # The deliverable is the robot's real ground-delivery shape (has commands_executed),
    # NOT a fabricated readings payload.
    assert payload.data == delivery_data
    assert "commands_executed" in payload.data
    assert "readings" not in payload.data

    # robot_execute_task was called with the default command sequence.
    exec_calls = [
        p for m, p in calls if m == "tools/call" and p.get("name", "").endswith("robot_execute_task")
    ]
    assert len(exec_calls) == 1
    sent = exec_calls[0]["arguments"]["parameters"]
    assert sent["commands"] == DEFAULT_TELEOP_COMMANDS


@pytest.mark.asyncio
async def test_explicit_task_commands_are_not_overridden():
    """Fix A: an explicit parameters['commands'] from the task spec wins over the default."""
    delivery_data = {
        "task_id": "req_test",
        "commands_executed": [{"command": "left", "timestamp_ms": 1, "duration_ms": 2}],
        "duration_s": 0.5,
        "completion_status": "completed",
        "summary": "ok",
    }
    exec_response = {"structuredContent": {"success": True, "delivery_data": delivery_data}}
    calls: list = []
    adapter = _adapter()
    adapter._mcp_call = _mock_mcp_call(exec_response, calls)  # type: ignore[method-assign]

    task = _ground_task(capability_requirements={"hard": {}, "commands": ["left", "stop"]})
    await adapter.execute(task)

    exec_calls = [
        p for m, p in calls if m == "tools/call" and p.get("name", "").endswith("robot_execute_task")
    ]
    assert exec_calls[0]["arguments"]["parameters"]["commands"] == ["left", "stop"]


@pytest.mark.asyncio
async def test_no_delivery_data_raises_instead_of_fabricating():
    """Fix B: a robot error (no delivery_data) raises RobotExecutionError, not a fake payload."""
    exec_response = {
        "structuredContent": {
            "success": False,
            "error": "parameters.commands missing or not a non-empty list",
            "partial_data": {},
        }
    }
    calls: list = []
    adapter = _adapter()
    adapter._mcp_call = _mock_mcp_call(exec_response, calls)  # type: ignore[method-assign]

    with pytest.raises(RobotExecutionError) as exc_info:
        await adapter.execute(_ground_task())

    # The robot's real error is surfaced, not swallowed.
    assert "parameters.commands missing" in str(exc_info.value)
