"""Tests for Ed25519 signing via eth_account (Track C, v1.0).

Covers:
- Key pair generation
- Ed25519 sign and verify round-trip
- Tampered bid rejection
- Wrong key rejection
- HMAC backward compatibility

Uses monkeypatch to set auction.core.SIGNING_MODE per test.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import auction.core as core
from auction.core import (
    Bid,
    generate_keypair,
    sign_bid,
    verify_bid,
)

# Skip the entire module if eth_account is not available
pytestmark = pytest.mark.skipif(
    not core._HAS_ETH_ACCOUNT,
    reason="eth_account not installed — Ed25519 tests require it",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bid(
    robot_id: str = "rover_1",
    request_id: str = "req_test_001",
    price: Decimal = Decimal("1.50"),
    bid_hash: str = "",
    sla_commitment_seconds: int = 300,
    ai_confidence: float = 0.95,
) -> Bid:
    return Bid(
        request_id=request_id,
        robot_id=robot_id,
        price=price,
        sla_commitment_seconds=sla_commitment_seconds,
        ai_confidence=ai_confidence,
        capability_metadata={},
        reputation_metadata={},
        bid_hash=bid_hash,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateKeypair:
    def test_generate_keypair_returns_tuple(self):
        """generate_keypair() returns (private_key_hex, address)."""
        priv, addr = generate_keypair()
        assert isinstance(priv, str)
        assert isinstance(addr, str)

    def test_generate_keypair_formats(self):
        """Private key is hex, address starts with 0x and is 42 chars."""
        priv, addr = generate_keypair()
        # Private key should be valid hex (with 0x prefix from .hex())
        assert len(priv) > 0
        # Address is a checksummed Ethereum address
        assert addr.startswith("0x")
        assert len(addr) == 42

    def test_generate_keypair_unique(self):
        """Two calls produce different keys."""
        priv1, addr1 = generate_keypair()
        priv2, addr2 = generate_keypair()
        assert priv1 != priv2
        assert addr1 != addr2


class TestSignBidEd25519:
    def test_sign_bid_ed25519_returns_hex(self, monkeypatch):
        """Ed25519 signing returns a hex signature string."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        priv, _addr = generate_keypair()
        sig = sign_bid("rover_1", "req_001", Decimal("1.50"), priv)
        assert isinstance(sig, str)
        assert len(sig) > 64  # Ed25519/secp256k1 sigs are longer than HMAC
        # Should be valid hex
        bytes.fromhex(sig)

    def test_sign_bid_ed25519_deterministic(self, monkeypatch):
        """Same inputs produce the same signature."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        priv, _addr = generate_keypair()
        sig1 = sign_bid("rover_1", "req_001", Decimal("1.50"), priv)
        sig2 = sign_bid("rover_1", "req_001", Decimal("1.50"), priv)
        assert sig1 == sig2


class TestVerifyBidEd25519:
    def test_verify_bid_ed25519_valid(self, monkeypatch):
        """A correctly signed bid verifies against the signer address."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        priv, addr = generate_keypair()
        sig = sign_bid("rover_1", "req_test_001", Decimal("1.50"), priv)
        bid = _make_bid(bid_hash=sig)
        assert verify_bid(bid, addr) is True

    def test_verify_bid_ed25519_tampered_price(self, monkeypatch):
        """Changing the price after signing causes verification to fail."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        priv, addr = generate_keypair()
        sig = sign_bid("rover_1", "req_test_001", Decimal("1.50"), priv)
        # Tamper: use the original signature but a different price
        tampered = _make_bid(price=Decimal("9.99"), bid_hash=sig)
        assert verify_bid(tampered, addr) is False

    def test_verify_bid_ed25519_wrong_key(self, monkeypatch):
        """Verifying against a different address fails."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        priv, _addr = generate_keypair()
        _other_priv, other_addr = generate_keypair()
        sig = sign_bid("rover_1", "req_test_001", Decimal("1.50"), priv)
        bid = _make_bid(bid_hash=sig)
        assert verify_bid(bid, other_addr) is False

    def test_verify_bid_ed25519_invalid_signature(self, monkeypatch):
        """A garbage signature returns False, not an exception."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        _priv, addr = generate_keypair()
        bid = _make_bid(bid_hash="deadbeef" * 16)
        assert verify_bid(bid, addr) is False


class TestSignVerifyRoundtrip:
    def test_sign_verify_roundtrip_ed25519(self, monkeypatch):
        """Full round-trip: generate key, sign bid, create Bid, verify."""
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        priv, addr = generate_keypair()
        robot_id = "tumbller_fi_01"
        request_id = "req_roundtrip_42"
        price = Decimal("0.75")
        sig = sign_bid(robot_id, request_id, price, priv)
        bid = Bid(
            request_id=request_id,
            robot_id=robot_id,
            price=price,
            sla_commitment_seconds=180,
            ai_confidence=0.88,
            capability_metadata={"sensors": ["temperature"]},
            reputation_metadata={"completion_rate": 0.95},
            bid_hash=sig,
        )
        assert verify_bid(bid, addr) is True


class TestHmacBackwardCompat:
    def test_hmac_still_works(self, monkeypatch):
        """With SIGNING_MODE=hmac, the original HMAC behavior is preserved."""
        monkeypatch.setattr(core, "SIGNING_MODE", "hmac")
        key = "test-secret-key-1234"
        robot_id = "rover_1"
        request_id = "req_hmac_001"
        price = Decimal("1.50")
        sig = sign_bid(robot_id, request_id, price, key)
        # HMAC-SHA256 produces a 64-char hex digest
        assert len(sig) == 64
        bid = _make_bid(
            robot_id=robot_id,
            request_id=request_id,
            price=price,
            bid_hash=sig,
        )
        assert verify_bid(bid, key) is True

    def test_hmac_tampered_fails(self, monkeypatch):
        """HMAC mode correctly rejects tampered bids."""
        monkeypatch.setattr(core, "SIGNING_MODE", "hmac")
        key = "test-secret-key-1234"
        sig = sign_bid("rover_1", "req_hmac_002", Decimal("1.50"), key)
        tampered = _make_bid(
            request_id="req_hmac_002",
            price=Decimal("9.99"),
            bid_hash=sig,
        )
        assert verify_bid(tampered, key) is False

    def test_dual_mode_switch(self, monkeypatch):
        """Switching SIGNING_MODE between calls works correctly."""
        priv, addr = generate_keypair()
        hmac_key = "shared-secret"

        # Sign in Ed25519 mode
        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        ed_sig = sign_bid("rover_1", "req_dual", Decimal("1.00"), priv)

        # Sign in HMAC mode
        monkeypatch.setattr(core, "SIGNING_MODE", "hmac")
        hmac_sig = sign_bid("rover_1", "req_dual", Decimal("1.00"), hmac_key)

        # They should be different (different algorithms, different keys)
        assert ed_sig != hmac_sig

        # Verify each with correct mode
        ed_bid = _make_bid(request_id="req_dual", price=Decimal("1.00"), bid_hash=ed_sig)
        hmac_bid = _make_bid(request_id="req_dual", price=Decimal("1.00"), bid_hash=hmac_sig)

        monkeypatch.setattr(core, "SIGNING_MODE", "ed25519")
        assert verify_bid(ed_bid, addr) is True

        monkeypatch.setattr(core, "SIGNING_MODE", "hmac")
        assert verify_bid(hmac_bid, hmac_key) is True
