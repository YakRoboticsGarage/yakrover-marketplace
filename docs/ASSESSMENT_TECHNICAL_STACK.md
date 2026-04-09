# Technical Stack Assessment & Architecture Recommendation

**Date:** 2026-04-09
**Scope:** Robot Task Auction Marketplace (yakrover-marketplace)
**Current state:** v1.4 shipped. 36 MCP tools. On-chain ERC-8004 registration. 3-method payment. Demo at yakrobot.bid/demo.

---

## Current Stack Summary

| Layer | Technology | Maturity | Risk |
|---|---|---|---|
| **Backend** | Python 3.14 + FastMCP 3.1 + Starlette + uvicorn | Beta runtime (3.14), stable framework | Medium — beta deps (`stripe 15.1.0b1`, `pydantic 2.13.0b2`, `eth-account 0.14.0b1`) |
| **Frontend** | Vanilla JS, single 3,500-line HTML file | No framework, no build step | High at scale — works for demo, doesn't scale to multi-page product |
| **Hosting** | Fly.io (always-on), Cloudflare Workers (API proxy), here.now (static) | Stable, cost-effective | Low |
| **Blockchain** | agent0-sdk 1.7.1 + ERC-8004 on Base/Ethereum | SDK still pre-1.0 semantically | Medium — SDK breaking changes possible |
| **Payments** | Stripe Connect Express + EIP-3009 USDC on Base | Production-grade for Stripe, experimental for USDC | Low (Stripe), Medium (USDC relay) |
| **Data** | SQLite in-memory (demo) / file (production) | Simple, no ops burden | Works to ~100 concurrent users |
| **CI/CD** | GitHub Actions (test only) + manual deploy scripts | Functional but no CD | Medium — drift risk between code and deployment |

---

## What Works Well

**1. Single MCP server as the universal API.** The 36-tool MCP server is the single backend. The demo page, Claude Code, Claude Desktop, and any MCP client all call the same tools. This is architecturally clean — one API surface, multiple frontends.

**2. On-chain identity as the source of truth.** Robots exist on ERC-8004. The marketplace discovers them via The Graph subgraph. Registration writes to the chain. This means robots are portable — they're not locked into this marketplace.

**3. Payment method flexibility.** Card, ACH, and USDC through one checkout flow. The payment method translation architecture (buyer pays one way, operator gets paid another) is the right abstraction.

**4. Fly.io + Cloudflare Workers split.** The MCP server (stateful, long-running) runs on Fly.io. The payment/chat proxy (stateless, edge) runs on Cloudflare Workers. Each service runs where it's best suited.

**5. SQLite as the persistence layer.** For the current scale (demo, <10 concurrent users), SQLite with WAL mode is ideal. Zero ops. No database server. File-backed persistence just works.

---

## What Needs to Change for Production

### Frontend — the 3,500-line single file is the biggest risk

The demo HTML file has grown organically to 3,500 lines with 36 MCP tools, 5 buyer phases, 3 registration steps, 3 payment flows, fleet management, on-chain verification, and an activity feed. It works, but:

- **No component reuse.** Every card, button group, and kv-row is duplicated in JS string templates. Changes require find-and-replace across innerHTML strings.
- **No type safety.** All state is in global `var` declarations and `window._*` properties. A typo in a property name fails silently.
- **No routing.** Phase switching is DOM show/hide. URL doesn't change. You can't link to a specific phase or share state.
- **No testing.** The frontend has zero tests. Every change is manually verified.

**Recommendation:** For the next version (v1.5), extract the demo into a lightweight framework:

| Option | Pros | Cons | Recommended? |
|---|---|---|---|
| **Next.js (React)** | Largest ecosystem, SSR for SEO, component model, TypeScript | Heavy, complex build pipeline, React learning curve | No — overkill for a demo/marketplace |
| **Astro + Islands** | Static by default, ship zero JS for content pages, use React/Vue only where needed | Newer, smaller community | Maybe — good for content-heavy pages (pitch, yaml explorer) |
| **SvelteKit** | Tiny bundle, no virtual DOM, built-in routing, TypeScript | Smaller ecosystem than React | **Yes** — best fit for interactive app with real-time updates |
| **Vanilla + Web Components** | No framework, progressive enhancement | Limited tooling, still manual state management | No — we've hit the ceiling of this approach |
| **htmx + server templates** | Server-rendered, minimal JS, works with Python backend | Limited client-side interactivity, not great for real-time | No — the payment/wallet flows need rich client-side JS |

**SvelteKit recommendation rationale:**
- The app is interactive (payment flows, wallet connections, real-time auction updates) — needs a real client-side framework
- SvelteKit's compiled output is tiny (~20KB for a complex app vs ~150KB for React)
- Built-in file-based routing solves the URL/phase problem
- TypeScript support catches the global state bugs
- Can deploy to Cloudflare Pages (edge) or Fly.io
- The ethers.js and Stripe.js integrations work identically in Svelte

### Backend — stable, needs minor hardening

The Python backend is solid. The MCP tool pattern is clean. Recommendations:

**1. Pin beta dependencies.** `stripe 15.1.0b1`, `pydantic 2.13.0b2`, and `eth-account 0.14.0b1` are all pre-release. Either pin to specific versions or switch to stable releases when available. `uv.lock` provides reproducibility, but pre-release deps can introduce breaking changes on `uv sync`.

**2. Add request-level error boundaries.** The `handle_tool_call` REST handler doesn't catch exceptions from the tool dispatch. If a tool raises an unhandled exception, Starlette returns a 500 with a Python traceback. Wrap the dispatch in a try/except that returns a structured JSON error.

**3. Migrate to Postgres when concurrent users exceed ~50.** SQLite with WAL handles concurrent reads well but has a single-writer lock. For a marketplace with multiple operators bidding simultaneously, Postgres (or Turso for edge SQLite) is the next step. The `SyncTaskStore` abstraction makes this a clean swap.

**4. Add structured logging.** The current `log()` function writes to stdout. For production, use structured JSON logging (e.g., `structlog`) so Fly.io log aggregation can filter by tool name, request ID, and error severity.

### Hosting — add CD and staging

**1. Automated deployment on merge.** Add a `deploy` job to GitHub Actions that runs `fly deploy` after tests pass on `main`. Use `FLY_API_TOKEN` as a repo secret. This eliminates drift between merged code and deployed code.

**2. Staging environment.** Create a second Fly.io app (`yakrover-marketplace-staging`) with its own domain. PRs get previewed there before merging. The cost is ~$0/month (scale-to-zero).

**3. Worker deployment.** Add `wrangler deploy` to the CI pipeline. Currently the worker is deployed manually with `scripts/deploy-worker.sh`.

### Blockchain — stable, monitor SDK updates

The `agent0-sdk` is the key external dependency. It controls how robots are registered, discovered, and verified. Recommendations:

**1. Pin SDK version.** `agent0-sdk>=0.1` allows any version. Pin to `~=1.7` (compatible release) to prevent accidental major version upgrades.

**2. Abstract the SDK interface.** Currently the SDK is called directly in `mcp_tools.py` and `mcp_server.py`. Create a `ChainService` class that wraps registration, discovery, and feedback. This isolates SDK changes to one file.

**3. Multi-chain gas monitoring.** The signer wallet needs ETH on 4 chains. Add a health check that reports per-chain balance and alerts when any drops below a threshold.

### Payments — production-ready with one gap

Stripe is production-grade. USDC payment is functional but the relay wallet pattern has a single point of failure (one hot wallet with a private key in env vars). Recommendations:

**1. Relay wallet monitoring.** Alert when the relay wallet's ETH balance drops below 0.005 ETH on any chain.

**2. Consider Stripe stablecoin payouts.** Stripe Connect now supports USDC payouts to US sole-proprietor operators. This would let operators receive USDC without the marketplace operating its own relay wallet — Stripe handles the conversion.

**3. Webhook verification.** The Cloudflare Worker verifies Stripe webhook signatures, but there's no retry mechanism for failed webhook deliveries. Add idempotency keys and a webhook event log.

---

## Recommended Architecture for v1.5+

```
                     ┌─────────────────────────────┐
                     │      yakrobot.bid            │
                     │   (Cloudflare Pages / Edge)  │
                     │                              │
                     │   SvelteKit App              │
                     │   ├── /demo (auction flow)   │
                     │   ├── /register (operator)   │
                     │   ├── /yaml (product brief)  │
                     │   └── /pitch (deck)          │
                     └──────────┬──────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              ┌─────▼─────┐ ┌──▼──────┐ ┌─▼──────────┐
              │ MCP Server │ │ Worker  │ │ Stripe API │
              │ (Fly.io)   │ │ (CF)    │ │            │
              │            │ │         │ │ PaymentInt │
              │ 36 tools   │ │ /api/*  │ │ Connect    │
              │ SQLite/PG  │ │ Relay   │ │ ACH        │
              │ Discovery  │ │ USDC tx │ │            │
              └─────┬──────┘ └────┬────┘ └────────────┘
                    │             │
              ┌─────▼─────────────▼─────┐
              │   Base / Ethereum       │
              │   ERC-8004 Registry     │
              │   USDC Transfers        │
              │   The Graph Subgraph    │
              └─────────────────────────┘
```

### Migration path

| Phase | What | Effort |
|---|---|---|
| **v1.5a** | Extract demo HTML into SvelteKit skeleton. Keep all logic, just restructure into components. | 1-2 weeks |
| **v1.5b** | Add TypeScript types for auction state, payment flows, registration. | 1 week |
| **v1.5c** | Deploy SvelteKit to Cloudflare Pages. Retire here.now for the main app. Keep here.now for pitch/yaml. | 1 day |
| **v1.5d** | Add GitHub Actions CD for Fly.io + Cloudflare. | 1 day |
| **v2.0** | Migrate SQLite → Postgres (Fly.io Postgres or Neon). Add structured logging. | 1 week |

### What NOT to change

- **MCP server architecture.** The 36-tool FastMCP server is the right pattern. Don't replace it with a REST API — MCP is the protocol layer for agent interaction.
- **Fly.io + Cloudflare Workers split.** This is the right hosting model. Don't consolidate onto one platform.
- **SQLite for now.** Don't migrate to Postgres until you actually hit the concurrent-writer limit. Premature database migration adds ops burden.
- **Single-file Python tools.** `mcp_tools.py` is 1,500 lines but well-organized by section. Don't split it into 36 files — the current structure is easier to search and maintain.
- **ERC-8004 on-chain identity.** This is the differentiator. Don't move to a centralized registry. The on-chain identity is what makes robots portable.

---

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Beta Python deps break on update | Medium | High | Pin versions, test before updating |
| Single-file frontend becomes unmaintainable | High | Medium | SvelteKit migration in v1.5 |
| Relay wallet key compromised | Low | Critical | Monitor wallet, rotate key, consider Stripe stablecoin payouts |
| agent0-sdk breaking change | Medium | High | Pin version, abstract behind ChainService |
| SQLite lock contention at scale | Low (current), High (v2.0+) | Medium | Migrate to Postgres when >50 concurrent users |
| No CD pipeline → deployment drift | Medium | Medium | Add GitHub Actions deploy job |

---

## Summary

The stack is well-chosen for the current stage (demo → first customers). The biggest technical debt is the single-file frontend, which should be the first thing to address in v1.5. The backend, hosting, and blockchain layers are solid and don't need fundamental changes — just hardening (pinned versions, error boundaries, CD pipeline).

The recommended path: **SvelteKit frontend → CD pipeline → Postgres when you need it.**
