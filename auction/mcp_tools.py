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

    # ------------------------------------------------------------------
    # Phase 2: RFP processing tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_process_rfp(
        rfp_text: str, jurisdiction: str = "MI", site_info: dict = {},
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
        try:
            from auction.rfp_processor import process_rfp
            specs = process_rfp(rfp_text, jurisdiction, site_info or None)

            warnings = []
            if not site_info.get("coordinates"):
                warnings.append("No coordinates — operators need lat/lon to plan flights. Provide site_info.coordinates.")
            if not site_info.get("survey_area"):
                warnings.append("No survey area — budget estimates may be inaccurate. Provide site_info.survey_area.")
            if not site_info.get("project_name"):
                warnings.append("No project name — extracted from RFP text, may be inaccurate.")

            return _decimals_to_strings({
                "jurisdiction": jurisdiction,
                "task_count": len(specs),
                "task_specs": specs,
                "site_info_provided": bool(site_info),
                "warnings": warnings,
                "note": (
                    "Each task_spec can be passed to auction_post_task. "
                    "Review and adjust budget_ceiling and sla_seconds before posting."
                ),
            })
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
    async def auction_award_with_confirmation(
        request_id: str, robot_id: str, buyer_notes: str = ""
    ) -> dict:
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
            record.awarded_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
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
        pdf_path: str, task_request_ids: list = [], project_state: str = "MI",
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
        try:
            from auction.bond_verifier import extract_text_from_pdf, verify_bond
            text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                return _error_response_structured(
                    "EMPTY_PDF", "No text extracted from PDF",
                    "The PDF may be image-only. OCR is not yet supported."
                )
            return verify_bond(
                text, task_request_ids, project_state,
                required_coverage if required_coverage > 0 else None,
            )
        except FileNotFoundError:
            return _error_response_structured(
                "FILE_NOT_FOUND", f"PDF not found: {pdf_path}",
                "Check the file path and try again."
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
            if not hasattr(engine, '_compliance_checker'):
                from auction.compliance import ComplianceChecker
                engine._compliance_checker = ComplianceChecker()
            return engine._compliance_checker.verify_operator(robot_id)
        except Exception as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_upload_compliance_doc(
        robot_id: str, doc_type: str, content: str
    ) -> dict:
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
            if not hasattr(engine, '_compliance_checker'):
                from auction.compliance import ComplianceChecker
                engine._compliance_checker = ComplianceChecker()
            record = engine._compliance_checker.upload_document(robot_id, doc_type, content)
            # After successful upload, update operator registry if it exists
            if hasattr(engine, '_operator_registry'):
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
    async def auction_compare_terms(
        operator_terms: str, gc_terms: str, project_state: str = "MI"
    ) -> dict:
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
            return check_sam_exclusion(entity_name)
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
            if not hasattr(engine, '_operator_registry'):
                from auction.operator_registry import OperatorRegistry
                engine._operator_registry = OperatorRegistry()
            profile = engine._operator_registry.register(
                company_name, contact_name, contact_email,
                location, coverage_states or [], max_range_miles,
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
            if not hasattr(engine, '_operator_registry'):
                from auction.operator_registry import OperatorRegistry
                engine._operator_registry = OperatorRegistry()
            return engine._operator_registry.add_equipment(
                operator_id, equipment_type, model, accuracy_cm=accuracy_cm,
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
            if not hasattr(engine, '_operator_registry'):
                from auction.operator_registry import OperatorRegistry
                engine._operator_registry = OperatorRegistry()
            return engine._operator_registry.activate(operator_id)
        except Exception as exc:
            return _error_response(exc)

    # ------------------------------------------------------------------
    # Phase 5: Agreement generation and project management tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def auction_generate_agreement(
        request_id: str, template: str = "consensusdocs_750"
    ) -> dict:
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
                raise ValueError(
                    f"generate_agreement requires state bid_accepted, got {record.state.value}"
                )
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
            from datetime import datetime, timezone
            record = engine._get_record(request_id)

            elapsed = None
            sla_remaining = None
            if record.task.posted_at:
                now = datetime.now(timezone.utc)
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

            return _decimals_to_strings({
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
            })
        except (ValueError, KeyError) as exc:
            return _error_response(exc)

    @mcp.tool()
    async def auction_list_tasks(filters: dict = None) -> dict:
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
