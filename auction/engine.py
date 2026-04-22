"""AuctionEngine — task lifecycle state machine for the robot auction.

Manages in-memory task state (AD-4), enforces valid state transitions,
and orchestrates the full auction lifecycle: post -> bid -> accept ->
execute -> deliver -> verify -> settle.

v0.5 additions: re-pooling on rejection/abandonment/provider-cancel,
wallet ledger integration, reputation tracking,
auto-accept timer, and SLA timeout enforcement.

v1.0 additions: optional SQLite persistence (SyncTaskStore), optional
Stripe settlement (StripeService). Both are no-ops when None, preserving
full v0.5 backward compatibility.

All data types are imported from core.py. This module adds only the
engine class and its TaskRecord dataclass.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from auction.events import EventEmitter
    from auction.store import SyncTaskStore
    from auction.stripe_service import StripeService

from auction.core import (
    WEIGHT_CONFIDENCE,
    WEIGHT_PRICE,
    WEIGHT_REPUTATION,
    WEIGHT_SLA,
    Bid,
    DeliveryPayload,
    Task,
    TaskState,
    check_hard_constraints,
    haversine_km,
    log,
    score_bids,
    validate_task_spec,
    verify_bid,
)

# Optional v0.5 dependencies — engine works without them (backward compat)
try:
    from auction.wallet import InsufficientBalance, WalletLedger
except ImportError:  # pragma: no cover
    WalletLedger = None  # type: ignore[assignment, misc]
    InsufficientBalance = None  # type: ignore[assignment, misc]

try:
    from auction.reputation import ReputationTracker
except ImportError:  # pragma: no cover
    ReputationTracker = None  # type: ignore[assignment, misc]

# Optional v1.0 dependencies — engine works without them (backward compat)
try:
    from auction.store import SyncTaskStore
except ImportError:  # pragma: no cover
    SyncTaskStore = None  # type: ignore[assignment, misc]

try:
    from auction.stripe_service import StripeService
except ImportError:  # pragma: no cover
    StripeService = None  # type: ignore[assignment, misc]

try:
    from auction.deliverable_qa import check_delivery as qa_check
except ImportError:  # pragma: no cover
    qa_check = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Rate limits and input size limits (Security M-1, M-4)
# ---------------------------------------------------------------------------

MAX_ACTIVE_TASKS_PER_WALLET = 20  # Prevent task-flooding
MAX_REPOOL_ROUNDS = 3  # Prevent infinite re-pool loops
MAX_DESCRIPTION_LENGTH = 2000  # Prevent oversized task descriptions
MAX_CAPABILITY_REQUIREMENTS_SIZE = 50  # Max keys in capability_requirements dict (nested)

# ---------------------------------------------------------------------------
# Valid state transitions (DM-6, Section 4 of PRODUCT_SPEC_V05)
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[TaskState | None, list[TaskState]] = {
    None: [TaskState.POSTED],
    TaskState.POSTED: [TaskState.BIDDING, TaskState.WITHDRAWN],
    TaskState.BIDDING: [TaskState.BID_ACCEPTED, TaskState.WITHDRAWN],
    TaskState.BID_ACCEPTED: [TaskState.IN_PROGRESS, TaskState.PROVIDER_CANCELLED, TaskState.WITHDRAWN],
    TaskState.IN_PROGRESS: [TaskState.DELIVERED, TaskState.ABANDONED, TaskState.WITHDRAWN],
    TaskState.DELIVERED: [TaskState.VERIFIED, TaskState.REJECTED, TaskState.WITHDRAWN],
    TaskState.VERIFIED: [TaskState.SETTLED],
    TaskState.REJECTED: [TaskState.RE_POOLED, TaskState.WITHDRAWN],  # allow cancel from rejected
    TaskState.ABANDONED: [TaskState.RE_POOLED, TaskState.WITHDRAWN],  # allow cancel from abandoned
    TaskState.PROVIDER_CANCELLED: [TaskState.RE_POOLED, TaskState.WITHDRAWN],  # allow cancel from cancelled
    TaskState.RE_POOLED: [TaskState.BIDDING, TaskState.WITHDRAWN],
    # Terminal states
    TaskState.SETTLED: [],
    TaskState.WITHDRAWN: [],
}


# ---------------------------------------------------------------------------
# TaskRecord — in-memory task store entry
# ---------------------------------------------------------------------------


@dataclass
class TaskRecord:
    """In-memory record for a single task's full lifecycle state."""

    request_id: str
    task: Task
    state: TaskState
    bids: list[Bid] = field(default_factory=list)
    winning_bid: Bid | None = None
    delivery: DeliveryPayload | None = None
    eligible_robots: list = field(default_factory=list)
    filter_reasons: dict[str, list[str]] = field(default_factory=dict)
    bid_round: int = 1
    previous_winners: list[str] = field(default_factory=list)
    buyer_notes: str = ""
    awarded_at: str = ""
    auto_accept_handle: asyncio.Task | None = field(default=None, repr=False)
    qa_result: dict[str, Any] | None = None

    @property
    def winner(self) -> Bid:
        """Return the winning bid, asserting it exists (state machine guarantees this)."""
        assert self.winning_bid is not None, f"No winning bid for {self.request_id}"
        return self.winning_bid


# ---------------------------------------------------------------------------
# AuctionEngine
# ---------------------------------------------------------------------------


class AuctionEngine:
    """Orchestrates the robot task auction lifecycle.

    In v0.1, all state is in-memory (AD-4). The engine is a pure Python
    library — no HTTP server, no database. ``demo.py`` calls these methods
    directly; in v0.5 they become MCP tools.

    v0.5: Accepts optional *wallet* and *reputation* parameters. When
    ``None``, payment operations are logged as stubs and reputation
    recording is skipped — preserving full v0.1 backward compatibility.
    """

    def __init__(
        self,
        robots: list,
        *,
        wallet: WalletLedger | None = None,
        reputation: ReputationTracker | None = None,
        store: SyncTaskStore | None = None,
        stripe_service: StripeService | None = None,
        events: EventEmitter | None = None,
    ) -> None:
        self.robots = robots
        self._robots_by_id: dict[str, Any] = {r.robot_id: r for r in robots}
        self._fleet_lock = threading.Lock()
        self._tasks: dict[str, TaskRecord] = {}
        self.wallet = wallet
        self.reputation = reputation
        self.store: SyncTaskStore | None = store
        self.stripe_service: StripeService | None = stripe_service
        self._last_stripe_transfer: dict[str, Any] | None = None
        self.events: EventEmitter | None = events
        # Lazily attached by mcp_tools.py
        self._operator_registry: Any = None
        self._compliance_checker: Any = None

        # Load active tasks from store on startup (restart recovery)
        if self.store is not None:
            self._load_from_store()

    # ------------------------------------------------------------------
    # Store persistence helpers
    # ------------------------------------------------------------------

    def _load_from_store(self) -> None:
        """Rebuild in-memory _tasks from SQLite store (restart recovery)."""
        assert self.store is not None
        active = self.store.load_active_tasks()
        for row in active:
            task_data = row["task"]
            task = Task(
                description=task_data["description"],
                task_category=task_data["task_category"],
                capability_requirements=task_data["capability_requirements"],
                budget_ceiling=Decimal(str(task_data["budget_ceiling"])),
                sla_seconds=task_data["sla_seconds"],
                request_id=task_data.get("request_id", row["request_id"]),
                auto_accept_seconds=task_data.get("auto_accept_seconds", 3600),
                task_decomposition=task_data.get("task_decomposition", {}),
                project_metadata=task_data.get("project_metadata", {}),
            )

            # Reconstruct winning bid if present
            winning_bid = None
            wb = row.get("winning_bid")
            if wb is not None:
                winning_bid = Bid(
                    request_id=wb["request_id"],
                    robot_id=wb["robot_id"],
                    price=Decimal(str(wb["price"])),
                    sla_commitment_seconds=wb["sla_commitment_seconds"],
                    ai_confidence=wb["ai_confidence"],
                    capability_metadata=wb.get("capability_metadata", {}),
                    reputation_metadata=wb.get("reputation_metadata", {}),
                    bid_hash=wb["bid_hash"],
                )

            # Reconstruct delivery if present
            delivery = None
            dl = row.get("delivery")
            if dl is not None:
                delivered_at = dl.get("delivered_at")
                if isinstance(delivered_at, str):
                    delivered_at = datetime.fromisoformat(delivered_at)
                    if delivered_at.tzinfo is None:
                        delivered_at = delivered_at.replace(tzinfo=UTC)
                delivery = DeliveryPayload(
                    request_id=dl["request_id"],
                    robot_id=dl["robot_id"],
                    data=dl["data"],
                    delivered_at=delivered_at,
                    sla_met=dl["sla_met"],
                )

            # Reconstruct bids list
            bids_list = []
            for bd in row.get("bids") or []:
                if isinstance(bd, dict) and "robot_id" in bd:
                    bids_list.append(
                        Bid(
                            request_id=bd["request_id"],
                            robot_id=bd["robot_id"],
                            price=Decimal(str(bd["price"])),
                            sla_commitment_seconds=bd["sla_commitment_seconds"],
                            ai_confidence=bd["ai_confidence"],
                            capability_metadata=bd.get("capability_metadata", {}),
                            reputation_metadata=bd.get("reputation_metadata", {}),
                            bid_hash=bd["bid_hash"],
                        )
                    )

            state = TaskState(row["state"])

            record = TaskRecord(
                request_id=row["request_id"],
                task=task,
                state=state,
                bids=bids_list,
                winning_bid=winning_bid,
                delivery=delivery,
                bid_round=row.get("bid_round", 1),
                previous_winners=row.get("previous_winners") or [],
            )

            self._tasks[row["request_id"]] = record
            log("RESTORE", f"{row['request_id']} | restored from store in state {state.value}")

            # Reconstruct auto-accept timers for DELIVERED state tasks
            if state == TaskState.DELIVERED:
                self._start_auto_accept_timer(record)

    def _persist_record(self, record: TaskRecord) -> None:
        """Save a TaskRecord to the sync store (if configured)."""
        if self.store is None:
            return

        # Serialize task
        task = record.task
        task_dict = {
            "description": task.description,
            "task_category": task.task_category,
            "capability_requirements": task.capability_requirements,
            "budget_ceiling": task.budget_ceiling,
            "sla_seconds": task.sla_seconds,
            "request_id": task.request_id,
            "commitment_hash": task.commitment_hash,
            "payment_method": task.payment_method,
            "auto_accept_seconds": task.auto_accept_seconds,
            "posted_at": task.posted_at.isoformat(),
            "task_decomposition": task.task_decomposition,
            "project_metadata": task.project_metadata,
        }

        # Serialize winning bid
        winning_bid_dict = None
        if record.winning_bid is not None:
            wb = record.winning_bid
            winning_bid_dict = {
                "request_id": wb.request_id,
                "robot_id": wb.robot_id,
                "price": wb.price,
                "sla_commitment_seconds": wb.sla_commitment_seconds,
                "ai_confidence": wb.ai_confidence,
                "capability_metadata": wb.capability_metadata,
                "reputation_metadata": wb.reputation_metadata,
                "bid_hash": wb.bid_hash,
            }

        # Serialize delivery
        delivery_dict = None
        if record.delivery is not None:
            dl = record.delivery
            delivery_dict = {
                "request_id": dl.request_id,
                "robot_id": dl.robot_id,
                "data": dl.data,
                "delivered_at": dl.delivered_at.isoformat(),
                "sla_met": dl.sla_met,
            }

        # Serialize bids
        bids_list = []
        for b in record.bids:
            bids_list.append(
                {
                    "request_id": b.request_id,
                    "robot_id": b.robot_id,
                    "price": b.price,
                    "sla_commitment_seconds": b.sla_commitment_seconds,
                    "ai_confidence": b.ai_confidence,
                    "capability_metadata": b.capability_metadata,
                    "reputation_metadata": b.reputation_metadata,
                    "bid_hash": b.bid_hash,
                }
            )

        self.store.save_task(
            request_id=record.request_id,
            task_dict=task_dict,
            state=record.state.value,
            bid_round=record.bid_round,
            winning_bid_dict=winning_bid_dict,
            delivery_dict=delivery_dict,
            bids_list=bids_list,
            previous_winners=record.previous_winners,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(
        self,
        record: TaskRecord,
        to_state: TaskState,
        detail: str,
    ) -> None:
        """Enforce and log a state transition."""
        from_state = record.state if hasattr(record, "state") else None
        valid = VALID_TRANSITIONS.get(from_state, [])
        if to_state not in valid:
            raise ValueError(f"Invalid transition: {from_state} -> {to_state}. Valid targets: {valid}")
        from_label = from_state.value if from_state else "(none)"
        log("STATE", f"{record.request_id} | {from_label} -> {to_state.value} | {detail}")
        record.state = to_state

        # Emit event for every state transition
        if self.events is not None:
            # Map task states to event types
            _state_event_map = {
                "posted": "task.posted",
                "bidding": "task.bidding_opened",
                "bid_accepted": "task.awarded",
                "in_progress": "task.execution_started",
                "delivered": "task.delivered",
                "verified": "task.accepted",
                "settled": "task.settled",
                "withdrawn": "task.withdrawn",
                "rejected": "task.rejected",
                "abandoned": "task.expired",
                "re_pooled": "task.re_pooled",
            }
            event_type = _state_event_map.get(to_state.value, f"task.{to_state.value}")
            self.events.emit(
                event_type,
                request_id=record.request_id,
                actor_role="system",
                data={
                    "from_state": from_label,
                    "to_state": to_state.value,
                    "detail": detail,
                },
            )

        # Persist to SQLite after every state change
        self._persist_record(record)

    def _get_record(self, request_id: str) -> TaskRecord:
        """Look up a task record or raise."""
        if request_id not in self._tasks:
            raise KeyError(f"Unknown request_id: {request_id}")
        return self._tasks[request_id]

    # Reservation/escrow removed — full payment on delivery only.
    # Reserve + escrow to be added in a later version per roadmap.

    # ------------------------------------------------------------------
    # Re-pooling helpers (v0.5)
    # ------------------------------------------------------------------

    def _re_pool(self, record: TaskRecord, reason: str) -> dict:
        """Re-pool a task for a new bid round.

        Clears bids/winning_bid, increments bid_round, excludes previous
        winner, and transitions RE_POOLED -> BIDDING (or WITHDRAWN if no
        eligible robots remain).
        """
        # Enforce max re-pool rounds (Security M-1)
        if record.bid_round >= MAX_REPOOL_ROUNDS:
            self._transition(record, TaskState.WITHDRAWN, f"max re-pool rounds ({MAX_REPOOL_ROUNDS}) exceeded")
            # No reservation to refund — payment only happens on delivery
            return {
                "request_id": record.request_id,
                "state": record.state.value,
                "reason": f"Task withdrawn: exceeded max re-pool rounds ({MAX_REPOOL_ROUNDS})",
            }

        # Record the previous winner for exclusion
        if record.winning_bid is not None:
            record.previous_winners.append(record.winner.robot_id)

        # Transition to RE_POOLED
        self._transition(record, TaskState.RE_POOLED, f"re-pool reason: {reason}")

        # Clear auction state for new round
        record.bids = []
        record.winning_bid = None
        record.delivery = None
        record.bid_round += 1

        # Recompute eligible robots excluding previous winners
        eligible: list = []
        for robot in self.robots:
            if robot.robot_id in record.previous_winners:
                log("FILTER", f"{robot.robot_id} excluded: previous winner (round {record.bid_round})")
                continue
            ok, reasons = check_hard_constraints(record.task, robot.capability_metadata)
            if ok:
                eligible.append(robot)
            else:
                log("FILTER", f"{robot.robot_id} excluded: {', '.join(reasons)}")

        record.eligible_robots = eligible

        if len(eligible) == 0:
            # No robots left — transition to BIDDING then WITHDRAWN
            self._transition(
                record,
                TaskState.BIDDING,
                f"bid round {record.bid_round}: 0 eligible robots after exclusions",
            )
            self._transition(record, TaskState.WITHDRAWN, "reason: no_capable_robots (all excluded)")
            log("REPOOL", f"{record.request_id} | no eligible robots remain, task withdrawn")
        else:
            self._transition(
                record,
                TaskState.BIDDING,
                f"bid round {record.bid_round}: {len(eligible)} eligible robots",
            )
            log(
                "REPOOL",
                f"{record.request_id} | re-pooled for round {record.bid_round} "
                f"({len(eligible)} eligible, {len(record.previous_winners)} excluded)",
            )

        return {
            "request_id": record.request_id,
            "state": record.state.value,
            "bid_round": record.bid_round,
            "eligible_robots": len(eligible),
            "previous_winners": record.previous_winners,
            "re_pooled": record.state == TaskState.BIDDING,
        }

    def _notify_losing_bidders(self, record: TaskRecord) -> None:
        """Log notification for each losing bidder."""
        if record.winning_bid is None:
            return
        for bid in record.bids:
            if bid.robot_id != record.winner.robot_id:
                log(
                    "NOTIFY",
                    f"{bid.robot_id} | not selected for {record.request_id} | winner: {record.winner.robot_id}",
                )

    # ------------------------------------------------------------------
    # Auto-accept timer (AD-7, v0.5)
    # ------------------------------------------------------------------

    def _start_auto_accept_timer(self, record: TaskRecord) -> None:
        """Create a background asyncio task for auto-accept after timeout."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop — skip timer (e.g. synchronous tests)
            log("TIMER", f"{record.request_id} | auto-accept timer skipped (no event loop)")
            return

        record.auto_accept_handle = asyncio.create_task(self._auto_accept_callback(record.request_id))
        log("TIMER", f"{record.request_id} | auto-accept timer started ({record.task.auto_accept_seconds}s)")

    def _cancel_auto_accept_timer(self, record: TaskRecord) -> None:
        """Cancel the auto-accept asyncio task if it exists and is running."""
        if record.auto_accept_handle is not None and not record.auto_accept_handle.done():
            record.auto_accept_handle.cancel()
            log("TIMER", f"{record.request_id} | auto-accept timer cancelled")
        record.auto_accept_handle = None

    async def _auto_accept_callback(self, request_id: str) -> None:
        """Background task: auto-accept delivery after timeout (AD-7)."""
        record = self._get_record(request_id)
        await asyncio.sleep(record.task.auto_accept_seconds)
        if record.state == TaskState.DELIVERED:
            log("TIMER", f"{request_id} | auto-accept timer fired after {record.task.auto_accept_seconds}s")
            self.confirm_delivery(request_id)

    # ------------------------------------------------------------------
    # post_task
    # ------------------------------------------------------------------

    def post_task(self, task_spec: dict) -> dict:
        """Post a new task, run hard-constraint filtering, transition to BIDDING.

        State transitions: (none) -> POSTED -> BIDDING  (or WITHDRAWN if 0 eligible).
        """
        # Input size limits (Security M-4)
        desc = task_spec.get("description", "")
        if len(desc) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"Description exceeds maximum length ({len(desc)} > {MAX_DESCRIPTION_LENGTH})")
        cap_req = task_spec.get("capability_requirements", {})
        if (
            isinstance(cap_req, dict)
            and sum(len(v) if isinstance(v, dict) else 1 for v in cap_req.values()) > MAX_CAPABILITY_REQUIREMENTS_SIZE
        ):
            raise ValueError(f"capability_requirements exceeds maximum size ({MAX_CAPABILITY_REQUIREMENTS_SIZE} keys)")

        # Rate limit — max active tasks per wallet (Security M-1)
        active_count = sum(1 for r in self._tasks.values() if r.state not in (TaskState.SETTLED, TaskState.WITHDRAWN))
        if active_count >= MAX_ACTIVE_TASKS_PER_WALLET:
            raise ValueError(
                f"Too many active tasks ({active_count} >= {MAX_ACTIVE_TASKS_PER_WALLET}). "
                "Complete or cancel existing tasks first."
            )

        # Validate full task spec upfront — return ALL errors at once (REC-3, REC-7)
        validation_errors = validate_task_spec(task_spec)
        if validation_errors:
            raise ValueError(
                f"Task validation failed with {len(validation_errors)} error(s): " + "; ".join(validation_errors)
            )

        # Build the Task (validates budget_ceiling, task_category, payment_method)
        task = Task(
            description=task_spec["description"],
            task_category=task_spec["task_category"],
            capability_requirements=task_spec["capability_requirements"],
            budget_ceiling=Decimal(str(task_spec["budget_ceiling"])),
            sla_seconds=task_spec["sla_seconds"],
            auto_accept_seconds=task_spec.get("auto_accept_seconds", 3600),
            payment_method=task_spec.get("payment_method", "auto"),
            task_decomposition=task_spec.get("task_decomposition", {}),
            project_metadata=task_spec.get("project_metadata", {}),
            latitude=task_spec.get("latitude"),
            longitude=task_spec.get("longitude"),
        )

        # Auto-inject delivery schema if not provided by caller
        cap_req = task.capability_requirements
        if isinstance(cap_req, dict) and "delivery_schema" not in cap_req:
            try:
                from auction.delivery_schemas import get_delivery_schema

                schema = get_delivery_schema(task.task_category)
                cap_req["delivery_schema"] = schema
            except ImportError:
                pass  # delivery_schemas module not available

        record = TaskRecord(
            request_id=task.request_id,
            task=task,
            state=None,  # type: ignore[arg-type]
        )

        # (none) -> POSTED
        self._transition(record, TaskState.POSTED, "post_task()")
        self._tasks[task.request_id] = record

        # Hard constraint filter (AD-5) + geographic + busy state
        eligible: list = []
        filter_reasons: dict[str, list[str]] = {}

        for robot in self.robots:
            reasons_list: list[str] = []

            # Sensor/capability check
            ok, cap_reasons = check_hard_constraints(task, robot.capability_metadata)
            if not ok:
                reasons_list.extend(cap_reasons)

            # Geographic hard cutoff — robot won't bid outside service radius
            if task.latitude is not None and task.longitude is not None:
                robot_lat = getattr(robot, "_latitude", None)
                robot_lng = getattr(robot, "_longitude", None)
                robot_radius = getattr(robot, "_service_radius_km", None)
                if robot_lat is not None and robot_lng is not None and robot_radius is not None:
                    dist = haversine_km(robot_lat, robot_lng, task.latitude, task.longitude)
                    if dist > robot_radius:
                        reasons_list.append(f"out_of_range:{dist:.0f}km>{robot_radius}km")

            # Busy state — robot is executing another task
            busy_until = getattr(robot, "_busy_until", None)
            if busy_until is not None and busy_until > datetime.now(UTC):
                remaining = (busy_until - datetime.now(UTC)).total_seconds()
                reasons_list.append(f"busy:{remaining:.0f}s_remaining")

            if not reasons_list:
                eligible.append(robot)
            else:
                filter_reasons[robot.robot_id] = reasons_list
                log("FILTER", f"{robot.robot_id} excluded: {', '.join(reasons_list)}")

        record.eligible_robots = eligible
        record.filter_reasons = filter_reasons

        total = len(self.robots)
        n_eligible = len(eligible)
        n_filtered = total - n_eligible

        # POSTED -> BIDDING (or WITHDRAWN)
        if n_eligible == 0:
            self._transition(
                record,
                TaskState.BIDDING,
                f"{total} robots found, {n_eligible} eligible, {n_filtered} filtered",
            )
            self._transition(
                record,
                TaskState.WITHDRAWN,
                "reason: no_capable_robots",
            )
        else:
            self._transition(
                record,
                TaskState.BIDDING,
                f"{total} robots found, {n_eligible} eligible, {n_filtered} filtered",
            )

        eligible_robot_ids = [r.robot_id for r in eligible]
        has_mock = any("fake" in rid or "mock" in rid for rid in eligible_robot_ids)

        return {
            "request_id": task.request_id,
            "commitment_hash": task.commitment_hash,
            "payment_method": task.payment_method,
            "state": record.state.value,
            "posted_at": task.posted_at.isoformat(),
            "eligible_robots": n_eligible,
            "eligible_robot_ids": eligible_robot_ids,
            "note": "Includes mock fleet robots not in on-chain registry" if has_mock else None,
            "filtered_robots": n_filtered,
            "filter_reasons": filter_reasons,
        }

    # ------------------------------------------------------------------
    # get_bids
    # ------------------------------------------------------------------

    def get_bids(self, request_id: str) -> dict:
        """Collect bids from eligible robots, verify signatures, score them.

        Requires state == BIDDING.
        In re-pool rounds, robots in previous_winners are excluded.
        """
        record = self._get_record(request_id)
        if record.state != TaskState.BIDDING:
            raise ValueError(f"get_bids requires state BIDDING, got {record.state.value}")

        bids: list[Bid] = []
        bid_details: list[dict] = []

        for robot in record.eligible_robots:
            # Exclude previous winners (enforced here as well as in _re_pool)
            if robot.robot_id in record.previous_winners:
                continue

            bid = robot.bid_engine(record.task)
            if bid is None:
                log("BID", f"{robot.robot_id} | declined to bid (bid_engine returned None)")
                continue
            bids.append(bid)

            log(
                "BID",
                f"{bid.robot_id} | ${bid.price} | SLA {bid.sla_commitment_seconds}s "
                f"| confidence {bid.ai_confidence} | hash: {bid.bid_hash[:8]}...",
            )

            sig_valid = verify_bid(bid, robot.signing_key)
            log("VERIFY", f"{bid.robot_id} bid signature: {'VALID' if sig_valid else 'INVALID'}")

            # Determine eligibility (over-budget bids are disqualified)
            over_budget = bid.price > record.task.budget_ceiling
            bid_entry = {
                "robot_id": bid.robot_id,
                "price": str(bid.price),
                "sla_commitment_seconds": bid.sla_commitment_seconds,
                "ai_confidence": bid.ai_confidence,
                "bid_hash": bid.bid_hash,
                "signature_valid": sig_valid,
                "eligible": not over_budget,
                "disqualification_reason": f"over_budget (${bid.price} > ${record.task.budget_ceiling})"
                if over_budget
                else None,
            }
            bid_details.append(bid_entry)

        record.bids = bids

        # Score bids (AD-6)
        scored = score_bids(record.task, bids)
        scores: dict[str, float] = {}
        score_breakdowns: dict[str, dict] = {}
        for bid, composite in scored:
            # Compute component scores for logging and breakdown
            price_score = float(1 - (bid.price / record.task.budget_ceiling))
            sla_score = min(1.0, float(1 - (bid.sla_commitment_seconds / record.task.sla_seconds)))
            conf_score = bid.ai_confidence
            rep_score = bid.reputation_metadata.get("completion_rate", 0.5)

            breakdown = {
                "price": round(price_score * WEIGHT_PRICE, 4),
                "sla": round(sla_score * WEIGHT_SLA, 4),
                "confidence": round(conf_score * WEIGHT_CONFIDENCE, 4),
                "reputation": round(rep_score * WEIGHT_REPUTATION, 4),
            }

            log(
                "SCORE",
                f"{bid.robot_id}: {composite} "
                f"(price={breakdown['price']:.3f} sla={breakdown['sla']:.3f} "
                f"conf={breakdown['confidence']:.3f} rep={breakdown['reputation']:.3f})",
            )
            scores[bid.robot_id] = composite
            score_breakdowns[bid.robot_id] = breakdown

        # Attach score_breakdown to each bid entry
        for bid_entry in bid_details:
            rid = bid_entry["robot_id"]
            if rid in score_breakdowns:
                bid_entry["score"] = scores[rid]
                bid_entry["score_breakdown"] = score_breakdowns[rid]

        recommended = scored[0][0].robot_id if scored else None

        return {
            "request_id": request_id,
            "state": record.state.value,
            "bid_round": record.bid_round,
            "bids": bid_details,
            "bid_count": len(bids),
            "scores": scores,
            "recommended_winner": recommended,
        }

    # ------------------------------------------------------------------
    # accept_bid
    # ------------------------------------------------------------------

    def accept_bid(self, request_id: str, robot_id: str) -> dict:
        """Accept a bid, transition BIDDING -> BID_ACCEPTED.

        Accepts the winning bid. Payment happens on delivery confirmation.
        reservation. Notifies losing bidders and starts auto-accept timer.
        """
        record = self._get_record(request_id)
        if record.state != TaskState.BIDDING:
            raise ValueError(f"accept_bid requires state BIDDING, got {record.state.value}")

        # Find the bid
        bid = None
        for b in record.bids:
            if b.robot_id == robot_id:
                bid = b
                break
        if bid is None:
            raise ValueError(f"No bid found from robot {robot_id} for {request_id}")

        # Re-verify signature at acceptance time
        robot = self._robots_by_id[robot_id]
        if not verify_bid(bid, robot.signing_key):
            raise ValueError(f"Bid signature verification failed for {robot_id}")

        # No upfront payment — full settlement on delivery confirmation
        record.winning_bid = bid

        # Set robot busy — cannot bid on other tasks until this one completes
        # Duration based on task type (see PLAN_100_ROBOT_FLEET.md Section 10)
        task_cat = record.task.task_category
        duration_map = {
            "env_sensing": 15,
            "sensor_reading": 15,  # seconds (in-situ)
            "topo_survey": 60 * 60,
            "aerial_survey": 45 * 60,
            "corridor_survey": 2 * 60 * 60,
            "subsurface_scan": 90 * 60,
            "utility_detection": 90 * 60,
            "visual_inspection": 30 * 60,
            "progress_monitoring": 45 * 60,
            "bridge_inspection": 60 * 60,
            "thermal_inspection": 30 * 60,
            "as_built": 2 * 60 * 60,
            "confined_space": 45 * 60,
            "volumetric": 30 * 60,
            "control_survey": 60 * 60,
            "site_survey": 60 * 60,
            "environmental_survey": 45 * 60,
        }
        busy_seconds = duration_map.get(task_cat, 30 * 60)  # default 30 min
        robot._busy_until = datetime.now(UTC) + timedelta(seconds=busy_seconds)
        log("BUSY", f"{robot_id} busy for {busy_seconds}s (task: {task_cat})")

        # BIDDING -> BID_ACCEPTED
        self._transition(
            record,
            TaskState.BID_ACCEPTED,
            f"winner: {robot_id} @ ${bid.price}",
        )

        # Notify losing bidders
        self._notify_losing_bidders(record)

        # Start auto-accept timer
        self._start_auto_accept_timer(record)

        return {
            "request_id": request_id,
            "state": record.state.value,
            "winning_robot": robot_id,
            "agreed_price": str(bid.price),
            "sla_commitment_seconds": bid.sla_commitment_seconds,
            "payment": "on_delivery",
            "next_action": "Call auction_execute(request_id) to dispatch the task to the winning robot.",
            "next_tool": "auction_execute",
        }

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    async def execute(self, request_id: str) -> dict:
        """Dispatch execution to the winning robot.

        Transitions BID_ACCEPTED -> IN_PROGRESS -> DELIVERED.
        v0.5: Wraps execution in asyncio.wait_for with SLA timeout.
        On timeout, transitions to ABANDONED and re-pools.
        """
        record = self._get_record(request_id)
        if record.state != TaskState.BID_ACCEPTED:
            raise ValueError(f"execute requires state BID_ACCEPTED, got {record.state.value}")

        winning_bid = record.winner
        robot = self._robots_by_id[winning_bid.robot_id]

        # BID_ACCEPTED -> IN_PROGRESS
        self._transition(
            record,
            TaskState.IN_PROGRESS,
            f"dispatching to {winning_bid.robot_id}",
        )

        try:
            # Enforce SLA timeout
            delivery: DeliveryPayload = await asyncio.wait_for(
                robot.execute(record.task),
                timeout=record.task.sla_seconds,
            )
        except TimeoutError:
            log(
                "TIMEOUT",
                f"{record.request_id} | {winning_bid.robot_id} timed out after {record.task.sla_seconds}s SLA",
            )

            # IN_PROGRESS -> ABANDONED
            self._transition(record, TaskState.ABANDONED, f"SLA timeout ({record.task.sla_seconds}s)")

            # No reservation to refund — payment only on delivery

            # Record reputation
            if self.reputation is not None:
                self.reputation.record_outcome(
                    robot_id=winning_bid.robot_id,
                    request_id=request_id,
                    outcome="abandoned",
                    sla_met=False,
                )

            # ABANDONED -> RE_POOLED -> BIDDING
            re_pool_result = self._re_pool(record, reason="sla_timeout")
            return {
                "request_id": request_id,
                "state": record.state.value,
                "robot_id": winning_bid.robot_id,
                "timeout": True,
                "sla_seconds": record.task.sla_seconds,
                "re_pool": re_pool_result,
            }

        record.delivery = delivery

        # Compute SLA info for log message
        elapsed = (delivery.delivered_at - record.task.posted_at).total_seconds()
        sla = record.task.sla_seconds
        sla_label = "met" if delivery.sla_met else "MISSED"

        # IN_PROGRESS -> DELIVERED
        self._transition(
            record,
            TaskState.DELIVERED,
            f"payload received, SLA {sla_label} ({elapsed:.0f}s < {sla}s)",
        )

        return {
            "request_id": request_id,
            "state": record.state.value,
            "robot_id": winning_bid.robot_id,
            "delivery": {
                "data": delivery.data,
                "sla_met": delivery.sla_met,
                "delivered_at": delivery.delivered_at.isoformat(),
            },
        }

    # ------------------------------------------------------------------
    # confirm_delivery
    # ------------------------------------------------------------------

    def confirm_delivery(self, request_id: str) -> dict:
        """Verify delivered payload, transition DELIVERED -> VERIFIED -> SETTLED.

        Cancels auto-accept timer, debits full amount from buyer, credits
        operator, and records reputation outcome.
        """
        record = self._get_record(request_id)
        if record.state != TaskState.DELIVERED:
            raise ValueError(f"confirm_delivery requires state DELIVERED, got {record.state.value}")

        # Cancel auto-accept timer
        self._cancel_auto_accept_timer(record)

        delivery = record.delivery
        assert delivery is not None
        task = record.task

        # Run deliverable QA at the buyer-configured level
        task_spec = {
            "task_category": task.task_category,
            "capability_requirements": task.capability_requirements,
        }
        qa_result = qa_check(delivery.data, task_spec)

        if qa_result.status == "FAIL":
            log("VERIFY", f"{request_id} | QA FAILED (level {qa_result.level}): {qa_result.issues}")
            raise ValueError(f"Delivery QA failed (level {qa_result.level}): {qa_result.issues}")

        if qa_result.status == "WARN":
            log("VERIFY", f"{request_id} | QA WARN (level {qa_result.level}): {qa_result.issues}")

        log(
            "VERIFY",
            f"{request_id} | QA {qa_result.status} (level {qa_result.level}, {len(qa_result.checks_run)} checks)",
        )

        # Store QA result on the record for downstream access
        record.qa_result = qa_result.to_dict()

        # DELIVERED -> VERIFIED
        self._transition(record, TaskState.VERIFIED, "agent confirmed")

        # Full payment on delivery confirmation (no upfront reservation)
        agreed_price = record.winner.price

        if self.wallet is not None:
            self.wallet.debit("buyer", agreed_price, request_id, "payment", note="Full payment on delivery")
            log("PAYMENT", f"${agreed_price} debited from buyer wallet")
            try:
                self.wallet.credit(
                    record.winner.robot_id,
                    agreed_price,
                    request_id,
                    "credit",
                    note=f"Operator payment for {request_id}",
                )
            except KeyError:
                self.wallet.create_wallet(record.winner.robot_id)
                self.wallet.credit(
                    record.winner.robot_id,
                    agreed_price,
                    request_id,
                    "credit",
                    note=f"Operator payment for {request_id}",
                )
            log("PAYMENT", f"${agreed_price} credited to {record.winner.robot_id} operator wallet")
        else:
            log("PAYMENT", f"(stub) Would debit ${agreed_price} from buyer wallet")
            log("PAYMENT", f"(stub) Would transfer ${agreed_price} to operator")

        # Record reputation
        if self.reputation is not None:
            self.reputation.record_outcome(
                robot_id=record.winner.robot_id,
                request_id=request_id,
                outcome="completed",
                sla_met=delivery.sla_met,
            )

        # Stripe transfer to operator (if stripe_service configured)
        stripe_transfer_result = None
        if self.stripe_service is not None:
            amount_cents = int(agreed_price * 100)
            robot_id = record.winner.robot_id
            stripe_transfer_result = self.stripe_service.create_transfer(
                amount_cents=amount_cents,
                destination_account_id=f"acct_{robot_id}",
                transfer_group=request_id,
                metadata={"request_id": request_id, "robot_id": robot_id},
            )
            self._last_stripe_transfer = stripe_transfer_result
            log(
                "STRIPE",
                f"Transfer {amount_cents}c to {robot_id}: {'stub' if stripe_transfer_result.get('stub') else 'live'}",
            )

        # VERIFIED -> SETTLED
        self._transition(record, TaskState.SETTLED, "task complete")

        settlement_status = "settled" if self.wallet is not None else "stub_logged"

        result = {
            "request_id": request_id,
            "state": record.state.value,
            "delivery": {
                "robot_id": delivery.robot_id,
                "data": delivery.data,
                "sla_met": delivery.sla_met,
                "delivered_at": delivery.delivered_at.isoformat(),
            },
            "qa": record.qa_result,
            "settlement": {
                "amount": str(agreed_price),
                "status": settlement_status,
            },
        }

        # Include Stripe transfer ID in response if available
        if stripe_transfer_result is not None:
            transfer_id = stripe_transfer_result.get("id") or stripe_transfer_result.get("action", "stub")
            result["settlement"]["stripe_transfer_id"] = transfer_id  # type: ignore[index]
            result["settlement"]["stripe_transfer"] = stripe_transfer_result  # type: ignore[index]

        return result

    # ------------------------------------------------------------------
    # reject_delivery
    # ------------------------------------------------------------------

    def reject_delivery(self, request_id: str, reason: str) -> dict:
        """Reject a delivered payload and re-pool the task (v0.5).

        Transitions DELIVERED -> REJECTED -> RE_POOLED -> BIDDING.
        Records rejection in reputation.
        """
        record = self._get_record(request_id)
        if record.state != TaskState.DELIVERED:
            raise ValueError(f"reject_delivery requires state DELIVERED, got {record.state.value}")

        # Cancel auto-accept timer
        self._cancel_auto_accept_timer(record)

        rejected_robot_id = record.winner.robot_id

        # DELIVERED -> REJECTED
        self._transition(record, TaskState.REJECTED, f"reason: {reason}")
        log("REJECT", f"{rejected_robot_id} | payload rejected: {reason}")

        # No reservation to refund — payment only on delivery

        # Record reputation
        if self.reputation is not None:
            self.reputation.record_outcome(
                robot_id=rejected_robot_id,
                request_id=request_id,
                outcome="rejected",
                sla_met=False,
            )

        # REJECTED -> RE_POOLED -> BIDDING (via _re_pool)
        re_pool_result = self._re_pool(record, reason=f"rejected: {reason}")

        return {
            "request_id": request_id,
            "state": record.state.value,
            "reason": reason,
            "re_pooled": re_pool_result.get("re_pooled", False),
            "re_pool": re_pool_result,
        }

    # ------------------------------------------------------------------
    # abandon_task (v0.5)
    # ------------------------------------------------------------------

    def abandon_task(self, request_id: str, *, reason: str = "abandoned") -> dict:
        """Manually abandon a task or cancel it as the provider.

        When reason == "provider_cancelled" and state is BID_ACCEPTED:
            Transitions BID_ACCEPTED -> PROVIDER_CANCELLED -> RE_POOLED -> BIDDING.
        Otherwise (default):
            Transitions IN_PROGRESS -> ABANDONED -> RE_POOLED -> BIDDING.

        No payment to refund (payment only on delivery).
        """
        record = self._get_record(request_id)

        if reason == "provider_cancelled":
            if record.state != TaskState.BID_ACCEPTED:
                raise ValueError(f"provider_cancelled requires state BID_ACCEPTED, got {record.state.value}")
            cancelled_robot_id = record.winner.robot_id

            # BID_ACCEPTED -> PROVIDER_CANCELLED
            self._transition(record, TaskState.PROVIDER_CANCELLED, f"provider cancelled ({cancelled_robot_id})")

            # No reservation to refund — payment only on delivery

            # Record reputation
            if self.reputation is not None:
                self.reputation.record_outcome(
                    robot_id=cancelled_robot_id,
                    request_id=request_id,
                    outcome="cancelled",
                    sla_met=False,
                )

            # PROVIDER_CANCELLED -> RE_POOLED -> BIDDING
            re_pool_result = self._re_pool(record, reason="provider_cancelled")

            return {
                "request_id": request_id,
                "state": record.state.value,
                "cancelled_robot": cancelled_robot_id,
                "re_pool": re_pool_result,
            }

        # Default: robot-initiated abandonment
        if record.state != TaskState.IN_PROGRESS:
            raise ValueError(f"abandon_task requires state IN_PROGRESS, got {record.state.value}")

        abandoned_robot_id = record.winner.robot_id

        # IN_PROGRESS -> ABANDONED
        self._transition(record, TaskState.ABANDONED, f"manually abandoned ({abandoned_robot_id} unresponsive)")

        # No reservation to refund — payment only on delivery

        # Record reputation
        if self.reputation is not None:
            self.reputation.record_outcome(
                robot_id=abandoned_robot_id,
                request_id=request_id,
                outcome="abandoned",
                sla_met=False,
            )

        # ABANDONED -> RE_POOLED -> BIDDING
        re_pool_result = self._re_pool(record, reason="manual_abandonment")

        return {
            "request_id": request_id,
            "state": record.state.value,
            "abandoned_robot": abandoned_robot_id,
            "re_pool": re_pool_result,
        }

    # ------------------------------------------------------------------
    # cancel_task (REC-5)
    # ------------------------------------------------------------------

    def cancel_task(self, request_id: str, reason: str) -> dict:
        """Cancel a task stuck in any non-terminal state.

        Refunds any wallet reservation if a bid was accepted, then
        transitions the task to WITHDRAWN. This lets agents recover from
        malformed specs or other issues without losing the reservation.
        """
        record = self._get_record(request_id)

        # Terminal states cannot be cancelled
        terminal_states = {TaskState.SETTLED, TaskState.WITHDRAWN}
        if record.state in terminal_states:
            raise ValueError(f"Cannot cancel task in terminal state {record.state.value}")

        # Cancel auto-accept timer if active
        self._cancel_auto_accept_timer(record)

        # No reservation to refund — payment only on delivery

        # Transition to WITHDRAWN
        self._transition(record, TaskState.WITHDRAWN, f"cancelled: {reason}")

        return {
            "request_id": request_id,
            "state": record.state.value,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # get_task_status (v0.5)
    # ------------------------------------------------------------------

    def get_task_status(self, request_id: str) -> dict:
        """Return full task state for agent inspection.

        Includes state, bid_round, winning_bid, bids, timer status.
        """
        record = self._get_record(request_id)

        winning_bid_info = None
        if record.winning_bid is not None:
            winning_bid_info = {
                "robot_id": record.winner.robot_id,
                "price": str(record.winner.price),
                "sla_commitment_seconds": record.winner.sla_commitment_seconds,
            }

        delivery_info = None
        if record.delivery is not None:
            delivery_info = {
                "robot_id": record.delivery.robot_id,
                "data": record.delivery.data,
                "sla_met": record.delivery.sla_met,
                "delivered_at": record.delivery.delivered_at.isoformat(),
            }

        timer_active = record.auto_accept_handle is not None and not record.auto_accept_handle.done()

        # Wallet entries for this request (if wallet exists)
        wallet_entries = []
        if self.wallet is not None:
            raw = self.wallet.get_entries(request_id=request_id)
            for e in raw:
                if isinstance(e, dict):
                    wallet_entries.append(e)
                else:
                    wallet_entries.append(
                        {
                            "entry_type": e.entry_type,
                            "amount": str(e.amount),
                            "wallet_id": e.wallet_id,
                        }
                    )

        # State-aware available actions and hints (REC-18)
        _actions_by_state = {
            TaskState.POSTED: (["auction_cancel_task"], None),
            TaskState.BIDDING: (
                ["auction_get_bids", "auction_cancel_task"],
                "Bids are being collected. Call auction_get_bids to see them.",
            ),
            TaskState.BID_ACCEPTED: (
                ["auction_execute", "auction_cancel_task"],
                "Call auction_execute to dispatch the task to the winning robot.",
            ),
            TaskState.IN_PROGRESS: (
                ["auction_cancel_task"],
                "Robot is executing. Wait for delivery.",
            ),
            TaskState.DELIVERED: (
                ["auction_confirm_delivery", "auction_reject_delivery", "auction_cancel_task"],
                "Payload received. Call auction_confirm_delivery to accept, or auction_reject_delivery to reject.",
            ),
            TaskState.VERIFIED: ([], "Task is complete."),
            TaskState.SETTLED: ([], "Task is complete."),
            TaskState.WITHDRAWN: ([], "Task ended."),
            TaskState.REJECTED: ([], "Task ended."),
        }
        available_actions, hint = _actions_by_state.get(
            record.state,
            ([], None),
        )

        # Auto-accept deadline as ISO timestamp (REC-20)
        auto_accept_deadline = None
        if timer_active:
            if record.delivery is not None:
                auto_accept_deadline = (
                    record.delivery.delivered_at + timedelta(seconds=record.task.auto_accept_seconds)
                ).isoformat()
            elif record.task.posted_at is not None:
                auto_accept_deadline = (
                    record.task.posted_at + timedelta(seconds=record.task.auto_accept_seconds)
                ).isoformat()

        result = {
            "request_id": request_id,
            "state": record.state.value,
            "task_description": record.task.description,
            "task_category": record.task.task_category,
            "budget_ceiling": str(record.task.budget_ceiling),
            "sla_seconds": record.task.sla_seconds,
            "bid_round": record.bid_round,
            "bid_count": len(record.bids),
            "winning_bid": winning_bid_info,
            "delivery": delivery_info,
            "previous_winners": record.previous_winners,
            "auto_accept_timer_active": timer_active,
            "auto_accept_seconds": record.task.auto_accept_seconds,
            "wallet_entries": wallet_entries,
            "available_actions": available_actions,
            "hint": hint,
        }

        if auto_accept_deadline is not None:
            result["auto_accept_deadline"] = auto_accept_deadline

        return result

    # ------------------------------------------------------------------
    # review_bids — structured bid comparison for buyer review (Phase 3)
    # ------------------------------------------------------------------

    def review_bids(self, request_id: str) -> dict:
        """Return a structured bid comparison for buyer review.

        Enriches bid data with operator info and recommends a winner.
        """
        record = self._get_record(request_id)
        if record.state != TaskState.BIDDING:
            raise ValueError(f"review_bids requires state BIDDING, got {record.state.value}")

        if not record.bids:
            return {
                "request_id": request_id,
                "state": record.state.value,
                "bid_count": 0,
                "bids": [],
                "recommendation": None,
                "message": "No bids received yet. Call auction_get_bids first to collect bids.",
            }

        scored = score_bids(record.task, record.bids)

        bid_comparisons = []
        for bid, score in scored:
            robot = self._robots_by_id.get(bid.robot_id)
            operator_info = {}
            if robot is not None:
                operator_info = {
                    "robot_id": robot.robot_id,
                    "name": getattr(robot, "name", robot.robot_id),
                    "capability_metadata": getattr(robot, "capability_metadata", {}),
                }

            bid_comparisons.append(
                {
                    "robot_id": bid.robot_id,
                    "price": str(bid.price),
                    "sla_commitment_seconds": bid.sla_commitment_seconds,
                    "ai_confidence": bid.ai_confidence,
                    "score": score,
                    "eligible": bid.price <= record.task.budget_ceiling,
                    "reputation": bid.reputation_metadata,
                    "operator": operator_info,
                }
            )

        recommended = scored[0][0].robot_id if scored else None

        return {
            "request_id": request_id,
            "state": record.state.value,
            "task_description": record.task.description,
            "budget_ceiling": str(record.task.budget_ceiling),
            "bid_count": len(bid_comparisons),
            "bids": bid_comparisons,
            "recommendation": {
                "robot_id": recommended,
                "reason": f"Highest composite score ({scored[0][1]}) across price, SLA, confidence, and reputation"
                if scored
                else None,
            }
            if recommended
            else None,
        }

    # ------------------------------------------------------------------
    # list_tasks — list all tasks with optional filters
    # ------------------------------------------------------------------

    def list_tasks(self, filters: dict | None = None) -> dict:
        """List all tasks with optional filters.

        Filters: state, rfp_id, robot_id, task_category.
        """
        filters = filters or {}
        results = []

        for rid, record in self._tasks.items():
            # Apply filters
            if "state" in filters and record.state.value != filters["state"]:
                continue
            if "rfp_id" in filters:
                rfp_id = record.task.task_decomposition.get("rfp_id", "")
                if rfp_id != filters["rfp_id"]:
                    continue
            if "robot_id" in filters and (record.winning_bid is None or record.winner.robot_id != filters["robot_id"]):
                continue
            if "task_category" in filters and record.task.task_category != filters["task_category"]:
                continue

            results.append(
                {
                    "request_id": rid,
                    "description": record.task.description,
                    "task_category": record.task.task_category,
                    "state": record.state.value,
                    "budget_ceiling": str(record.task.budget_ceiling),
                    "bid_count": len(record.bids),
                    "winning_robot": record.winner.robot_id if record.winning_bid else None,
                    "rfp_id": record.task.task_decomposition.get("rfp_id"),
                    "task_index": record.task.task_decomposition.get("task_index"),
                    "posted_at": record.task.posted_at.isoformat(),
                }
            )

        return {
            "total": len(results),
            "filters_applied": filters,
            "tasks": results,
        }
