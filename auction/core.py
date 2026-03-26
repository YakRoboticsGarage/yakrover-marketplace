"""Core data types, scoring, signing, and constraint checking for the robot task auction.

This module is the foundation of the auction package. It has ZERO dependencies
on src/ or any external packages — stdlib only (except optional eth_account for
Ed25519 signing). See DECISIONS.md for the rationale behind each type and
function (referenced by ID throughout).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

# ---------------------------------------------------------------------------
# Optional eth_account import for Ed25519 signing (v1.0)
# Falls back to HMAC-only mode if not installed.
# ---------------------------------------------------------------------------

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct

    _HAS_ETH_ACCOUNT = True
except ImportError:
    _HAS_ETH_ACCOUNT = False

# ---------------------------------------------------------------------------
# Signing mode: "hmac" (v0.5 backward compat) or "ed25519" (v1.0)
# Read once at import time. Tests override via monkeypatch on the module attr.
# ---------------------------------------------------------------------------

SIGNING_MODE = os.environ.get("SIGNING_MODE", "hmac")


# ---------------------------------------------------------------------------
# DM-6: Task lifecycle states (AD-8)
# ---------------------------------------------------------------------------

class TaskState(str, Enum):
    """Task lifecycle states. See DECISIONS.md DM-6, AD-8."""

    # v0.1 — fully implemented
    POSTED = "posted"
    BIDDING = "bidding"
    BID_ACCEPTED = "bid_accepted"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    VERIFIED = "verified"
    SETTLED = "settled"

    # v0.1 — used only in no-bid scenario
    WITHDRAWN = "withdrawn"

    # v0.5+ — defined but not reachable in v0.1
    REJECTED = "rejected"
    RE_POOLED = "re_pooled"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    PROVIDER_CANCELLED = "provider_cancelled"


# ---------------------------------------------------------------------------
# DM-1: Task
# ---------------------------------------------------------------------------

VALID_TASK_CATEGORIES = frozenset(
    ["env_sensing", "visual_inspection", "mapping", "delivery_ground", "aerial_survey"]
)


def infer_task_category(capability_requirements: dict) -> str:
    """Infer task_category from capability_requirements when not provided.

    Looks at hard.sensors_required to guess the category:
    - temperature/humidity -> "env_sensing"
    - rgb_camera/thermal_camera -> "visual_inspection"
    - lidar -> "mapping"
    - default -> "env_sensing"
    """
    if not isinstance(capability_requirements, dict):
        return "env_sensing"
    hard = capability_requirements.get("hard", {})
    if not isinstance(hard, dict):
        return "env_sensing"
    sensors = hard.get("sensors_required", [])
    if not isinstance(sensors, list):
        return "env_sensing"
    sensors_lower = [s.lower() for s in sensors if isinstance(s, str)]
    if any(s in sensors_lower for s in ("rgb_camera", "thermal_camera")):
        return "visual_inspection"
    if "lidar" in sensors_lower:
        return "mapping"
    if any(s in sensors_lower for s in ("temperature", "humidity")):
        return "env_sensing"
    return "env_sensing"


def validate_task_spec(task_spec: dict) -> list[str]:
    """Validate a task specification dict and return ALL errors at once.

    Returns an empty list if the spec is valid. Each string in the returned
    list describes one validation failure. This allows agents to fix every
    issue in a single round-trip rather than iterating one error at a time.
    """
    errors: list[str] = []

    # budget_ceiling
    try:
        budget = Decimal(str(task_spec.get("budget_ceiling", 0)))
        if budget < Decimal("0.50"):
            errors.append(
                f"budget_ceiling must be >= $0.50, got ${budget}"
            )
    except Exception:
        errors.append(
            f"budget_ceiling must be a number, got {task_spec.get('budget_ceiling')!r}"
        )

    # task_category — infer from capability_requirements when not provided
    category = task_spec.get("task_category")
    if not category or category == "":
        inferred = infer_task_category(task_spec.get("capability_requirements", {}))
        task_spec["task_category"] = inferred
        category = inferred
    if category not in VALID_TASK_CATEGORIES:
        errors.append(
            f"task_category must be one of {sorted(VALID_TASK_CATEGORIES)}, got {category!r}"
        )

    # capability_requirements must be a dict
    cap_req = task_spec.get("capability_requirements")
    if not isinstance(cap_req, dict):
        errors.append(
            f"capability_requirements must be a dict, got {type(cap_req).__name__}. "
            f'Expected shape: {{"tool": "<robot_tool_name>", "hard": {{"sensors_required": [...]}}, '
            f'"payload": {{"format": "json", "fields": [...]}}}}'
        )
    else:
        # Warn if none of the expected top-level keys are present
        _expected_cap_keys = {"hard", "soft", "payload", "tool"}
        if not _expected_cap_keys.intersection(cap_req.keys()):
            errors.append(
                f"capability_requirements has no recognised keys (found: {sorted(cap_req.keys())}). "
                f"Expected keys: 'tool', 'hard', 'soft', 'payload'. "
                f'Example: {{"tool": "tumbller_get_temperature_humidity", '
                f'"payload": {{"format": "json", "fields": ["temperature_celsius"]}}}}'
            )
        # If hard constraints are provided, sensors_required must be a list
        hard = cap_req.get("hard")
        if hard is not None:
            sensors = hard.get("sensors_required")
            if sensors is not None and not isinstance(sensors, list):
                errors.append(
                    f"capability_requirements.hard.sensors_required must be a list, "
                    f"got {type(sensors).__name__}"
                )

        # If payload is provided, validate its structure
        payload = cap_req.get("payload")
        if payload is not None:
            if not isinstance(payload, dict):
                errors.append(
                    f"capability_requirements.payload must be a dict, "
                    f"got {type(payload).__name__}"
                )
            else:
                fmt = payload.get("format")
                if fmt is not None and not isinstance(fmt, str):
                    errors.append(
                        f"capability_requirements.payload.format must be a string, "
                        f"got {type(fmt).__name__}"
                    )
                fields = payload.get("fields")
                if fields is not None and not isinstance(fields, list):
                    errors.append(
                        f"capability_requirements.payload.fields must be a list, "
                        f"got {type(fields).__name__}"
                    )

    # sla_seconds must be a positive integer
    sla = task_spec.get("sla_seconds")
    if not isinstance(sla, int) or sla <= 0:
        errors.append(
            f"sla_seconds must be a positive integer, got {sla!r}"
        )

    return errors


@dataclass(frozen=True)
class Task:
    """A posted task requesting robot services. See DECISIONS.md DM-1."""

    description: str
    task_category: str = ""
    capability_requirements: dict = field(default_factory=dict)
    budget_ceiling: Decimal = Decimal("0.50")
    sla_seconds: int = 120
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    auto_accept_seconds: int = 3600  # AD-7: stubbed in v0.1
    posted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.budget_ceiling < Decimal("0.50"):
            raise ValueError(
                f"budget_ceiling must be >= $0.50 (TC-1), got ${self.budget_ceiling}"
            )
        # Infer task_category from capability_requirements when not provided
        if not self.task_category:
            inferred = infer_task_category(self.capability_requirements)
            object.__setattr__(self, "task_category", inferred)
        if self.task_category not in VALID_TASK_CATEGORIES:
            raise ValueError(
                f"task_category must be one of {sorted(VALID_TASK_CATEGORIES)}, "
                f"got '{self.task_category}'"
            )


# ---------------------------------------------------------------------------
# DM-2: Bid
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Bid:
    """A robot's bid on a task. See DECISIONS.md DM-2."""

    request_id: str
    robot_id: str
    price: Decimal
    sla_commitment_seconds: int
    ai_confidence: float  # 0.0–1.0
    capability_metadata: dict  # v0.1: flat dict, not full WoT TD
    reputation_metadata: dict  # See DM-5
    bid_hash: str  # HMAC-SHA256 signature (PD-3, Phase 0 exception)


# ---------------------------------------------------------------------------
# DM-3: AuctionResult
# ---------------------------------------------------------------------------

@dataclass
class AuctionResult:
    """Outcome of a completed auction. See DECISIONS.md DM-3.

    Canonical return type for scoring results, used by the test suite and
    available for consumers. The dict-based ``get_bids()`` return in
    ``engine.py`` is the MCP-compatible format; this dataclass is the
    structured contract type.
    """

    request_id: str
    winning_bid: Bid | None
    all_bids: list[Bid]
    scores: dict[str, float]  # robot_id → composite score
    reason: str  # "accepted" | "no_capable_robots" | "budget_exceeded" | "withdrawn"


# ---------------------------------------------------------------------------
# DM-4: DeliveryPayload
# ---------------------------------------------------------------------------

@dataclass
class DeliveryPayload:
    """Payload delivered by the winning robot. See DECISIONS.md DM-4."""

    request_id: str
    robot_id: str
    data: dict
    delivered_at: datetime
    sla_met: bool


# ---------------------------------------------------------------------------
# Hard constraint filter (AD-5, Phase 1)
# ---------------------------------------------------------------------------

def check_hard_constraints(
    task: Task,
    robot_capabilities: dict,
) -> tuple[bool, list[str]]:
    """Check if a robot meets ALL hard constraints for a task.

    Returns (eligible, rejection_reasons). If eligible is True,
    rejection_reasons is empty. See DECISIONS.md AD-5.
    """
    rejections: list[str] = []
    hard = task.capability_requirements.get("hard", {})

    # v0.5: support WoT TD sensor format (list of dicts with "type" key)
    # alongside v0.1 flat string lists.  Backward compatible.
    raw_sensors = robot_capabilities.get("sensors", [])
    if raw_sensors and isinstance(raw_sensors[0], dict):
        robot_sensors = set(s["type"] for s in raw_sensors if "type" in s)
    else:
        robot_sensors = set(raw_sensors)

    # 1. Required sensors — robot must have ALL
    for required_sensor in hard.get("sensors_required", []):
        if required_sensor not in robot_sensors:
            rejections.append(f"missing_sensor:{required_sensor}")

    # 2. Indoor capability
    if hard.get("indoor_capable") and not robot_capabilities.get("indoor_capable", False):
        rejections.append("not_indoor_capable")

    # 3. Minimum battery
    min_battery = hard.get("min_battery_percent")
    if min_battery is not None:
        robot_battery = robot_capabilities.get("battery_percent", 0)
        if robot_battery < min_battery:
            rejections.append(f"battery_too_low:{robot_battery}%<{min_battery}%")

    # 4. Maximum distance — only activated when both the task specifies
    #    max_distance_meters and the robot reports distance_meters.
    max_distance = hard.get("max_distance_meters")
    if max_distance is not None:
        robot_distance = robot_capabilities.get("distance_meters")
        if robot_distance is not None and robot_distance > max_distance:
            rejections.append(f"too_far:{robot_distance}m>{max_distance}m")

    return (len(rejections) == 0, rejections)


# ---------------------------------------------------------------------------
# Scoring function (AD-6)
# ---------------------------------------------------------------------------

# Weights — TraderBots-inspired, configurable
WEIGHT_PRICE = 0.40
WEIGHT_SLA = 0.25
WEIGHT_CONFIDENCE = 0.20
WEIGHT_REPUTATION = 0.15


def score_bids(task: Task, bids: list[Bid]) -> list[tuple[Bid, float]]:
    """Score and rank bids using four-factor weighted scoring.

    Bids where price > budget_ceiling are excluded entirely.
    Returns list sorted by composite score descending (best first).
    See DECISIONS.md AD-6.
    """
    scored: list[tuple[Bid, float]] = []

    for bid in bids:
        if bid.price > task.budget_ceiling:
            continue

        price_score = float(1 - (bid.price / task.budget_ceiling))
        sla_score = max(0.0, min(1.0, float(1 - (bid.sla_commitment_seconds / task.sla_seconds))))
        confidence_score = bid.ai_confidence
        reputation_score = bid.reputation_metadata.get("completion_rate", 0.5)

        composite = (
            price_score * WEIGHT_PRICE
            + sla_score * WEIGHT_SLA
            + confidence_score * WEIGHT_CONFIDENCE
            + reputation_score * WEIGHT_REPUTATION
        )

        scored.append((bid, round(composite, 4)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Bid signing (PD-3)
# Dual-mode: HMAC-SHA256 (v0.5 compat) or Ed25519 via eth_account (v1.0).
# Controlled by the module-level SIGNING_MODE constant.
# ---------------------------------------------------------------------------


def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519/secp256k1 key pair via eth_account.

    Returns (private_key_hex, address).
    Raises RuntimeError if eth_account is not installed.
    """
    if not _HAS_ETH_ACCOUNT:
        raise RuntimeError(
            "eth_account is not installed — cannot generate Ed25519 keypair. "
            "Install it with: pip install eth-account"
        )
    account = Account.create()
    return (account.key.hex(), account.address)


def _sign_bid_hmac(robot_id: str, request_id: str, price: Decimal, key: str) -> str:
    """Sign a bid using HMAC-SHA256 (v0.5 behavior)."""
    message = f"{robot_id}:{request_id}:{price}"
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _verify_bid_hmac(bid: Bid, key: str) -> bool:
    """Verify a bid's HMAC-SHA256 signature. Timing-safe comparison."""
    expected = _sign_bid_hmac(bid.robot_id, bid.request_id, bid.price, key)
    return hmac.compare_digest(bid.bid_hash, expected)


def _sign_bid_ed25519(robot_id: str, request_id: str, price: Decimal, key: str) -> str:
    """Sign a bid using the robot's ERC-8004 signer key via eth_account.

    ``key`` is a hex private key (with or without 0x prefix).
    Returns the signature as a hex string.
    """
    if not _HAS_ETH_ACCOUNT:
        warnings.warn(
            "eth_account not installed — falling back to HMAC signing",
            RuntimeWarning,
            stacklevel=3,
        )
        return _sign_bid_hmac(robot_id, request_id, price, key)
    message = f"{robot_id}:{request_id}:{price}"
    msg = encode_defunct(text=message)
    signed = Account.sign_message(msg, private_key=key)
    return signed.signature.hex()


def _verify_bid_ed25519(bid: Bid, key: str) -> bool:
    """Verify a bid signature and check signer address.

    ``key`` is the expected signer address (not a private key).
    Recovers the signer from the signature and compares to ``key``.
    """
    if not _HAS_ETH_ACCOUNT:
        warnings.warn(
            "eth_account not installed — falling back to HMAC verification",
            RuntimeWarning,
            stacklevel=3,
        )
        return _verify_bid_hmac(bid, key)
    message = f"{bid.robot_id}:{bid.request_id}:{bid.price}"
    msg = encode_defunct(text=message)
    try:
        recovered = Account.recover_message(msg, signature=bytes.fromhex(bid.bid_hash))
    except Exception:
        return False
    return recovered.lower() == key.lower()


def sign_bid(robot_id: str, request_id: str, price: Decimal, key: str) -> str:
    """Sign a bid. Dispatches to HMAC or Ed25519 based on SIGNING_MODE.

    When SIGNING_MODE == "hmac": ``key`` is a shared secret string.
    When SIGNING_MODE == "ed25519": ``key`` is a hex private key.
    """
    if SIGNING_MODE == "ed25519":
        return _sign_bid_ed25519(robot_id, request_id, price, key)
    return _sign_bid_hmac(robot_id, request_id, price, key)


def verify_bid(bid: Bid, key: str) -> bool:
    """Verify a bid signature. Dispatches to HMAC or Ed25519 based on SIGNING_MODE.

    When SIGNING_MODE == "hmac": ``key`` is the shared secret.
    When SIGNING_MODE == "ed25519": ``key`` is the expected signer address.
    """
    if SIGNING_MODE == "ed25519":
        return _verify_bid_ed25519(bid, key)
    return _verify_bid_hmac(bid, key)


# ---------------------------------------------------------------------------
# Console logging
# ---------------------------------------------------------------------------

def log(tag: str, message: str) -> None:
    """Print a tagged log line. Tag is left-padded to 10 chars with brackets."""
    print(f"[{tag:<8s}] {message}")


# ---------------------------------------------------------------------------
# DM-NEW: LedgerEntry — shared type used by wallet.py (v0.5)
# ---------------------------------------------------------------------------

@dataclass
class LedgerEntry:
    """Single debit or credit in the wallet ledger. See PRODUCT_SPEC_V05 §3.4."""

    wallet_id: str
    amount: Decimal
    entry_type: str  # "reservation_25" | "delivery_75" | "release" | "credit" | "refund"
    request_id: str = ""
    note: str = ""
    balance_after: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# DM-NEW: ReputationRecord — shared type used by reputation.py (v0.5)
# ---------------------------------------------------------------------------

@dataclass
class ReputationRecord:
    """Single task outcome for reputation computation. See PRODUCT_SPEC_V05 §3.3."""

    robot_id: str
    request_id: str
    outcome: str  # "completed" | "rejected" | "abandoned" | "cancelled"
    sla_met: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
