"""MCP tool registration for the robot task auction marketplace.

Provides ``register_auction_tools(mcp, engine)`` which registers thin
MCP tool wrappers around :class:`AuctionEngine` methods on a FastMCP
server instance.  Each tool catches expected exceptions and returns a
structured error dict instead of raising, and converts Decimal values
to strings for JSON serialization.

v1.0 additions: fund_wallet, get_wallet_balance, onboard_operator,
get_operator_status, accept_and_execute, cancel_task, get_task_schema,
and quick_hire — bringing the total to 15 tools.  Also: stripe_transfer_id
in confirm_delivery response and structured error responses on all tools.

This module is imported by the upstream ``src/core/server.py`` when
auction mode is enabled.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

from auction.core import VALID_TASK_CATEGORIES
from auction.engine import AuctionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decimals_to_strings(obj: Any) -> Any:
    """Recursively convert Decimal values to strings for JSON serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _decimals_to_strings(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_decimals_to_strings(item) for item in obj]
    return obj


def _error_response_structured(
    error_code: str, message: str, hint: str,
) -> dict:
    """Build a structured, agent-friendly error dict."""
    return {"error_code": error_code, "message": message, "hint": hint}


def _error_response(exc: Exception) -> dict:
    """Map a Python exception to a structured, agent-friendly error dict.

    Never exposes Python exception class names to MCP consumers.
    """
    msg = str(exc)
    # Map known exception patterns to descriptive codes
    if isinstance(exc, AttributeError) and "capability_requirements" in msg:
        return _error_response_structured(
            "INVALID_CAPABILITY_REQUIREMENTS_TYPE",
            f"capability_requirements must be a dict: {msg}",
            'Expected shape: {"tool": "...", "hard": {...}, "payload": {"format": "json"}}',
        )
    if isinstance(exc, AttributeError):
        return _error_response_structured(
            "INVALID_ARGUMENT_TYPE",
            msg,
            "Check argument types — a dict may have been passed as a list or string.",
        )
    if isinstance(exc, KeyError):
        key = msg.strip("'\"")
        if "wallet" in key.lower() or "buyer" in key.lower() or "does not exist" in msg.lower():
            return _error_response_structured(
                "WALLET_NOT_FOUND",
                f"Wallet not found: {key}",
                "Use auction_fund_wallet to create and fund a wallet, or use the default wallet_id 'buyer'.",
            )
        return _error_response_structured(
            "NOT_FOUND",
            msg,
            "Check the ID and try again.",
        )
    if isinstance(exc, ValueError):
        return _error_response_structured(
            "VALIDATION_ERROR",
            msg,
            "Check the tool description or call auction_get_task_schema for the expected format.",
        )
    if isinstance(exc, asyncio.TimeoutError):
        return _error_response_structured(
            "SLA_TIMEOUT",
            "Task execution exceeded the SLA deadline.",
            "The task will be re-pooled automatically. Check auction_get_status.",
        )
    # Generic fallback — still no Python class name exposed
    return _error_response_structured(
        "INTERNAL_ERROR",
        msg,
        "An unexpected error occurred. Retry or contact support.",
    )


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_auction_tools(
    mcp: FastMCP,
    engine: AuctionEngine,
    *,
    stripe_wallet_service: object | None = None,
    stripe_service: object | None = None,
) -> None:
    """Register auction MCP tools on a FastMCP server instance.

    Parameters
    ----------
    mcp:
        The FastMCP server to register tools on.
    engine:
        The :class:`AuctionEngine` instance whose methods the tools wrap.
    stripe_wallet_service:
        Optional :class:`StripeWalletService` for wallet top-up tools.
    stripe_service:
        Optional :class:`StripeService` for operator onboarding tools.
    """

    @mcp.tool()
    async def auction_post_task(task_spec: dict) -> dict:
        """Post a task to the robot auction marketplace.

        Accepts a task specification dict with these keys:

        - description (str): Human-readable task description.
        - task_category (str, optional): One of "env_sensing", "visual_inspection",
          "mapping", "delivery_ground", "aerial_survey". If omitted, inferred
          from capability_requirements.
        - capability_requirements (dict): Robot capability filter and payload
          specification. Structure:
            {
              "tool": "<robot_tool_name>",
              "hard": {                        # optional hard constraints
                "sensors_required": ["temperature", "humidity"],
                "indoor_capable": true,
                "min_battery_percent": 20,
                "max_distance_meters": 50
              },
              "payload": {                     # expected delivery format
                "format": "json",
                "fields": ["temperature_celsius", "humidity_percent"]
              }
            }
        - budget_ceiling (float): Maximum price in USD. Minimum $0.50.
          Typical range: $0.50-$5.00 for sensor readings.
        - sla_seconds (int): Maximum seconds for task completion. Must be > 0.

        Example task_spec:
        {
          "description": "Read temperature in Bay 3",
          "task_category": "env_sensing",
          "capability_requirements": {
            "tool": "tumbller_get_temperature_humidity",
            "payload": {"format": "json", "fields": ["temperature_celsius", "humidity_percent"]}
          },
          "budget_ceiling": 0.50,
          "sla_seconds": 120
        }

        Returns task status including eligible robots and request_id.
        If the spec has errors, ALL validation errors are returned at once.
        """
        try:
            result = engine.post_task(task_spec)
            return _decimals_to_strings(result)
        except ValueError as exc:
            error_msg = str(exc)
            response = _error_response(exc)
            # If it's a batch validation error, parse individual errors into a list
            if "Task validation failed with" in error_msg and "; " in error_msg:
                # Extract the errors portion after the prefix
                prefix_end = error_msg.index(": ") + 2
                errors_str = error_msg[prefix_end:]
                response["errors"] = errors_str.split("; ")
            return response

    @mcp.tool()
    async def auction_get_bids(request_id: str) -> dict:
        """Collect and score bids from eligible robots for a posted task.

        Returns scored bids with recommended winner. Each bid includes an
        "eligible" flag indicating whether it is within budget, and a
        "disqualification_reason" (null when eligible).

        Scoring weights: price 40%, SLA 25%, confidence 20%, reputation 15%.
        Bids exceeding budget_ceiling receive a score of 0 and are marked
        ineligible.
        """
        try:
            result = engine.get_bids(request_id)
            return _decimals_to_strings(result)
        except KeyError as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_accept_bid(request_id: str, robot_id: str) -> dict:
        """Accept a bid from a specific robot.

        Triggers 25% payment reservation and notifies losing bidders.
        The task must be in "bidding" state. The robot_id must match one of
        the bids returned by auction_get_bids.

        **Next step:** After accepting, call auction_execute(request_id) to
        dispatch the task to the winning robot. Or use auction_accept_and_execute
        to combine both steps.

        Valid task states for this action: "bidding".
        """
        try:
            result = engine.accept_bid(request_id, robot_id)
            return _decimals_to_strings(result)
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_execute(request_id: str) -> dict:
        """Dispatch the task to the winning robot for execution.

        Awaits the robot's execution coroutine with SLA timeout enforcement.
        Returns delivery payload with sensor data, or re-pool info on timeout.
        """
        try:
            result = await engine.execute(request_id)
            return _decimals_to_strings(result)
        except (ValueError, KeyError, asyncio.TimeoutError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_accept_and_execute(request_id: str, robot_id: str) -> dict:
        """Accept a bid and immediately execute the task in one step.

        Convenience tool that calls accept_bid then execute sequentially.
        Use this when you want to accept the winning bid and dispatch
        execution without a separate auction_execute call.

        The separate auction_accept_bid and auction_execute tools remain
        available for fine-grained control.

        Valid task states for this action: "bidding".
        """
        try:
            accept_result = engine.accept_bid(request_id, robot_id)
            execute_result = await engine.execute(request_id)
            return _decimals_to_strings({
                "accept": accept_result,
                "execute": execute_result,
                "state": execute_result.get("state"),
                "request_id": request_id,
            })
        except (ValueError, KeyError, asyncio.TimeoutError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_confirm_delivery(request_id: str) -> dict:
        """Confirm that the delivered payload is satisfactory.

        Triggers 75% delivery payment, operator credit, settlement, and
        Stripe transfer (if StripeService is configured).

        Valid task states for this action: "delivered".
        If payload.format is not specified in capability_requirements, it
        defaults to "json".

        If confirm_delivery is not called within auto_accept_seconds
        (default 3600 = 1 hour), the delivery is automatically accepted
        and payment is settled.
        """
        try:
            result = engine.confirm_delivery(request_id)
            return _decimals_to_strings(result)
        except ValueError as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_reject_delivery(request_id: str, reason: str) -> dict:
        """Reject the delivered payload with a reason.

        Refunds the 25% reservation and re-pools the task for new bids.
        Valid task states for this action: "delivered".
        """
        try:
            result = engine.reject_delivery(request_id, reason)
            return _decimals_to_strings(result)
        except ValueError as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_cancel_task(request_id: str, reason: str) -> dict:
        """Cancel a task stuck in any non-terminal state and refund reservations.

        Use this to recover from a malformed spec, an unresponsive robot, or
        any situation where the auction should not continue. Refunds any 25%
        wallet reservation if a bid was previously accepted.

        Works in any state except "settled" and "withdrawn" (terminal).
        Transitions the task to "withdrawn".
        """
        try:
            result = engine.cancel_task(request_id, reason)
            return _decimals_to_strings(result)
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_get_task_schema() -> dict:
        """Return the expected JSON schema for task_spec, including valid categories and constraints.

        Use this before calling auction_post_task to understand the required
        structure and avoid trial-and-error. The returned schema describes
        every field, its type, valid values, and constraints.
        """
        return {
            "task_spec_schema": {
                "description": {
                    "type": "string",
                    "required": True,
                    "description": "Human-readable task description.",
                },
                "task_category": {
                    "type": "string",
                    "required": False,
                    "valid_values": sorted(VALID_TASK_CATEGORIES),
                    "description": "Task category enum. Optional — inferred from capability_requirements if omitted.",
                },
                "capability_requirements": {
                    "type": "dict",
                    "required": True,
                    "description": "Robot capability filter and expected delivery format.",
                    "properties": {
                        "tool": {
                            "type": "string",
                            "required": False,
                            "description": "Name of the robot tool to invoke (e.g. 'tumbller_get_temperature_humidity').",
                        },
                        "hard": {
                            "type": "dict",
                            "required": False,
                            "description": "Hard constraint filter. Robots not meeting these are excluded.",
                            "properties": {
                                "sensors_required": {"type": "list[str]", "description": "Sensors the robot must have."},
                                "indoor_capable": {"type": "bool", "description": "Robot must be indoor-capable."},
                                "min_battery_percent": {"type": "int", "description": "Minimum battery percentage."},
                                "max_distance_meters": {"type": "float", "description": "Maximum distance to task location."},
                            },
                        },
                        "payload": {
                            "type": "dict",
                            "required": False,
                            "description": "Expected delivery payload specification.",
                            "properties": {
                                "format": {"type": "string", "default": "json", "description": "Payload format. Defaults to 'json'."},
                                "fields": {"type": "list[str]", "description": "Expected field names in the delivered data."},
                            },
                        },
                    },
                },
                "budget_ceiling": {
                    "type": "float",
                    "required": True,
                    "constraint": ">= 0.50",
                    "description": "Maximum price in USD. Minimum $0.50. Typical range: $0.50-$5.00 for sensor readings.",
                },
                "sla_seconds": {
                    "type": "int",
                    "required": True,
                    "constraint": "> 0",
                    "description": "Maximum seconds for task completion.",
                },
            },
            "example": {
                "description": "Read temperature in Bay 3",
                "task_category": "env_sensing",
                "capability_requirements": {
                    "tool": "tumbller_get_temperature_humidity",
                    "payload": {"format": "json", "fields": ["temperature_celsius", "humidity_percent"]},
                },
                "budget_ceiling": 0.50,
                "sla_seconds": 120,
            },
        }

    @mcp.tool()
    async def auction_get_status(request_id: str) -> dict:
        """Get full status of a task including state, bids, wallet entries, and timer info.

        The response includes available_actions (tools callable in the current
        state) and a hint describing the expected next step.

        If auto_accept_timer_active is true, the response includes
        auto_accept_deadline (ISO timestamp). If confirm_delivery is not
        called within auto_accept_seconds (default 3600 = 1 hour), the
        delivery is automatically accepted and payment is settled.
        """
        try:
            result = engine.get_task_status(request_id)
            return _decimals_to_strings(result)
        except KeyError as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # v1.0 tools: wallet + operator management
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_fund_wallet(
        wallet_id: str = "buyer",
        amount: float = 10.0,
        payment_method: str = "pm_card_visa",
    ) -> dict:
        """Fund an auction wallet via Stripe PaymentIntent.

        Creates a Stripe PaymentIntent for the given amount and credits
        the internal wallet.  In stub mode (no STRIPE_SECRET_KEY), the
        Stripe call is simulated but the internal ledger is still updated.

        wallet_id defaults to "buyer" (the standard buyer wallet).
        """
        if stripe_wallet_service is None:
            # Fall back to engine's internal wallet when Stripe is not configured
            if engine.wallet is not None:
                try:
                    # Ensure wallet exists
                    try:
                        engine.wallet.get_balance(wallet_id)
                    except KeyError:
                        engine.wallet.create_wallet(wallet_id)
                    engine.wallet.credit(
                        wallet_id, Decimal(str(amount)), "", "credit",
                        note=f"Funded ${amount} (no Stripe — internal ledger)",
                    )
                    balance = engine.wallet.get_balance(wallet_id)
                    return {
                        "wallet_id": wallet_id,
                        "funded": str(Decimal(str(amount))),
                        "balance": str(balance),
                        "source": "internal_ledger",
                    }
                except Exception as exc:
                    return _error_response(exc)
            return _error_response_structured(
                "WALLET_SERVICE_NOT_CONFIGURED",
                "Neither Stripe wallet service nor internal wallet is available.",
                "Ensure the auction engine is initialized with a WalletLedger.",
            )
        try:
            result = stripe_wallet_service.fund_wallet(wallet_id, Decimal(str(amount)), payment_method)
            return _decimals_to_strings(result)
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_get_wallet_balance(wallet_id: str = "buyer") -> dict:
        """Get the current balance of an auction wallet.

        wallet_id defaults to "buyer" (the standard buyer wallet).
        """
        if stripe_wallet_service is None:
            # Fall back to engine wallet if available
            if engine.wallet is not None:
                try:
                    balance = engine.wallet.get_balance(wallet_id)
                    return {"wallet_id": wallet_id, "balance": str(balance)}
                except KeyError:
                    return _error_response_structured(
                        "WALLET_NOT_FOUND",
                        f"Wallet '{wallet_id}' does not exist.",
                        "Use auction_fund_wallet to create and fund a wallet, or use the default wallet_id 'buyer'.",
                    )
            return _error_response_structured(
                "WALLET_SERVICE_NOT_CONFIGURED",
                "Neither Stripe wallet service nor internal wallet is available.",
                "Ensure the auction engine is initialized with a WalletLedger.",
            )
        try:
            balance = stripe_wallet_service.get_balance(wallet_id)
            return {"wallet_id": wallet_id, "balance": str(balance)}
        except KeyError:
            return _error_response_structured(
                "WALLET_NOT_FOUND",
                f"Wallet '{wallet_id}' does not exist.",
                "Use auction_fund_wallet to create and fund a wallet, or use the default wallet_id 'buyer'.",
            )

    @mcp.tool()
    async def auction_onboard_operator(
        email: str,
        robot_id: str,
        country: str = "FI",
    ) -> dict:
        """Onboard a robot operator by creating a Stripe Connect Express account.

        Returns the Connect account details (or a stub dict in stub mode).
        """
        if stripe_service is None:
            return {"error": "Stripe service not configured", "error_type": "ConfigError"}
        try:
            result = stripe_service.create_connect_account(email=email, country=country)
            result["robot_id"] = robot_id
            return _decimals_to_strings(result)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_get_operator_status(robot_id: str) -> dict:
        """Get the Stripe Connect account status for a robot operator.

        Uses the convention ``acct_{robot_id}`` for the account ID.
        """
        if stripe_service is None:
            return {"error": "Stripe service not configured", "error_type": "ConfigError"}
        try:
            account_id = f"acct_{robot_id}"
            result = stripe_service.get_account(account_id)
            result["robot_id"] = robot_id
            return _decimals_to_strings(result)
        except Exception as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # Convenience tools (REC-16b, REC-19)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_quick_hire(task_spec: dict) -> dict:
        """Post a task, wait for bids, accept the best one, execute, and confirm — all in one call.

        Returns the sensor data, cost, and robot ID. For simple tasks where you want the result
        without managing individual auction steps.

        Accepts the same task_spec as auction_post_task. Example:
        {
          "description": "Read temperature in Bay 3",
          "task_category": "env_sensing",
          "capability_requirements": {
            "tool": "tumbller_get_temperature_humidity",
            "payload": {"format": "json", "fields": ["temperature_celsius", "humidity_percent"]}
          },
          "budget_ceiling": 0.50,
          "sla_seconds": 120
        }

        The individual auction tools (post_task, get_bids, accept_bid, execute,
        confirm_delivery) remain available for fine-grained control.
        """
        current_state = "init"
        request_id = None
        try:
            # Step 1: Post task
            current_state = "posting"
            post_result = engine.post_task(task_spec)
            request_id = post_result["request_id"]

            if post_result["state"] == "withdrawn":
                return _decimals_to_strings({
                    "error_code": "NO_ELIGIBLE_ROBOTS",
                    "message": "No robots are eligible for this task.",
                    "request_id": request_id,
                    "state": post_result["state"],
                    "hint": "Check capability_requirements or try a different task_category.",
                })

            # Step 2: Get bids
            current_state = "bidding"
            bids_result = engine.get_bids(request_id)

            if bids_result["bid_count"] == 0:
                return _decimals_to_strings({
                    "error_code": "NO_BIDS",
                    "message": "No robots submitted bids.",
                    "request_id": request_id,
                    "state": bids_result["state"],
                    "hint": "Try increasing budget_ceiling or relaxing capability_requirements.",
                })

            recommended = bids_result.get("recommended_winner")
            if recommended is None:
                return _decimals_to_strings({
                    "error_code": "NO_ELIGIBLE_BIDS",
                    "message": "All bids were disqualified (e.g. over budget).",
                    "request_id": request_id,
                    "state": bids_result["state"],
                    "hint": "Try increasing budget_ceiling.",
                })

            # Step 3: Accept recommended winner
            current_state = "accepting"
            accept_result = engine.accept_bid(request_id, recommended)

            # Step 4: Execute
            current_state = "executing"
            execute_result = await engine.execute(request_id)

            # Handle timeout / re-pool
            if execute_result.get("timeout"):
                return _decimals_to_strings({
                    "error_code": "EXECUTION_TIMEOUT",
                    "message": f"Robot {recommended} timed out during execution.",
                    "request_id": request_id,
                    "state": execute_result["state"],
                    "hint": "The task has been re-pooled for new bids. Use auction_get_bids to continue manually.",
                })

            # Step 5: Confirm delivery
            current_state = "confirming"
            confirm_result = engine.confirm_delivery(request_id)

            return _decimals_to_strings({
                "request_id": request_id,
                "state": confirm_result["state"],
                "robot_id": recommended,
                "data": confirm_result["delivery"]["data"],
                "cost": confirm_result["settlement"]["operator_transfer"],
                "sla_met": confirm_result["delivery"]["sla_met"],
                "delivered_at": confirm_result["delivery"]["delivered_at"],
            })

        except Exception as exc:
            error = _error_response(exc)
            error["request_id"] = request_id
            error["failed_at_step"] = current_state
            return error
