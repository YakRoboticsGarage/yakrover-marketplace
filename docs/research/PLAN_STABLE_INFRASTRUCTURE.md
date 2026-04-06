# Plan: Stable Infrastructure — From "5 Terminals" to "Always On"

**Date:** 2026-04-06
**Status:** Partially complete — Fly.io deployed, remaining issues below
**Goal:** Demo runs without anyone at a terminal. Visitor opens yakrobot.bid/mcp-demo-3, everything works.

---

## Current fragility audit

### What requires a human at a terminal right now

| Component | Runs on | Lifetime | What breaks when it dies |
|-----------|---------|----------|--------------------------|
| Fakerover simulator (:8080) | Rafa's laptop | Until terminal closes | FakeRover execution fails |
| Robot MCP server (:8000) | Rafa's laptop | Until terminal closes | All robot bids + execution fail |
| Cloudflared → :8000 (fleet) | Rafa's laptop | Random URL, dies with terminal | On-chain MCP endpoints go stale |
| Marketplace MCP server (:8001) | Rafa's laptop | Until terminal closes | Entire auction pipeline fails |
| Cloudflared → :8001 (marketplace) | Rafa's laptop | Random URL, dies with terminal | Demo page can't reach engine |
| Tumbller MCP server | Anuraj's machine | Until Anuraj closes it | Real robot unavailable |

**6 processes on 2 people's laptops.** Any one dying breaks the demo.

### What's already stable (no human needed)

| Component | Hosted on | Always on? |
|-----------|-----------|-----------|
| Demo page (mcp-demo-3) | here.now (yakrobot.bid) | Yes |
| Cloudflare Worker (API) | Cloudflare Workers | Yes |
| Robot registrations | Base mainnet (ERC-8004) | Yes |
| Subgraph indexing | The Graph | Yes |
| USDC contracts | Base mainnet | Yes |
| Stripe API | Stripe | Yes |

---

## Tasks to complete: Stable tunnel URLs

### When yakrover.online is active on Cloudflare:

- [ ] `cloudflared tunnel login`
- [ ] `cloudflared tunnel create yakrover-mcp`
- [ ] `cloudflared tunnel create yakrover-fleet`
- [ ] `cloudflared tunnel route dns yakrover-mcp mcp.yakrover.online`
- [ ] `cloudflared tunnel route dns yakrover-fleet fleet.yakrover.online`
- [ ] Create `~/.cloudflared/config.yml` with both ingress rules
- [ ] Test: `cloudflared tunnel run yakrover-mcp` → both subdomains work
- [ ] Update Berlin robots' on-chain MCP endpoint to `https://fleet.yakrover.online/fakerover/mcp`
- [ ] Update Tumbller MCP endpoint to `https://fleet.yakrover.online/tumbller/mcp` (coordinate with Anuraj)
- [ ] Update demo-3 default tunnel URL to `https://mcp.yakrover.online`
- [ ] Update CORS in `mcp_server.py` to allow `yakrover.online`

---

## Path to "always on" (no terminals needed)

### Option A: Cloud VPS (simplest, ~$5-10/month)

Deploy both servers to a single VPS (Fly.io, Railway, or Render):

```
VPS ($5/mo)
├── Marketplace MCP server (:8001)
├── Fakerover simulator (:8080)
├── Robot MCP server (:8000)
└── Cloudflared tunnel (stable URLs)
```

**Pros:** Single machine, one deploy, always on, ~$5/month on Fly.io
**Cons:** Fakerover simulator runs on the VPS (not on a real robot). Tumbller still needs Anuraj's machine.
**Effort:** Half a day. Dockerfile + fly.toml.

### Option B: Cloudflare Workers for the marketplace (free)

The marketplace MCP server (`mcp_server.py`) is Python/Starlette. It can't run directly on CF Workers (which is JS). But we could:
- Port the REST API part (`/api/tool/{name}`) to the existing Cloudflare Worker
- The worker already calls the MCP server — it could call the tools directly instead
- Removes the marketplace server entirely

**Pros:** Free, no server to manage, always on
**Cons:** Major rewrite. Python auction engine would need to be ported to JS or called via HTTP from the worker. The MCP server also does on-chain discovery at startup.
**Effort:** Several days.

### Option C: Hybrid — VPS for servers, Cloudflare for routing

```
Cloudflare (always on, free)
├── yakrobot.bid → here.now (demo pages)
├── Worker → API endpoints (chat, payment, IPFS)
└── Tunnel → VPS

VPS (Fly.io, $5/mo)
├── mcp_server.py (marketplace auction engine)
├── fakerover simulator
├── robot MCP server (for FakeRovers)
└── Stable hostname via Cloudflare Tunnel
```

Tumbller stays on Anuraj's machine with its own tunnel.

**Pros:** Clean separation. Marketplace is always on. Real robots connect when available.
**Cons:** Still need VPS. Tumbller availability depends on Anuraj.
**Effort:** Half a day.

### Recommendation: Option C (Hybrid)

1. **Immediate (this week):** Set up yakrover.online tunnel URLs (already in progress)
2. **Soon:** Deploy marketplace + fakerover to Fly.io ($5/mo). Single `Dockerfile` with all 3 processes.
3. **Later:** Anuraj sets up a stable tunnel for Tumbller (or deploys to a Raspberry Pi with always-on tunnel)

End state:
- Visitor opens demo → everything works, no setup
- Real Tumbller available when Anuraj's machine is on (graceful fallback to FakeRovers)
- Marketplace + FakeRovers always on via Fly.io

---

## Remaining faux/fragile items in the demo

### 1. Auction uses mock construction operators for non-sensor tasks
**Status:** The 7 Michigan construction survey operators (Great Lakes Aerial, Wolverine Survey, etc.) are in-memory mock robots. They don't exist on-chain and don't have MCP endpoints.
**Impact:** Low — the demo only runs env_sensing tasks. Construction operators are filtered out.
**Fix:** Register construction survey operators on-chain (future, when real operators onboard).

### 2. Delivery schema is hardcoded in the demo page
**Status:** `DELIVERY_SCHEMA` is a JS constant in the HTML. It matches what the fakerover/Tumbller returns but isn't read from the task spec dynamically.
**Impact:** Low — works for env_sensing. Would need updating for other task types.
**Fix:** Read schema from the auction engine's task spec response.

### 3. IPFS upload uses demo data, not signed by robot
**Status:** The demo uploads the delivery payload to IPFS via the worker's `/api/upload-delivery`. The robot doesn't sign or upload — the marketplace does.
**Impact:** Medium — in production, the robot should upload to IPFS and provide the CID. The marketplace verifies.
**Fix:** Robot's `robot_execute_task` returns an IPFS CID. Marketplace verifies it.

### 4. QA validation is client-side only
**Status:** Schema validation runs in the browser (JavaScript `validateSchema()`). The server-side QA (`auction_confirm_delivery`) also validates, but the demo shows the client-side result.
**Impact:** Low — both use the same logic. Client-side is for display, server-side is authoritative.

### 5. No on-chain settlement record
**Status:** USDC transfers happen on-chain, but there's no on-chain record linking the payment to the task/robot/delivery. Just raw USDC transfers.
**Impact:** Medium — no on-chain proof that payment was for a specific task.
**Research needed:** Design an on-chain settlement broadcast mechanism. Options to investigate:
- ERC-8004 metadata update with settlement hash after payment
- Dedicated settlement event emitted by the escrow contract (RobotTaskEscrow.sol, deferred to v1.5)
- Off-chain attestation (EAS on Base) linking task_id + payment_tx + delivery_cid + agent_id
- Simple on-chain memo/log transaction with settlement data
See `docs/DECISIONS.md` FD-1 (settlement abstraction) for architectural context.

### 6. Feedback goes to GitHub Issues only
**Status:** Demo feedback (stars + comment) creates a GitHub issue via the worker. Not posted to 8004scan or on-chain.
**Impact:** Medium — robot reputation isn't visible to future buyers on 8004scan.
**Fix (next):** POST feedback to 8004scan's feedback API for the winning robot's agent profile.
