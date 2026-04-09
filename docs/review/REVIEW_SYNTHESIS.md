# Demo UI Code Review — Synthesis

**Date:** 2026-04-09
**File reviewed:** `docs/mcp_demo_5/index.html` (~3,460 lines), `mcp_server.py`, `auction/mcp_tools.py`, `auction/mock_fleet.py`
**Agents:** 7 (Buyer Journey, Operator Registration, Frontend Code Quality, Backend Code Quality, Deployment & CI/CD, Admin Journey, Visual Design)

---

## Critical Findings (fix before next demo)

| # | Source | Issue | Impact |
|---|---|---|---|
| C1 | Buyer | `resetBtn()` re-enables "Hire Operator" during active auction with wrong label ("Run Auction"). User can fire parallel auctions. | Data corruption, double payment risk |
| C2 | Buyer | Duplicate `#stripeEmbedMount` ID — static and injected. `querySelector('.pay-btn-stripe')` grabs stale DOM. | Card/ACH payment mounts to wrong element |
| C3 | Buyer | `releasePayment()` has no double-click guard at function level. Selector fragility. | Double payment release |
| C4 | Frontend | Zero ARIA attributes in entire file. No `aria-live`, `role="dialog"`, `aria-label`. | Inaccessible to screen readers |
| C5 | Frontend | No focus management on phase transitions. Focus stays on invisible elements. | Keyboard users lost |

## High-Priority Findings (fix in current sprint)

| # | Source | Issue |
|---|---|---|
| H1 | Buyer | No form validation before `runAuction()` — empty RFP proceeds to API |
| H2 | Buyer | `runExecution()` doesn't check `response.ok` — HTTP errors swallowed |
| H3 | Buyer | `payWithUSDC()` uses `alert()` for wallet errors — breaks mobile |
| H4 | Buyer | ACH copy says "won't be charged until you approve" — factually wrong for ACH |
| H5 | Buyer | `showPaymentSuccess()` dead redirect code path renders broken settle phase |
| H6 | Buyer | No bid step → silent $0.50 fallback with dummy operator name |
| H7 | Registration | "Back to Payment & Bidding" on all-fail doesn't restore form section — empty view |
| H8 | Backend | No input validation on `auction_register_robot_onchain` — empty names, invalid emails, bad bid_pct all accepted |
| H9 | Backend | Unsynchronized mutations of `engine.robots` — no lock between registration and fleet discovery |
| H10 | Frontend | Unescaped server URLs in `href` attributes (receipt_url, 8004scan_url) — XSS / open redirect vector |
| H11 | Frontend | Race condition: mobile button not disabled before `showPhase()` — double auction on fast tap |
| H12 | Frontend | `runExecution()` callable from 3 payment paths with no re-entry guard |
| H13 | Frontend | All form inputs lack `<label for="...">` — screen readers can't identify fields |
| H14 | Frontend | `outline:none` on all inputs/buttons — no visible focus ring for keyboard nav |
| H15 | Frontend | 203 inline style attributes — presentation mixed into JS render functions |
| H16 | Frontend | Focus trap missing in modal dialogs (feed detail, feedback popup) |

## Medium-Priority Findings

| # | Source | Issue |
|---|---|---|
| M1 | Buyer | Duplicate Stripe publishable key fetch (2 network calls per payment) |
| M2 | Buyer | Feed detail divs accumulate in `<body>` — never cleaned on reset |
| M3 | Buyer | Hardcoded Stripe Connect ID fallback — silent charge to wrong account |
| M4 | Buyer | USDC domain `version` hardcoded to `'2'` — may not match all deployments |
| M5 | Buyer | Payment buttons don't go column on mobile — cramped layout |
| M6 | Buyer | QA FAIL leaves buyer with no action — UI stuck |
| M7 | Registration | Only `equipTypes[0]` sent to API — multi-select silently truncated |
| M8 | Registration | No per-step validation — errors only surface on final submit |
| M9 | Registration | Progress animation timeout can mark completed chain back to "pending" |
| M10 | Backend | Bare `next()` on SDK endpoints — `StopIteration` escapes exception handler |
| M11 | Backend | Duplicate fleet entry on repeated registration with same email |
| M12 | Backend | Discovery race — `_discovery_done` boolean guard not atomic |
| M13 | Backend | CORS `allow_origins` contains invalid wildcard patterns (dead weight) |
| M14 | Frontend | 24 globals + 16 `window._*` state properties — no encapsulation |
| M15 | Frontend | `auctionComplete` variable never set to `true` — dead state |
| M16 | Frontend | `--text-3: #6B7280` fails WCAG AA (4.48:1 on white) |
| M17 | Frontend | ethers.js + Stripe.js synchronously block HTML parse — no `defer` |
| M18 | Frontend | Subgraph URL map duplicated in global scope and submitRegistration() |

## Low-Priority Findings

| # | Source | Issue |
|---|---|---|
| L1 | Buyer | Feedback `request_id` always new timestamp — never links to task |
| L2 | Buyer | Duplicate `id="feedbackStatus"` in feedback popup |
| L3 | Buyer | `normalizeCase()` mangles acronyms (SLA→Sla, USDC→Usdc) |
| L4 | Buyer | `simulatorOnly` dual source of truth (var vs DOM) |
| L5 | Buyer | Eth Sepolia → Base Sepolia silent chain remap |
| L6 | Registration | Static header crumb `onclick` bypasses `_regHighest` guard |
| L7 | Registration | Empty "Other" model silently registers blank string |
| L8 | Registration | No validation that at least one payment channel selected |
| L9 | Registration | All chains inherit single `verified` boolean from first chain |
| L10 | Registration | Newly registered robot shows null wallet in sidebar |
| L11 | Registration | `resetBtn()` writes "Run Auction" instead of "Hire Operator" |
| L12 | Backend | SDK exception messages may leak RPC URLs or formatted keys |
| L13 | Backend | `asyncio.to_thread(_blocking_register)` not wrapped in try/except |
| L14 | Backend | SDK instances created per-chain with no `.close()` |
| L15 | Backend | Return value shape differs between error and success paths |
| L16 | Backend | `RuntimeRegisteredRobot._price = Decimal("1")` latent MRO bug |
| L17 | Frontend | `previewStars`/`resetStars` defined but hover handlers never wired |
| L18 | Frontend | `runDemo` alias is dead code |
| L19 | Frontend | `PLATFORM_WALLET` constant declared but never used |

---

## Top 10 Recommended Actions (ordered by impact)

1. **Add `threading.Lock` to fleet mutations** — prevents registration + discovery race. Backend, ~10 lines.

2. **Input validation on `auction_register_robot_onchain`** — reject empty names, invalid emails, bad bid_pct. Backend, ~15 lines.

3. **Fix `resetBtn()` label + disable parallel auction** — change text to "Hire Operator", add `_auctionRunning` flag. Frontend, ~10 lines.

4. **Remove duplicate `#stripeEmbedMount` ID** — delete static div, scope payment button selectors. Frontend, ~5 lines.

5. **Fix all-chains-fail error recovery** — restore `regFormSection` display when "Back to Payment" is clicked. Frontend, 1 line.

6. **Send all `equipTypes` to API** — change `equipment_type` to `equipment_types` (array), update backend to register all sensors. Frontend + backend, ~15 lines.

7. **Add ARIA attributes** — `role="alert"` on errorMsg, `role="status"` on progress, `aria-label` on buttons, `<label for>` on inputs. Frontend, ~40 lines across file.

8. **Replace `alert()` with `showError()`** — in `payWithUSDC()`. Frontend, 2 lines.

9. **Add `defer` to ethers.js and Stripe.js script tags** — reduces time-to-interactive by 1-3 seconds. Frontend, 2 characters.

10. **Fix ACH copy** — "won't be charged until you approve" is false for ACH. Change to "bank transfer initiated." Frontend, 1 string.

---

## Deployment & CI/CD Findings (Agent 5 — complete)

| # | Severity | Issue |
|---|---|---|
| D1 | HIGH | Both Dockerfiles run as root — no non-root user |
| D2 | MEDIUM | `COPY . .` before `uv sync` busts layer cache on every code change |
| D3 | MEDIUM | Fleet Dockerfile clones unpinned GitHub HEAD at build time |
| D4 | MEDIUM | No automated deployment on merge — all deploys manual |
| D5 | MEDIUM | No rollback mechanism in any deploy script |
| D6 | MEDIUM | Fly.io marketplace secrets not documented |
| D7 | MEDIUM | No dependency vulnerability scan in CI |
| D8 | MEDIUM | Slug-to-URL mapping scattered — no single registry |
| D9 | LOW | Python 3.14-slim (pre-release) in Dockerfiles |
| D10 | LOW | `uv:latest` not pinned in Docker |
| D11 | LOW | `agent0-sdk>=0.1` floor-only version constraint |
| D12 | LOW | Ruff in CI covers `auction/` only — root `.py` files excluded |
| D13 | LOW | `sed -i ''` in deploy-demo.sh fails on Linux/CI |

**Key deployment recommendation:** Create `scripts/deploy-marketplace.sh` with secret verification (like `deploy-worker.sh`) and a slug registry file `docs/SLUG_REGISTRY.yaml` as single source of truth for which slug serves which URL.

## Admin Journey Findings (Agent 6 — complete)

| # | Severity | Issue |
|---|---|---|
| A1 | CRITICAL | Switching to "Production" mode does NOT change Stripe key — backend worker controls this regardless of UI dropdown selection. Risk of accidental live payment in test mode or vice versa. |
| A2 | HIGH | Auction prompt uses unfiltered `discoveredRobots`, not `getFilteredRobots()` — Claude references FakeRovers even when "Hide FakeRovers" is checked |
| A3 | HIGH | FakeRover-registered robot disappears from sidebar on filter toggle but may still bid — filter deferred to next discovery cycle |
| A4 | HIGH | Admin passcode `"robotadmin"` plaintext in client JS (expected for demo, needs documentation) |
| A5 | MEDIUM | Auto-detection in `renderRobotsSidebar()` silently overrides manual "Production" selection after filter toggle |
| A6 | MEDIUM | Both filters unchecked — no UI explanation of "show all" mode; help text inaccurate |
| A7 | MEDIUM | Base Sepolia robots link to wrong explorer (etherscan instead of sepolia.basescan); 8004scan path hardcoded to `base/` |
| A8 | MEDIUM | Clearing admin passcode silently prepends `FakeRover-` to already-typed custom name |
| A9 | MEDIUM | No UI feedback that mid-auction filter toggle only takes effect on next auction |
| A10 | MEDIUM | `/health` returns fleet=0 before first auction with no indication this is expected |

## Updated Totals

| Severity | Count |
|---|---|
| **Critical** | 7 (Buyer 3, Frontend 2, Admin 1, +1 Production mode) |
| **High** | 20 |
| **Medium** | 34 |
| **Low** | 27 |
| **Total** | **88 findings** |

## Visual Design Findings (Agent 7 — complete)

| # | Severity | Issue |
|---|---|---|
| V1 | HIGH | `#FEE2E2` / `#FECACA` error colors hardcoded 3+ times — no `--red-bg` / `--red-border` variables |
| V2 | HIGH | `.robot-name` and `.robot-chain` have inline styles that duplicate existing class rules verbatim |
| V3 | MEDIUM | ACH button green `#1a6b47` hardcoded in 3 places — needs `--ach` variable |
| V4 | MEDIUM | 5 inline-overridden small buttons in JS strings — need `.btn-sm` class |
| V5 | MEDIUM | Admin key input `padding:5px` off the 4px grid |
| V6 | MEDIUM | 3 badge systems not consolidated (`.badge`, `.qa-badge`, inline registration badges) |
| V7 | MEDIUM | `rgba(26,125,78,0.2)` hardcodes `--green` value numerically instead of using a variable |
| V8 | LOW | 3 dead CSS variables: `--radius-lg`, `--border-focus`, `--accent-light` |
| V9 | LOW | `.card-label` rules re-implemented inline in JS at 3 locations |
| V10 | LOW | 203 inline `style=""` attributes; ~15 repeating patterns should be utility classes |

**Key design recommendation:** Add `--red-bg`, `--red-border`, `--ach`, `--ach-hover` to `:root`. Create `.btn-sm` and `.field-hint` utility classes. Consolidate badge systems. Remove 3 dead variables.

**Error display note:** Errors use 3 different patterns: (1) `#errorMsg` banner at top of main, (2) `alert()` in USDC flow, (3) inline red blocks in registration progress. These should be consolidated into one pattern — the `#errorMsg` banner — with a "Copy error" button and optional "Submit as GitHub issue" link (reusing the existing `openFeedbackIssue()` pattern).

---

## Final Totals

| Severity | Count |
|---|---|
| **Critical** | 7 |
| **High** | 23 |
| **Medium** | 40 |
| **Low** | 30 |
| **Total** | **100 findings** |

---

## Top 15 Recommended Actions (final, ordered by impact)

### Immediate (before next demo)

1. **Add `threading.Lock` to fleet mutations** — prevents registration + discovery race condition. Backend, ~10 lines. (H9, Backend)

2. **Input validation on `auction_register_robot_onchain`** — reject empty names, invalid emails, bad bid_pct. Backend, ~15 lines. (H8, Backend)

3. **Fix `resetBtn()` label + disable parallel auction** — change text to "Hire Operator", add `_auctionRunning` flag, disable mobile button simultaneously. Frontend, ~10 lines. (C1, H11)

4. **Remove duplicate `#stripeEmbedMount` ID** — delete static div, scope payment button selectors to `#commitSlot`. Frontend, ~5 lines. (C2)

5. **Fix all-chains-fail error recovery** — restore `regFormSection` display when "Back to Payment" clicked. Frontend, 1 line. (H7)

### Current sprint

6. **Send all `equipTypes` to API** — change `equipment_type` to `equipment_types` array, update backend to register all sensors. Frontend + backend, ~15 lines. (M7)

7. **Add ARIA attributes** — `role="alert"` on errorMsg, `role="status"` on progress, `aria-label` on buttons, `<label for>` on inputs. Frontend, ~40 lines. (C4, C5, H13, H14, H16)

8. **Replace `alert()` with `showError()`** in `payWithUSDC()`. Frontend, 2 lines. (H3)

9. **Add `defer` to ethers.js and Stripe.js** — reduces time-to-interactive. Frontend, 2 chars. (M17)

10. **Fix ACH copy** — "won't be charged until you approve" is false for ACH. Frontend, 1 string. (H4)

11. **Add `--red-bg`, `--red-border`, `--ach` CSS variables** — replace all hardcoded error/ACH colors. Frontend, ~10 lines. (V1, V3)

12. **Use `getFilteredRobots()` in auction prompt** — not raw `discoveredRobots`. Frontend, 1 line. (A2)

13. **Add Dockerfile non-root user** — `RUN useradd` + `USER appuser`. Deployment, 2 lines. (D1)

### Next sprint

14. **Consolidate error display** — one pattern (`#errorMsg` banner) with copy button and GitHub issue link. Replace `alert()`, inline red blocks, and status-on-button patterns. Frontend, ~30 lines.

15. **Create slug registry file** — `docs/SLUG_REGISTRY.yaml` as single source of truth for which slug serves which URL. Replace hardcoded slugs in deploy scripts. Deployment, new file + script updates.
