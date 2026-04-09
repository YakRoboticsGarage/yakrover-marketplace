# Development Strategy — Code Safety & Testing for Real Money

**Date:** 2026-03-27 (updated 2026-04-09)
**Status:** Active. v1.3 shipped with 284 tests, 35 MCP tools. Next: v1.4 (operator registration frontend). v1.5 (settlement abstraction) gated on v1.4.
**Applies to:** yakrover-marketplace, yakrover-8004-mcp, and all marketplace repos

> This project handles real money (Stripe charges, USDC on Base). Code that touches payments, escrow, or wallet operations must meet a higher bar than typical application code. This document defines the development practices, testing strategy, and tooling that enforce that bar.

---

## Current State (Gaps)

| Area | Status | Risk |
|------|--------|------|
| **Test suite** | 151 tests, 3,723 lines across 10 files | Good coverage of auction logic; weak on payment edge cases |
| **Stripe testing** | Mock-only (`unittest.mock.patch`) | No test-mode API validation — mocks can drift from real Stripe behavior |
| **USDC/blockchain testing** | None | No escrow contract tests, no on-chain settlement tests |
| **CI/CD** | None (manual `pytest` only) | Broken code can be pushed to main unchecked |
| **Linting/type checking** | None configured | Type errors in payment code are silent |
| **Secret protection** | `.gitignore` for `.env` only | No automated detection of leaked keys in code |
| **Integration testing** | `test_integration_v10.py` (mock fleet) | No tests against real robot fleet or real Stripe test mode |
| **Code review** | No PR process enforced | Direct push to main |

---

## 1. Testing Strategy (Layered)

### Layer 1: Unit Tests (existing, strengthen)

What's here: 151 tests covering auction engine, scoring, state machine, wallet ledger, signing, reputation, and Stripe service (mocked).

**Gaps to fill for v1.5:**

| Missing Test Area | Why It Matters | Priority |
|---|---|---|
| Settlement abstraction interface | Core architectural piece — must verify all 4 modes route correctly | Must |
| Commitment hash generation/verification | Cryptographic correctness — wrong hash = broken audit trail | Must |
| Escrow state machine (deposit/hold/release/refund) | Real money locked in contract — every edge case matters | Must |
| x402 middleware payment verification | Facilitator sees wrong amount = free robot services | Must |
| Robot ID → wallet address resolution | Wrong address = payment sent to wrong operator | Must |
| Encrypted task spec round-trip | Encrypt → store → retrieve → decrypt must be lossless | Should |
| Payment method routing (Stripe vs USDC) | Wrong path = failed settlement | Must |

**Property-based tests** (hypothesis is already a dependency — use it):
- `score_bids()` with randomized bids: winner always has highest composite score
- Wallet ledger: sum of debits + credits always equals balance
- Commitment hash: `H(request_id || salt)` is deterministic for same inputs, unique for different inputs
- Escrow state machine: no valid sequence of operations produces negative escrow balance

### Layer 2: Stripe Test-Mode Integration Tests

**Problem:** Current tests mock the Stripe SDK. Mocks can drift from real API behavior — you already discovered this when German Stripe accounts reject USD currency.

**Solution:** A separate test suite that calls real Stripe test-mode APIs.

```
auction/tests/
├── test_*.py                    # Unit tests (mocked, fast, CI)
└── integration/
    ├── test_stripe_live.py      # Real Stripe test-mode API calls
    ├── test_stripe_connect.py   # Real Connect Express onboarding flow
    ├── test_stripe_webhooks.py  # Webhook signature verification
    └── conftest.py              # Fixtures: test accounts, API keys from env
```

**What these tests verify:**
- `PaymentIntent.create()` with real test cards succeeds
- `Transfer.create()` to a real Connect Express test account succeeds
- Webhook signatures validate with Stripe's test signing secret
- Currency handling: EUR for EU accounts, USD for US accounts
- Edge: expired authorization (7-day hold), declined card, insufficient funds
- Edge: Stripe rate limits (429 response handling)

**Run with:** `uv run pytest auction/tests/integration/ -m stripe --tb=short`
**Requires:** `STRIPE_SECRET_KEY` set to a test-mode key (`sk_test_...`)
**NOT run in CI** (requires secrets) — run manually before releases

### Layer 3: On-Chain Integration Tests (new for v1.5)

**What these test:**
- `RobotTaskEscrow.sol` deployment on Base Sepolia
- USDC deposit into escrow, hold during task, release to operator
- Commitment hash embedded correctly in transaction memo
- Escrow refund on task failure/timeout
- Gas estimation accuracy (don't run out of gas mid-settlement)

**Tooling:** Foundry (`forge test`) for Solidity contract tests + Python integration tests using `web3.py` against Base Sepolia.

**Run with:** `forge test` (Solidity unit) + `uv run pytest auction/tests/integration/test_base_settlement.py`
**Requires:** `BASE_SEPOLIA_RPC_URL`, funded test wallet on Base Sepolia

### Layer 4: Real Robot Network Integration Test

**This is the most important gap.** The marketplace has never been tested end-to-end with a real robot completing a real task and receiving real (test-mode) payment.

**What this test verifies:**
1. Claude (as agent) posts a real task via MCP tool call
2. Real robot fleet (tumbller or fakerover on real server) discovers the task
3. Robot bids autonomously via `bid()` plugin method
4. Auction scores and selects winner
5. Robot executes task (sensor reading via HTTP to real hardware)
6. Agent verifies delivery
7. Stripe test-mode payment settles to operator's Connect account
8. Audit trail: `request_id` → commitment hash → Stripe metadata all link correctly

**Setup needed:**
- A persistent test fleet server (the ngrok URL from yakrover-8004-mcp)
- A funded Stripe test-mode buyer account
- A Stripe Connect Express test operator account
- The fakerover simulator running (or real tumbller if available)

**Run cadence:** Before every version release. This is the "smoke test that matters."

**Document as:** `auction/tests/integration/test_e2e_real_fleet.py`

### Layer 5: Adversarial / Chaos Tests (v2.0+)

For when real money is flowing:
- Robot goes offline mid-task — verify escrow refunds correctly
- Double-bid from same robot — verify deduplication
- Tampered bid signature — verify rejection
- Stripe webhook delivered twice — verify idempotent handling
- Database crash during settlement — verify recovery
- x402 facilitator timeout — verify graceful degradation

---

## 2. CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - run: uv run pytest auction/tests/ -q --tb=short -x
        # -x stops on first failure (fast feedback)

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - run: uv run mypy auction/ --ignore-missing-imports

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - run: uv run ruff check auction/ src/

  # Integration tests run manually or on release tags only
  stripe-integration:
    if: github.event_name == 'workflow_dispatch' || startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - run: uv run pytest auction/tests/integration/ -m stripe -q
        env:
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_TEST_KEY }}
```

### Branch Protection (once CI is set up)

- Require PR for all pushes to `main`
- Require unit tests + lint + type-check to pass
- Require at least 1 review for payment-related files

---

## 3. Code Quality Tooling

### Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.0",
    "pytest-cov>=6.0",
    "hypothesis>=6.0",
    "ruff>=0.9",
    "mypy>=1.14",
]

[tool.ruff]
target-version = "py313"
line-length = 120

[tool.ruff.lint]
select = [
    "E", "W",    # pycodestyle
    "F",          # pyflakes
    "I",          # isort
    "S",          # bandit (security)
    "B",          # bugbear
    "C4",         # comprehensions
    "UP",         # pyupgrade
]

[tool.ruff.lint.per-file-ignores]
"auction/tests/*" = ["S101"]  # allow assert in tests

[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true  # strict for payment code

[[tool.mypy.overrides]]
module = "stripe.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "strict"
markers = [
    "stripe: requires STRIPE_SECRET_KEY for live Stripe test API calls",
    "blockchain: requires BASE_SEPOLIA_RPC_URL for on-chain tests",
    "fleet: requires running fleet server for robot integration tests",
]
addopts = "--strict-markers"
```

Key points:
- **ruff `S` rules** = bandit security linting — catches hardcoded passwords, SQL injection, insecure random
- **mypy `disallow_untyped_defs`** = forces type annotations on all functions — catches type confusion in payment amounts
- **pytest markers** = clearly separate fast unit tests from slow integration tests

---

## 4. Claude Code Configuration

### CLAUDE.md Updates for yakrover-marketplace

The existing CLAUDE.md (in the archive) is framework-level. The marketplace repo needs payment-specific instructions:

```markdown
## Payment Code Rules

- NEVER hardcode Stripe API keys, USDC private keys, or wallet addresses in source code
- ALL payment operations must be idempotent — handle retries safely
- Stripe test mode (`sk_test_*`) for all development; live keys ONLY in production env
- Every payment state change must be logged to the audit trail (SQLite `audit_log` table)
- Webhook handlers MUST verify Stripe signatures before processing
- On-chain transactions MUST use commitment hash (FD-4), never raw request_id

## Testing Requirements

- Run `uv run pytest auction/tests/ -q` before committing payment code changes
- Run `uv run ruff check auction/` before committing any changes
- Payment-related PRs require integration test results (Stripe test mode)
- New payment features require both happy-path and failure-path tests

## Key Commands

uv sync --all-extras          # Install all dependencies
uv run pytest auction/tests/ -q --tb=short    # Fast unit tests
uv run pytest -m stripe       # Stripe integration (needs STRIPE_SECRET_KEY)
uv run pytest -m blockchain   # On-chain tests (needs BASE_SEPOLIA_RPC_URL)
uv run ruff check auction/ src/               # Lint
uv run mypy auction/          # Type check
```

### Claude Code Hooks

Configure in `.claude/settings.json`:

**1. Run tests after payment code changes:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "FILE=$(cat | jq -r '.tool_input.file_path // empty'); if echo \"$FILE\" | grep -qE '(payment|stripe|escrow|wallet|settlement)'; then echo '⚠ Payment code changed — run tests' >&2; fi; exit 0"
          }
        ]
      }
    ]
  }
}
```

**2. Block secrets in code files:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "CONTENT=$(cat | jq -r '.tool_input.content // empty'); if echo \"$CONTENT\" | grep -qiE '(sk_live_|sk_test_|0x[a-fA-F0-9]{64}|PRIVATE.KEY)'; then echo 'BLOCKED: Content contains what looks like a secret key' >&2; exit 2; fi; exit 0"
          }
        ]
      }
    ]
  }
}
```

---

## 5. Real Fleet Testing Setup

### What's needed

| Component | Current State | What to Set Up |
|-----------|--------------|----------------|
| **Fleet server** | yakrover-8004-mcp runs locally | Deploy persistent instance (ngrok static domain or cloud VM) |
| **Test robot** | fakerover simulator available | Run fakerover 24/7 on the fleet server; optionally connect real tumbller |
| **Stripe buyer account** | Test mode keys exist | Create a dedicated test buyer with funded wallet |
| **Stripe operator account** | Connect Express test account exists | Verify it can receive transfers |
| **Base Sepolia wallet** | Not set up for marketplace | Fund a test wallet with Sepolia ETH + test USDC |
| **MCP connection** | `.mcp.json` templates exist | Configure Claude Code to connect to test fleet |

### Test Fleet Architecture

```
Claude Code (agent)
    │
    ├── .mcp.json → fleet server (ngrok or localhost)
    │                    │
    │                    ├── /fleet/mcp (auction tools)
    │                    ├── /fakerover/mcp (simulator)
    │                    └── /tumbller/mcp (real hardware, when available)
    │
    ├── Stripe test mode (sk_test_...)
    │       ├── PaymentIntent → buyer wallet top-up
    │       └── Transfer → operator Connect account
    │
    └── Base Sepolia
            ├── RobotTaskEscrow.sol (deployed)
            └── USDC test tokens (faucet)
```

### Integration Test Sequence

```python
# auction/tests/integration/test_e2e_real_fleet.py

@pytest.mark.fleet
async def test_full_lifecycle_with_real_fleet():
    """
    End-to-end: post task → auction → execute on real fleet → settle via Stripe.
    Requires: running fleet server, STRIPE_SECRET_KEY, funded buyer wallet.
    """
    # 1. Fund buyer wallet (Stripe test mode)
    wallet = await fund_test_wallet(amount_cents=2500)

    # 2. Post task via MCP
    task = await mcp_call("auction_post_task", {
        "description": "Temperature reading, Bay 3",
        "capability_requirements": {"hard": {"sensors_required": ["temperature"]}},
        "budget_ceiling": "2.00",
        "sla_seconds": 300,
    })

    # 3. Collect bids (real robots respond)
    bids = await mcp_call("auction_get_bids", {"request_id": task["request_id"]})
    assert len(bids["bids"]) >= 1, "No bids from fleet"

    # 4. Accept best bid
    result = await mcp_call("auction_accept_bid", {"request_id": task["request_id"]})
    assert result["status"] == "bid_accepted"

    # 5. Execute task (robot reads sensor)
    execution = await mcp_call("auction_execute", {"request_id": task["request_id"]})

    # 6. Confirm delivery
    confirmation = await mcp_call("auction_confirm_delivery", {
        "request_id": task["request_id"]
    })
    assert confirmation["status"] == "settled"

    # 7. Verify Stripe transfer
    assert confirmation["payment"]["transfer_id"].startswith("tr_")

    # 8. Verify audit trail
    status = await mcp_call("auction_get_status", {"request_id": task["request_id"]})
    assert status["state"] == "settled"
    assert "commitment_hash" in status  # FD-4
```

---

## 6. Roadmap Integration

### v1.5 Additions (development infrastructure)

| Item | Effort | Impact |
|------|--------|--------|
| Add ruff + mypy to pyproject.toml and CI | 2 hours | Catches bugs before they reach payment code |
| GitHub Actions workflow (unit + lint + type-check) | 4 hours | Every push verified automatically |
| Stripe integration test suite (5-8 tests) | 1 day | Validates real Stripe behavior, not just mocks |
| Base Sepolia escrow test suite (Foundry + Python) | 1 day | Validates on-chain settlement before mainnet |
| Settlement abstraction unit tests | 4 hours | Verifies routing logic for all 4 modes |
| Commitment hash property tests (hypothesis) | 2 hours | Cryptographic correctness |
| CLAUDE.md with payment safety rules | 1 hour | Every Claude session starts with safety context |

### v2.0 Additions

| Item | Effort | Impact |
|------|--------|--------|
| Real fleet integration test (fakerover + Stripe) | 2 days | First true end-to-end with real robots + real payments |
| Branch protection on main | 1 hour | No unreviewed payment code reaches main |
| Webhook idempotency tests | 4 hours | Prevents double-charge on retry |
| TEE encrypted matching tests | 1 day | Verifies encryption round-trip for Diane's story |
| Chaos/adversarial test suite | 2 days | Robot offline, double-bid, tampered signature scenarios |
| Coverage gating (>80% for payment code) | 2 hours | Ensures payment paths are tested |

### Pre-Mainnet Checklist (before live Stripe + Base mainnet)

- [ ] All Stripe integration tests pass against test-mode API
- [ ] Escrow contract audited (at minimum: internal review + Foundry fuzzing)
- [ ] Webhook signature verification tested with real Stripe webhook events
- [ ] On-chain commitment hash verified on Base Sepolia explorer
- [ ] Real fleet e2e test completes with actual robot + Stripe test payment
- [ ] No hardcoded keys in source (automated grep in CI)
- [ ] Rate limit handling tested (Stripe 429, Base RPC throttling)
- [ ] Error recovery tested: what happens when Stripe is down? When Base RPC is down?
- [ ] Wallet balance never goes negative under any test scenario
- [ ] Escrow balance never goes negative under any test scenario
- [ ] Gas estimation tested with 20% safety margin

---

## 7. Recommended MCP Configuration

Update `.mcp.json` for the marketplace development setup:

```json
{
  "mcpServers": {
    "test-fleet": {
      "type": "http",
      "url": "http://localhost:8001/fleet/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_BEARER_TOKEN}"
      }
    },
    "fakerover": {
      "type": "http",
      "url": "http://localhost:8080/fakerover/mcp"
    }
  }
}
```

For remote fleet testing (when real tumbller is available):
```json
{
  "mcpServers": {
    "finland-fleet": {
      "type": "http",
      "url": "https://${NGROK_DOMAIN}/fleet/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_BEARER_TOKEN}"
      }
    }
  }
}
```

---

## Summary: What Changes Now vs Later

| Now (v1.5 build start) | Before mainnet | v2.0+ |
|---|---|---|
| Add ruff + mypy | Stripe integration tests pass | Real fleet e2e test |
| GitHub Actions CI | Escrow Foundry fuzz tests | Chaos test suite |
| CLAUDE.md payment rules | No hardcoded keys (CI grep) | Coverage gating |
| Settlement abstraction tests | Webhook idempotency verified | Branch protection |
| Commitment hash property tests | Real fleet smoke test | Adversarial tests |
| Hooks for secret detection | Gas estimation validated | TEE matching tests |
