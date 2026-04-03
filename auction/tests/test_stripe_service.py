"""Unit tests for StripeService — all Stripe SDK calls are mocked."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch

import stripe

from auction.stripe_service import StripeService

# ---------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------


class TestInit:
    def test_init_with_key(self):
        """When an API key is provided, stripe.api_key is set and stub_mode is False."""
        with patch.object(stripe, "api_key", None):
            svc = StripeService(api_key="sk_test_abc123")
            assert svc.api_key == "sk_test_abc123"
            assert svc.stub_mode is False
            assert stripe.api_key == "sk_test_abc123"

    def test_init_stub_mode(self):
        """When no API key is provided, stub_mode is True and stripe.api_key is untouched."""
        original = stripe.api_key
        svc = StripeService(api_key=None)
        assert svc.api_key is None
        assert svc.stub_mode is True
        # stripe.api_key should not have been changed
        assert stripe.api_key == original


# ---------------------------------------------------------------
# Stub mode
# ---------------------------------------------------------------


class TestStubMode:
    def setup_method(self):
        self.svc = StripeService(api_key=None)

    def test_create_wallet_topup_stub(self):
        """Stub mode returns a dict with stub=True and the action name."""
        result = self.svc.create_wallet_topup(amount_cents=2500, currency="usd")
        assert result["stub"] is True
        assert result["action"] == "create_wallet_topup"
        assert result["amount_cents"] == 2500
        assert result["currency"] == "usd"

    def test_create_transfer_stub(self):
        """Stub mode returns a dict describing the transfer intent."""
        result = self.svc.create_transfer(
            amount_cents=35,
            destination_account_id="acct_test_123",
            transfer_group="req_abc",
            metadata={"request_id": "req_abc"},
        )
        assert result["stub"] is True
        assert result["action"] == "create_transfer"
        assert result["amount_cents"] == 35
        assert result["destination_account_id"] == "acct_test_123"
        assert result["transfer_group"] == "req_abc"

    def test_create_connect_account_stub(self):
        """Stub mode returns a dict describing the account creation intent."""
        result = self.svc.create_connect_account(email="op@example.com", country="FI")
        assert result["stub"] is True
        assert result["action"] == "create_connect_account"
        assert result["email"] == "op@example.com"
        assert result["country"] == "FI"

    def test_get_payment_intent_stub(self):
        """Stub mode returns a dict with the PI ID."""
        result = self.svc.get_payment_intent("pi_test_xyz")
        assert result["stub"] is True
        assert result["action"] == "get_payment_intent"
        assert result["pi_id"] == "pi_test_xyz"

    def test_get_account_stub(self):
        """Stub mode returns a dict with the account ID."""
        result = self.svc.get_account("acct_test_456")
        assert result["stub"] is True
        assert result["action"] == "get_account"
        assert result["account_id"] == "acct_test_456"


# ---------------------------------------------------------------
# Live mode — mocked SDK calls
# ---------------------------------------------------------------


class TestLiveMode:
    def setup_method(self):
        self.svc = StripeService.__new__(StripeService)
        self.svc.api_key = "sk_test_live"
        self.svc.stub_mode = False

    @patch("stripe.PaymentIntent.create")
    def test_create_wallet_topup_live(self, mock_pi_create):
        """Live mode calls stripe.PaymentIntent.create with the correct params."""
        mock_pi = MagicMock()
        mock_pi.to_dict_recursive.return_value = {
            "id": "pi_test_123",
            "status": "requires_payment_method",
        }
        mock_pi_create.return_value = mock_pi

        result = self.svc.create_wallet_topup(
            amount_cents=2500,
            currency="usd",
            metadata={"wallet_id": "buyer_1"},
        )

        mock_pi_create.assert_called_once_with(
            amount=2500,
            currency="usd",
            metadata={"wallet_id": "buyer_1"},
            automatic_payment_methods={"enabled": True},
            idempotency_key=ANY,
        )
        assert result["id"] == "pi_test_123"

    @patch("stripe.Transfer.create")
    def test_create_transfer_live(self, mock_transfer_create):
        """Live mode calls stripe.Transfer.create with correct destination and transfer_group."""
        mock_transfer = MagicMock()
        mock_transfer.to_dict_recursive.return_value = {
            "id": "tr_test_456",
            "amount": 35,
        }
        mock_transfer_create.return_value = mock_transfer

        result = self.svc.create_transfer(
            amount_cents=35,
            destination_account_id="acct_op_789",
            transfer_group="req_abc",
            metadata={"request_id": "req_abc"},
        )

        mock_transfer_create.assert_called_once_with(
            amount=35,
            currency="usd",
            destination="acct_op_789",
            transfer_group="req_abc",
            metadata={"request_id": "req_abc"},
            idempotency_key=ANY,
        )
        assert result["id"] == "tr_test_456"

    @patch("stripe.Account.create")
    def test_create_connect_account_live(self, mock_account_create):
        """Live mode calls stripe.Account.create with type=express and correct params."""
        mock_account = MagicMock()
        mock_account.to_dict_recursive.return_value = {
            "id": "acct_test_new",
            "type": "express",
        }
        mock_account_create.return_value = mock_account

        result = self.svc.create_connect_account(email="op@robots.fi", country="FI")

        mock_account_create.assert_called_once_with(
            type="express",
            country="FI",
            email="op@robots.fi",
            capabilities={"transfers": {"requested": True}},
        )
        assert result["id"] == "acct_test_new"

    @patch("stripe.PaymentIntent.retrieve")
    def test_get_payment_intent_live(self, mock_pi_retrieve):
        """Live mode retrieves a PaymentIntent by ID."""
        mock_pi = MagicMock()
        mock_pi.to_dict_recursive.return_value = {
            "id": "pi_test_existing",
            "status": "succeeded",
        }
        mock_pi_retrieve.return_value = mock_pi

        result = self.svc.get_payment_intent("pi_test_existing")

        mock_pi_retrieve.assert_called_once_with("pi_test_existing")
        assert result["id"] == "pi_test_existing"
        assert result["status"] == "succeeded"

    @patch("stripe.Account.retrieve")
    def test_get_account_live(self, mock_account_retrieve):
        """Live mode retrieves a Connect account by ID."""
        mock_account = MagicMock()
        mock_account.to_dict_recursive.return_value = {
            "id": "acct_test_xyz",
            "charges_enabled": True,
        }
        mock_account_retrieve.return_value = mock_account

        result = self.svc.get_account("acct_test_xyz")

        mock_account_retrieve.assert_called_once_with("acct_test_xyz")
        assert result["id"] == "acct_test_xyz"


# ---------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------


class TestErrorHandling:
    def setup_method(self):
        self.svc = StripeService.__new__(StripeService)
        self.svc.api_key = "sk_test_live"
        self.svc.stub_mode = False

    @patch("stripe.PaymentIntent.create")
    def test_stripe_error_handling_payment_intent(self, mock_pi_create):
        """StripeError from PaymentIntent.create is caught and returned as error dict."""
        mock_pi_create.side_effect = stripe.error.CardError(
            message="Your card was declined.",
            param="payment_method",
            code="card_declined",
        )

        result = self.svc.create_wallet_topup(amount_cents=500)

        assert "error" in result
        assert "card_declined" in result["error"] or "declined" in result["error"]
        assert result["error_type"] == "CardError"

    @patch("stripe.Transfer.create")
    def test_stripe_error_handling_transfer(self, mock_transfer_create):
        """StripeError from Transfer.create is caught and returned as error dict."""
        mock_transfer_create.side_effect = stripe.error.InvalidRequestError(
            message="No such destination: 'acct_invalid'",
            param="destination",
        )

        result = self.svc.create_transfer(
            amount_cents=100,
            destination_account_id="acct_invalid",
            transfer_group="req_fail",
        )

        assert "error" in result
        assert "acct_invalid" in result["error"]
        assert result["error_type"] == "InvalidRequestError"

    @patch("stripe.Account.create")
    def test_stripe_error_handling_account(self, mock_account_create):
        """StripeError from Account.create is caught and returned as error dict."""
        mock_account_create.side_effect = stripe.error.AuthenticationError(
            message="Invalid API Key provided: sk_test_***invalid",
        )

        result = self.svc.create_connect_account(email="test@test.com")

        assert "error" in result
        assert result["error_type"] == "AuthenticationError"

    @patch("stripe.PaymentIntent.retrieve")
    def test_stripe_error_handling_retrieve(self, mock_pi_retrieve):
        """StripeError from PaymentIntent.retrieve is caught and returned as error dict."""
        mock_pi_retrieve.side_effect = stripe.error.InvalidRequestError(
            message="No such payment_intent: 'pi_nonexistent'",
            param="id",
        )

        result = self.svc.get_payment_intent("pi_nonexistent")

        assert "error" in result
        assert result["error_type"] == "InvalidRequestError"
