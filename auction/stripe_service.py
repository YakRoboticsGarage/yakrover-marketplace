"""Stripe API wrapper for the robot task auction marketplace.

Supports two modes:
- Live mode: initialized with a Stripe API key, makes real Stripe SDK calls.
- Stub mode: initialized without a key (None), logs actions and returns stub dicts.

All methods return plain dicts. Stripe errors are caught and returned as
{"error": str, "error_type": str} rather than raised.
"""

from __future__ import annotations

import logging

import stripe

logger = logging.getLogger(__name__)


def _to_dict(stripe_obj: object) -> dict:
    """Convert a Stripe API response object to a plain dict.

    Stripe SDK objects expose a ``to_dict_recursive()`` method.  For plain
    dicts or other mappings we fall through to ``dict()``.
    """
    if hasattr(stripe_obj, "to_dict_recursive"):
        return stripe_obj.to_dict_recursive()
    return dict(stripe_obj)  # type: ignore[arg-type]


class StripeService:
    """Thin wrapper around the Stripe Python SDK for wallet top-ups,
    Connect account management, and operator payouts."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize with Stripe API key. If None, runs in stub mode (logs only)."""
        self.api_key = api_key
        self.stub_mode = api_key is None
        if api_key:
            stripe.api_key = api_key

    # ------------------------------------------------------------------
    # Wallet top-up
    # ------------------------------------------------------------------

    def create_wallet_topup(
        self,
        amount_cents: int,
        currency: str = "usd",
        metadata: dict | None = None,
    ) -> dict:
        """Create a PaymentIntent for wallet top-up.

        Returns the PaymentIntent as a dict, or a stub dict in stub mode.
        """
        if self.stub_mode:
            result = {
                "stub": True,
                "action": "create_wallet_topup",
                "amount_cents": amount_cents,
                "currency": currency,
                "metadata": metadata or {},
            }
            logger.info("STUB create_wallet_topup: %s", result)
            return result

        try:
            pi = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True},
            )
            return _to_dict(pi)
        except stripe.error.StripeError as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}

    # ------------------------------------------------------------------
    # Connect accounts
    # ------------------------------------------------------------------

    def create_connect_account(
        self,
        email: str,
        country: str = "US",
    ) -> dict:
        """Create a Stripe Connect Express account for a robot operator."""
        if self.stub_mode:
            result = {
                "stub": True,
                "action": "create_connect_account",
                "email": email,
                "country": country,
            }
            logger.info("STUB create_connect_account: %s", result)
            return result

        try:
            account = stripe.Account.create(
                type="express",
                country=country,
                email=email,
                capabilities={"transfers": {"requested": True}},
            )
            return _to_dict(account)
        except stripe.error.StripeError as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}

    def get_account(self, account_id: str) -> dict:
        """Retrieve a Connect account by ID."""
        if self.stub_mode:
            result = {
                "stub": True,
                "action": "get_account",
                "account_id": account_id,
            }
            logger.info("STUB get_account: %s", result)
            return result

        try:
            account = stripe.Account.retrieve(account_id)
            return _to_dict(account)
        except stripe.error.StripeError as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}

    # ------------------------------------------------------------------
    # Transfers (operator payouts)
    # ------------------------------------------------------------------

    def create_transfer(
        self,
        amount_cents: int,
        destination_account_id: str,
        transfer_group: str,
        metadata: dict | None = None,
    ) -> dict:
        """Transfer funds to a connected account (operator payout)."""
        if self.stub_mode:
            result = {
                "stub": True,
                "action": "create_transfer",
                "amount_cents": amount_cents,
                "destination_account_id": destination_account_id,
                "transfer_group": transfer_group,
                "metadata": metadata or {},
            }
            logger.info("STUB create_transfer: %s", result)
            return result

        try:
            transfer = stripe.Transfer.create(
                amount=amount_cents,
                currency="usd",
                destination=destination_account_id,
                transfer_group=transfer_group,
                metadata=metadata or {},
            )
            return _to_dict(transfer)
        except stripe.error.StripeError as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}

    # ------------------------------------------------------------------
    # PaymentIntent retrieval
    # ------------------------------------------------------------------

    def get_payment_intent(self, pi_id: str) -> dict:
        """Retrieve a PaymentIntent by ID."""
        if self.stub_mode:
            result = {
                "stub": True,
                "action": "get_payment_intent",
                "pi_id": pi_id,
            }
            logger.info("STUB get_payment_intent: %s", result)
            return result

        try:
            pi = stripe.PaymentIntent.retrieve(pi_id)
            return _to_dict(pi)
        except stripe.error.StripeError as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}
