"""Robot task auction marketplace — core library.

See docs/PRODUCT_SPEC_V01.md for the complete specification.
See docs/DECISIONS.md for all product and technical decisions.
"""

from .core import (
    WEIGHT_CONFIDENCE,
    WEIGHT_PRICE,
    WEIGHT_REPUTATION,
    WEIGHT_SLA,
    AuctionResult,
    Bid,
    DeliveryPayload,
    LedgerEntry,
    ReputationRecord,
    Task,
    TaskState,
    check_hard_constraints,
    log,
    score_bids,
    sign_bid,
    verify_bid,
)

__all__ = [
    "AuctionResult",
    "Bid",
    "DeliveryPayload",
    "LedgerEntry",
    "ReputationRecord",
    "Task",
    "TaskState",
    "WEIGHT_CONFIDENCE",
    "WEIGHT_PRICE",
    "WEIGHT_REPUTATION",
    "WEIGHT_SLA",
    "check_hard_constraints",
    "log",
    "score_bids",
    "sign_bid",
    "verify_bid",
]
