"""
Stripe test-mode integration tests.

These call the real Stripe API with test-mode keys.
They catch issues that mocks miss (currency restrictions, API version drift, etc.).

Run: uv run pytest auction/tests/integration/test_stripe_live.py -m stripe -v
Requires: STRIPE_SECRET_KEY=sk_test_...
"""

from __future__ import annotations

import pytest

stripe = pytest.importorskip("stripe")


@pytest.mark.stripe
class TestStripeWalletTopUp:
    """Verify wallet top-up via PaymentIntent works against real Stripe."""

    def test_create_payment_intent(self, stripe_api_key: str) -> None:
        stripe.api_key = stripe_api_key
        pi = stripe.PaymentIntent.create(
            amount=2500,  # $25.00
            currency="usd",
            metadata={"purpose": "integration_test", "wallet_id": "test_buyer_1"},
            automatic_payment_methods={"enabled": True},
        )
        assert pi.id.startswith("pi_")
        assert pi.amount == 2500
        assert pi.status in ("requires_payment_method", "requires_confirmation")
        assert pi.metadata["wallet_id"] == "test_buyer_1"

    def test_minimum_charge_enforced(self, stripe_api_key: str) -> None:
        """Stripe rejects charges below $0.50 — verify our minimum (TC-1) aligns."""
        stripe.api_key = stripe_api_key
        # $0.49 should fail
        with pytest.raises(stripe.InvalidRequestError):
            stripe.PaymentIntent.create(
                amount=49,
                currency="usd",
                automatic_payment_methods={"enabled": True},
            )


@pytest.mark.stripe
class TestStripeOperatorTransfer:
    """Verify operator payout via Connect Express works."""

    def test_transfer_to_operator(self, stripe_api_key: str, stripe_operator_account: str) -> None:
        stripe.api_key = stripe_api_key

        # Fund platform balance first (test mode only)
        stripe.Charge.create(
            amount=1000,
            currency="usd",
            source="tok_bypassPending",
            description="Integration test: fund platform balance",
        )

        # Transfer to operator
        transfer = stripe.Transfer.create(
            amount=35,  # $0.35
            currency="usd",
            destination=stripe_operator_account,
            metadata={
                "purpose": "integration_test",
                "request_id": "test-req-001",
            },
        )
        assert transfer.id.startswith("tr_")
        assert transfer.amount == 35
        assert transfer.destination == stripe_operator_account


@pytest.mark.stripe
class TestStripeWebhookSignature:
    """Verify webhook signature verification works."""

    def test_valid_signature_verifies(self, stripe_api_key: str) -> None:
        """Construct a signed webhook event and verify it."""
        import time

        payload = '{"id": "evt_test", "type": "payment_intent.succeeded"}'
        secret = "whsec_test_secret"
        timestamp = str(int(time.time()))

        # Compute expected signature
        import hashlib
        import hmac

        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        header = f"t={timestamp},v1={signature}"

        # This should not raise
        event = stripe.Webhook.construct_event(payload, header, secret)
        assert event["id"] == "evt_test"

    def test_invalid_signature_rejected(self) -> None:
        """Tampered payload must be rejected."""
        with pytest.raises(stripe.SignatureVerificationError):
            stripe.Webhook.construct_event(
                '{"id": "evt_test"}',
                "t=123,v1=badsignature",
                "whsec_test_secret",
            )
