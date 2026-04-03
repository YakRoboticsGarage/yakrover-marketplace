"""HTTP API layer for the robot marketplace web frontend.

Provides REST endpoints that wrap the auction engine's MCP tools for
browser-based access. This bridges the HTML frontend to the auction engine.

v1.1.1: Initial scaffold with CORS, intent capture, and core auction endpoints.

Usage:
    from auction.api import create_api_router
    app.include_router(create_api_router(engine))
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Optional FastAPI import — api.py is only used when serving the web frontend
try:
    from fastapi import APIRouter, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware

    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False


def create_api_router(engine: object) -> APIRouter:
    """Create a FastAPI router with REST endpoints wrapping the auction engine.

    Args:
        engine: An AuctionEngine instance.

    Returns:
        A FastAPI APIRouter to be mounted on the main app.
    """
    if not _HAS_FASTAPI:
        raise ImportError("FastAPI is required for the HTTP API layer. Install with: uv add fastapi")

    router = APIRouter(prefix="/api/v1", tags=["marketplace"])

    # ------------------------------------------------------------------
    # Intent capture — zero-auth, records user exploration before login
    # ------------------------------------------------------------------

    # In-memory intent store (replace with persistent store in production)
    _intents: dict[str, dict] = {}

    @router.post("/intent")
    async def capture_intent(request: Request) -> dict:
        """Capture user intent before authentication.

        This is the first API call from the frontend — it records what the
        user wants before asking them to log in. Zero friction.

        Body: {"query": "I need a temperature reading in Bay 3"}
        Returns: {"intent_id": "...", "query": "...", "captured_at": "..."}
        """
        body = await request.json()
        query = body.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        if len(query) > 2000:
            raise HTTPException(status_code=400, detail="query exceeds 2000 characters")

        intent_id = f"intent_{uuid.uuid4().hex[:12]}"
        intent = {
            "intent_id": intent_id,
            "query": query,
            "captured_at": datetime.now(UTC).isoformat(),
            "structured_task": None,  # Populated after Claude structures it
            "status": "captured",
        }
        _intents[intent_id] = intent
        logger.info("Intent captured: %s — %s", intent_id, query[:80])

        return {
            "intent_id": intent_id,
            "query": query,
            "captured_at": intent["captured_at"],
            "next_step": "Connect Claude to structure this request",
        }

    @router.get("/intent/{intent_id}")
    async def get_intent(intent_id: str) -> dict:
        """Retrieve a captured intent by ID."""
        intent = _intents.get(intent_id)
        if not intent:
            raise HTTPException(status_code=404, detail="Intent not found")
        return intent

    # ------------------------------------------------------------------
    # Task lifecycle — wraps engine MCP tools
    # ------------------------------------------------------------------

    @router.post("/tasks")
    async def post_task(request: Request) -> dict:
        """Post a new task to the auction.

        Body: standard task_spec dict (description, capability_requirements,
        budget_ceiling, sla_seconds, payment_method).

        Optionally include intent_id to link this task to a captured intent.
        """
        body = await request.json()
        intent_id = body.pop("intent_id", None)

        try:
            result = engine.post_task(body)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        # Link intent if provided
        if intent_id and intent_id in _intents:
            _intents[intent_id]["structured_task"] = result.get("request_id")
            _intents[intent_id]["status"] = "task_posted"

        return result

    @router.get("/tasks/{request_id}")
    async def get_task_status(request_id: str) -> dict:
        """Get full status of a task."""
        try:
            return engine.get_status(request_id)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=404, detail=str(e)) from None

    @router.post("/tasks/{request_id}/bids")
    async def get_bids(request_id: str) -> dict:
        """Collect and score bids for a task."""
        try:
            return engine.get_bids(request_id)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @router.post("/tasks/{request_id}/accept")
    async def accept_bid(request_id: str, request: Request) -> dict:
        """Accept the best bid (or a specific robot's bid)."""
        body = await request.json() if request.headers.get("content-type") else {}
        robot_id = body.get("robot_id")

        try:
            if robot_id:
                return engine.accept_bid(request_id, robot_id)
            else:
                return engine.accept_bid(request_id)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @router.post("/tasks/{request_id}/execute")
    async def execute_task(request_id: str) -> dict:
        """Dispatch the task to the winning robot."""
        try:
            return engine.execute(request_id)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @router.post("/tasks/{request_id}/confirm")
    async def confirm_delivery(request_id: str) -> dict:
        """Confirm delivery and settle payment."""
        try:
            return engine.confirm_delivery(request_id)
        except (KeyError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    # ------------------------------------------------------------------
    # Robot feed — for the real-time ticker on the frontend
    # ------------------------------------------------------------------

    @router.get("/robots")
    async def list_robots() -> dict:
        """List available robots and their capabilities.

        Returns data suitable for the frontend's robot feed/ticker.
        No wallet addresses are included (PP-2).
        """
        robots = []
        for robot in engine.robots:
            robots.append(
                {
                    "robot_id": robot.robot_id,
                    "capabilities": getattr(robot, "capability_metadata", {}),
                    "status": "available",
                }
            )
        return {"robots": robots, "count": len(robots)}

    # ------------------------------------------------------------------
    # MCP discovery — for agent-readable interface
    # ------------------------------------------------------------------

    @router.get("/mcp-config")
    async def mcp_config(request: Request) -> dict:
        """Return MCP server configuration for agents.

        This endpoint enables the "Add to Claude" button on the frontend.
        An agent or user can fetch this to auto-configure their MCP client.
        """
        base_url = str(request.base_url).rstrip("/")
        return {
            "mcpServers": {
                "yakrover-marketplace": {
                    "type": "http",
                    "url": f"{base_url}/fleet/mcp",
                    "description": "Robot task auction marketplace — post tasks, hire robots, pay on delivery",
                    "capabilities": [
                        "auction_post_task",
                        "auction_get_bids",
                        "auction_accept_bid",
                        "auction_execute",
                        "auction_confirm_delivery",
                        "auction_quick_hire",
                        "auction_get_status",
                        "auction_fund_wallet",
                    ],
                }
            },
            "instructions": "Add this to your Claude Code .mcp.json or paste the URL into Claude Desktop MCP settings.",
        }

    return router


def add_cors(app: object) -> None:
    """Add CORS middleware to a FastAPI app for browser access."""
    if not _HAS_FASTAPI:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
