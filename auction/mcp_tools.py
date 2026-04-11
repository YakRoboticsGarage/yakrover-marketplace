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
import os
from datetime import UTC
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

from auction.core import VALID_TASK_CATEGORIES, TaskState
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
    error_code: str,
    message: str,
    hint: str,
) -> dict[str, Any]:
    """Build a structured, agent-friendly error dict."""
    return {"error_code": error_code, "message": message, "hint": hint}


def _error_response(exc: Exception) -> dict[str, Any]:
    """Map a Python exception to a structured, agent-friendly error dict.

    Never exposes Python exception class names to MCP consumers.
    """
    msg = str(exc)[:500]  # truncate to avoid leaking internal details
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
    stripe_wallet_service: Any = None,
    stripe_service: Any = None,
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
        """Post a construction survey task to the marketplace.

        Accepts a task specification dict. For construction surveys, use
        auction_process_rfp first to generate specs from an RFP — it handles
        sensor mapping, budget estimation, and task decomposition.

        Required keys:
        - description (str): What survey is needed.
        - task_category (str): "site_survey", "bridge_inspection", "progress_monitoring",
          "as_built", "subsurface_scan", "control_survey", "aerial_survey", or
          "env_sensing", "visual_inspection", "mapping".
        - capability_requirements (dict): Sensors needed and deliverable formats.
        - budget_ceiling (float): Maximum price in USD. Construction range: $1,500-$120,000.
        - sla_seconds (int): Deadline in seconds (e.g., 14 days = 1209600).

        Example (construction survey):
        {
          "description": "Pre-bid topographic survey for US-131 corridor, 6.6 miles",
          "task_category": "site_survey",
          "capability_requirements": {
            "hard": {"sensors_required": ["aerial_lidar", "rtk_gps"]},
            "payload": {"format": "multi_file", "fields": ["LandXML", "DXF", "LAS"]}
          },
          "budget_ceiling": 50000,
          "sla_seconds": 1209600
        }

        Tip: Use auction_process_rfp to auto-generate task specs from RFP text.
        Returns task status including eligible operators and request_id.
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

        Notifies losing bidders. Payment happens on delivery confirmation.
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
        except (TimeoutError, ValueError, KeyError) as exc:
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
            return _decimals_to_strings(
                {
                    "accept": accept_result,
                    "execute": execute_result,
                    "state": execute_result.get("state"),
                    "request_id": request_id,
                }
            )
        except (TimeoutError, ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_confirm_delivery(request_id: str) -> dict:
        """Confirm that the delivered payload is satisfactory.

        Triggers full payment, operator credit, settlement, and
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

        Re-pools the task for new bids (no reservation to refund).
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
        any situation where the auction should not continue. No payment
        reservation to refund (payment only on delivery).

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
                                "sensors_required": {
                                    "type": "list[str]",
                                    "description": "Sensors the robot must have.",
                                },
                                "indoor_capable": {"type": "bool", "description": "Robot must be indoor-capable."},
                                "min_battery_percent": {"type": "int", "description": "Minimum battery percentage."},
                                "max_distance_meters": {
                                    "type": "float",
                                    "description": "Maximum distance to task location.",
                                },
                            },
                        },
                        "payload": {
                            "type": "dict",
                            "required": False,
                            "description": "Expected delivery payload specification.",
                            "properties": {
                                "format": {
                                    "type": "string",
                                    "default": "json",
                                    "description": "Payload format. Defaults to 'json'.",
                                },
                                "fields": {
                                    "type": "list[str]",
                                    "description": "Expected field names in the delivered data.",
                                },
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
                        wallet_id,
                        Decimal(str(amount)),
                        "",
                        "credit",
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
                return _decimals_to_strings(
                    {
                        "error_code": "NO_ELIGIBLE_ROBOTS",
                        "message": "No robots are eligible for this task.",
                        "request_id": request_id,
                        "state": post_result["state"],
                        "hint": "Check capability_requirements or try a different task_category.",
                    }
                )

            # Step 2: Get bids
            current_state = "bidding"
            bids_result = engine.get_bids(request_id)

            if bids_result["bid_count"] == 0:
                return _decimals_to_strings(
                    {
                        "error_code": "NO_BIDS",
                        "message": "No robots submitted bids.",
                        "request_id": request_id,
                        "state": bids_result["state"],
                        "hint": "Try increasing budget_ceiling or relaxing capability_requirements.",
                    }
                )

            recommended = bids_result.get("recommended_winner")
            if recommended is None:
                return _decimals_to_strings(
                    {
                        "error_code": "NO_ELIGIBLE_BIDS",
                        "message": "All bids were disqualified (e.g. over budget).",
                        "request_id": request_id,
                        "state": bids_result["state"],
                        "hint": "Try increasing budget_ceiling.",
                    }
                )

            # Step 3: Accept recommended winner
            current_state = "accepting"
            engine.accept_bid(request_id, recommended)

            # Step 4: Execute
            current_state = "executing"
            execute_result = await engine.execute(request_id)

            # Handle timeout / re-pool
            if execute_result.get("timeout"):
                return _decimals_to_strings(
                    {
                        "error_code": "EXECUTION_TIMEOUT",
                        "message": f"Robot {recommended} timed out during execution.",
                        "request_id": request_id,
                        "state": execute_result["state"],
                        "hint": "The task has been re-pooled for new bids. Use auction_get_bids to continue manually.",
                    }
                )

            # Step 5: Confirm delivery
            current_state = "confirming"
            confirm_result = engine.confirm_delivery(request_id)

            return _decimals_to_strings(
                {
                    "request_id": request_id,
                    "state": confirm_result["state"],
                    "robot_id": recommended,
                    "data": confirm_result["delivery"]["data"],
                    "cost": confirm_result["settlement"]["operator_transfer"],
                    "sla_met": confirm_result["delivery"]["sla_met"],
                    "delivered_at": confirm_result["delivery"]["delivered_at"],
                }
            )

        except Exception as exc:
            error = _error_response(exc)
            error["request_id"] = request_id
            error["failed_at_step"] = current_state
            return error

    # ------------------------------------------------------------------
    # Phase 2: RFP processing tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_process_rfp(
        rfp_text: str,
        jurisdiction: str = "MI",
        site_info: dict | None = None,
    ) -> dict:
        """Process a construction RFP into structured task specs for the auction.

        Takes raw RFP text and extracts survey requirements, decomposing them
        into independently biddable task specs. Each spec can be passed directly
        to auction_post_task.

        The agent MUST provide site_info for accurate task generation. Without
        geographic context, operators cannot plan flights or estimate costs.

        Args:
            rfp_text: The RFP document text (or relevant excerpt).
            jurisdiction: State code for standards (default "MI" for Michigan).
            site_info: Geographic and project context (strongly recommended):
                - project_name (str): Official project name
                - location (str): City/county/address
                - coordinates (dict): {"lat": float, "lon": float}
                - survey_area (dict): {"type": "corridor", "acres": float,
                    "length_miles": float, "width_ft": float}
                - agency (str): Contracting agency (e.g., "MDOT")
                - project_id (str): Agency project number
                - letting_date (str): Bid date (ISO format)
                - terrain (str): "flat"|"corridor"|"urban"|"underground"
                - access_restrictions (list): e.g., ["highway_traffic"]
                - airspace_class (str): FAA class (default "G")
                - reference_standards (list): e.g., ["MDOT Section 104.09"]

        Returns dict with task_specs list, warnings for missing fields, and metadata.
        """
        if site_info is None:
            site_info = {}
        try:
            from auction.rfp_processor import process_rfp

            specs = await asyncio.to_thread(
                process_rfp, rfp_text, jurisdiction, site_info or None
            )

            warnings = []
            if not site_info.get("coordinates"):
                warnings.append(
                    "No coordinates — operators need lat/lon to plan flights. Provide site_info.coordinates."
                )
            if not site_info.get("survey_area"):
                warnings.append("No survey area — budget estimates may be inaccurate. Provide site_info.survey_area.")
            if not site_info.get("project_name"):
                warnings.append("No project name — extracted from RFP text, may be inaccurate.")

            return _decimals_to_strings(
                {
                    "jurisdiction": jurisdiction,
                    "task_count": len(specs),
                    "task_specs": specs,
                    "site_info_provided": bool(site_info),
                    "warnings": warnings,
                    "note": (
                        "Each task_spec can be passed to auction_post_task. "
                        "Review and adjust budget_ceiling and sla_seconds before posting."
                    ),
                }
            )
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_validate_task_specs(task_specs: list) -> dict:
        """Validate an array of task specs against the engine schema.

        Returns per-spec pass/fail with detailed error messages. Use this
        before calling auction_post_task to catch all issues upfront.
        """
        try:
            from auction.rfp_processor import validate_task_specs

            return validate_task_specs(task_specs)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_get_site_recon(rfp_text: str, task_specs: list) -> dict:
        """Generate a site reconnaissance report from an RFP and task specs.

        Returns execution context: airspace, terrain, weather constraints,
        and access considerations. Each field is tagged with source confidence
        (RFP, LOOKUP, INFERRED, UNKNOWN).

        Use after auction_process_rfp to get the operational context for
        task execution planning.
        """
        try:
            from auction.rfp_processor import get_site_recon

            return get_site_recon(rfp_text, task_specs)
        except Exception as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # Phase 3: Buyer review and award confirmation tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_review_bids(request_id: str) -> dict:
        """Get a structured bid comparison for buyer review and decision-making.

        Returns all bids with scores, operator info, and a recommended winner.
        Use this after auction_get_bids to present options to the buyer.

        The response includes:
        - All bids ranked by composite score
        - Operator profiles and reputation data
        - Recommended winner with explanation
        - Budget comparison

        After review, use auction_award_with_confirmation to lock in the selection.
        """
        try:
            result = engine.review_bids(request_id)
            return _decimals_to_strings(result)
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_award_with_confirmation(request_id: str, robot_id: str, buyer_notes: str = "") -> dict:
        """Award a task to a specific operator with buyer confirmation.

        Unlike auction_accept_bid which can auto-execute, this tool accepts
        the bid and waits at bid_accepted state for a separate auction_execute
        call. This allows the buyer to review the award before work begins.

        Args:
            request_id: The task request ID.
            robot_id: The winning operator's robot ID.
            buyer_notes: Optional notes from the buyer about the award decision.

        After this, call auction_execute to dispatch the task.
        """
        try:
            result = engine.accept_bid(request_id, robot_id)
            # Record buyer notes
            record = engine._get_record(request_id)
            record.buyer_notes = buyer_notes
            record.awarded_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            result["buyer_notes"] = buyer_notes
            result["awarded_at"] = record.awarded_at
            result["next_step"] = (
                "Call auction_execute to dispatch the task, "
                "or auction_generate_agreement to create the subcontract first."
            )
            return _decimals_to_strings(result)
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # Phase 4: Compliance verification tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_verify_bond(bond_text: str, task_request_ids: list) -> dict:
        """Verify a payment bond document against task requirements.

        Extracts bond fields (bond number, surety, penal sum, parties, dates)
        and verifies against Treasury Circular 570 for federal bond standing.

        Returns VERIFIED, PARTIAL, or FAILED with detailed check results.
        """
        try:
            from auction.bond_verifier import verify_bond

            return verify_bond(bond_text, task_request_ids)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_verify_bond_pdf(
        pdf_path: str,
        task_request_ids: list | None = None,
        project_state: str = "MI",
        required_coverage: float = 0,
    ) -> dict:
        """Verify a payment bond from a PDF file.

        Extracts text from the PDF using PyMuPDF, then runs full Treasury
        Circular 570 verification.

        Args:
            pdf_path: Path to the bond PDF file.
            task_request_ids: Task IDs this bond should cover.
            project_state: State code for licensing check.
            required_coverage: Minimum coverage amount (optional).
        """
        if task_request_ids is None:
            task_request_ids = []
        try:
            from auction.bond_verifier import extract_text_from_pdf, verify_bond

            text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                return _error_response_structured(
                    "EMPTY_PDF", "No text extracted from PDF", "The PDF may be image-only. OCR is not yet supported."
                )
            return verify_bond(
                text,
                task_request_ids,
                project_state,
                required_coverage if required_coverage > 0 else None,
            )
        except FileNotFoundError:
            return _error_response_structured(
                "FILE_NOT_FOUND", f"PDF not found: {pdf_path}", "Check the file path and try again."
            )
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_verify_operator_compliance(robot_id: str) -> dict:
        """Check an operator's compliance status across all dimensions.

        Returns a checklist covering:
        - FAA Part 107 certification
        - Insurance COI (Certificate of Insurance)
        - PLS (Professional Land Surveyor) license
        - SAM.gov registration (federal contracts)
        - State DOT prequalification
        - DBE/MBE/WBE certification

        Each item returns VERIFIED, MISSING, EXPIRED, or NOT_REQUIRED.
        """
        try:
            if not hasattr(engine, "_compliance_checker"):
                from auction.compliance import ComplianceChecker

                engine._compliance_checker = ComplianceChecker()
            return engine._compliance_checker.verify_operator(robot_id)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_upload_compliance_doc(robot_id: str, doc_type: str, content: str) -> dict:
        """Upload a compliance document for an operator.

        doc_type must be one of:
        - faa_part_107: FAA Remote Pilot Certificate
        - insurance_coi: Certificate of Insurance (ACORD 25)
        - pls_license: Professional Land Surveyor license
        - sam_registration: SAM.gov registration
        - dot_prequalification: State DOT prequalification
        - dbe_certification: DBE/MBE/WBE certification

        The document is stored and marked as VERIFIED.
        """
        try:
            if not hasattr(engine, "_compliance_checker"):
                from auction.compliance import ComplianceChecker

                engine._compliance_checker = ComplianceChecker()
            record = engine._compliance_checker.upload_document(robot_id, doc_type, content)
            # After successful upload, update operator registry if it exists
            if hasattr(engine, "_operator_registry"):
                try:
                    op = engine._operator_registry._get(robot_id)
                    if doc_type not in op.certifications:
                        op.certifications.append(doc_type)
                except KeyError:
                    pass  # Operator not registered via registry (e.g., mock fleet)
            return {
                "robot_id": record.robot_id,
                "doc_type": record.doc_type,
                "status": record.status,
                "verified_at": record.verified_at.isoformat(),
            }
        except (ValueError, Exception) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_compare_terms(operator_terms: str, gc_terms: str, project_state: str = "MI") -> dict:
        """Compare operator standard terms vs. GC subcontract terms.

        Analyzes across 12 dimensions: indemnification, limitation of liability,
        insurance, payment terms, retainage, data ownership, standard of care,
        consequential damages, dispute resolution, termination, change orders,
        and PLS responsibility.

        Flags deviations from marketplace baseline (ConsensusDocs 750 aligned)
        and checks state-specific anti-indemnity statutes.

        Args:
            operator_terms: Operator's standard terms text.
            gc_terms: GC's proposed subcontract terms text.
            project_state: State code for anti-indemnity statute lookup.
        """
        try:
            from auction.terms_comparator import compare_terms

            return compare_terms(operator_terms, gc_terms, project_state)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_check_sam_exclusion(entity_name: str) -> dict:
        """Check if an entity is excluded (debarred) from federal contracting.

        Calls the real SAM.gov Exclusions API v4 when SAM_GOV_API_KEY is set.
        Without a key, returns WARN status indicating manual check needed.

        Use this before awarding tasks on federally-funded projects.
        Checks both operators and surety companies.

        Returns: CLEAR (not excluded), EXCLUDED (debarred), WARN (no API key), ERROR.
        """
        try:
            from auction.compliance import check_sam_exclusion

            return await asyncio.to_thread(check_sam_exclusion, entity_name)
        except Exception as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # Operator registration tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_register_operator(
        company_name: str,
        contact_name: str,
        contact_email: str,
        location: str,
        coverage_states: list | None = None,
        max_range_miles: int = 200,
    ) -> dict:
        """Register a new operator on the marketplace.

        Creates an operator profile. After registration, the operator must:
        1. Add equipment via auction_add_equipment
        2. Upload compliance docs via auction_upload_compliance_doc
        3. Set insurance via auction_register_operator (update)
        4. Call auction_activate_operator to start bidding

        Args:
            company_name: Legal business name
            contact_name: Primary contact person
            contact_email: Contact email
            location: Base location (e.g., "Detroit, MI")
            coverage_states: States where operator can work (e.g., ["MI", "OH"])
            max_range_miles: Maximum travel distance from base
        """
        try:
            if not hasattr(engine, "_operator_registry"):
                from auction.operator_registry import OperatorRegistry

                engine._operator_registry = OperatorRegistry()
            profile = engine._operator_registry.register(
                company_name,
                contact_name,
                contact_email,
                location,
                coverage_states or [],
                max_range_miles,
            )
            return engine._operator_registry.get_profile(profile.operator_id)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_add_equipment(
        operator_id: str,
        equipment_type: str,
        model: str,
        accuracy_cm: float = 0,
    ) -> dict:
        """Add equipment to an operator's profile.

        equipment_type should match sensor types used in task specs:
        aerial_lidar, terrestrial_lidar, photogrammetry, gpr, rtk_gps,
        thermal_camera, robotic_total_station

        Args:
            operator_id: From auction_register_operator response
            equipment_type: Sensor/equipment type
            model: Equipment model (e.g., "DJI Matrice 350 RTK + Zenmuse L2")
            accuracy_cm: Equipment accuracy in centimeters
        """
        try:
            if not hasattr(engine, "_operator_registry"):
                from auction.operator_registry import OperatorRegistry

                engine._operator_registry = OperatorRegistry()
            return engine._operator_registry.add_equipment(
                operator_id,
                equipment_type,
                model,
                accuracy_cm=accuracy_cm,
            )
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_activate_operator(operator_id: str) -> dict:
        """Activate an operator for bidding on the marketplace.

        Checks that the operator has: at least 1 equipment item,
        FAA Part 107 certification, and insurance on file.
        Returns activation status or list of issues to fix.
        """
        try:
            if not hasattr(engine, "_operator_registry"):
                from auction.operator_registry import OperatorRegistry

                engine._operator_registry = OperatorRegistry()
            return engine._operator_registry.activate(operator_id)
        except Exception as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # On-chain robot registration (v1.4)
    # ------------------------------------------------------------------

    SENSOR_TO_CATEGORY = {
        "aerial_lidar": "env_sensing",
        "terrestrial_lidar": "env_sensing",
        "photogrammetry": "visual_inspection",
        "gpr": "env_sensing",
        "rtk_gps": "env_sensing",
        "thermal_camera": "visual_inspection",
        "robotic_total_station": "env_sensing",
    }

    CHAIN_CONFIG = {
        "base-mainnet": {"chain_id": 8453, "rpc": "https://mainnet.base.org"},
        "base-sepolia": {"chain_id": 84532, "rpc": "https://sepolia.base.org"},
        "eth-mainnet": {"chain_id": 1, "rpc": "https://ethereum-rpc.publicnode.com"},
        "eth-sepolia": {"chain_id": 11155111, "rpc": "https://ethereum-sepolia-rpc.publicnode.com"},
    }
    DEFAULT_CHAIN = "base-mainnet"

    @mcp.tool()
    async def auction_register_robot_onchain(
        name: str,
        description: str,
        company_name: str,
        contact_email: str = "",
        location: str = "",
        equipment_type: str = "aerial_lidar",
        model: str = "",
        min_bid_cents: int = 50,
        bid_pct: float = 0.80,
        operator_wallet: str = "",
        stripe_connect_id: str = "",
        usdc_wallet: str = "",
        mcp_endpoint_url: str = "",
        equipment_types: list[str] | None = None,
        chain: str = "base-mainnet",
        is_test: bool = False,
        latitude: float | None = None,
        longitude: float | None = None,
        service_radius_km: int | None = None,
        home_type: str = "",
    ) -> dict:
        """Register a robot on-chain (ERC-8004) and add to bidding fleet.

        Registers on a single chain (default: base-mainnet).
        Supported: base-mainnet, base-sepolia, eth-mainnet, eth-sepolia.

        Creates an operator profile, registers the robot via agent0-sdk
        (2 transactions + IPFS upload), and hot-adds a fleet robot so it
        can bid on tasks immediately. Takes 30-60 seconds.

        If operator_wallet is provided, token ownership is transferred to
        that address after minting.
        """
        import asyncio

        # Input validation
        if not name or not name.strip():
            return _error_response_structured("INVALID_NAME", "name is required.", "Provide a non-empty robot name.")
        if not company_name or not company_name.strip():
            return _error_response_structured("INVALID_COMPANY", "company_name is required.", "Provide a company or operator name.")
        if not location or not location.strip():
            return _error_response_structured("INVALID_LOCATION", "location is required.", "e.g. Detroit, MI")
        # Validate equipment_type — allow known types and custom types (from "Other" input)
        # Custom types are accepted but mapped to "env_sensing" for on-chain task_categories
        if not equipment_type or not equipment_type.strip():
            return _error_response_structured(
                "INVALID_EQUIPMENT_TYPE",
                "equipment_type is required.",
                f"Standard types: {sorted(SENSOR_TO_CATEGORY)}. Custom types also accepted.",
            )
        if not (0.0 < bid_pct <= 1.0):
            return _error_response_structured("INVALID_BID_PCT", "bid_pct must be between 0 (exclusive) and 1 (inclusive).", "Typical values: 0.70–0.95")
        if min_bid_cents < 1:
            return _error_response_structured("INVALID_MIN_BID", "min_bid_cents must be >= 1.", "Use 50 or higher.")

        signer_key = os.environ.get("SIGNER_PVT_KEY")
        pinata_jwt = os.environ.get("PINATA_JWT")
        if not signer_key:
            return _error_response_structured(
                "MISSING_SIGNER_KEY",
                "SIGNER_PVT_KEY environment variable is not set.",
                "Set SIGNER_PVT_KEY to the platform deployer wallet private key.",
            )
        if not pinata_jwt:
            return _error_response_structured(
                "MISSING_PINATA_JWT",
                "PINATA_JWT environment variable is not set.",
                "Set PINATA_JWT to your Pinata v3 API JWT.",
            )

        marketplace_base = os.environ.get("MCP_PUBLIC_URL", "https://mcp.yakrover.online")
        marketplace_endpoint = marketplace_base + "/mcp"
        # The robot's MCP endpoint — where it actually lives (not the marketplace)
        robot_mcp_url = mcp_endpoint_url or "https://fleet.yakrover.online/fakerover/mcp"
        all_sensor_list = equipment_types if equipment_types else [equipment_type]
        task_categories = sorted({SENSOR_TO_CATEGORY.get(s, "env_sensing") for s in all_sensor_list})
        task_category = ",".join(task_categories)

        def _blocking_register():
            # 1. Operator profile
            if not hasattr(engine, "_operator_registry") or engine._operator_registry is None:
                from auction.operator_registry import OperatorRegistry
                engine._operator_registry = OperatorRegistry()

            profile = engine._operator_registry.register(
                company_name=company_name,
                contact_name=company_name,
                contact_email=contact_email,
                location=location,
            )
            op_id = profile.operator_id if hasattr(profile, "operator_id") else profile.get("operator_id", "")
            # Register all equipment types (multi-select)
            all_sensors = equipment_types if equipment_types else [equipment_type]
            for sensor in all_sensors:
                engine._operator_registry.add_equipment(op_id, sensor, model)

            # 2. On-chain registration (single chain)
            target_chain = chain if chain else DEFAULT_CHAIN
            cfg = CHAIN_CONFIG.get(target_chain)
            if not cfg:
                return _error_response_structured(
                    "INVALID_CHAIN",
                    f"Unknown chain '{target_chain}'.",
                    f"Valid chains: {sorted(CHAIN_CONFIG)}",
                )

            chain_result = {}
            robot_tools = []
            try:
                from agent0_sdk import SDK
                sdk = SDK(
                    chainId=cfg["chain_id"],
                    rpcUrl=cfg["rpc"],
                    signer=signer_key,
                    ipfs="pinata",
                    pinataJwt=pinata_jwt,
                )

                agent = sdk.createAgent(name=name, description=description, image="")
                agent.setMCP(robot_mcp_url, auto_fetch=False)

                mcp_ep = next(
                    (ep for ep in agent.registration_file.endpoints
                     if hasattr(ep, "type") and str(ep.type).lower().endswith("mcp")),
                    None,
                )
                if mcp_ep is None:
                    raise ValueError("agent0-sdk did not create an MCP endpoint — check SDK version")

                # Discover the robot's actual tools from its MCP server
                robot_tools = []
                try:
                    import httpx
                    probe = httpx.post(
                        robot_mcp_url,
                        json={"jsonrpc": "2.0", "method": "initialize",
                              "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                         "clientInfo": {"name": "registrar", "version": "1.0"}}, "id": 1},
                        headers={"Accept": "text/event-stream",
                                 "Authorization": f"Bearer {os.environ.get('FLEET_MCP_TOKEN', '')}"},
                        timeout=10.0,
                    )
                    if probe.status_code == 200:
                        import json as _json
                        tools_resp = httpx.post(
                            robot_mcp_url,
                            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2},
                            headers={"Accept": "text/event-stream",
                                     "Mcp-Session-Id": probe.headers.get("mcp-session-id", ""),
                                     "Authorization": f"Bearer {os.environ.get('FLEET_MCP_TOKEN', '')}"},
                            timeout=10.0,
                        )
                        for line in tools_resp.text.splitlines():
                            if line.startswith("data: "):
                                try:
                                    msg = _json.loads(line[6:])
                                    for t in msg.get("result", {}).get("tools", []):
                                        if isinstance(t, dict) and "name" in t:
                                            robot_tools.append(t["name"])
                                except Exception:
                                    pass
                except Exception:
                    pass  # tool discovery failed — will use fallback defaults

                mcp_ep.meta["mcpTools"] = robot_tools if robot_tools else ["robot_submit_bid", "robot_execute_task"]
                mcp_ep.meta["fleetEndpoint"] = marketplace_endpoint

                agent.setTrust(reputation=True)
                agent.setActive(True)
                if hasattr(agent, "setX402Support"):
                    agent.setX402Support(False)

                metadata = {
                    "category": "robot",
                    "robot_type": "survey_platform",
                    "fleet_provider": "yakrover",
                    "fleet_domain": "yakrobot.bid",
                    "min_bid_price": str(min_bid_cents),
                    "accepted_currencies": "usd,usdc",
                    "task_categories": task_category,
                }
                if stripe_connect_id:
                    metadata["stripe_connect_id"] = stripe_connect_id
                # Additional operator metadata (written on-chain via setMetadata + included in IPFS agent card)
                metadata["operator_company"] = company_name
                metadata["operator_location"] = location
                metadata["equipment_model"] = model
                # bid_pct intentionally NOT stored on-chain or IPFS — competitive intelligence
                metadata["sensors"] = ",".join(all_sensors)
                if usdc_wallet:
                    metadata["preferred_usdc_wallet"] = usdc_wallet
                # Geographic and fleet metadata
                if is_test:
                    metadata["is_test"] = "true"
                if latitude is not None:
                    metadata["latitude"] = str(latitude)
                if longitude is not None:
                    metadata["longitude"] = str(longitude)
                if service_radius_km is not None:
                    metadata["service_radius_km"] = str(service_radius_km)
                if home_type:
                    metadata["home_type"] = home_type
                # Platform attestation: EAS (Ethereum Attestation Service) — not metadata.
                # See PLAN_100_ROBOT_FLEET.md Section 9 for EAS integration plan.
                agent.setMetadata(metadata)

                # Step 1: Mint token with on-chain metadata (no IPFS URI yet)
                import time as _time
                metadata_entries = agent._collectMetadataForRegistration()
                tx1_hash = sdk.web3_client.transact_contract(
                    sdk.identity_registry,
                    "register",
                    "",  # empty URI — set in step 2
                    metadata_entries,
                )
                receipt = sdk.web3_client.wait_for_transaction(tx1_hash, timeout=120)
                agent_id_int = agent._extractAgentIdFromReceipt(receipt)
                agent_id = f"{cfg['chain_id']}:{agent_id_int}"
                agent.registration_file.agentId = agent_id
                agent.registration_file.updatedAt = int(_time.time())

                # Step 2: Upload IPFS agent card + set URI (with delay for RPC state propagation)
                agent_uri = ""
                _time.sleep(3)  # let RPC nodes sync minted token state
                try:
                    ipfs_cid = sdk.ipfs_client.addRegistrationFile(
                        agent.registration_file,
                        chainId=cfg["chain_id"],
                        identityRegistryAddress=sdk.identity_registry.address,
                    )
                    tx2_hash = sdk.web3_client.transact_contract(
                        sdk.identity_registry,
                        "setAgentURI",
                        agent_id_int,
                        f"ipfs://{ipfs_cid}",
                    )
                    sdk.web3_client.wait_for_transaction(tx2_hash, timeout=60)
                    agent_uri = f"ipfs://{ipfs_cid}"
                    agent.registration_file.agentURI = agent_uri
                except Exception as uri_exc:
                    # Mint succeeded but IPFS/URI failed — robot is on-chain, card is missing
                    agent_uri = f"pending ({str(uri_exc)[:80]})"

                chain_result = {
                    "agent_id": agent_id,
                    "agent_uri": agent_uri,
                    "status": "ok",
                }

                # Transfer ownership if operator wallet provided
                if operator_wallet and operator_wallet.startswith("0x"):
                    try:
                        agent_id_int = int(agent_id.split(":")[-1]) if ":" in agent_id else int(agent_id)
                        deployer_addr = sdk.web3_client.account.address
                        sdk.web3_client.transact_contract(
                            sdk.identity_registry,
                            "transferFrom",
                            deployer_addr,
                            operator_wallet,
                            agent_id_int,
                        )
                        chain_result["transferred_to"] = operator_wallet
                    except Exception as te:
                        chain_result["transfer_error"] = str(te)[:200]

                del sdk

            except Exception as exc:
                error_msg = str(exc)[:200]
                if hasattr(agent, "registration_file") and getattr(agent.registration_file, "agentId", None):
                    chain_result = {
                        "status": "ok",
                        "agent_id": str(agent.registration_file.agentId),
                        "agent_uri": str(getattr(agent.registration_file, "agentURI", "") or ""),
                        "warning": f"Registered on-chain. Metadata update pending: {error_msg}",
                    }
                else:
                    chain_result = {"status": "error", "error": error_msg}

            # 3. Create fleet robot if registration succeeded
            registration_ok = chain_result.get("status") == "ok"
            execution_mode = "mock"
            if registration_ok:
                sensors = list(all_sensors)
                robot = None

                # If MCP endpoint provided and reachable, create a real adapter
                if mcp_endpoint_url and mcp_endpoint_url.startswith("http"):
                    try:
                        from auction.mcp_robot_adapter import MCPRobotAdapter
                        bearer = os.environ.get("FLEET_MCP_TOKEN", "")
                        adapter = MCPRobotAdapter(
                            robot_id=name,
                            mcp_endpoint=mcp_endpoint_url,
                            wallet=usdc_wallet or "",
                            chain_id=cfg["chain_id"],
                            description=description,
                            bearer_token=bearer,
                            mcp_tools=robot_tools if robot_tools else None,
                        )
                        if adapter.is_reachable(timeout=10.0):
                            robot = adapter
                            execution_mode = "live"
                        else:
                            execution_mode = "mock (MCP endpoint unreachable)"
                    except Exception as mcp_exc:
                        execution_mode = f"mock ({str(mcp_exc)[:60]})"

                # Fall back to mock robot if no live MCP endpoint
                if robot is None:
                    from auction.mock_fleet import RuntimeRegisteredRobot
                    capability_metadata = {
                        "sensors": sensors,
                        "mobility_type": "aerial" if any("aerial" in s or s == "photogrammetry" for s in sensors) else "ground",
                        "indoor_capable": False,
                        "equipment": [{"type": s, "model": model} for s in sensors],
                        "coverage_area": {"base": location},
                    }
                    robot = RuntimeRegisteredRobot(
                        robot_id=op_id,
                        name=name,
                        sensors=sensors,
                        capability_metadata=capability_metadata,
                        reputation_metadata={"completion_rate": 0.95},
                        signing_key=f"reg_{op_id}",
                        bid_pct=bid_pct,
                        sla_seconds=3600,
                        ai_confidence=0.85,
                    )

                with engine._fleet_lock:
                    if op_id not in engine._robots_by_id:
                        engine.robots.append(robot)
                    engine._robots_by_id[op_id] = robot

            status = "active" if registration_ok else "failed"
            message = (
                f"{name} registered on {target_chain} and added to fleet. {len(engine.robots)} robots active."
                if registration_ok
                else f"Registration failed on {target_chain}: {chain_result.get('error', 'unknown')}. Robot not added to fleet."
            )

            return {
                "operator_id": op_id,
                "status": status,
                "name": name,
                "company": company_name,
                "equipment": {"type": equipment_type, "model": model},
                "sensors": list(all_sensors),
                "chain": target_chain,
                "chain_result": chain_result,
                "fleet_size": len(engine.robots),
                "execution_mode": execution_mode,
                "message": message,
            }

        try:
            return await asyncio.to_thread(_blocking_register)
        except Exception as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # Attestation management tools
    # ------------------------------------------------------------------
    # Platform attestation: planned via EAS (Ethereum Attestation Service).
    # See PLAN_100_ROBOT_FLEET.md Section 9 and docs/research/ for design.
    # EAS contract on Base Sepolia: 0x4200000000000000000000000000000000000021
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Phase 5: Agreement generation and project management tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_generate_agreement(request_id: str, template: str = "consensusdocs_750") -> dict:
        """Generate a subcontract agreement for an awarded task.

        Creates a structured agreement from the task spec, winning bid,
        and template. The agreement includes all ConsensusDocs 750 fields:
        scope, fee, insurance, PLS supervision, limitation of liability,
        retainage, data ownership, dispute resolution, and governing law.

        Call this after auction_award_with_confirmation and before
        auction_execute.

        Args:
            request_id: The task request ID (must be in bid_accepted state).
            template: Agreement template ("consensusdocs_750" or "aia_a401").
        """
        try:
            from auction.agreement import generate_agreement

            record = engine._get_record(request_id)
            if record.state != TaskState.BID_ACCEPTED:
                raise ValueError(f"generate_agreement requires state bid_accepted, got {record.state.value}")
            if record.winning_bid is None:
                raise ValueError("No winning bid to generate agreement for")

            agreement = generate_agreement(record, template)
            return _decimals_to_strings(agreement)
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_track_execution(request_id: str) -> dict:
        """Get detailed execution tracking for an active task.

        Returns: task state, time elapsed vs SLA, operator info,
        deliverable status, and progress milestones.

        More detailed than auction_get_status — designed for project
        management during task execution.
        """
        try:
            from datetime import datetime

            record = engine._get_record(request_id)

            elapsed = None
            sla_remaining = None
            if record.task.posted_at:
                now = datetime.now(UTC)
                elapsed_seconds = (now - record.task.posted_at).total_seconds()
                elapsed = int(elapsed_seconds)
                sla_remaining = max(0, record.task.sla_seconds - int(elapsed_seconds))

            delivery_status = "pending"
            if record.delivery is not None:
                delivery_status = "delivered"
            elif record.state == TaskState.IN_PROGRESS:
                delivery_status = "in_progress"
            elif record.state in (TaskState.VERIFIED, TaskState.SETTLED):
                delivery_status = "accepted"

            return _decimals_to_strings(
                {
                    "request_id": request_id,
                    "state": record.state.value,
                    "task_description": record.task.description,
                    "task_category": record.task.task_category,
                    "budget_ceiling": str(record.task.budget_ceiling),
                    "sla_seconds": record.task.sla_seconds,
                    "elapsed_seconds": elapsed,
                    "sla_remaining_seconds": sla_remaining,
                    "sla_met": sla_remaining > 0 if sla_remaining is not None else None,
                    "winning_robot": record.winning_bid.robot_id if record.winning_bid else None,
                    "winning_price": str(record.winning_bid.price) if record.winning_bid else None,
                    "delivery_status": delivery_status,
                    "delivery_data": record.delivery.data if record.delivery else None,
                    "bid_round": record.bid_round,
                    "rfp_id": record.task.task_decomposition.get("rfp_id"),
                    "task_index": record.task.task_decomposition.get("task_index"),
                }
            )
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_list_tasks(filters: dict | None = None) -> dict:
        """List all tasks with optional filters.

        Filters (all optional):
        - state: Filter by task state (e.g., "bidding", "settled")
        - rfp_id: Filter by RFP ID (from task_decomposition)
        - robot_id: Filter by winning robot ID
        - task_category: Filter by category (e.g., "site_survey")

        Essential for managing multi-task projects from a single RFP.
        """
        try:
            result = engine.list_tasks(filters)
            return _decimals_to_strings(result)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_update_progress(
        request_id: str,
        progress_state: str,
        percent_complete: int = 0,
        status_text: str = "",
        location: dict | None = None,
    ) -> dict:
        """Report execution progress on an active task.

        Operators call this to push status updates visible to buyers.
        Progress states: mobilizing, en_route, on_site, capturing,
        processing, uploading.

        Args:
            request_id: Task request ID.
            progress_state: One of: mobilizing, en_route, on_site,
                capturing, processing, uploading.
            percent_complete: 0-100 (optional).
            status_text: Free-text status update (optional).
            location: {lat, lng} GPS coordinates (optional).
        """
        if location is None:
            location = {}
        try:
            from auction.events import VALID_PROGRESS_STATES

            if progress_state not in VALID_PROGRESS_STATES:
                return {
                    "error": True,
                    "error_code": "INVALID_PROGRESS_STATE",
                    "message": f"progress_state must be one of {sorted(VALID_PROGRESS_STATES)}",
                }

            if percent_complete < 0 or percent_complete > 100:
                return {
                    "error": True,
                    "error_code": "INVALID_PERCENT",
                    "message": "percent_complete must be 0-100",
                }

            # Verify the task exists and is in a valid state
            record = engine._get_record(request_id)
            if record.state.value not in ("bid_accepted", "in_progress"):
                return {
                    "error": True,
                    "error_code": "TASK_NOT_IN_PROGRESS",
                    "message": f"Task is in state '{record.state.value}', progress updates only valid for bid_accepted or in_progress",
                }

            robot_id = record.winning_bid.robot_id if record.winning_bid else None

            # Emit progress event
            if engine.events is not None:
                engine.events.emit(
                    "task.progress_update",
                    request_id=request_id,
                    actor_id=robot_id,
                    actor_role="operator",
                    data={
                        "progress_state": progress_state,
                        "percent_complete": percent_complete,
                        "status_text": status_text,
                        "location": location if location else None,
                    },
                )

            return {
                "request_id": request_id,
                "progress_state": progress_state,
                "percent_complete": percent_complete,
                "status_text": status_text,
                "recorded": True,
            }
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_get_task_feed(
        request_id: str = "",
        actor_id: str = "",
        event_type: str = "",
        since: str = "",
        limit: int = 50,
    ) -> dict:
        """Get the event feed for a task or actor.

        Returns a chronological list of events (state changes, progress
        updates, payments) for real-time tracking dashboards.

        Args:
            request_id: Filter by task (optional).
            actor_id: Filter by buyer wallet_id or robot_id (optional).
            event_type: Filter by event type, e.g. "task.progress_update" (optional).
            since: ISO timestamp — only return events after this time (optional).
            limit: Max events to return (default 50).
        """
        try:
            if engine.events is None:
                return {
                    "events": [],
                    "total": 0,
                    "note": "Event tracking not enabled. Initialize engine with events=EventEmitter().",
                }

            events = engine.events.get_events(
                request_id=request_id or None,
                actor_id=actor_id or None,
                event_type=event_type or None,
                since=since or None,
                limit=limit,
            )

            return {
                "events": events,
                "total": len(events),
                "has_more": len(events) >= limit,
            }
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_submit_feedback(
        request_id: str,
        role: str = "buyer",
        rating: int = 5,
        comment: str = "",
        robot_id: str = "",
    ) -> dict:
        """Submit feedback after a completed auction.

        Both buyers and operators can rate the transaction. Feedback
        is recorded in the event log and reputation system.

        Args:
            request_id: Task request ID.
            role: "buyer" or "operator".
            rating: 1-5 stars.
            comment: Optional free-text feedback.
            robot_id: Robot/operator ID (required if role is "buyer").
        """
        try:
            if rating < 1 or rating > 5:
                return {"error": True, "error_code": "INVALID_RATING", "message": "rating must be 1-5"}

            if role not in ("buyer", "operator"):
                return {"error": True, "error_code": "INVALID_ROLE", "message": "role must be 'buyer' or 'operator'"}

            # Record in reputation system
            if engine.reputation is not None and role == "buyer" and robot_id:
                # Buyer rating of operator — record as reputation signal
                engine.reputation.record_outcome(
                    robot_id=robot_id,
                    request_id=request_id,
                    outcome="feedback",
                    sla_met=rating >= 3,
                )

            # Emit event
            if engine.events is not None:
                engine.events.emit(
                    "feedback.submitted",
                    request_id=request_id,
                    actor_id=robot_id if role == "operator" else "buyer",
                    actor_role=role,
                    data={
                        "rating": rating,
                        "comment": comment,
                        "robot_id": robot_id,
                    },
                )

            return {
                "recorded": True,
                "request_id": request_id,
                "role": role,
                "rating": rating,
                "note": "Feedback recorded in event log and reputation system.",
            }
        except Exception as exc:
            return _error_response(exc)
