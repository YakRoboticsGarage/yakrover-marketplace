"""Wallet ledger for the robot task auction marketplace.

In-memory ledger tracking all debits and credits across buyer and robot
wallets.  Every mutation records a timestamped entry so the full history
is auditable.  See PRODUCT_SPEC_V05.md Section 7 for flow diagrams.

v1.0 addition: ``StripeWalletService`` coordinates WalletLedger (internal)
with StripeService (external Stripe API) for real/stub payment flows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

# ---------------------------------------------------------------------------
# Try to import LedgerEntry from core; fall back to dict-based entries.
# The other agent may not have added LedgerEntry to core.py yet.
# ---------------------------------------------------------------------------

_USE_LEDGER_ENTRY_DATACLASS = False

try:
    from auction.core import LedgerEntry  # noqa: F401

    _USE_LEDGER_ENTRY_DATACLASS = True
except ImportError:
    pass

# Valid entry_type values
VALID_ENTRY_TYPES = frozenset(
    ["reservation_25", "delivery_75", "release", "credit", "refund", "fund"]
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InsufficientBalance(Exception):
    """Raised when a debit would bring the wallet balance below zero."""

    def __init__(self, wallet_id: str, required: Decimal, available: Decimal) -> None:
        self.wallet_id = wallet_id
        self.required = required
        self.available = available
        super().__init__(
            f"Wallet '{wallet_id}': insufficient balance "
            f"(required={required}, available={available})"
        )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _make_entry(
    *,
    wallet_id: str,
    entry_type: str,
    amount: Decimal,
    balance_after: Decimal,
    request_id: str | None,
    note: str,
) -> dict:
    """Create a ledger entry dict (or LedgerEntry dataclass if available)."""
    entry = {
        "entry_id": f"le_{uuid.uuid4().hex[:12]}",
        "wallet_id": wallet_id,
        "entry_type": entry_type,
        "amount": amount,
        "balance_after": balance_after,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc),
        "note": note,
    }

    if _USE_LEDGER_ENTRY_DATACLASS:
        # LedgerEntry dataclass may not have entry_id; pass only known fields.
        import inspect

        _le_fields = {f.name for f in __import__("dataclasses").fields(LedgerEntry)}
        filtered = {k: v for k, v in entry.items() if k in _le_fields}
        return LedgerEntry(**filtered)  # type: ignore[return-value]

    return entry


# ---------------------------------------------------------------------------
# WalletLedger
# ---------------------------------------------------------------------------


class WalletLedger:
    """In-memory wallet ledger with debit/credit tracking.

    Each wallet is identified by a string id (e.g. ``"buyer"`` or a
    ``robot_id``).  All monetary values use :class:`~decimal.Decimal` for
    precision.
    """

    def __init__(self) -> None:
        self._balances: dict[str, Decimal] = {}
        self._entries: list[dict] = []

    # -- helpers ----------------------------------------------------------

    def _require_wallet(self, wallet_id: str) -> None:
        if wallet_id not in self._balances:
            raise KeyError(f"Wallet '{wallet_id}' does not exist")

    # -- public API -------------------------------------------------------

    def create_wallet(
        self, wallet_id: str, initial_balance: Decimal = Decimal("0")
    ) -> None:
        """Create a new wallet.  Raises ``ValueError`` if it already exists."""
        if wallet_id in self._balances:
            raise ValueError(f"Wallet '{wallet_id}' already exists")
        self._balances[wallet_id] = Decimal(str(initial_balance))

    def fund_wallet(
        self, wallet_id: str, amount: Decimal, note: str = ""
    ) -> dict:
        """Add funds to an existing wallet and record a ledger entry."""
        self._require_wallet(wallet_id)
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Fund amount must be positive")

        self._balances[wallet_id] += amount
        entry = _make_entry(
            wallet_id=wallet_id,
            entry_type="fund",
            amount=amount,
            balance_after=self._balances[wallet_id],
            request_id=None,
            note=note or "Wallet funded",
        )
        self._entries.append(entry)
        return entry

    def check_balance(self, wallet_id: str, required: Decimal) -> bool:
        """Return ``True`` if the wallet has at least *required* funds."""
        self._require_wallet(wallet_id)
        return self._balances[wallet_id] >= Decimal(str(required))

    def debit(
        self,
        wallet_id: str,
        amount: Decimal,
        request_id: str,
        entry_type: str,
        note: str = "",
    ) -> dict:
        """Subtract *amount* from the wallet.

        Raises :class:`InsufficientBalance` if the wallet cannot cover
        the debit.  The *amount* is stored as a **negative** value in the
        ledger entry (outflow).
        """
        self._require_wallet(wallet_id)
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        if self._balances[wallet_id] < amount:
            raise InsufficientBalance(wallet_id, amount, self._balances[wallet_id])

        self._balances[wallet_id] -= amount
        entry = _make_entry(
            wallet_id=wallet_id,
            entry_type=entry_type,
            amount=-amount,
            balance_after=self._balances[wallet_id],
            request_id=request_id,
            note=note,
        )
        self._entries.append(entry)
        return entry

    def credit(
        self,
        wallet_id: str,
        amount: Decimal,
        request_id: str,
        entry_type: str,
        note: str = "",
    ) -> dict:
        """Add *amount* back to the wallet (refunds, operator credits, etc.).

        The *amount* is stored as a **positive** value in the ledger entry
        (inflow).
        """
        self._require_wallet(wallet_id)
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        self._balances[wallet_id] += amount
        entry = _make_entry(
            wallet_id=wallet_id,
            entry_type=entry_type,
            amount=amount,
            balance_after=self._balances[wallet_id],
            request_id=request_id,
            note=note,
        )
        self._entries.append(entry)
        return entry

    def get_balance(self, wallet_id: str) -> Decimal:
        """Return the current balance of *wallet_id*."""
        self._require_wallet(wallet_id)
        return self._balances[wallet_id]

    def get_entries(
        self,
        wallet_id: str | None = None,
        request_id: str | None = None,
    ) -> list[dict]:
        """Return ledger entries, optionally filtered by wallet and/or request."""
        results = self._entries
        if wallet_id is not None:
            results = [
                e
                for e in results
                if (e["wallet_id"] if isinstance(e, dict) else e.wallet_id) == wallet_id
            ]
        if request_id is not None:
            results = [
                e
                for e in results
                if (e["request_id"] if isinstance(e, dict) else e.request_id) == request_id
            ]
        return list(results)


# ---------------------------------------------------------------------------
# StripeWalletService — coordinates WalletLedger + StripeService (v1.0)
# ---------------------------------------------------------------------------


class StripeWalletService:
    """Coordinates WalletLedger (internal) with StripeService (external).

    Provides ``fund_wallet`` (Stripe PaymentIntent -> internal credit) and
    ``get_balance`` convenience methods.  The StripeService may be in stub
    mode (no real Stripe calls) — the internal ledger is always updated.
    """

    def __init__(self, ledger: WalletLedger, stripe_service: object) -> None:
        self.ledger = ledger
        self.stripe = stripe_service

    def fund_wallet(
        self,
        wallet_id: str,
        amount: Decimal,
        payment_method: str = "pm_card_visa",
    ) -> dict:
        """Create a Stripe PaymentIntent and fund the internal wallet.

        In stub mode, the Stripe call returns a stub dict but the internal
        ledger is still credited — this enables demo/test flows without a
        real Stripe key.

        Returns a dict with ``payment_intent`` (Stripe response) and
        ``balance`` (new wallet balance as string).
        """
        amount = Decimal(str(amount))
        amount_cents = int(amount * 100)

        pi_result = self.stripe.create_wallet_topup(
            amount_cents=amount_cents,
            metadata={"wallet_id": wallet_id, "payment_method": payment_method},
        )

        # Fund the internal ledger regardless of stub/live mode
        # (In live mode you would wait for webhook confirmation; for v1.0
        # we credit immediately for simplicity.)
        self.ledger.fund_wallet(wallet_id, amount, note=f"Stripe top-up ({wallet_id})")

        return {
            "payment_intent": pi_result,
            "balance": str(self.ledger.get_balance(wallet_id)),
        }

    def get_balance(self, wallet_id: str) -> Decimal:
        """Return the current internal wallet balance."""
        return self.ledger.get_balance(wallet_id)
