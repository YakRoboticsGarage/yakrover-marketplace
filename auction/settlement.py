"""Settlement abstraction layer for the robot task auction marketplace.

Defines the interface that all settlement modes (Stripe fiat, Base x402,
Horizen L3 private, DTN batched) must implement. See FD-1 in ROADMAP_v2.md.

v1.1.1: Types and interface only. Implementations come in v1.5+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

# ---------------------------------------------------------------------------
# FD-1: Settlement modes
# ---------------------------------------------------------------------------


class SettlementMode(StrEnum):
    """Four settlement modes covering timing × privacy dimensions.

    See FOUNDATIONAL_TECH_ANALYSIS.md for rationale.
    """

    IMMEDIATE_TRANSPARENT = "immediate_transparent"  # v1.5: Base x402
    IMMEDIATE_PRIVATE = "immediate_private"  # v2.1-P: Horizen L3 candidate
    BATCHED_TRANSPARENT = "batched_transparent"  # v2.1-L: DTN lunar
    BATCHED_PRIVATE = "batched_private"  # v3.0: convergence


# ---------------------------------------------------------------------------
# Settlement receipt (returned by all settlement implementations)
# ---------------------------------------------------------------------------


@dataclass
class SettlementReceipt:
    """Proof that a settlement was completed (or attempted)."""

    task_request_id: str
    commitment_hash: str  # H(request_id || salt) — never raw request_id
    mode: SettlementMode
    amount: Decimal
    currency: str  # "usd", "usdc", "eur"
    recipient_id: str  # Platform-internal robot/operator ID (not wallet address)
    tx_hash: str | None = None  # On-chain tx hash (None for Stripe)
    stripe_transfer_id: str | None = None  # Stripe transfer ID (None for crypto)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Settlement interface (Protocol — structural typing, no base class needed)
# ---------------------------------------------------------------------------


class SettlementInterface(Protocol):
    """Interface that all settlement implementations must satisfy.

    Use structural typing (Protocol) so implementations don't need to inherit.
    Both StripeSettlement and BaseX402Settlement will implement this.
    """

    def settle(
        self,
        task_request_id: str,
        commitment_hash: str,
        mode: SettlementMode,
        amount: Decimal,
        currency: str,
        recipient_id: str,
        idempotency_key: str | None = None,
    ) -> SettlementReceipt:
        """Execute a single settlement.

        Args:
            task_request_id: The task's request_id (for internal tracking only).
            commitment_hash: H(request_id || salt) — goes on-chain/in metadata.
            mode: Which settlement mode to use.
            amount: Amount to settle.
            currency: Currency code.
            recipient_id: Platform-internal robot/operator ID.
            idempotency_key: For retry safety.

        Returns:
            SettlementReceipt with proof of settlement.

        Raises:
            NotImplementedError: If the mode is not yet implemented.
        """
        ...

    def verify(self, receipt: SettlementReceipt) -> bool:
        """Verify that a settlement receipt is valid and the payment occurred."""
        ...

    def batch_settle(
        self,
        settlements: list[dict],
    ) -> list[SettlementReceipt]:
        """Execute multiple settlements in a batch (for DTN/lunar use).

        Each dict in settlements has the same keys as settle() args.
        Returns a list of receipts (one per settlement).

        Raises:
            NotImplementedError: If batched settlement is not supported.
        """
        ...


# ---------------------------------------------------------------------------
# Pending settlement (queued for batched modes)
# ---------------------------------------------------------------------------


@dataclass
class PendingSettlement:
    """A settlement waiting to be batched and posted on-chain."""

    task_request_id: str
    commitment_hash: str
    amount: Decimal
    currency: str
    recipient_id: str
    queued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
