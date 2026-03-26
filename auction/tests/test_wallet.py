"""Unit tests for auction.wallet — the wallet ledger module.

12 tests covering: creation, funding, debit, credit, balance checks,
entry queries, and a full auction flow.

See docs/BUILD_PLAN_V05.md Phase B-3 and PRODUCT_SPEC_V05.md Section 10.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from auction.wallet import InsufficientBalance, WalletLedger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry_field(entry, field: str):
    """Extract a field from a ledger entry (dict or dataclass)."""
    if isinstance(entry, dict):
        return entry[field]
    return getattr(entry, field)


# ---------------------------------------------------------------------------
# 1. test_create_wallet
# ---------------------------------------------------------------------------

def test_create_wallet():
    """Creating a wallet with no initial balance yields zero."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer")
    assert ledger.get_balance("buyer") == Decimal("0")


# ---------------------------------------------------------------------------
# 2. test_create_wallet_initial_balance
# ---------------------------------------------------------------------------

def test_create_wallet_initial_balance():
    """Creating a wallet with an explicit initial balance stores it."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("10.00"))
    assert ledger.get_balance("buyer") == Decimal("10.00")


# ---------------------------------------------------------------------------
# 3. test_fund_wallet
# ---------------------------------------------------------------------------

def test_fund_wallet():
    """Funding a wallet increases the balance and records a ledger entry."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer")
    entry = ledger.fund_wallet("buyer", Decimal("5.00"))

    assert ledger.get_balance("buyer") == Decimal("5.00")
    assert _entry_field(entry, "entry_type") == "fund"
    assert _entry_field(entry, "amount") == Decimal("5.00")
    assert _entry_field(entry, "balance_after") == Decimal("5.00")


# ---------------------------------------------------------------------------
# 4. test_debit_success
# ---------------------------------------------------------------------------

def test_debit_success():
    """Debiting reduces the balance and records a negative amount."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("10.00"))
    entry = ledger.debit(
        "buyer", Decimal("3.00"), request_id="req_001", entry_type="reservation_25"
    )

    assert ledger.get_balance("buyer") == Decimal("7.00")
    assert _entry_field(entry, "amount") == Decimal("-3.00")
    assert _entry_field(entry, "balance_after") == Decimal("7.00")


# ---------------------------------------------------------------------------
# 5. test_debit_insufficient
# ---------------------------------------------------------------------------

def test_debit_insufficient():
    """Debiting more than the balance raises InsufficientBalance."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("1.00"))

    with pytest.raises(InsufficientBalance) as exc_info:
        ledger.debit(
            "buyer", Decimal("5.00"), request_id="req_002", entry_type="reservation_25"
        )

    assert exc_info.value.wallet_id == "buyer"
    assert exc_info.value.required == Decimal("5.00")
    assert exc_info.value.available == Decimal("1.00")
    # Balance unchanged
    assert ledger.get_balance("buyer") == Decimal("1.00")


# ---------------------------------------------------------------------------
# 6. test_credit
# ---------------------------------------------------------------------------

def test_credit():
    """Crediting (refund) adds funds back and records a positive amount."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("10.00"))
    ledger.debit(
        "buyer", Decimal("4.00"), request_id="req_003", entry_type="reservation_25"
    )
    assert ledger.get_balance("buyer") == Decimal("6.00")

    entry = ledger.credit(
        "buyer", Decimal("4.00"), request_id="req_003", entry_type="refund",
        note="Reservation refunded on rejection",
    )

    assert ledger.get_balance("buyer") == Decimal("10.00")
    assert _entry_field(entry, "amount") == Decimal("4.00")
    assert _entry_field(entry, "balance_after") == Decimal("10.00")
    assert _entry_field(entry, "entry_type") == "refund"


# ---------------------------------------------------------------------------
# 7. test_check_balance_true
# ---------------------------------------------------------------------------

def test_check_balance_true():
    """check_balance returns True when the wallet has sufficient funds."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("5.00"))
    assert ledger.check_balance("buyer", Decimal("5.00")) is True
    assert ledger.check_balance("buyer", Decimal("3.00")) is True


# ---------------------------------------------------------------------------
# 8. test_check_balance_false
# ---------------------------------------------------------------------------

def test_check_balance_false():
    """check_balance returns False when funds are insufficient."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("2.00"))
    assert ledger.check_balance("buyer", Decimal("5.00")) is False


# ---------------------------------------------------------------------------
# 9. test_get_entries_all
# ---------------------------------------------------------------------------

def test_get_entries_all():
    """get_entries() with no filters returns all recorded entries."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("0"))
    ledger.fund_wallet("buyer", Decimal("10.00"))
    ledger.debit(
        "buyer", Decimal("1.00"), request_id="req_010", entry_type="reservation_25"
    )
    ledger.credit(
        "buyer", Decimal("0.50"), request_id="req_010", entry_type="refund"
    )

    entries = ledger.get_entries()
    assert len(entries) == 3


# ---------------------------------------------------------------------------
# 10. test_get_entries_by_wallet
# ---------------------------------------------------------------------------

def test_get_entries_by_wallet():
    """get_entries(wallet_id=...) filters entries to a single wallet."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("0"))
    ledger.create_wallet("robot_a", initial_balance=Decimal("0"))
    ledger.fund_wallet("buyer", Decimal("10.00"))
    ledger.fund_wallet("robot_a", Decimal("5.00"))

    buyer_entries = ledger.get_entries(wallet_id="buyer")
    assert len(buyer_entries) == 1
    assert all(_entry_field(e, "wallet_id") == "buyer" for e in buyer_entries)

    robot_entries = ledger.get_entries(wallet_id="robot_a")
    assert len(robot_entries) == 1


# ---------------------------------------------------------------------------
# 11. test_get_entries_by_request
# ---------------------------------------------------------------------------

def test_get_entries_by_request():
    """get_entries(request_id=...) filters entries by request."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer", initial_balance=Decimal("20.00"))
    ledger.debit(
        "buyer", Decimal("1.00"), request_id="req_A", entry_type="reservation_25"
    )
    ledger.debit(
        "buyer", Decimal("2.00"), request_id="req_B", entry_type="reservation_25"
    )
    ledger.debit(
        "buyer", Decimal("3.00"), request_id="req_A", entry_type="delivery_75"
    )

    req_a = ledger.get_entries(request_id="req_A")
    assert len(req_a) == 2
    assert all(_entry_field(e, "request_id") == "req_A" for e in req_a)


# ---------------------------------------------------------------------------
# 12. test_full_auction_flow
# ---------------------------------------------------------------------------

def test_full_auction_flow():
    """Simulate: fund $10 -> debit $0.09 (reservation) -> debit $0.26 (delivery) -> verify $9.65."""
    ledger = WalletLedger()
    ledger.create_wallet("buyer")

    # Fund
    ledger.fund_wallet("buyer", Decimal("10.00"))
    assert ledger.get_balance("buyer") == Decimal("10.00")

    req_id = "req_full_flow"

    # 25% reservation debit
    e1 = ledger.debit(
        "buyer", Decimal("0.09"), request_id=req_id, entry_type="reservation_25",
        note="25% reservation hold",
    )
    assert ledger.get_balance("buyer") == Decimal("9.91")
    assert _entry_field(e1, "balance_after") == Decimal("9.91")

    # 75% delivery debit
    e2 = ledger.debit(
        "buyer", Decimal("0.26"), request_id=req_id, entry_type="delivery_75",
        note="75% delivery payment",
    )
    assert ledger.get_balance("buyer") == Decimal("9.65")
    assert _entry_field(e2, "balance_after") == Decimal("9.65")

    # Verify all entries for this request
    flow_entries = ledger.get_entries(request_id=req_id)
    assert len(flow_entries) == 2
